from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
import os

from services.build_sqlite import build_or_download_board_db

router = APIRouter(tags=["Board DB Export"])


@router.get("/export-board-db")
def export_board_db(
    board: str = Query(..., description="Board name (e.g. tension, kilter)"),
    require: str = Query(
        "logbook",
        enum=["images", "logbook"],
        description="Required DB capability",
    ),
    username: str | None = Query(
        None,
        description="Board username (required for some boards)",
    ),
    password: str | None = Query(
        None,
        description="Board password (required for some boards)",
    ),
):
    """
    Export a validated board SQLite DB.

    - images   → image + layout tables
    - logbook  → climbs + layouts + attempts resolution
    """

    board = board.lower().strip()

    try:
        db_path = build_or_download_board_db(
            board=board,
            username=username,
            password=password,
            require=require,
        )

        if not os.path.exists(db_path):
            raise HTTPException(
                status_code=500,
                detail=f"DB file not found after build: {db_path}",
            )

        return FileResponse(
            path=db_path,
            filename=f"{board}.db",
            media_type="application/octet-stream",
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export {require} DB for board '{board}': {str(e)}",
        )
