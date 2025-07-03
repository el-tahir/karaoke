"""Lyrics fetching utility.

Uses `syncedlyrics` to retrieve time-synchronized LRC lyrics and saves them to a file.

CLI Usage
---------
python -m karaoke.lyrics --track "Song Title" --artist "Artist Name" [--output-dir ./lyrics]

Alternatively, supply a `.meta.txt` produced by `karaoke.input`:
python -m karaoke.lyrics --meta "song.meta.txt"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import syncedlyrics  # type: ignore

DEFAULT_OUTPUT_DIR = Path("lyrics")


def sanitize_filename(name: str) -> str:
    # Remove characters that are problematic on most file systems
    return "".join(c for c in name if c not in "\\/:*?\"<>|").strip()


def fetch_lrc(track: str, artist: str, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Fetch lyrics via syncedlyrics and save as .lrc.

    Returns the path to the saved LRC file. Raises RuntimeError if lyrics not found.
    """
    search_query = f"{track} {artist}"
    print(f"Searching for lyrics: {search_query}")
    lrc_content: Optional[str] = syncedlyrics.search(search_query, enhanced=True)

    if not lrc_content:
        raise RuntimeError(f"No synchronized lyrics found for '{track}' by '{artist}'.")

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(track) or "lyrics"
    lrc_path = output_dir / f"{filename}.lrc"
    lrc_path.write_text(lrc_content, encoding="utf-8")
    print(f"Saved lyrics to {lrc_path}")
    return lrc_path


def parse_meta_file(meta_path: Path) -> tuple[str, str]:
    """Read .meta.txt (key=value per line) and extract track & artist."""
    text = meta_path.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, val = line.split("=", 1)
            values[key.strip()] = val.strip()
    track = values.get("track")
    artist = values.get("artist")
    if not track or not artist:
        raise ValueError("Meta file does not contain 'track' and 'artist' entries.")
    return track, artist


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:  # pragma: no cover
    p = argparse.ArgumentParser(description="Fetch time-synchronized lyrics for a song.")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--meta", help="Path to .meta.txt file produced by karaoke.input")
    group.add_argument("--track", help="Track title if not using --meta")
    p.add_argument("--artist", help="Artist name (required if --track used)")
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory in which to save the .lrc file")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    args = parse_args(argv)

    if args.meta:
        meta_path = Path(args.meta).expanduser().resolve()
        if not meta_path.exists():
            print(f"Meta file not found: {meta_path}", file=sys.stderr)
            sys.exit(1)
        track, artist = parse_meta_file(meta_path)
    else:
        if not args.artist:
            print("--artist is required when using --track", file=sys.stderr)
            sys.exit(1)
        track = args.track
        artist = args.artist
    try:
        fetch_lrc(track, artist, Path(args.output_dir))
    except RuntimeError as err:
        print(str(err), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main() 