"""Karaoke video builder.

Combines audio, an ASS subtitle file, and a background into an MP4 video.
"""
from __future__ import annotations

from pathlib import Path
import ffmpeg
import logging

from . import config
from .cache import cache_manager

logger = logging.getLogger(__name__)

def _probe_duration(audio_path: Path) -> float:
    """Return audio duration in seconds using ffprobe."""
    try:
        probe = ffmpeg.probe(str(audio_path))
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
        if audio_stream and 'duration' in audio_stream:
            return float(audio_stream['duration'])
    except ffmpeg.Error as e:
        raise RuntimeError(f"ffprobe failed: {e.stderr.decode()}") from e
    raise RuntimeError("Could not determine audio duration.")

def build_video(
    audio_path: Path,
    ass_path: Path,
    output_path: Path,
    resolution: str = config.DEFAULT_RESOLUTION,
    background_color: str = config.DEFAULT_BACKGROUND,
) -> Path:
    """Generate karaoke MP4 video."""
    # Check cache first (with error handling)
    try:
        cached_video = cache_manager.get_cached_video(audio_path, ass_path, resolution, background_color)
        if cached_video:
            return cached_video
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Cache check failed, proceeding with video generation: {e}")
    
    duration = _probe_duration(audio_path)
    width, height = map(int, resolution.split("x"))

    color_source = ffmpeg.input(f"color=c={background_color}:s={width}x{height}:d={duration}", f="lavfi").video
    audio_in = ffmpeg.input(str(audio_path)).audio
    video_with_subs = color_source.filter("ass", filename=str(ass_path))

    (
        ffmpeg.output(
            video_with_subs,
            audio_in,
            str(output_path),
            vcodec="libx264",
            acodec="aac",
            audio_bitrate="192k",
            shortest=None,
            movflags="+faststart",
        )
        .overwrite_output()
        .run(quiet=True)
    )
    
    # Cache the generated video (with error handling)
    try:
        cache_manager.cache_video(audio_path, ass_path, resolution, background_color, output_path)
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Failed to cache video, but video was generated successfully: {e}")
    
    return output_path
 