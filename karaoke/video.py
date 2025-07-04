"""Karaoke video builder – *enhanced version*.

Combines an audio file, an ASS subtitle file, and either a solid colour,
image, or looping video background into an MP4 suitable for YouTube.

Key **enhancements** vs. the previous revision:
    • Optional `background_path` parameter – supports static images or video
      clips; falls back to solid colour when omitted.
    • CRF‑based quality control (`crf=18` default) and `preset` selector for
      sharper text after YouTube re‑encoding.
    • Accepts higher‑level theme settings via config (resolution, colours).
    • Expanded cache key to include background_path and crf so variants are
      stored separately.
    • More explicit ffmpeg filter chain with auto‑scaling and trimming to
      guarantee the background matches the audio duration exactly.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import ffmpeg

from . import config
from .cache import cache_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _probe_duration(audio_path: Path) -> float:
    """Return duration in seconds using ffprobe (raises on failure)."""
    try:
        probe = ffmpeg.probe(str(audio_path))
        audio_stream = next((s for s in probe["streams"] if s["codec_type"] == "audio"), None)
        if audio_stream and "duration" in audio_stream:
            return float(audio_stream["duration"])
    except ffmpeg.Error as e:
        stderr = e.stderr.decode()
        logger.error(f"ffprobe failed for {audio_path}: {stderr}")
        raise RuntimeError(f"ffprobe failed: {stderr}") from e
    raise RuntimeError(f"Could not determine audio duration for {audio_path}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_video(
    audio_path: Path,
    ass_path: Path,
    output_path: Path,
    *,
    resolution: str = config.DEFAULT_RESOLUTION,
    background_color: str = getattr(config, "DEFAULT_BACKGROUND", "black"),
    background_path: Optional[Path] = None,
    crf: int = 18,
    preset: str = "medium",
) -> Path:
    """Generate a karaoke MP4 video.

    Parameters
    ----------
    audio_path : Path
        Input audio (instrumental) track.
    ass_path : Path
        Subtitle file with karaoke effects.
    output_path : Path
        Target MP4 path.
    resolution : str, optional
        WxH string like "1920x1080".
    background_color : str, optional
        Solid background colour if no `background_path`.
    background_path : Path | None, optional
        Static image or looping video to use as background.
    crf : int, optional
        Constant Rate Factor for libx264; 18≈ visually lossless.
    preset : str, optional
        x264 speed/quality preset.
    """
    logger.info("--- Karaoke Video Build ---")
    logger.info(f"Audio       : {audio_path}")
    logger.info(f"Subtitles   : {ass_path}")
    logger.info(f"Background  : {background_path or background_color}")
    logger.info(f"Resolution  : {resolution}")
    logger.info(f"CRF/Preset  : {crf}/{preset}")

    # Validate inputs
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not ass_path.exists():
        raise FileNotFoundError(f"Subtitle file not found: {ass_path}")
    if background_path and not background_path.exists():
        raise FileNotFoundError(f"Background file not found: {background_path}")

    # -------------------------------------------------------------------
    # Cache check – key now includes background and crf
    # -------------------------------------------------------------------
    try:
        cached = cache_manager.get_cached_video(
            audio_path,
            ass_path,
            resolution,
            background_color,
            str(background_path) if background_path else None,
            crf,
        )
        if cached:
            logger.info(f"✅ Using cached video: {cached}")
            return cached
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Cache check failed, proceeding: {e}")

    duration = _probe_duration(audio_path)
    width, height = map(int, resolution.split("x"))

    # -------------------------------------------------------------------
    # Build ffmpeg filter graph
    # -------------------------------------------------------------------
    if background_path:
        # Decide if image or video
        bg_input = ffmpeg.input(str(background_path))
        if background_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            # Static image – loop forever, then trim
            bg_stream = (
                bg_input
                .filter("scale", width, height)
                .filter("loop", loop=-1, size=1, start=0)
                .filter("trim", duration=duration)
                .filter("setsar", "1")
            )
        else:
            # Video background – scale and trim to song length
            bg_stream = (
                bg_input
                .filter("scale", width, height)
                .filter("trim", duration=duration)
                .filter("setsar", "1")
            )
    else:
        # Solid colour background
        colour_spec = f"color=c={background_color}:s={width}x{height}:d={duration}"
        bg_stream = ffmpeg.input(colour_spec, f="lavfi")

    # Burn in subtitles
    video_with_subs = bg_stream.video.filter("ass", filename=str(ass_path))

    # Audio
    audio_in = ffmpeg.input(str(audio_path)).audio

    # -------------------------------------------------------------------
    # Output settings
    # -------------------------------------------------------------------
    stream = (
        ffmpeg
        .output(
            video_with_subs,
            audio_in,
            str(output_path),
            vcodec="libx264",
            acodec="aac",
            audio_bitrate="192k",
            crf=crf,
            preset=preset,
            movflags="+faststart",
            shortest=None,
        )
        .overwrite_output()
    )

    logger.info("Running ffmpeg…")
    process = stream.run_async(pipe_stdout=True, pipe_stderr=True, quiet=False)
    for line in iter(process.stderr.readline, b""):
        # Pass through ffmpeg log lines for user visibility
        print(f"[ffmpeg] {line.decode().rstrip()}", file=sys.stderr)
    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with return code {process.returncode}")

    logger.info(f"✅ Video created: {output_path}")

    # Cache result
    try:
        cache_manager.cache_video(
            audio_path,
            ass_path,
            resolution,
            background_color,
            str(background_path) if background_path else None,
            crf,
            output_path,
        )
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Video caching failed (non‑fatal): {e}")

    return output_path
