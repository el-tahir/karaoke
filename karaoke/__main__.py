from __future__ import annotations

"""karaoke.__main__

End-to-end pipeline that orchestrates the complete karaoke video generation
workflow.

This script wires together the previously implemented modules:

1. `karaoke.input`      – Handle audio source (local file or YouTube) and metadata
2. `karaoke.lyrics`     – Fetch time-synchronised LRC lyrics
3. `karaoke.separate`   – Separate vocals to obtain an instrumental track
4. `karaoke.subtitles`  – Convert the LRC file to ASS subtitles with \K tags
5. `karaoke.video`      – Burn subtitles onto a coloured background to create
   the final MP4 video

CLI Usage (examples)
--------------------
python -m karaoke --file "song.mp3" --track "Song Title" --artist "Artist"
python -m karaoke --youtube-url "https://youtu.be/xyz" --track "Song" --artist "Artist"
"""

import argparse
import sys
from pathlib import Path

from . import input as kinput
from . import lyrics as klyrics
from . import separate as kseparate
from . import subtitles as ksubs
from . import video as kvideo

# Default output directories (mirroring those in the dedicated modules)
LYRICS_DIR = klyrics.DEFAULT_OUTPUT_DIR
SUBS_DIR = ksubs.DEFAULT_OUTPUT_DIR
STEMS_DIR = kseparate.DEFAULT_OUTPUT_DIR


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:  # pragma: no cover
    """Aggregate CLI covering the options of all sub-steps."""
    p = argparse.ArgumentParser(description="Run the full karaoke pipeline on a song.")

    # Audio source options – none required now. If neither provided, the pipeline
    # will attempt to search YouTube based on the provided track/artist metadata.
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--file", help="Path to a local audio file")
    g.add_argument("--youtube-url", help="YouTube URL to download audio from")

    # Optional metadata if it cannot be inferred from the filename
    p.add_argument("--track", help="Track title (optional – inferred from filename if possible)")
    p.add_argument("--artist", help="Artist name (optional – inferred from filename if possible)")

    # Video generation options (subset – background image support is Task 9)
    p.add_argument("--resolution", default=kvideo.DEFAULT_RES, help="Video resolution WIDTHxHEIGHT (default 1280x720)")
    p.add_argument("--background", default=kvideo.DEFAULT_BG, help="Background colour (default black)")

    # Additional output: full-song video (instrumental + vocals)
    p.add_argument(
        "--full-output",
        default=None,
        help="If provided, also generate a video with the original full song audio at this path (default adds '_full' before the .mp4 extension of --output).",
    )

    # Output locations
    p.add_argument(
        "--output",
        default=None,
        help="Path for the generated MP4 video (default is '<Artist> - <Track>.mp4')",
    )

    return p.parse_args(argv)


def run_pipeline(args: argparse.Namespace) -> tuple[Path, Path]:
    """Execute the pipeline and return the final video paths."""

    # 1. Resolve / download audio & gather metadata -----------------------------------
    track: str | None = args.track
    artist: str | None = args.artist

    # If an explicit audio source is provided, validate / download it first.
    if args.youtube_url:
        audio_path = kinput.download_from_youtube(args.youtube_url)
    elif args.file:
        audio_path = kinput.validate_audio_file(args.file)
    else:
        # No explicit source – we require at least the track name to search YouTube.
        if not track:
            raise RuntimeError("When neither --file nor --youtube-url is provided, you must supply --track (and optionally --artist) so the pipeline can search YouTube.")

        # Build a YouTube search query and let yt-dlp fetch the first result.
        search_query = track if artist is None else f"{track} {artist}"
        yt_search_url = f"ytsearch1:{search_query} audio"
        print(f"🔍 Searching YouTube for: {search_query}")
        audio_path = kinput.download_from_youtube(yt_search_url)

    # If metadata still missing, try to infer it from the downloaded/validated filename.
    if not track or not artist:
        inferred_track, inferred_artist = kinput._infer_metadata_from_filename(audio_path)  # type: ignore
        track = track or inferred_track
        artist = artist or inferred_artist

    if not track or not artist:
        raise RuntimeError(
            "Could not determine both track and artist metadata. Please supply --track and --artist or use a filename in the form 'Artist - Track.ext'."
        )

    # 2. Fetch lyrics ------------------------------------------------------------------
    try:
        lrc_path = klyrics.fetch_lrc(track, artist, LYRICS_DIR)  # type: ignore[arg-type]
    except Exception as exc:
        raise RuntimeError(f"Lyrics fetching failed: {exc}") from exc

    # 3. Separate vocals ---------------------------------------------------------------
    try:
        instrumental_path, _ = kseparate.separate(audio_path, STEMS_DIR)
    except Exception as exc:
        raise RuntimeError(f"Audio separation failed: {exc}") from exc

    # 4. Generate ASS subtitles --------------------------------------------------------
    ass_name = lrc_path.with_suffix(".ass").name
    ass_path = SUBS_DIR / ass_name
    try:
        ksubs.lrc_to_ass(lrc_path, ass_path)
    except Exception as exc:
        raise RuntimeError(f"Subtitle generation failed: {exc}") from exc

    # 5. Build final video -------------------------------------------------------------
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        # Fallback naming based on metadata – ensure no illegal filesystem chars
        from .lyrics import sanitize_filename  # re-use helper

        safe_track = sanitize_filename(track or "output")
        safe_artist = sanitize_filename(artist or "")
        if safe_artist:
            fname = f"{safe_artist} - {safe_track}.mp4"
        else:
            fname = f"{safe_track}.mp4"
        output_path = Path(fname).expanduser().resolve()

    # Build karaoke (instrumental) video
    try:
        kvideo.build_video(
            instrumental_path,
            ass_path,
            output_path,
            resolution=args.resolution,
            background_color=args.background,
        )
    except Exception as exc:
        raise RuntimeError(f"Karaoke video generation failed: {exc}") from exc

    # Determine full-song output path (original audio with vocals)
    if args.full_output:
        full_output_path = Path(args.full_output).expanduser().resolve()
    else:
        full_output_path = output_path.with_name(output_path.stem + "_full" + output_path.suffix)

    # Build full-song video
    try:
        kvideo.build_video(
            audio_path,
            ass_path,
            full_output_path,
            resolution=args.resolution,
            background_color=args.background,
        )
    except Exception as exc:
        raise RuntimeError(f"Full-song video generation failed: {exc}") from exc

    return output_path, full_output_path


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    args = _parse_args(argv)
    try:
        final_video, full_video = run_pipeline(args)
        print(f"✅ Karaoke video created: {final_video}")
        print(f"✅ Full-song video created: {full_video}")
    except Exception as err:
        print(f"❌ Pipeline failed: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main() 