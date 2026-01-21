import os
import sys
import sqlite3
import subprocess
from config import get_settings
from supabase import create_client, Client

# ---------------------------------------------------
#  Environment
# ---------------------------------------------------

settings = get_settings()

SUPABASE_URL = settings.public_supabase_url
SUPABASE_KEY = settings.supabase_service_role_key

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase URL or KEY not found")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CACHE_DIR = "server/board_dbs"
BUCKET_NAME = "board-dbs"

# Boards that REQUIRE auth for full DBs
AUTH_REQUIRED_BOARDS = {"kilter", "moon"}


# ---------------------------------------------------
#  Utilities
# ---------------------------------------------------

def get_python_bin() -> str:
    return sys.executable


def get_tables(db_path: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    conn.close()
    return tables


def has_image_capability(db_path: str) -> bool:
    """
    Required for:
    - images
    - layout rendering
    """
    try:
        tables = get_tables(db_path)
        return "product_sizes_layouts_sets" in tables
    except Exception:
        return False


def has_logbook_capability(db_path: str) -> bool:
    """
    Required for:
    - logbook
    - attempts
    - climb name resolution
    """
    try:
        tables = get_tables(db_path)
        return {
            "climbs",
            "product_sizes_layouts_sets",
        }.issubset(tables)
    except Exception:
        return False
    
def has_public_capability(db_path: str) -> bool:
    """
    Required for:
    - problem definitions
    - hold coordinates
    - image overlays
    """
    try:
        tables = get_tables(db_path)
        return {
            "problems",
            "problem_holds",
            "holds",
            "product_sizes_layouts_sets",
        }.issubset(tables)
    except Exception:
        return False

def has_catalog_capability(db_path: str) -> bool:
    try:
        tables = get_tables(db_path)
        return {
            "climbs",
            "product_sizes_layouts_sets",
        }.issubset(tables)
    except Exception:
        return False

def has_geometry_capability(db_path: str) -> bool:
    try:
        tables = get_tables(db_path)
        return {
            "problems",
            "problem_holds",
            "holds",
        }.issubset(tables)
    except Exception:
        return False

def download_from_supabase(board: str, local_path: str) -> bool:
    try:
        bucket = supabase.storage.from_(BUCKET_NAME)
        data = bucket.download(f"{board}.db")

        if isinstance(data, bytes):
            with open(local_path, "wb") as f:
                f.write(data)
            return True

        if hasattr(data, "data") and data.data:
            with open(local_path, "wb") as f:
                f.write(data.data)
            return True

    except Exception as e:
        print(f"⚠️ Supabase download failed: {e}")

    return False


def upload_to_supabase(board: str, local_path: str):
    try:
        with open(local_path, "rb") as f:
            supabase.storage.from_(BUCKET_NAME).upload(
                f"{board}.db",
                f,
                upsert=True,
                content_type="application/octet-stream",
            )
        print(f"☁️ Uploaded '{board}.db' to Supabase cache")
    except Exception as e:
        print(f"⚠️ Supabase upload failed: {e}")


# ---------------------------------------------------
#  Main entry point
# ---------------------------------------------------

def build_or_download_board_db(
    board: str,
    *,
    # user_id: str,          # 👈 NEW (Clerk user id)
    username: str | None = None,
    password: str | None = None,
    # require: str = "logbook",  # "images" | "logbook" | "public"
    require: str = "catalog"  # layouts | catalog | geometry | logbook
) -> str:
    """
    Returns path to a DB that satisfies required capability.

    require:
      - "images"   → image/layout tables
      - "logbook"  → climbs + layouts (default)
    """

    os.makedirs(CACHE_DIR, exist_ok=True)
    local_path = os.path.join(CACHE_DIR, f"{board}.db")
    # user_dir = os.path.join(CACHE_DIR, "users", user_id)
    # os.makedirs(user_dir, exist_ok=True)

    # local_path = os.path.join(user_dir, f"{board}.db")

#     If you are on:

# Vercel serverless → ❌ breaks

# ephemeral Docker → ❌ breaks

# You need:

# persistent volume

# OR upload user DBs to object storage (S3) on shutdown/startup

    def is_valid(db_path: str) -> bool:
        # if require == "images":
        if require == "layouts":
            return has_image_capability(db_path)
        if require == "catalog":
            return has_catalog_capability(db_path)
        if require == "geometry":
            return has_geometry_capability(db_path)
        # if require == "public":
        #     return has_public_capability(db_path)
        return has_logbook_capability(db_path)

    # ---------------------------------------------------
    # 1️⃣ Local cache
    # ---------------------------------------------------
    if os.path.exists(local_path):
        if is_valid(local_path):
            print(f"✅ Using local {require}-capable DB for '{board}'")
            return local_path

        print(f"♻️ Local DB missing {require} capability, rebuilding")
        os.remove(local_path)

    # ---------------------------------------------------
    # 2️⃣ Supabase cache
    # ---------------------------------------------------
    # print(f"📡 Checking Supabase cache for '{board}.db'")
    # if download_from_supabase(board, local_path):
    #     if is_valid(local_path):
    #         print(f"⬇️ Using Supabase {require}-capable DB for '{board}'")
    #         return local_path

    #     print(f"🧨 Supabase DB missing {require} capability, discarding")
    #     os.remove(local_path)

    # ---------------------------------------------------
    # 3️⃣ Build via boardlib
    # ---------------------------------------------------
    if board in AUTH_REQUIRED_BOARDS and (not username or not password):
        raise RuntimeError(
            f"Board '{board}' requires username/password for full DB"
        )

    python_bin = get_python_bin()
    cmd = [
        python_bin,
        "-m",
        "boardlib",
        "database",
        board,
        local_path,
    ]

    if username:
        cmd.append(f"--username={username}")

    stdin_input = f"{password}\n" if password else None

    print("🛠 Running boardlib:")
    print(" ", " ".join(cmd))

    result = subprocess.run(
        cmd,
        input=stdin_input,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("❌ boardlib stdout:\n", result.stdout)
        print("❌ boardlib stderr:\n", result.stderr)
        raise RuntimeError("boardlib database build failed")

    # ---------------------------------------------------
    # 4️⃣ Validate built DB
    # ---------------------------------------------------
    if not is_valid(local_path):
        raise RuntimeError(
            f"boardlib built DB without required '{require}' capability. "
            "Authentication likely failed."
        )

    print(f"🎉 Successfully built {require}-capable DB for '{board}'")

    # ---------------------------------------------------
    # 5️⃣ Cache to Supabase
    # ---------------------------------------------------
    upload_to_supabase(board, local_path) 
    # Disable Supabase caching for authenticated DBs. Only cache: public, catalog, geometry

    return local_path
