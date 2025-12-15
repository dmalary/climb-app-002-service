from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import csv
import json
import sys
import tempfile
import os

router = APIRouter()

def get_python_bin():
    return sys.executable


class FetchBoardRequest(BaseModel):
    board: str
    username: str
    database_path: str
    password: str | None = None


@router.post("/fetch-user-board-data")
def fetch_user(data: FetchBoardRequest):

    python_bin = get_python_bin()

    # Temporary CSV file for output
    tmp_fd, tmp_csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(tmp_fd)

    # Build boardlib logbook command
    args = [
        python_bin, "-m", "boardlib",
        "logbook", data.board,
        f"--username={data.username}",
        f"--database-path={data.database_path}",
        f"--output={tmp_csv_path}",
        # f"--password={data.password}",
    ]

    # Prepare the password for interactive prompt
    stdin_input = f"{data.password}\n" if data.password else None

    # Call boardlib with stdin support
    result = subprocess.run(
        args,
        input=stdin_input,   # send password
        capture_output=True,
        text=True
    )

    print("=== boardlib stdout ===")
    print(result.stdout)
    print("=== boardlib stderr ===")
    print(result.stderr)

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"boardlib failed: {result.stderr}"
        )

    # Validate CSV exists
    if not os.path.exists(tmp_csv_path):
        raise HTTPException(status_code=500, detail="CSV not created")

    # Convert CSV → JSON
    logbook = []
    with open(tmp_csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            logbook.append(row)

    # Cleanup file
    os.remove(tmp_csv_path)

    return {"logbook": logbook}
