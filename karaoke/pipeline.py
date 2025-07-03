"""Core karaoke pipeline orchestration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Generator, Dict, Any, Tuple
import json

from . import config
from . import audio_source as k_audio
from . import lyrics as k_lyrics
from . import separate as k_separate
from . import subtitles as k_subs
from . import video as k_video
from . import metadata as k_meta

logger = logging.getLogger(__name__)

class KaraokePipeline:
    def __init__(self, track: Optional[str] = None, artist: Optional[str] = None,
                 file_path: Optional[str] = None, youtube_url: Optional[str] = None,
                 cookies: Optional[str] = None, resolution: str = config.DEFAULT_RESOLUTION,
                 background: str = config.DEFAULT_BACKGROUND):
        self.track = track
        self.artist = artist
        self.file_path = file_path
        self.youtube_url = youtube_url
        self.cookies = cookies
        self.resolution = resolution
        self.background = background
        self.audio_path: Optional[Path] = None

    def _resolve_audio(self):
        if self.youtube_url:
            self.audio_path = k_audio.download_from_youtube(self.youtube_url, self.cookies)
        elif self.file_path:
            self.audio_path = k_audio.validate_audio_file(self.file_path)
        else:
            if not self.track:
                raise ValueError("Track name is required to search on YouTube.")
            search_query = f"{self.track} {self.artist}" if self.artist else self.track
            self.audio_path = k_audio.download_from_youtube(f"ytsearch1:{search_query} audio", self.cookies)

        if not self.track or not self.artist:
            inferred_track, inferred_artist = k_meta.infer_metadata_from_filename(self.audio_path)
            self.track = self.track or inferred_track
            self.artist = self.artist or inferred_artist

        if not self.track:
            raise ValueError("Could not determine track title.")
        self.artist = self.artist or ""

    def run(self) -> Tuple[Path, Path]:
        self._resolve_audio()
        lrc_path = k_lyrics.fetch_lrc(self.track, self.artist, config.LYRICS_DIR)
        instrumental_path, _ = k_separate.separate(self.audio_path, config.STEMS_DIR)
        ass_path = k_subs.lrc_to_ass(lrc_path, config.SUBS_DIR / lrc_path.with_suffix(".ass").name)
        
        safe_track = k_meta.sanitize_filename(self.track or "output")
        safe_artist = k_meta.sanitize_filename(self.artist or "")
        video_name = f"{safe_artist} - {safe_track}.mp4" if safe_artist else f"{safe_track}.mp4"
        
        output_path = config.OUTPUT_DIR / video_name
        full_output_path = config.OUTPUT_DIR / (output_path.stem + "_full" + output_path.suffix)

        k_video.build_video(instrumental_path, ass_path, output_path, self.resolution, self.background)
        k_video.build_video(self.audio_path, ass_path, full_output_path, self.resolution, self.background)

        return output_path, full_output_path

    def run_streaming(self) -> Generator[str, None, None]:
        def _sse(event: str, message: str, data: Optional[Dict[str, Any]] = None) -> str:
            payload = {"event": event, "message": message, "data": data or {}}
            return f"data: {json.dumps(payload)}\n\n"

        try:
            yield _sse("start", "Pipeline initiated...")
            
            yield _sse("audio:start", "Resolving audio source...")
            self._resolve_audio()
            yield _sse("audio:done", f"Using audio: {self.audio_path.name}")

            yield _sse("lyrics:start", "Fetching lyrics...")
            lrc_path = k_lyrics.fetch_lrc(self.track, self.artist, config.LYRICS_DIR)
            yield _sse("lyrics:done", f"Lyrics downloaded: {lrc_path.name}")

            yield _sse("separation:start", "Separating vocals...")
            instrumental_path, _ = k_separate.separate(self.audio_path, config.STEMS_DIR)
            yield _sse("separation:done", f"Instrumental created: {instrumental_path.name}")

            yield _sse("subtitles:start", "Generating subtitles...")
            ass_path = k_subs.lrc_to_ass(lrc_path, config.SUBS_DIR / lrc_path.with_suffix(".ass").name)
            yield _sse("subtitles:done", f"Subtitles generated: {ass_path.name}")

            yield _sse("video:start", "Rendering videos...")
            output_path, full_output_path = self.run()
            yield _sse("video:done", "Videos rendered.")

            final_data = {
                "karaoke_video_url": f"/videos/{output_path.name}",
                "full_song_video_url": f"/videos/{full_output_path.name}",
            }
            yield _sse("done", "Pipeline completed successfully!", final_data)

        except Exception as e:
            logger.exception("Pipeline failed: %s", e)
            yield _sse("error", "Pipeline failed", {"detail": str(e)})
