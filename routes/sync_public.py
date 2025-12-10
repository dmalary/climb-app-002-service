from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import os
import sqlite3
from typing import List, Dict, Any
import tempfile
import json
import sys

# router = APIRouter(prefix="/sync-public", tags=["Public Board Data"])
router = APIRouter(tags=["Public Board Data"])

def get_python_bin():
    """
    Returns the path to the active Python binary (prefer venv Python 3.14 if available).
    """
    python_bin = sys.executable  # current Python running this code
    if os.path.exists(python_bin):
        return python_bin
    # fallback to system Python
    return "/usr/bin/python3.14"

# --- Request model ---
class SyncPublicRequest(BaseModel):
    board: str
    username: str = None  # optional, required for some boards (like Moonboard)

# --- Utility: extract climbs from SQLite ---
def extract_climbs_from_db(db_path: str) -> List[Dict[str, Any]]:
    """
    Opens the downloaded SQLite DB and extracts climb metadata.
    This assumes a 'climbs' or similar table exists (depends on boardlib schema).
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Dynamically inspect available tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]

    if "climbs" not in tables:
        raise ValueError(f"No 'climbs' table found in database. Found tables: {tables}")

    # cursor.execute("SELECT * FROM climbs LIMIT 10;")  # preview
    cursor.execute("SELECT * FROM climbs")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    climbs = [dict(zip(columns, row)) for row in rows]
    return climbs


# @router.post("/")
@router.post("/sync-public-data")
def sync_public_board(payload: SyncPublicRequest):
    """
    Sync the public climb database for a given board using boardlib.
    Downloads or updates the SQLite DB, parses climb data, and returns metadata.
    """
    python_bin = get_python_bin()

    board = payload.board.lower().strip()
    username = payload.username

    # Create a temporary path to store SQLite DB
    tmp_dir = tempfile.mkdtemp(prefix=f"{board}_db_")
    db_path = os.path.join(tmp_dir, f"{board}_public.sqlite")

    try:
        # --- Step 1: Build the boardlib database command ---
        cmd = [
            python_bin,
            "-m",
            "boardlib", 
            "database",
            board,
            db_path,
        ]
        if username:
            cmd += ["--username", username]

        # --- Step 2: Run the sync command ---
        print(f"📥 Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"boardlib sync failed: {result.stderr or result.stdout}",
            )

        # --- Step 3: Extract climb data from SQLite ---
        climbs = extract_climbs_from_db(db_path)

        # --- Step 4: Optionally, persist to Supabase (future) ---
        # (Add DB integration here if you want to cache climbs in your schema)

        return {
            "board": board,
            "status": "ok",
            "climb_count": len(climbs),
            "climbs": climbs,
            "sample": climbs[:1],  # return only first few climbs for preview
        }

    except subprocess.SubprocessError as e:
        raise HTTPException(status_code=500, detail=f"Subprocess error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # You can optionally delete the temp DB file here if you don’t want to keep it
        os.remove(db_path)
        pass

# extend this easily:
# Save the SQLite DB to persistent storage (/data/boards/tension.sqlite) instead of a temp dir.