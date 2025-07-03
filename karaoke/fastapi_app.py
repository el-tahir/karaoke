# /karaoke/fastapi_app.py
import argparse, asyncio, logging, shutil
from pathlib import Path
from typing import Optional
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from . import api_pipeline, config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
config.ensure_dirs_exist()
app = FastAPI(title="Karaoke-O-Matic API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
BASE_DIR = Path(__file__).parent
app.mount("/videos", StaticFiles(directory=config.OUTPUT_DIR), name="videos")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
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
    if not youtube_url and not (file and file.filename):
        raise HTTPException(status_code=400, detail="Either a YouTube URL or an audio file must be provided.")
    file_path_str = None
    if file and file.filename:
        upload_dir = config.DOWNLOADS_DIR
        safe_filename = Path(file.filename).name
        file_path = upload_dir / safe_filename
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_path_str = str(file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
        finally:
            file.file.close()
    args = argparse.Namespace(youtube_url=youtube_url, file=file_path_str, track=track, artist=artist, resolution=resolution, background=background, cookies=None)
    return StreamingResponse(api_pipeline.run_pipeline_streaming(args), media_type="text/event-stream")