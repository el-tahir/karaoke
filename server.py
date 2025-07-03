from __future__ import annotations

from pathlib import Path
import logging
import sys
import os

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from karaoke.pipeline import KaraokePipeline
from karaoke.config import OUTPUT_DIR

app = FastAPI(title="Karaoke Generator API")

# Configure CORS
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if frontend_url := os.getenv("FRONTEND_URL"):
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\\.run\\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/videos", StaticFiles(directory=str(OUTPUT_DIR)), name="videos")

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

@app.get("/generate-karaoke")
async def generate_karaoke(
    request: Request,
    youtube_url: str = "",
    track: str = "",
    artist: str = "",
    cookies: str = "",
):
    """Kick off the karaoke generation pipeline and stream progress via SSE."""
    pipeline = KaraokePipeline(
        youtube_url=youtube_url or None,
        track=track or None,
        artist=artist or None,
        cookies=cookies or None,
    )
    generator = pipeline.run_streaming()
    return StreamingResponse(generator, media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
 