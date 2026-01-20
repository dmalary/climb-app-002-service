from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import os
import sys
from typing import List
from services.build_sqlite import build_or_download_board_db

router = APIRouter(tags=["Public Board Data"])

def get_python_bin():
    """
    Returns the path to the active Python binary (prefer venv Python 3.14 if available).
    """
    python_bin = sys.executable
    if os.path.exists(python_bin):
        return python_bin
    return "/usr/bin/python3.14"

# --- Request model ---
class SyncImagesRequest(BaseModel):
    board: str
    username: str | None = None
    password: str | None = None

@router.post("/fetch-board-images")
def fetch_board_images(payload: SyncImagesRequest):
    """
    Fetch images for a given board. Builds or downloads the SQLite DB first (supports username/password),
    then runs the boardlib images command and caches images in data/boards/<board>/images.
    """
    board = payload.board.lower().strip()
    username = payload.username
    password = payload.password

    try:
        # Step 1: Ensure DB exists
        db_path = build_or_download_board_db(board=board, username=username, password=password, require="layouts")
        if not os.path.exists(db_path):
            raise HTTPException(status_code=500, detail=f"DB file not found at {db_path}")

        # Step 2: Prepare images directory
        images_dir = os.path.join("data", "boards", board, "images")
        os.makedirs(images_dir, exist_ok=True)

        # If images already exist, skip fetching
        existing_images = [
            f for f in os.listdir(images_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        if existing_images:
            return {
                "board": board,
                "status": "cached",
                "image_count": len(existing_images),
                "sample": existing_images[:5]
            }

        # Step 3: Run boardlib images command
        python_bin = get_python_bin()
        cmd = [
            python_bin, "-m", "boardlib",
            "images",
            board,
            db_path,
            images_dir
        ]
        # if username:
        #     cmd += ["--username", username]

        # check if terminal prompt for pass, if yes then update re sync_user

        # stdin_input = f"{password}\n" if password else None
        stdin_input = None  # not needed

        print(f"📥 Running boardlib images: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            # input=stdin_input,
            capture_output=True,
            text=True,
            check=False
        )

        print("=== boardlib stdout ===")
        print(result.stdout)
        print("=== boardlib stderr ===")
        print(result.stderr)

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"boardlib images failed: {result.stderr or result.stdout}")

        # Step 4: List downloaded images
        downloaded_images = [
            f for f in os.listdir(images_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        return {
            "board": board,
            "status": "fetched",
            "image_count": len(downloaded_images),
            # "images": downloaded_images,
            "sample": downloaded_images[:1]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
