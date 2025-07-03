"""Handles metadata extraction and management."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple, Optional

def infer_metadata_from_filename(file_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Infer (artist, track) from a filename of the form ""artist - track.ext""."""
    stem = file_path.stem
    if " - " in stem:
        artist, track = stem.split(" - ", 1)
        return track.strip() or None, artist.strip() or None
    return None, None

def sanitize_filename(name: str) -> str:
    """Remove characters that are problematic on most file systems."""
    return "".join(c for c in name if c not in "\\/:*?""<>|").strip()
