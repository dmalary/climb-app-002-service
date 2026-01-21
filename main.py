# import os
from config import get_settings

settings = get_settings()

# from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys

print("🔍 FastAPI running with Python:", sys.executable)

# Import your routes
from routes.sync_user import router as import_private_router
from routes.sync_public import router as sync_public_router
from routes.export_board import router as export_board_router
from routes.sync_images import router as sync_images_router
from routes.render_climb_image import router as render_images_router

# load_dotenv()

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
app.include_router(export_board_router)
app.include_router(sync_images_router)
app.include_router(render_images_router)