"""Audio input and basic metadata handling utilities.

This module provides a simple CLI that accepts:
* --file   Path to an audio file (mp3 / wav / flac)
* --track  Song title (optional – inferred from filename if omitted)
* --artist Artist name (optional – inferred from filename if omitted)

Example:
    python -m karaoke.input --file "song.mp3" --track "Watching TV" --artist "Magdalena Bay"

If the title/artist flags are omitted, the script attempts to parse them from the
filename using the pattern "<artist> - <track>.<ext>" (e.g., "Magdalena Bay - Watching TV.mp3").
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Tuple, Optional
import random
import time
import os
import tempfile

# Supported audio extensions (case-insensitive)
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"}

# New import for YouTube downloading
try:
    import yt_dlp  # type: ignore
except ImportError:  # pragma: no cover
    yt_dlp = None  # Will be checked at runtime

DOWNLOADS_DIR = Path("downloads")


def _infer_metadata_from_filename(file_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Infer (artist, track) from a filename of the form "artist - track.ext".

    Returns (track, artist) where either may be None if parsing fails.
    """
    stem = file_path.stem  # filename without extension
    if " - " in stem:
        artist, track = stem.split(" - ", 1)
        artist = artist.strip()
        track = track.strip()
        return track or None, artist or None
    return None, None


def validate_audio_file(path_str: str) -> Path:
    """Validate that the provided path exists and is a supported audio file."""
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    if path.suffix.lower() not in AUDIO_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format '{path.suffix}'. Supported formats: {', '.join(AUDIO_EXTENSIONS)}"
        )
    return path


def download_from_youtube(url: str, output_dir: Path = DOWNLOADS_DIR, cookies: str | None = None) -> Path:
    """Download audio from a YouTube URL using yt-dlp and return the file path.
    
    Args:
        url: YouTube URL to download from
        output_dir: Directory to save the downloaded file
        cookies: Optional cookies string (Netscape format) or path to cookies file
    """
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is required for YouTube downloads. Install with `pip install yt-dlp`.")

    output_dir.mkdir(parents=True, exist_ok=True)
    # Template: use video title as filename with .mp3 extension
    outtmpl = str(output_dir / "%(title)s.%(ext)s")

    # Add random delay to avoid rapid-fire requests
    time.sleep(random.uniform(1, 3))

    # Handle cookies - check parameter, environment variable, or use default
    cookies_source = cookies or os.getenv("YOUTUBE_COOKIES")
    cookies_file = None
    
    if cookies_source:
        # Create a temporary cookies file if cookies string is provided
        if cookies_source.startswith("# Netscape HTTP Cookie File") or "\t" in cookies_source:
            # Looks like cookie content, write to temp file
            cookies_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            cookies_file.write(cookies_source)
            cookies_file.close()
        elif Path(cookies_source).exists():
            # Path to existing cookies file
            cookies_file = cookies_source
        else:
            # Invalid cookies format
            print(f"Warning: Invalid cookies format provided, proceeding without cookies")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        # Bot detection evasion
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "http_headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        },
        "extractor_retries": 3,
        "fragment_retries": 3,
        "retry_sleep_functions": {"http": lambda n: 2 ** n},
        # Additional anti-bot measures
        "sleep_interval_requests": random.uniform(1, 2),
        "sleep_interval_subtitles": random.uniform(0.5, 1.5),
        "socket_timeout": 30,
        "retries": 5,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    # Add cookies if available
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file if isinstance(cookies_file, str) else cookies_file.name

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[attr-defined]
            info = ydl.extract_info(url, download=True)
    finally:
        # Clean up temporary cookies file if we created one
        if cookies_file and hasattr(cookies_file, 'name') and Path(cookies_file.name).exists():
            try:
                Path(cookies_file.name).unlink()
            except Exception:
                pass  # Ignore cleanup errors

    # When using search (e.g., ytsearch1:), yt-dlp returns a 'playlist' dict with
    # an 'entries' list. Grab the first video entry in that case.
    if info.get('_type') == 'playlist':
        if not info.get('entries'):
            raise RuntimeError("YouTube search returned no results.")
        info = info['entries'][0]

    # Attempt to determine the final file path that yt-dlp wrote. The most
    # reliable location is in 'requested_downloads' – available for newer yt-dlp
    # versions – which contains the exact filepath after post-processing.
    requested = info.get('requested_downloads') or []
    if requested:
        filepath = requested[0].get('filepath')
        if filepath and Path(filepath).exists():
            return Path(filepath).resolve()

    # Fallback: build path from title (may fail if yt-dlp sanitises differently)
    candidate = output_dir / f"{info['title']}.mp3"
    if candidate.exists():
        return candidate.resolve()

    raise RuntimeError("Failed to download audio from YouTube.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Provide an audio source (file or YouTube URL) and metadata for the karaoke pipeline."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to an audio file (mp3, wav, flac, etc.)")
    group.add_argument("--youtube-url", help="YouTube URL to download audio from")

    parser.add_argument("--track", help="Song title. If omitted, inferred from filename if possible.")
    parser.add_argument("--artist", help="Artist name. If omitted, inferred from filename if possible.")
    parser.add_argument("--download-dir", default=str(DOWNLOADS_DIR), help="Directory for downloaded YouTube audio")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    args = parse_args(argv)

    # Determine audio source (file vs YouTube)
    if args.youtube_url:
        audio_path = download_from_youtube(args.youtube_url, Path(args.download_dir))
    else:
        audio_path = validate_audio_file(args.file)

    # Determine track and artist metadata
    track = args.track
    artist = args.artist
    if not track or not artist:
        inferred_track, inferred_artist = _infer_metadata_from_filename(audio_path)
        track = track or inferred_track
        artist = artist or inferred_artist

    if not track or not artist:
        print(
            "Warning: Could not determine track/artist metadata. Please specify --track and --artist.",
            file=sys.stderr,
        )

    print("Audio file:", audio_path)
    print("Track title:", track or "(unknown)")
    print("Artist:", artist or "(unknown)")

    # Persist choices for downstream steps (simple text file output for now)
    meta_file = audio_path.with_suffix(".meta.txt")
    meta_file.write_text(f"file={audio_path}\ntrack={track or ''}\nartist={artist or ''}\n", encoding="utf-8")
    print(f"Metadata saved to {meta_file}")


if __name__ == "__main__":  # pragma: no cover
    main() 