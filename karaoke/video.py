# /karaoke/video.py

"""Karaoke video builder.

Combines audio, an ASS subtitle file, and a background into an MP4 video.
"""
from __future__ import annotations

from pathlib import Path
import ffmpeg
import logging
import sys

from . import config
from .cache import cache_manager

logger = logging.getLogger(__name__)

def _probe_duration(audio_path: Path) -> float:
    """Return audio duration in seconds using ffprobe."""
    logger.info(f"Probing duration for: {audio_path}")
    try:
        probe = ffmpeg.probe(str(audio_path))
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
        if audio_stream and 'duration' in audio_stream:
            duration = float(audio_stream['duration'])
            logger.info(f"Duration found: {duration} seconds")
            return duration
    except ffmpeg.Error as e:
        logger.error(f"ffprobe failed for {audio_path}: {e.stderr.decode()}")
        raise RuntimeError(f"ffprobe failed: {e.stderr.decode()}") from e
    
    logger.error(f"Could not determine audio duration for {audio_path}")
    raise RuntimeError("Could not determine audio duration.")

def build_video(
    audio_path: Path,
    ass_path: Path,
    output_path: Path,
    resolution: str = config.DEFAULT_RESOLUTION,
    background_color: str = config.DEFAULT_BACKGROUND,
) -> Path:
    """Generate karaoke MP4 video with extensive logging."""
    logger.info("--- Starting Video Build ---")
    logger.info(f"Audio Input: {audio_path}")
    logger.info(f"Subtitles Input: {ass_path}")
    logger.info(f"Output Path: {output_path}")
    logger.info(f"Resolution: {resolution}")
    logger.info(f"Background: {background_color}")

    # Validate inputs
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found for video creation: {audio_path}")
    if not ass_path.exists():
        raise FileNotFoundError(f"Subtitles file not found for video creation: {ass_path}")

    # Check cache first
    try:
        cached_video = cache_manager.get_cached_video(audio_path, ass_path, resolution, background_color)
        if cached_video:
            logger.info(f"✅ Using cached video: {cached_video}")
            return cached_video
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Cache check failed, proceeding with video generation: {e}")
    
    try:
        duration = _probe_duration(audio_path)
        width, height = map(int, resolution.split("x"))

        logger.info("Constructing ffmpeg command...")
        color_source = ffmpeg.input(f"color=c={background_color}:s={width}x{height}:d={duration}", f="lavfi").video
        audio_in = ffmpeg.input(str(audio_path)).audio
        video_with_subs = color_source.filter("ass", filename=str(ass_path))

        stream = ffmpeg.output(
            video_with_subs,
            audio_in,
            str(output_path),
            vcodec="libx264",
            acodec="aac",
            audio_bitrate="192k",
            shortest=None,
            movflags="+faststart",
        ).overwrite_output()

        logger.info("Executing ffmpeg command...")
        # The key change: capture stdout and stderr to see ffmpeg's progress/errors
        process = stream.run_async(pipe_stdout=True, pipe_stderr=True, quiet=False)
        
        # Print ffmpeg's output in real-time
        for line in iter(process.stderr.readline, b''):
            print(f"[ffmpeg] {line.decode('utf-8').strip()}", file=sys.stderr)
        
        process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"ffmpeg command failed with return code {process.returncode}")

        logger.info(f"✅ Video successfully created: {output_path}")

        # Cache the generated video
        try:
            cache_manager.cache_video(audio_path, ass_path, resolution, background_color, output_path)
        except (FileNotFoundError, RuntimeError) as e:
            logger.warning(f"Failed to cache video, but video was generated successfully: {e}")
        
        return output_path

    except ffmpeg.Error as e:
        logger.error("ffmpeg Error during video build:")
        # Decode and print stderr for detailed error info
        stderr = e.stderr.decode()
        logger.error(stderr)
        raise RuntimeError(f"ffmpeg failed during video build: {stderr}") from e
    except Exception as e:
        logger.exception("An unexpected error occurred during video build.")
        raise