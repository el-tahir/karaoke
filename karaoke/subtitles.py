"""Subtitle generation utility.

Converts an LRC lyrics file into an Advanced SubStation Alpha (.ass) subtitle
file with word-by-word karaoke highlighting.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List
import logging

import pylrc
import pysubs2

from . import config
from .cache import cache_manager

logger = logging.getLogger(__name__)

TIMESTAMP_BRACKET_RE = re.compile(r"[(\d{2}):(\d{2})\.(\d{2})]")
TIMESTAMP_INLINE_RE = re.compile(r"<(\d{2}):(\d{2})\.(\d{2})>")


def _components_to_seconds(mins: str, secs: str, centis: str) -> float:
    """Helper converting regex capture groups to seconds float."""
    return int(mins) * 60 + int(secs) + int(centis) / 100.0


def _parse_inline_timings(text: str):
    """Return list[(word, start_time_sec)] if inline <mm:ss.xx> timings exist."""
    matches = list(TIMESTAMP_INLINE_RE.finditer(text))
    if not matches:
        return None

    tokens = []
    for idx, match in enumerate(matches):
        start_sec = _components_to_seconds(*match.groups())
        start_idx = match.end()
        end_idx = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        word_text = text[start_idx:end_idx].strip()
        if word_text:
            tokens.append((word_text, start_sec))
    return tokens


def lrc_to_ass(lrc_path: Path, output_path: Path) -> Path:
    """Convert an LRC file to an ASS subtitle file."""
    # Check cache first (with error handling)
    try:
        cached_subtitles = cache_manager.get_cached_subtitles(lrc_path)
        if cached_subtitles:
            return cached_subtitles
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Cache check failed, proceeding with subtitle generation: {e}")
    
    lrc = pylrc.parse(lrc_path.read_text(encoding="utf-8"))
    lines = sorted(lrc, key=lambda l: l.time)
    subs = pysubs2.SSAFile()

    # Styles
    style_default = pysubs2.SSAStyle("Default", primarycolor=pysubs2.Color(255, 255, 255, 0), alignment=pysubs2.Alignment.MIDDLE_CENTER)
    style_karaoke = pysubs2.SSAStyle("Karaoke", primarycolor=pysubs2.Color(255, 255, 255, 0), secondarycolor=pysubs2.Color(255, 0, 0, 0), alignment=pysubs2.Alignment.MIDDLE_CENTER)
    subs.styles["Default"] = style_default
    subs.styles["Karaoke"] = style_karaoke

    # Events
    for idx, line in enumerate(lines):
        start_sec = line.time
        end_sec = lines[idx + 1].time if idx < len(lines) - 1 else start_sec + 2.0
        tokens = _parse_inline_timings(line.text)

        if tokens:
            words, starts = zip(*tokens)
            durations: List[float] = [starts[i + 1] - t_start if i + 1 < len(starts) else max(0.1, end_sec - t_start) for i, t_start in enumerate(starts)]
            ass_tokens: List[str] = [f"{{\\K{max(1, int(round(dur * 100)))}}}{word}" for word, dur in zip(words, durations)]
            ass_text = " ".join(ass_tokens)
            style_name = "Karaoke"
        else:
            ass_text = TIMESTAMP_INLINE_RE.sub("", line.text).strip()
            style_name = "Default"

        subs.events.append(
            pysubs2.SSAEvent(
                start=int(start_sec * 1000),
                end=int(end_sec * 1000),
                text=ass_text,
                style=style_name,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    subs.save(str(output_path))
    
    # Cache the generated subtitles (with error handling)
    try:
        cache_manager.cache_subtitles(lrc_path, output_path)
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Failed to cache subtitles, but generation was successful: {e}")
    
    return output_path
 