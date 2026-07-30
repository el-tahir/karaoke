"""
fetches line-level synced lyrics as an .lrc file
"""

import logging
import shutil
from pathlib import Path

import syncedlyrics

from karaoke.errors import KaraokeError
from karaoke.models import Song

log = logging.getLogger(__name__)

_PROVIDERS = ["lrclib", "netease"]

def get_lyrics(song: Song, work_dir: Path, lrc_file: Path | None = None) -> Path:
    out = work_dir / "lyrics.lrc"
    tmp = work_dir / "lyrics.tmp.lrc"

    if lrc_file is not None:
        if not (lrc_file.exists() and lrc_file.stat().st_size):
            raise KaraokeError(f"no lyrics in {lrc_file}")
        shutil.copyfile(lrc_file, tmp) # bytes as-is; encoding is lrc.py's problem
        tmp.replace(out) # an explicit --lrc-file wins over a cached fetch
        log.info("lyrics copied from %s", lrc_file)
        return out

    if out.exists() and out.stat().st_size:
        log.info("lyrics already fetched: %s", out)
        return out

    query = f"{song.artist} {song.track}"
    log.info("searching lyrics for %s", query)

    try:
        lrc = syncedlyrics.search(query, synced_only=True, providers=_PROVIDERS)
    except Exception as e:
        raise KaraokeError(f"lyrics searched failed for {query} : {e}") from e


    if not (lrc and lrc.strip()):
        raise KaraokeError(f"no synced lyrics found for {query}; pass --lrc-file to supply your own")

    tmp.write_text(lrc, encoding="utf-8")
    tmp.replace(out)
    log.info("lyrics ready : %s (%d lines)", out, len(lrc.splitlines()))

    return out
