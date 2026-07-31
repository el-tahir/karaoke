"""
burns the subtitles over a solid background and muxes in the audio
"""

import logging
import subprocess
import time
from pathlib import Path

from karaoke.config import Config
from karaoke.errors import KaraokeError

log = logging.getLogger(__name__)

_STDERR_LINES = 20

def _tail(stderr: str) -> str:
    return "\n".join(stderr.strip().splitlines()[-_STDERR_LINES:])

def render(audio: Path, subs: Path, out_path: Path, cfg: Config) -> Path:
    for path in (audio, subs):
        if not (path.exists() and path.stat().st_size):
            raise KaraokeError(f"nothing to render: {path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp.mp4")

    cmd = [
        cfg.ffmpeg, "-y", "-hide_banner", "-nostdin",
        "-f", "lavfi", "-i", f"color=c={cfg.background}:s={cfg.resolution}:r={cfg.fps}",
        "-i", str(audio.resolve()),
        "-map", "0:v", "-map", "1:a", # not letting ffmpeg guess; cover art is a video stream
        "-vf", f"ass={subs.name}", # bare name, ffmpeg will run inside the subs dir
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", # 4:2:0 or it wont play on a phone (will need to double check this)
        "-c:a", "aac", "-b:a", "320k",
        "-shortest",
        str(tmp.resolve())
    ]

    log.info("rendering %s", out_path)
    t0 = time.monotonic()

    try:
        # subs.parent exists (we checked subs above)
        done = subprocess.run(cmd, cwd=subs.parent, capture_output=True,
            text=True, errors="replace")
    except FileNotFoundError as e:
        raise KaraokeError("ffmpeg not found - install it or set ffmpeg in config") from e

    if done.returncode:
        tmp.unlink(missing_ok=True)
        raise KaraokeError(f"ffmpeg failed for {out_path}:\n{_tail(done.stderr)}")

    if not (tmp.exists() and tmp.stat().st_size):
        raise KaraokeError(f"ffmpeg produced no video for {out_path}")

    tmp.replace(out_path)
    log.info("video ready: %s (%.1f MB, %.0fs)",
        out_path, out_path.stat().st_size / 1e6, time.monotonic() - t0)
    return out_path
