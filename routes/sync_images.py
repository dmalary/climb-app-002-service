from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from services.build_sqlite import build_or_download_board_db
from config import get_settings

router = APIRouter(tags=["Public Board Data"])
settings = get_settings()

class SyncImagesRequest(BaseModel):
    board: str
    username: str | None = None
    password: str | None = None

def iter_images_recursive(root: str):
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                yield os.path.join(dirpath, f)


@router.post("/fetch-board-images")
def fetch_board_images(payload: SyncImagesRequest):
    """
    Fetch images for a given board. Builds or downloads the SQLite DB first (supports username/password),
    then runs the boardlib images command and caches images in data/boards/<board>/images.
    """
    board = payload.board.lower().strip()

    try:
        # 1) Ensure DB exists (needs layouts/images table)
        db_path = build_or_download_board_db(
            board=board,
            username=payload.username,
            password=payload.password,
            require="layouts",
        )
        if not os.path.exists(db_path):
            raise HTTPException(status_code=500, detail=f"DB file not found at {db_path}")

        # 2) Images root directory (BoardLib will create nested subfolders under this)
        images_dir = os.path.join(settings.data_dir, "boards", board, "images")
        os.makedirs(images_dir, exist_ok=True)

        # 3) If already cached (recursive), return cached
        existing = list(iter_images_recursive(images_dir))
        if existing:
            return {
                "board": board,
                "status": "cached",
                "image_count": len(existing),
                "sample": [os.path.relpath(existing[0], images_dir)],
            }

        # 4) Import BoardLib directly (no subprocess)
        try:
            from boardlib.api.aurora import download_images
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to import BoardLib. Is 'boardlib' installed in this env? {e}",
            )

        download_images(board, db_path, images_dir)

        downloaded = list(iter_images_recursive(images_dir))
        return {
            "board": board,
            "status": "fetched",
            "image_count": len(downloaded),
            "sample": [os.path.relpath(downloaded[0], images_dir)] if downloaded else [],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
