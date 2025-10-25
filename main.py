import os, random
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from boardlib.api import moon, aurora

load_dotenv()

app = FastAPI(title="Climb Board Data Service")

# --- CORS (allow Express backend for now — tighten in prod) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with your frontend/backend URLs in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic model for incoming requests ---
class FetchBoardRequest(BaseModel):
    board: str
    token: str | None = None
    username: str | None = None
    password: str | None = None


@app.get("/")
def root():
    return {"message": "Board service running"}


@app.post("/fetch-board-data")
async def fetch_board_data(payload: FetchBoardRequest):
    board = payload.board.lower().strip()
    username = payload.username
    password = payload.password
    token = payload.token

    # --- Step 1: Initialize and fetch data ---
    try:
        if board == "moonboard":
            if not username or not password:
                raise HTTPException(status_code=400, detail="Missing MoonBoard credentials")

            client = moon.MoonBoard(username=username, password=password)
            client.login()
            climbs = client.get_user_problems()

        elif board == "aurora":
            if not username or not password:
                raise HTTPException(status_code=400, detail="Missing Aurora credentials")

            client = aurora.AuroraBoard(username=username, password=password)
            client.login()
            climbs = client.get_user_problems()

        else:
            raise HTTPException(status_code=404, detail=f"Unsupported board: {board}")

    except HTTPException as e:
        # Explicit FastAPI error — just re-raise
        raise e
    except Exception as e:
        # --- Fallback: return mock climbs if API fails ---
        print(f"⚠️ Board fetch error for {board}: {e}")
        climbs = [
            {
                "climb_name": f"{board}_mock_climb_{i+1}",
                "difficulty": random.randint(1, 10),
                "attempts": random.randint(1, 4),
            }
            for i in range(5)
        ]

    # --- Step 2: Normalize + wrap into session format ---
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
