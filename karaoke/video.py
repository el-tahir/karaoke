"""Karaoke video builder.

Combines instrumental audio, an ASS subtitle file, and a color background
into an MP4 video. Relies on *ffmpeg* being installed and accessible in PATH.

CLI Usage
---------
python -m karaoke.video \
  --audio stems/Watching\ TV_Inst.wav \
  --ass subtitles/Watching\ TV.ass \
  --output karaoke_output.mp4

Optional:
  --resolution 1280x720  (WIDTHxHEIGHT)
  --background "black"   (any FFmpeg color value)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Tuple

import ffmpeg  # type: ignore

DEFAULT_RES = "1280x720"
DEFAULT_BG = "black"


def _probe_duration(audio_path: Path) -> float:
    """Return audio duration in seconds using ffprobe."""
    try:
        probe = ffmpeg.probe(str(audio_path))
        for stream in probe["streams"]:
            if stream["codec_type"] == "audio":
                return float(stream["duration"])
    except ffmpeg.Error as e:  # pragma: no cover
        print("ffprobe failed:", e.stderr.decode(), file=sys.stderr)
    raise RuntimeError("Could not determine audio duration with ffprobe.")


def build_video(
    audio_path: Path,
    ass_path: Path,
    output_path: Path,
    resolution: str = DEFAULT_RES,
    background_color: str = DEFAULT_BG,
) -> Path:
    """Generate karaoke MP4 video and return output path."""
    duration = _probe_duration(audio_path)
    width, height = resolution.split("x")

    # Color video source
    color_source = (
        ffmpeg.input(
            f"color=c={background_color}:s={width}x{height}:d={duration}",
            f="lavfi",
        )
        .video
    )

    audio_in = ffmpeg.input(str(audio_path)).audio

    # Burn subtitles
    video_with_subs = color_source.filter("ass", filename=str(ass_path))

    out = ffmpeg.output(
        video_with_subs,
        audio_in,
        str(output_path),
        vcodec="libx264",
        acodec="aac",
        audio_bitrate="192k",
        shortest=None,
        movflags="+faststart",
    )

    ffmpeg.run(out, overwrite_output=True)
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:  # pragma: no cover
    p = argparse.ArgumentParser(description="Generate karaoke MP4 video from audio + ASS subtitles.")
    p.add_argument("--audio", required=True, help="Path to instrumental audio file")
    p.add_argument("--ass", required=True, help="Path to ASS subtitle file with \K tags")
    p.add_argument("--output", default="karaoke_output.mp4", help="Output MP4 path")
    p.add_argument("--resolution", default=DEFAULT_RES, help="Video resolution WIDTHxHEIGHT (default 1280x720)")
    p.add_argument("--background", default=DEFAULT_BG, help="Background color (default black)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    args = parse_args(argv)
    audio_path = Path(args.audio).expanduser().resolve()
    ass_path = Path(args.ass).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not audio_path.exists():
        print(f"Audio file not found: {audio_path}", file=sys.stderr)
        sys.exit(1)
    if not ass_path.exists():
        print(f"ASS file not found: {ass_path}", file=sys.stderr)
        sys.exit(1)

    try:
        build_video(audio_path, ass_path, output_path, args.resolution, args.background)
        print(f"Karaoke video saved to {output_path}")
    except Exception as e:
        print("Error building video:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main() 