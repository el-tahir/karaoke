"""Lyrics fetching utility.

Uses `syncedlyrics` to retrieve time-synchronized LRC lyrics and saves them to a file.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import logging

import syncedlyrics

from . import config
from . import metadata
from .cache import cache_manager

logger = logging.getLogger(__name__)

def fetch_lrc(track: str, artist: str, output_dir: Path = config.LYRICS_DIR) -> Path:
    """Fetch lyrics via syncedlyrics and save as .lrc.

    Returns the path to the saved LRC file. Raises RuntimeError if lyrics not found.
    """
    # Check cache first (with error handling)
    try:
        cached_lyrics = cache_manager.get_cached_lyrics(track, artist)
        if cached_lyrics:
            return cached_lyrics
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Cache check failed, proceeding with lyrics fetch: {e}")
    
    search_query = f"{track} {artist}"
    print(f"Searching for lyrics: {search_query}")
    lrc_content: Optional[str] = syncedlyrics.search(search_query, enhanced=True)

    if not lrc_content:
        raise RuntimeError(f"No synchronized lyrics found for '{track}' by '{artist}'.")

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = metadata.sanitize_filename(track) or "lyrics"
    lrc_path = output_dir / f"{filename}.lrc"
    lrc_path.write_text(lrc_content, encoding="utf-8")
    print(f"Saved lyrics to {lrc_path}")
    
    # Cache the lyrics (with error handling)
    try:
        cache_manager.cache_lyrics(track, artist, lrc_path)
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Failed to cache lyrics, but fetch was successful: {e}")
    
    return lrc_path
 