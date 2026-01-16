from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import csv
import sys
import tempfile
import os
import pexpect

from services.build_sqlite import build_or_download_board_db

router = APIRouter(tags=["User Board Data"])


def get_python_bin():
    return sys.executable


# ---------------------------------------------------
# Request model
# ---------------------------------------------------

class FetchBoardRequest(BaseModel):
    board: str
    username: str
    password: str | None = None


# ---------------------------------------------------
# Route
# ---------------------------------------------------

@router.post("/fetch-user-board-data")
def fetch_user_board_data(data: FetchBoardRequest):
    """
    Fetch authenticated user logbook data for a board.
    Ensures a FULL (logbook-capable) SQLite DB exists before running boardlib.
    """

    board = data.board.lower().strip()
    python_bin = get_python_bin()

    # ---------------------------------------------------
    # 1️⃣ Ensure logbook-capable DB
    # ---------------------------------------------------
    try:
        db_path = build_or_download_board_db(
            board=board,
            username=data.username,
            password=data.password,
            require="logbook",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not os.path.exists(db_path):
        raise HTTPException(
            status_code=500,
            detail=f"Database not found at {db_path}",
        )

    # ---------------------------------------------------
    # 2️⃣ Temp CSV output
    # ---------------------------------------------------
    tmp_fd, tmp_csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(tmp_fd)

    # ---------------------------------------------------
    # 3️⃣ Build boardlib logbook command
    # ---------------------------------------------------
    # cmd = [
    #     python_bin,
    #     "-m",
    #     "boardlib",
    #     "logbook",
    #     board,
    #     f"--username={data.username}",
    #     f"--database-path={db_path}",
    #     f"--output={tmp_csv_path}",
    # ]

    # stdin_input = f"{data.password}\n" if data.password else None

    # print("📘 Running boardlib logbook:")
    # print(" ", " ".join(cmd))

    # result = subprocess.run(
    #     cmd,
    #     input=stdin_input,
    #     capture_output=True,
    #     text=True,
    # )

    # print("=== boardlib stdout ===")
    # print(result.stdout)
    # print("=== boardlib stderr ===")
    # print(result.stderr)

    # if result.returncode != 0:
    #     os.remove(tmp_csv_path)
    #     raise HTTPException(
    #         status_code=500,
    #         detail=f"boardlib logbook failed: {result.stderr or result.stdout}",
    #     )

    cmd = f"{python_bin} -m boardlib logbook {board} --username={data.username} --database-path={db_path} --output={tmp_csv_path}"

    print("📘 Running boardlib logbook via pexpect:")
    print(" ", cmd)

    try:
        child = pexpect.spawn(cmd)
        if data.password:
            child.expect("Password:")  # matches boardlib prompt
            child.sendline(data.password)
        child.expect(pexpect.EOF)
        output = child.before.decode()  # capture stdout/stderr
    except Exception as e:
        os.remove(tmp_csv_path)
        raise HTTPException(status_code=500, detail=f"boardlib logbook failed: {str(e)}")

    # ---------------------------------------------------
    # 4️⃣ Parse CSV → JSON
    # ---------------------------------------------------
    if not os.path.exists(tmp_csv_path):
        raise HTTPException(
            status_code=500,
            detail="boardlib did not produce CSV output",
        )

    logbook = []
    with open(tmp_csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize fields
            date = row["date"]
            climb_name = row["climb_name"]
            tries_total = row.get("tries_total") or "1"
            sessions_count = row.get("sessions_count") or "1"

            if not date or not climb_name:
                continue  # skip malformed rows

            # Deterministic unique ID
            row["board_attempt_id"] = f"{date}|{climb_name}|{tries_total}|{sessions_count}"
            # row["board_attempt_id"] = f"{"date"}|{"climb_name"}|{"tries_total"}|{"sessions_count"}"
            
            logbook.append(row)

    os.remove(tmp_csv_path)

    print("🧪 Sample attempt:", logbook[0])

    return {
        "board": board,
        "entries": logbook,
        "count": len(logbook),
    }
