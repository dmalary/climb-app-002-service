import os
import sys
import sqlite3
import subprocess
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------
#  Environment
# ---------------------------------------------------

load_dotenv()

SUPABASE_URL = os.environ.get("PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Supabase URL or KEY not found. Check .env and FastAPI environment."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CACHE_DIR = "server/board_dbs"
BUCKET_NAME = "board-dbs"

# Boards that REQUIRE authentication to build a complete DB
AUTH_REQUIRED_BOARDS = {"kilter", "moon"}


# ---------------------------------------------------
#  Utilities
# ---------------------------------------------------

def get_python_bin() -> str:
    """Ensure FastAPI uses the same Python interpreter."""
    return sys.executable


def has_required_image_tables(db_path: str) -> bool:
    """
    Verify DB contains tables required for image + layout operations.
    Prevents using partially-built (unauthenticated) DBs.
    """
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            AND name='product_sizes_layouts_sets'
        """)
        exists = cur.fetchone() is not None
        conn.close()
        return exists
    except Exception:
        return False


def download_from_supabase(board: str, local_path: str) -> bool:
    """Attempt to download cached DB from Supabase."""
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
    """Upload DB to Supabase cache."""
    try:
        with open(local_path, "rb") as f:
            supabase.storage.from_(BUCKET_NAME).upload(
                f"{board}.db",
                f,
                upsert=True,
                content_type="application/octet-stream"
            )
        print(f"☁️ Uploaded '{board}.db' to Supabase cache")
    except Exception as e:
        print(f"⚠️ Failed to upload DB to Supabase: {e}")


# ---------------------------------------------------
#  Main entry point
# ---------------------------------------------------

def build_or_download_board_db(
    board: str,
    username: str | None = None,
    password: str | None = None
) -> str:
    """
    Returns a local path to a valid SQLite DB for a board.

    Strategy:
    1. Use local cache if valid
    2. Download from Supabase cache if valid
    3. Build via boardlib CLI (with auth if required)
    4. Upload validated DB back to Supabase
    """

    os.makedirs(CACHE_DIR, exist_ok=True)
    local_path = os.path.join(CACHE_DIR, f"{board}.db")

    # ---------------------------------------------------
    # 1️⃣ Local cache (validated)
    # ---------------------------------------------------
    if os.path.exists(local_path):
        if board in AUTH_REQUIRED_BOARDS:
            if has_required_image_tables(local_path):
                print(f"✅ Valid authenticated DB found locally for '{board}'")
                return local_path
            else:
                print(f"♻️ Incomplete DB detected for '{board}', rebuilding…")
                os.remove(local_path)
        else:
            print(f"✅ Local DB found for '{board}'")
            return local_path

    # ---------------------------------------------------
    # 2️⃣ Supabase cache
    # ---------------------------------------------------
    print(f"📡 Checking Supabase cache for '{board}.db'")
    if download_from_supabase(board, local_path):
        if board in AUTH_REQUIRED_BOARDS:
            if has_required_image_tables(local_path):
                print(f"⬇️ Downloaded valid authenticated DB for '{board}'")
                return local_path
            else:
                print(f"🧨 Supabase DB incomplete for '{board}', discarding")
                os.remove(local_path)
        else:
            print(f"⬇️ Downloaded DB for '{board}'")
            return local_path

    # ---------------------------------------------------
    # 3️⃣ Build DB via boardlib
    # ---------------------------------------------------
    if board in AUTH_REQUIRED_BOARDS and (not username or not password):
        raise RuntimeError(
            f"Board '{board}' requires username/password to build full DB"
        )

    python_bin = get_python_bin()
    cmd = [
        python_bin,
        "-m",
        "boardlib",
        "database",
        board,
        local_path
    ]

    if username:
        cmd += ["--username", username]

    stdin_input = f"{password}\n" if password else None

    print("🛠 Running boardlib:")
    print(" ", " ".join(cmd))

    result = subprocess.run(
        cmd,
        input=stdin_input,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ boardlib stdout:\n", result.stdout)
        print("❌ boardlib stderr:\n", result.stderr)
        raise RuntimeError(f"boardlib failed for board '{board}'")

    # ---------------------------------------------------
    # 4️⃣ Validate built DB
    # ---------------------------------------------------
    if board in AUTH_REQUIRED_BOARDS:
        if not has_required_image_tables(local_path):
            raise RuntimeError(
                f"boardlib built an incomplete DB for '{board}'. "
                "Authentication likely failed."
            )

    print(f"🎉 Successfully built DB for '{board}'")

    # ---------------------------------------------------
    # 5️⃣ Upload to Supabase
    # ---------------------------------------------------
    upload_to_supabase(board, local_path)

    return local_path
