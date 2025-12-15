import os
from dotenv import load_dotenv
import subprocess
import sys
from supabase import create_client, Client

load_dotenv()

supabase_url: str = os.environ.get("PUBLIC_SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_url or not supabase_key:
    raise RuntimeError(
        "Supabase URL or KEY not found. Check .env and FastAPI environment."
    )

supabase: Client = create_client(supabase_url, supabase_key)

CACHE_DIR = "server/board_dbs"


# ---------------------------------------------------
#  Ensure FastAPI uses correct python interpreter
# ---------------------------------------------------
def get_python_bin():
    return sys.executable


# ---------------------------------------------------
#  Main logic
# ---------------------------------------------------
def build_or_download_board_db(board: str, username: str | None = None, password: str | None = None) -> str:
    """
    Returns local path to the SQLite DB by:
    1. Checking local cache
    2. Downloading from Supabase cache
    3. Building using boardlib CLI if needed
    Supports optional username/password for boards that require login.
    """

    os.makedirs(CACHE_DIR, exist_ok=True)
    local_path = os.path.join(CACHE_DIR, f"{board}.db")

    # 1️⃣ Local cache
    if os.path.exists(local_path):
        print(f"✅ Local DB already exists for '{board}'")
        return local_path

    # 2️⃣ Try Supabase
    print(f"📡 Checking Supabase for cached DB: {board}.db")
    try:
        bucket = supabase.storage.from_("board-dbs")
        dl = bucket.download(f"{board}.db")
    except Exception as e:
        print(f"❌ Supabase download error (connection or permissions): {e}")
        dl = None

    if dl:
        try:
            # supabase-py returns bytes directly
            if isinstance(dl, bytes):
                with open(local_path, "wb") as f:
                    f.write(dl)
                print(f"⬇️ Downloaded cached DB for '{board}'")
                return local_path

            # If SDK returns an object instead (older versions)
            if hasattr(dl, "data") and dl.data:
                with open(local_path, "wb") as f:
                    f.write(dl.data)
                print(f"⬇️ Downloaded cached DB for '{board}'")
                return local_path

        except Exception as e:
            print(f"❌ Failed writing Supabase DB to disk: {e}")

    print(f"📭 No Supabase cache found for '{board}'. Building new DB…")

    # 3️⃣ Build using boardlib CLI
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

    # Prepare password for stdin prompt
    stdin_input = f"{password}\n" if password else None

    print(f"🛠 Running boardlib:\n{' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        input=stdin_input,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ boardlib stdout:", result.stdout)
        print("❌ boardlib stderr:", result.stderr)
        raise RuntimeError(f"boardlib failed for board '{board}'")

    print(f"🎉 Successfully built DB for '{board}' at {local_path}")

    # 4️⃣ Upload to Supabase
    try:
        with open(local_path, "rb") as f:
            bucket.upload(
                f"{board}.db",
                f,
                upsert=True,
                content_type="application/octet-stream"
            )
        print(f"☁️ Uploaded '{board}.db' to Supabase cache")
    except Exception as e:
        print(f"⚠️ Warning: failed to upload DB to Supabase cache: {e}")

    return local_path