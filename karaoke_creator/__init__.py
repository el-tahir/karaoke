"""
Karaoke Creator - Generate karaoke videos from YouTube songs.

This package provides a complete pipeline for creating karaoke videos by:
1. Searching and downloading audio from YouTube
2. Separating vocals from instrumentals
3. Fetching synchronized lyrics
4. Generating subtitle tracks with karaoke effects
5. Rendering final karaoke videos
"""

__version__ = "1.0.0"
__author__ = "Eltah"

from .core.pipeline import KaraokeCreator
from .models.song_info import SongInfo
from .utils.config import Config

__all__ = ["KaraokeCreator", "SongInfo", "Config"]