from fastapi import APIRouter
from boardlib.api import moon, aurora

router = APIRouter(prefix="/fetch-board-data")

@router.get("/{board_name}")
async def fetch_board_data(board_name: str):
    if board_name.lower() == "moonboard":
        data = moonboard.fetch_data()  # example, depends on lib
    elif board_name.lower() == "aurora":
        data = aurora.fetch_data()
    else:
        return {"error": "Invalid board name"}
    return {"board": board_name, "data": data}
