from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from services.build_sqlite import build_or_download_board_db
from services.build_climb_image import build_climb_image
from services.climb_loader import load_climb_from_db
from services.board_assets import resolve_board_image_path
import tempfile

# ---------------------------------------------------
#  Environment
# ---------------------------------------------------

load_dotenv()

SUPABASE_URL = os.environ.get("PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase URL or KEY not found")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------
# FastAPI router
# ---------------------------------------------------
router = APIRouter(tags=["Climb Images"])

class RenderClimbRequest(BaseModel):
    board: str
    climb_uuid: str
    force: bool = False

def dict_from_row(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}

@router.post("/render-climb-image")
def render_climb_image_endpoint(payload: RenderClimbRequest):
    # 0️⃣ Extract payload FIRST
    board = payload.board.lower().strip()
    climb_uuid = payload.climb_uuid
    force = payload.force

    # 1️⃣ Define storage path FIRST
    supabase_path = f"{board}/{climb_uuid}.png"

    # 2️⃣ Return cached image unless forced
    if not force:
        try:
            existing = supabase.storage.from_("climb-images").list(board)
            if any(obj["name"] == f"{climb_uuid}.png" for obj in existing):
                public_url = supabase.storage.from_("climb-images").get_public_url(
                    supabase_path
                )
                return {
                    "status": "cached",
                    "image_url": public_url,
                    "climb_uuid": climb_uuid,
                }
        except Exception:
            # Storage list failure should not crash render
            pass

    # 3️⃣ Load board DB
    db_path = build_or_download_board_db(board=board, require="layouts")

    climb = load_climb_from_db(db_path, climb_uuid)
    if not climb:
        raise HTTPException(status_code=404, detail=f"Climb {climb_uuid} not found")

    # 4️⃣ Render image locally
    local_out = f"/tmp/{climb_uuid}.png"
    base_board_img = resolve_board_image_path(board, climb)

    build_climb_image(
        base_board_path=base_board_img,
        climb=climb,
        output_path=local_out
    )

    # 5️⃣ Upload to Supabase
    with open(local_out, "rb") as f:
        file_options = {
            "content-type": "image/png",
        }

        # Only allow overwrite when explicitly forced
        if payload.force:
            file_options["x-upsert"] = "true"  # MUST be a string

        supabase.storage.from_("climb-images").upload(
            path=supabase_path,
            file=f,
            file_options=file_options,
        )



    public_url = supabase.storage.from_("climb-images").get_public_url(
        supabase_path
    )

    return {
        "status": "rendered",
        "image_url": public_url,
        "climb_uuid": climb_uuid,
    }
