from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from build_sqlite import build_local_board_db
import os

router = APIRouter(tags=["Board DB Export"])

@router.get("/export-board-db")
def export_board_db(board: str = Query(...)):
    database_path = f"{board}.db"

    build_local_board_db(board)

    if not os.path.exists(database_path):
        return {"error": "DB file not created"}

    return FileResponse(
        path=database_path,
        filename=database_path,
        media_type="application/octet-stream"
    )
