from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import subprocess
import json

router = APIRouter(tags=["Board Data"])

class FetchBoardRequest(BaseModel):
    board: str
    username: str
    database_path: str
    password: Optional[str] = None  # ✅ harmless, ignored by CLI

# def run_user_logbook(board, username, password, database_path):
def run_user_logbook(board, username, database_path):
    """
    Runs: boardlib logbook <board> --username=<username> --database-path=<db_path> --output=logbook.json
    Returns parsed JSON logbook content. Raises RuntimeError on CLI failure.
    """    
    result = subprocess.run(
        [
            "boardlib", "logbook", board,
            f"--username={username}",
            f"--database-path={database_path}",
            # f"--password={password}",
            "--output=logbook.json"
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    with open("logbook.json") as f:
        return json.load(f)

@router.post("/fetch-user-board-data")
def fetch_user(data: FetchBoardRequest):
    # logbook = run_user_logbook(data.board, data.username, data.password, data.db_path)
    logbook = run_user_logbook(
        board=data.board,
        username=data.username,
        database_path=data.database_path,
        # password=data.password
    )
    return logbook
