import os
import subprocess
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["create_karaoke_video"]


def _get_audio_duration(audio_file: str) -> float:
    """Return duration of audio file in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        audio_file,
    ]
    output = subprocess.check_output(cmd)
    data = json.loads(output)
    return float(data["format"]["duration"])


def create_karaoke_video(
    audio_file: str,
    ass_file: str,
    output_file: str | None = None,
    resolution: str = "1280x720",
    background_color: str = "black",
) -> str:
    """Create karaoke video by burning ASS subtitles onto a blank canvas with audio.

    This is a simple FFmpeg-based implementation kept for backward compatibility
    until a more advanced `VideoRenderer` class is provided.
    """
    if output_file is None:
        base = Path(audio_file).stem
        output_file = f"{base}_karaoke.mp4"

    duration = _get_audio_duration(audio_file)

    cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        f"color=c={background_color}:s={resolution}:d={duration}",
        "-i",
        audio_file,
        "-vf",
        f"subtitles={ass_file}",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-shortest",
        output_file,
    ]

    try:
        subprocess.run(cmd, check=True)
        logger.info("Created karaoke video: %s", output_file)
        return output_file
    except subprocess.CalledProcessError as exc:
        logger.error("Error creating video: %s", exc)
        raise 