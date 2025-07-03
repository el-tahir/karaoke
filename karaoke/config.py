"""Centralized configuration for the karaoke pipeline."""
from pathlib import Path

# --- Directory Paths ---
BASE_DIR = Path(__file__).parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
LYRICS_DIR = BASE_DIR / "lyrics"
SUBS_DIR = BASE_DIR / "subtitles"
STEMS_DIR = BASE_DIR / "stems"
OUTPUT_DIR = BASE_DIR / "output_videos"
CACHE_DIR = BASE_DIR / ".cache"

# --- Video Settings ---
DEFAULT_RESOLUTION = "1280x720"
DEFAULT_BACKGROUND = "black"

# --- Audio Settings ---
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"}

# --- Cache Settings ---
ENABLE_CACHE = True  # Set to False to disable caching entirely
CACHE_MAX_SIZE_GB = 10.0  # Maximum cache size in GB (approximate)

# --- YouTube Downloader Settings ---
YDL_OPTS = {
    "format": "bestaudio/best",
    "outtmpl": str(DOWNLOADS_DIR / "%(title)s.%(ext)s"),
    "quiet": True,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "http_headers": {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    },
    "extractor_retries": 3,
    "fragment_retries": 3,
    "socket_timeout": 30,
    "retries": 5,
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }
    ],
}

def ensure_dirs_exist():
    """Create all necessary output directories."""
    for path in [DOWNLOADS_DIR, LYRICS_DIR, SUBS_DIR, STEMS_DIR, OUTPUT_DIR, CACHE_DIR]:
        path.mkdir(exist_ok=True)

ensure_dirs_exist()
