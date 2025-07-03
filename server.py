from __future__ import annotations

from pathlib import Path
import argparse
import logging
import sys
import os

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Directory where rendered videos are stored – must match api_pipeline.OUTPUT_DIR
OUTPUT_DIR = Path("output_videos")
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Karaoke Generator API")

# Configure CORS for both local development and production
allowed_origins = [
    "http://localhost:3000", 
    "http://127.0.0.1:3000",
    "https://karaoke-frontend-620262589404.us-east4.run.app",  # Your deployed frontend
]

# In production, you might also want to allow all .run.app domains
# For now, we'll be explicit about the frontend domain
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the finished videos so the frontend can download/stream them
app.mount("/videos", StaticFiles(directory=str(OUTPUT_DIR)), name="videos")

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

@app.get("/generate-karaoke")
async def generate_karaoke(
    request: Request,
    youtube_url: str = "",
    track: str = "",
    artist: str = "",
):
    """Kick off the karaoke generation pipeline and stream progress via SSE.

    Query parameters (at least one source must be provided):
    - youtube_url: URL to a YouTube video
    - track / artist: Metadata used to search YouTube when no URL is given
    """
    # Build args namespace compatible with the existing pipeline logic
    args = argparse.Namespace(
        youtube_url=youtube_url or None,
        file=None,
        track=track or None,
        artist=artist or None,
        resolution=None,
        background=None,
    )

    # Lazy-import to avoid long startup times
    from karaoke.api_pipeline import run_pipeline_streaming  # noqa: WPS433 – runtime import

    generator = run_pipeline_streaming(args)
    return StreamingResponse(generator, media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True) 