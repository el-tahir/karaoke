# /karaoke/fastapi_app.py

import argparse
import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import api_pipeline, config

# --- Setup ---
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure all necessary directories exist
config.ensure_dirs_exist()

# FastAPI App Initialization
app = FastAPI(
    title="Karaoke-O-Matic API",
    description="API for creating karaoke videos from audio sources.",
    version="1.0.0",
)

# --- Middleware ---
# Allow Cross-Origin Resource Sharing (CORS) for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for simplicity in a demo environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static File and Template Serving ---
# Mount directories to serve generated videos and a simple frontend
app.mount("/videos", StaticFiles(directory=config.OUTPUT_DIR), name="videos")
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """Serves the main HTML user interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/run-pipeline")
async def run_pipeline_endpoint(
    youtube_url: Optional[str] = Form(None),
    track: Optional[str] = Form(None),
    artist: Optional[str] = Form(None),
    resolution: str = Form(config.DEFAULT_RESOLUTION),
    background: str = Form(config.DEFAULT_BACKGROUND),
    file: Optional[UploadFile] = File(None),
):
    """
    The main endpoint to run the karaoke pipeline.
    Accepts form data including an optional file upload.
    Streams progress back to the client using Server-Sent Events (SSE).
    """
    if not youtube_url and not file:
        raise HTTPException(status_code=400, detail="Either a YouTube URL or an audio file must be provided.")

    file_path_str = None
    if file:
        # Securely save the uploaded file to the downloads directory
        upload_dir = config.DOWNLOADS_DIR
        safe_filename = Path(file.filename).name  # Basic sanitization
        file_path = upload_dir / safe_filename
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_path_str = str(file_path)
            logger.info(f"Uploaded file saved to {file_path_str}")
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
        finally:
            file.file.close()

    # Mimic argparse.Namespace to pass arguments to the existing pipeline logic
    args = argparse.Namespace(
        youtube_url=youtube_url,
        file=file_path_str,
        track=track,
        artist=artist,
        resolution=resolution,
        background=background,
        cookies=None,  # Cookies can be added as a parameter if needed
    )

    # Return a streaming response that yields progress updates
    return StreamingResponse(api_pipeline.run_pipeline_streaming(args), media_type="text/event-stream")


def start():
    """Launches the Uvicorn server. For use with `python -m karaoke.fastapi_app`"""
    uvicorn.run("karaoke.fastapi_app:app", host="0.0.0.0", port=8000, reload=True) 