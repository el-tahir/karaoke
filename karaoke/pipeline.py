"""Core karaoke pipeline orchestration – *updated for enhanced video builder*.

Changes versus previous version:
    • All calls to `k_video.build_video` now use **keyword arguments** for
      `resolution` and `background_color` – this is fully compatible with the
      enhanced `video.py` (which still accepts them positionally) and avoids
      the accidental TypeError that arose when the signature changed.
    • Optional support for `background_path` and `crf` can be passed through
      in future without refactoring (shown as TODO comments).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Tuple

from . import audio_source as k_audio
from . import config
from . import lyrics as k_lyrics
from . import metadata as k_meta
from . import separate as k_separate
from . import subtitles as k_subs
from . import video as k_video

logger = logging.getLogger(__name__)


class KaraokePipeline:
    def __init__(
        self,
        track: Optional[str] = None,
        artist: Optional[str] = None,
        file_path: Optional[str] = None,
        youtube_url: Optional[str] = None,
        cookies: Optional[str] = None,
        resolution: str = config.DEFAULT_RESOLUTION,
        background: str = config.DEFAULT_BACKGROUND,
        # background_path: Optional[str] = None,  # ← future enhancement
        # crf: int = 18,                          # ← future enhancement
    ) -> None:
        self.track = track
        self.artist = artist
        self.file_path = file_path
        self.youtube_url = youtube_url
        self.cookies = cookies
        self.resolution = resolution
        self.background = background
        # self.background_path = Path(background_path) if background_path else None
        # self.crf = crf
        self.audio_path: Optional[Path] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_audio(self) -> None:
        if self.youtube_url:
            self.audio_path = k_audio.download_from_youtube(self.youtube_url, self.cookies)
        elif self.file_path:
            self.audio_path = k_audio.validate_audio_file(self.file_path)
        else:
            if not self.track:
                raise ValueError("Track name is required to search on YouTube.")
            search_query = f"{self.track} {self.artist}" if self.artist else self.track
            self.audio_path = k_audio.download_from_youtube(
                f"ytsearch1:{search_query} audio", self.cookies
            )

        if not self.track or not self.artist:
            inferred_track, inferred_artist = k_meta.infer_metadata_from_filename(self.audio_path)
            self.track = self.track or inferred_track
            self.artist = self.artist or inferred_artist

        if not self.track:
            raise ValueError("Could not determine track title.")
        self.artist = self.artist or ""

    # ------------------------------------------------------------------
    # Non‑streaming mode
    # ------------------------------------------------------------------
    def run(self) -> Tuple[Path, Path]:
        """Execute the pipeline synchronously (CLI use)."""
        self._resolve_audio()
        lrc_path = k_lyrics.fetch_lrc(self.track, self.artist, config.LYRICS_DIR)
        instrumental_path, _ = k_separate.separate(self.audio_path, config.STEMS_DIR)
        ass_path = k_subs.lrc_to_ass(lrc_path, config.SUBS_DIR / lrc_path.with_suffix(".ass").name)

        safe_track = k_meta.sanitize_filename(self.track or "output")
        safe_artist = k_meta.sanitize_filename(self.artist or "")
        video_name = f"{safe_artist} - {safe_track}.mp4" if safe_artist else f"{safe_track}.mp4"

        output_path = config.OUTPUT_DIR / video_name
        full_output_path = config.OUTPUT_DIR / (output_path.stem + "_full" + output_path.suffix)

        # Karaoke (instrumental) video
        k_video.build_video(
            audio_path=instrumental_path,
            ass_path=ass_path,
            output_path=output_path,
            resolution=self.resolution,
            background_color=self.background,
            # background_path=self.background_path,  # if using image/video bg
            # crf=self.crf,
        )
        # Full‑song video (original audio)
        k_video.build_video(
            audio_path=self.audio_path,
            ass_path=ass_path,
            output_path=full_output_path,
            resolution=self.resolution,
            background_color=self.background,
        )
        return output_path, full_output_path

    # ------------------------------------------------------------------
    # Streaming (Server‑Sent Events) mode
    # ------------------------------------------------------------------
    def run_streaming(self) -> Generator[str, None, None]:
        """Execute pipeline with SSE progress updates (API use)."""

        def _sse(event: str, message: str, data: Optional[Dict[str, Any]] = None) -> str:
            payload = {"event": event, "message": message, "data": data or {}}
            return f"data: {json.dumps(payload)}\n\n"

        try:
            yield _sse("start", "Pipeline initiated…")

            # 1. Audio resolution
            yield _sse("audio:start", "Resolving audio source…")
            self._resolve_audio()
            yield _sse("audio:done", f"Using audio: {self.audio_path.name}")

            # 2. Lyrics
            yield _sse("lyrics:start", "Fetching lyrics…")
            lrc_path = k_lyrics.fetch_lrc(self.track, self.artist, config.LYRICS_DIR)
            yield _sse("lyrics:done", f"Lyrics downloaded: {lrc_path.name}")

            # 3. Separation
            yield _sse("separation:start", "Separating vocals…")
            instrumental_path, _ = k_separate.separate(self.audio_path, config.STEMS_DIR)
            yield _sse("separation:done", f"Instrumental created: {instrumental_path.name}")

            # 4. Subtitles
            yield _sse("subtitles:start", "Generating subtitles…")
            ass_path = k_subs.lrc_to_ass(lrc_path, config.SUBS_DIR / lrc_path.with_suffix(".ass").name)
            yield _sse("subtitles:done", f"Subtitles generated: {ass_path.name}")

            # 5. Video render
            yield _sse("video:start", "Rendering videos…")

            safe_track = k_meta.sanitize_filename(self.track or "output")
            safe_artist = k_meta.sanitize_filename(self.artist or "")
            video_name = (
                f"{safe_artist} - {safe_track}.mp4" if safe_artist else f"{safe_track}.mp4"
            )
            output_path = config.OUTPUT_DIR / video_name
            full_output_path = config.OUTPUT_DIR / (
                output_path.stem + "_full" + output_path.suffix
            )

            # Karaoke version
            k_video.build_video(
                audio_path=instrumental_path,
                ass_path=ass_path,
                output_path=output_path,
                resolution=self.resolution,
                background_color=self.background,
            )
            # Full version
            k_video.build_video(
                audio_path=self.audio_path,
                ass_path=ass_path,
                output_path=full_output_path,
                resolution=self.resolution,
                background_color=self.background,
            )

            yield _sse("video:done", "Videos rendered.")
            yield _sse(
                "done",
                "Pipeline completed successfully!",
                {
                    "karaoke_video_url": f"/videos/{output_path.name}",
                    "full_song_video_url": f"/videos/{full_output_path.name}",
                },
            )

        except Exception as e:
            logger.exception("Pipeline failed: %s", e)
            yield _sse("error", "Pipeline failed", {"detail": str(e)})
