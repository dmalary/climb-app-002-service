from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import sqlite3
from typing import List, Dict, Any

from services.build_sqlite import build_or_download_board_db

router = APIRouter(tags=["Public Board Data"])

DEBUG = False  # ← flip to True when inspecting schemas


# ---------------------------------------------------
# Request model
# ---------------------------------------------------

class SyncPublicRequest(BaseModel):
    board: str
    username: str | None = None
    password: str | None = None


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def dict_from_cursor(cursor):
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def list_tables(conn) -> List[str]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall()]


def table_columns(conn, table: str) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    rows = cur.fetchall()
    return [
        {
            "cid": r[0],
            "name": r[1],
            "type": r[2],
            "notnull": r[3],
            "default": r[4],
            "pk": r[5],
        }
        for r in rows
    ]


def detect_pk(columns: List[str]) -> str:
    for candidate in ("id", "uuid"):
        if candidate in columns:
            return candidate
    raise RuntimeError(f"Could not detect primary key. Columns: {columns}")


# ---------------------------------------------------
# Core extractor (BOARDLIB-CORRECT + SAFE)
# ---------------------------------------------------

def extract_climb_catalog(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Required table
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}

    if "climbs" not in tables:
        conn.close()
        return []

    # Detect columns
    cur.execute("PRAGMA table_info(climbs)")
    cols = [r[1] for r in cur.fetchall()]

    # Detect PK
    pk = "id" if "id" in cols else "uuid" if "uuid" in cols else None
    if not pk:
        raise RuntimeError(f"No primary key in climbs: {cols}")

    optional = [c for c in (
        "name",
        "grade",
        "setter",
        "product_sizes_layouts_set_id",
    ) if c in cols]

    select_cols = ", ".join([pk] + optional)

    cur.execute(f"SELECT {select_cols} FROM climbs")
    climbs = [dict(r) for r in cur.fetchall()]

    conn.close()
    return climbs


# ---------------------------------------------------
# Route
# ---------------------------------------------------

@router.post("/sync-public-data")
def sync_public_board(payload: SyncPublicRequest):
    board = payload.board.lower().strip()

    try:
        db_path = build_or_download_board_db(
            board=board,
            username=payload.username,
            password=payload.password,
            require="logbook",
        )

        if not os.path.exists(db_path):
            raise HTTPException(status_code=500, detail="DB not found")

        climbs = extract_climb_catalog(db_path)

        return {
            "board": board,
            "status": "ok",
            "climb_count": len(climbs),
            "sample": climbs[:1],
            # "climbs": climbs,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
