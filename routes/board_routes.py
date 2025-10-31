from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import random
from boardlib.api import moon, aurora
# tension, decoy, kilter

# router = APIRouter(prefix="/fetch-board-data", tags=["Board Data"])
router = APIRouter(tags=["Board Data"])

# --- Request body model ---
class FetchBoardRequest(BaseModel):
    board: str
    token: str = None
    username: str = None
    password: str = None


# @router.post("/")
@router.post("/fetch-board-data")
def fetch_board_data(payload: FetchBoardRequest): 
    """
    Fetch climbing data for a given board (MoonBoard, Aurora, etc.)
    Optionally uses credentials if the API requires them.
    """
    board = payload.board.lower().strip()
    username = payload.username
    password = payload.password
    token = payload.token

    try:
        # --- Select and initialize board client ---
        if board == "moonboard":
            if not username or not password:
                raise HTTPException(status_code=400, detail="Missing MoonBoard credentials")

            client = moon.MoonBoard(username=username, password=password)
            client.login()
            climbs = client.get_user_problems()

        # elif board == "aurora":
        #     if not username or not password:
        #         raise HTTPException(status_code=400, detail="Missing Aurora credentials")

        #     client = aurora.AuroraBoard(username=username, password=password)
        #     # can i update this line to handle aurora.tension or .decoy, etc
        #     client.login()
        #     climbs = client.get_user_problems()

        elif board in ["aurora", "tension", "decoy", "grasshopper", "kilter", "soill", "touchstone"]:
            if not username or not password:
                raise HTTPException(status_code=400, detail="Missing Aurora credentials")

            # Get the correct host for this board
            host = aurora.HOST_BASES.get(board, "auroraboardapp") #string is a fallback

            client = aurora.AuroraBoard(username=username, password=password, host=host)
            client.login()
            climbs = client.get_user_problems()

        else:
            raise HTTPException(status_code=404, detail=f"Unsupported board: {board}")

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"⚠️ Board fetch error for {board}: {e}")
        # --- fallback mock data ---
        climbs = [
            {
                "climb_name": f"{board}_mock_climb_{i+1}",
                "difficulty": random.randint(1, 10),
                "attempts": random.randint(1, 4),
            }
            for i in range(5)
        ]

    # --- Normalize and structure session-like response ---
    sessions = [
        {
            "session_id": f"sess_{i+1}",
            "board": board,
            "date": f"2025-10-{10+i}",
            "climbs": climbs,
        }
        for i in range(2)
    ]

    return {
        "board": board,
        "status": "ok",
        "data": sessions,
    }
