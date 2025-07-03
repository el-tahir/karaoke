from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Generator, Dict, Any
import logging

from . import input as kinput
from . import lyrics as klyrics
from . import separate as kseparate
from . import subtitles as ksubs
from . import video as kvideo

LYRICS_DIR = klyrics.DEFAULT_OUTPUT_DIR
SUBS_DIR = ksubs.DEFAULT_OUTPUT_DIR
STEMS_DIR = kseparate.DEFAULT_OUTPUT_DIR
OUTPUT_DIR = Path("output_videos")
OUTPUT_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)


def _sse(event: str, message: str, data: Dict[str, Any] | None = None) -> str:
    """Build a Server-Sent Event line."""
    payload = {"event": event, "message": message, "data": data or {}}
    # According to the SSE spec each event block must end with *two* new-lines.
    return f"data: {json.dumps(payload)}\n\n"


def run_pipeline_streaming(args: argparse.Namespace) -> Generator[str, None, None]:
    """Run the karaoke pipeline, yielding progress updates as Server-Sent Events.

    The function mirrors the logic of `karaoke.__main__.run_pipeline` but yields
    informative updates before and after each major step so that a frontend can
    display live progress to the user.
    """
    try:
        logger.info("Pipeline initiated with args: %s", args)
        yield _sse("start", "Pipeline initiated…")

        # ------------------------------------------------------------------
        # 1. Resolve / download audio & gather metadata
        # ------------------------------------------------------------------
        logger.info("Resolving audio source…")
        yield _sse("audio:start", "Resolving audio source…")
        track: str | None = args.track
        artist: str | None = args.artist

        if args.youtube_url:
            try:
                # Check if cookies are provided in args
                cookies = getattr(args, 'cookies', None)
                audio_path = kinput.download_from_youtube(args.youtube_url, cookies=cookies)
            except Exception as e:
                error_msg = str(e)
                if "Sign in to confirm you're not a bot" in error_msg or "bot" in error_msg.lower():
                    user_friendly_msg = (
                        "YouTube has blocked this request due to bot detection. "
                        "This is common on cloud servers. Please try: "
                        "1) A different YouTube URL, "
                        "2) Upload an audio file directly, or "
                        "3) Try again later as restrictions may be temporary."
                    )
                    yield _sse("error", user_friendly_msg, {"technical_detail": error_msg, "error_type": "youtube_blocked"})
                    return
                else:
                    # Re-raise other YouTube errors as-is
                    raise
        elif args.file:
            audio_path = kinput.validate_audio_file(args.file)
        else:
            if not track:
                raise RuntimeError("When neither --file nor --youtube-url is provided, you must supply --track (and optionally --artist) so the pipeline can search YouTube.")
            search_query = track if artist is None else f"{track} {artist}"
            yt_search_url = f"ytsearch1:{search_query} audio"
            try:
                # Check if cookies are provided in args
                cookies = getattr(args, 'cookies', None)
                audio_path = kinput.download_from_youtube(yt_search_url, cookies=cookies)
            except Exception as e:
                error_msg = str(e)
                if "Sign in to confirm you're not a bot" in error_msg or "bot" in error_msg.lower():
                    user_friendly_msg = (
                        f"YouTube search for '{search_query}' was blocked due to bot detection. "
                        "Please provide a direct YouTube URL or upload an audio file instead."
                    )
                    yield _sse("error", user_friendly_msg, {"technical_detail": error_msg, "error_type": "youtube_search_blocked"})
                    return
                else:
                    # Re-raise other YouTube errors as-is
                    raise

        logger.info("Audio source resolved → %s", audio_path)
        yield _sse("audio:done", f"Using audio: {audio_path.name}")

        # If metadata missing, try to infer it from filename.
        if not track or not artist:
            inferred_track, inferred_artist = kinput._infer_metadata_from_filename(audio_path)  # type: ignore
            track = track or inferred_track
            artist = artist or inferred_artist

        if not track:
            raise RuntimeError("Could not determine track title. Please supply --track explicitly or ensure the YouTube video/file name contains it.")
        # If artist is still missing, continue with an empty string so that downstream steps can still attempt a lyrics search.
        artist = artist or ""

        # ------------------------------------------------------------------
        # 2. Fetch lyrics
        # ------------------------------------------------------------------
        logger.info("Fetching synchronised lyrics…")
        yield _sse("lyrics:start", "Fetching synchronised lyrics…")
        lrc_path = klyrics.fetch_lrc(track, artist, LYRICS_DIR)  # type: ignore[arg-type]
        logger.info("Lyrics fetched → %s", lrc_path)
        yield _sse("lyrics:done", f"Lyrics downloaded → {lrc_path.name}")

        # ------------------------------------------------------------------
        # 3. Separate vocals
        # ------------------------------------------------------------------
        logger.info("Separating vocals…")
        yield _sse("separation:start", "Separating vocals (this may take a while)…")
        instrumental_path, _ = kseparate.separate(audio_path, STEMS_DIR)
        logger.info("Separation done → %s", instrumental_path)
        yield _sse("separation:done", f"Instrumental created → {instrumental_path.name}")

        # ------------------------------------------------------------------
        # 4. Generate subtitles
        # ------------------------------------------------------------------
        logger.info("Generating subtitles…")
        yield _sse("subtitles:start", "Generating karaoke subtitles…")
        ass_name = lrc_path.with_suffix(".ass").name
        ass_path = SUBS_DIR / ass_name
        ksubs.lrc_to_ass(lrc_path, ass_path)
        logger.info("Subtitles generated → %s", ass_path)
        yield _sse("subtitles:done", f"Subtitles generated → {ass_path.name}")

        # ------------------------------------------------------------------
        # 5. Build karaoke & full-song videos
        # ------------------------------------------------------------------
        logger.info("Rendering videos…")
        yield _sse("video:start", "Rendering videos…")

        # Determine output filenames – always place them inside OUTPUT_DIR.
        from .lyrics import sanitize_filename  # reuse helper

        safe_track = sanitize_filename(track or "output")
        safe_artist = sanitize_filename(artist or "")
        if safe_artist:
            video_name = f"{safe_artist} - {safe_track}.mp4"
        else:
            video_name = f"{safe_track}.mp4"

        output_path = OUTPUT_DIR / video_name
        full_output_path = OUTPUT_DIR / (output_path.stem + "_full" + output_path.suffix)

        kvideo.build_video(
            instrumental_path,
            ass_path,
            output_path,
            resolution=(getattr(args, "resolution", None) or kvideo.DEFAULT_RES),
            background_color=(getattr(args, "background", None) or kvideo.DEFAULT_BG),
        )

        kvideo.build_video(
            audio_path,
            ass_path,
            full_output_path,
            resolution=(getattr(args, "resolution", None) or kvideo.DEFAULT_RES),
            background_color=(getattr(args, "background", None) or kvideo.DEFAULT_BG),
        )

        logger.info("Videos rendered successfully → %s / %s", output_path, full_output_path)
        yield _sse("video:done", "Videos rendered successfully.")

        # ------------------------------------------------------------------
        # Final – success!
        # ------------------------------------------------------------------
        final_data = {
            "karaoke_video_url": f"/videos/{output_path.name}",
            "full_song_video_url": f"/videos/{full_output_path.name}",
        }
        logger.info("Pipeline completed successfully.")
        yield _sse("done", "All videos created successfully!", final_data)

    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        # Emit an error event for the frontend to display.
        yield _sse("error", "Pipeline failed", {"detail": str(exc)}) 