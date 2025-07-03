from __future__ import annotations

from pathlib import Path
import argparse
import logging
import sys
import os

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
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
    # Allow other potential frontend URLs
    "https://*.run.app",
]

# In production, you might also want to allow all .run.app domains
# For now, we'll be explicit about the frontend domain
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Explicitly declared origins
    allow_origin_regex=r"https://.*\\.run\\.app",  # Fallback for other Cloud Run previews
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
    cookies: str = "",
):
    """Kick off the karaoke generation pipeline and stream progress via SSE.

    Query parameters (at least one source must be provided):
    - youtube_url: URL to a YouTube video
    - track / artist: Metadata used to search YouTube when no URL is given
    - cookies: Optional YouTube cookies (Netscape format) for authentication
    """
    # Build args namespace compatible with the existing pipeline logic
    args = argparse.Namespace(
        youtube_url=youtube_url or None,
        file=None,
        track=track or None,
        artist=artist or None,
        resolution=None,
        background=None,
        cookies=cookies or None,
    )

    # Lazy-import to avoid long startup times
    from karaoke.api_pipeline import run_pipeline_streaming  # noqa: WPS433 – runtime import

    generator = run_pipeline_streaming(args)
    return StreamingResponse(generator, media_type="text/event-stream")


@app.get("/cookie-instructions", response_class=HTMLResponse)
async def get_cookie_instructions():
    """Return instructions for setting up YouTube cookies."""
    from karaoke.cookies_helper import get_cookie_instructions
    instructions = get_cookie_instructions().replace('\n', '<br>')
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Cookies Setup</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            pre {{ background-color: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            .warning {{ color: #d63384; font-weight: bold; }}
            .tip {{ color: #0d6efd; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>🍪 YouTube Cookies Setup Guide</h1>
        <div style="white-space: pre-line;">{instructions}</div>
        
        <h2>🧪 Test Your Setup</h2>
        <p>After setting up cookies, test with a YouTube URL that was previously blocked:</p>
        <pre>
curl -X GET "https://your-backend-url/generate-karaoke?youtube_url=https://youtu.be/0vrBBRjk2fc&track=smuckers&artist=tyler+the+creator"
        </pre>
        
        <p><a href="/">← Back to API</a></p>
    </body>
    </html>
    """
    return html_content


@app.post("/validate-cookies")
async def validate_cookies(request: Request):
    """Validate YouTube cookies format."""
    try:
        body = await request.body()
        cookies_content = body.decode('utf-8')
        
        from karaoke.cookies_helper import validate_cookies
        is_valid = validate_cookies(cookies_content)
        
        return {
            "valid": is_valid,
            "message": "Cookies format looks correct!" if is_valid else "Invalid cookies format. Please check the instructions.",
            "has_netscape_header": cookies_content.startswith("# Netscape HTTP Cookie File"),
            "line_count": len([line for line in cookies_content.split('\n') if line.strip()]),
        }
    except Exception as e:
        return {"valid": False, "message": f"Error validating cookies: {str(e)}"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True) 