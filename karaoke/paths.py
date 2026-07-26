import re
from pathlib import Path

_STRIP = re.compile(r"[^\w\s-]")
_COLLAPSE = re.compile(r"[\s_]+")

def slug(artist: str, track: str) -> str:
    cleaned = _STRIP.sub("", f"{artist} {track}")
    collapsed = _COLLAPSE.sub("_", cleaned)
    return collapsed.strip("_") or "untitled"

def work_dir_for(root: Path, artist: str, track: str) -> Path:
    return root / slug(artist, track)
