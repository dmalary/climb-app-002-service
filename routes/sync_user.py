from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import csv
import os
import sys
import tempfile
import re

import pexpect

from services.build_sqlite import build_or_download_board_db

router = APIRouter(tags=["User Board Data"])


def get_python_bin() -> str:
    return sys.executable


class FetchBoardRequest(BaseModel):
    board: str
    username: str
    password: str | None = None


def _strip_ansi(s: str) -> str:
    # remove terminal color codes so logs are readable
    return re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", s)


@router.post("/fetch-user-board-data")
def fetch_user_board_data(data: FetchBoardRequest):
    """
    Fetch authenticated user logbook data for a board.

    Uses pexpect to handle the interactive password prompt that boardlib uses.
    If boardlib fails, we return a 500 with the captured traceback (instead of
    returning count=0 silently).
    """

    board = data.board.lower().strip()
    python_bin = get_python_bin()

    # 1) Ensure "logbook-capable" DB exists (mainly for name resolution / boardlib expectations)
    try:
        db_path = build_or_download_board_db(
            board=board,
            username=data.username,
            password=data.password,
            require="logbook",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB build failed: {str(e)}")

    if not os.path.exists(db_path):
        raise HTTPException(status_code=500, detail=f"Database not found at {db_path}")

    # 2) Temp CSV output
    tmp_fd, tmp_csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(tmp_fd)

    # 3) Run boardlib logbook via pexpect (interactive prompt)
    cmd = (
        f"{python_bin} -m boardlib logbook {board} "
        f"--username={data.username} "
        f"--database-path={db_path} "
        f"--output={tmp_csv_path}"
    )

    print("📘 Running boardlib logbook via pexpect:")
    print(" ", cmd)

    output_text = ""
    try:
        # encoding lets us read child.before directly as str
        child = pexpect.spawn(cmd, encoding="utf-8", timeout=90)

        # Some boardlib versions prompt "Password:" (case varies), sometimes with leading text.
        # We try to answer it if it appears; if it doesn't appear, we continue.
        if data.password:
            i = child.expect([r"(?i)password\s*:", pexpect.EOF, pexpect.TIMEOUT])
            if i == 0:
                child.sendline(data.password)
                # then wait for completion
                child.expect(pexpect.EOF)

        else:
            # No password provided; just run to completion
            child.expect(pexpect.EOF)

        output_text = child.before or ""
    except Exception as e:
        try:
            if os.path.exists(tmp_csv_path):
                os.remove(tmp_csv_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"boardlib logbook failed (pexpect): {str(e)}")
    finally:
        try:
            child.close()
        except Exception:
            pass

    output_text_clean = _strip_ansi(output_text)

    # 4) Validate CSV actually exists + has content
    if not os.path.exists(tmp_csv_path):
        raise HTTPException(
            status_code=500,
            detail=(
                "boardlib did not produce CSV output.\n\n"
                f"board={board} user={data.username}\n"
                f"db={db_path}\n\n"
                "boardlib output (first 3000 chars):\n"
                f"{output_text_clean[:3000]}"
            ),
        )

    # If boardlib crashed, it often leaves a 0-byte file behind.
    file_size = os.path.getsize(tmp_csv_path)
    if file_size == 0:
        # This is the “silent empty csv” failure mode you’re seeing
        try:
            os.remove(tmp_csv_path)
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=(
                "boardlib produced EMPTY CSV.\n\n"
                f"board={board} user={data.username}\n"
                f"db={db_path}\n\n"
                "boardlib output (first 3000 chars):\n"
                f"{output_text_clean[:3000]}"
            ),
        )

    # 5) Parse CSV → JSON
    logbook: list[dict] = []
    try:
        with open(tmp_csv_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            print("🧾 CSV headers:", headers)

            for row in reader:
                # Defensive: boardlib *should* include climb_name, but it’s the crash point right now.
                # If it’s missing in some future format, skip row safely.
                date = (row.get("date") or "").strip()
                climb_name = (row.get("climb_name") or "").strip()

                if not date or not climb_name:
                    continue

                tries_total = (row.get("tries_total") or "1").strip()
                sessions_count = (row.get("sessions_count") or "1").strip()

                row["board_attempt_id"] = f"{date}|{climb_name}|{tries_total}|{sessions_count}"
                logbook.append(row)

    finally:
        try:
            os.remove(tmp_csv_path)
        except Exception:
            pass

    if logbook:
        print("🧪 Sample attempt:", logbook[0])
    else:
        print("⚠️ No logbook rows parsed (CSV existed but rows missing required fields).")

    return {
        "board": board,
        "entries": logbook,
        "count": len(logbook),
    }
