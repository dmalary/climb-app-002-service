from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
import os

from services.build_sqlite import build_or_download_board_db

router = APIRouter(tags=["Board DB Export"])

@router.get("/export-board-db")
def export_board_db(board: str = Query(...)):
    """
    Ensures the board DB exists (cached, downloaded, or built via boardlib)
    and returns it as a downloadable file.
    """
    try:
        # Build or download cached DB
        db_path = build_or_download_board_db(board)

        # Safety check
        if not os.path.exists(db_path):
            raise HTTPException(
                status_code=500,
                detail=f"DB file not found after build: {db_path}"
            )

        # Return as file download
        return FileResponse(
            path=db_path,
            filename=os.path.basename(db_path),
            media_type="application/octet-stream"
        )

    except HTTPException:
        # rethrow FastAPI-generated HTTPExceptions
        raise

    except Exception as e:
        # Log & raise clean error message
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export DB for board '{board}': {str(e)}"
        )
