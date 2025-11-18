import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import your routes
from routes.user_board_routes import router as import_private_router
from routes.sync_public import router as sync_public_router

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

# --- Root route (health check) ---
@app.get("/")
def root():
    return {"message": "Board service running"}

# --- Register routers ---
app.include_router(import_private_router)
app.include_router(sync_public_router)