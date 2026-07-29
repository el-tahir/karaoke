"""
downloads the song's audio as a 320kbps mp3
"""

import logging
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import YoutubeDLError

from karaoke.config import Config
from karaoke.errors import KaraokeError
from karaoke.models import Song
from karaoke.ydl import ydl_opts

log = logging.getLogger(__name__)

def download(song: Song, work_dir: Path, cfg: Config) -> Path:
    out = work_dir / "audio.mp3"
    if out.exists() and out.stat().st_size:
        log.info("audio already downloaded: %s", out)
        return out

    tmp = work_dir / "audio.tmp.mp3" # expected file
    tmp.unlink(missing_ok=True) # a crashed run could leave a truncated one

    opts = ydl_opts(
        cfg,
        format="bestaudio/best",
        outtmpl=str(work_dir / "audio.tmp.%(ext)s"),
        noplaylist=True,
        retries=3,
        postprocessors=[{
            "key": "FFmpegExtractAudio",
            "preferredcodec" : "mp3",
            "preferredquality" : "320",
        }],
    )

    log.info("downloading %s", song.url)

    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([song.url])
    except YoutubeDLError as e:
        raise KaraokeError(f"could not download {song.url} : {e}") from e

    if not (tmp.exists() and tmp.stat().st_size):
        raise KaraokeError(f"download produced no audio for {song.url}")

    tmp.replace(out)
    log.info("audio ready: %s (%.1f MB)", out, out.stat().st_size / 1e6)
    return out
