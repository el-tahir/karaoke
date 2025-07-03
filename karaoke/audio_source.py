"""Handles audio input from various sources."""
from __future__ import annotations

import os
import tempfile
import time
import random
from pathlib import Path
from typing import Optional
import logging

import yt_dlp

from . import config
from .cache import cache_manager

logger = logging.getLogger(__name__)

def validate_audio_file(path_str: str) -> Path:
    """Validate that the provided path exists and is a supported audio file."""
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    if path.suffix.lower() not in config.AUDIO_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format '{path.suffix}'. Supported formats: {', '.join(config.AUDIO_EXTENSIONS)}"
        )
    return path

def download_from_youtube(url: str, cookies: Optional[str] = None) -> Path:
    """Download audio from a YouTube URL using yt-dlp."""
    # Check cache first (with error handling)
    try:
        cached_audio = cache_manager.get_cached_audio(url)
        if cached_audio:
            return cached_audio
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Cache check failed, proceeding with download: {e}")
    
    time.sleep(random.uniform(1, 3))

    opts = config.YDL_OPTS.copy()
    cookies_source = cookies or os.getenv("YOUTUBE_COOKIES")
    temp_cookie_file = None

    if cookies_source:
        if cookies_source.startswith("# Netscape HTTP Cookie File") or "\t" in cookies_source:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(cookies_source)
                opts["cookiefile"] = f.name
                temp_cookie_file = f.name
        elif Path(cookies_source).exists():
            opts["cookiefile"] = cookies_source

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info.get('_type') == 'playlist':
                if not info.get('entries'):
                    raise RuntimeError("YouTube search returned no results.")
                info = info['entries'][0]
            
            requested = info.get('requested_downloads') or []
            if requested:
                filepath = requested[0].get('filepath')
                if filepath and Path(filepath).exists():
                    audio_path = Path(filepath).resolve()
                    # Cache the downloaded audio (with error handling)
                    try:
                        cache_manager.cache_audio(url, audio_path)
                    except (FileNotFoundError, RuntimeError) as e:
                        logger.warning(f"Failed to cache audio, but download was successful: {e}")
                    return audio_path

            candidate = config.DOWNLOADS_DIR / f"{info['title']}.mp3"
            if candidate.exists():
                audio_path = candidate.resolve()
                # Cache the downloaded audio (with error handling)
                try:
                    cache_manager.cache_audio(url, audio_path)
                except (FileNotFoundError, RuntimeError) as e:
                    logger.warning(f"Failed to cache audio, but download was successful: {e}")
                return audio_path
            
            raise RuntimeError("Failed to determine downloaded file path.")

    finally:
        if temp_cookie_file:
            os.unlink(temp_cookie_file)
