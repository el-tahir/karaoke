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

    # Define base properties for all our text
    font_name = "Arial"
    font_size = 36
    alignment = pysubs2.Alignment.BOTTOM_CENTER # Move to bottom for better viewing
    margin_v = 30 # Vertical margin from the bottom of the screen

    # Style for the CURRENT line (the one with karaoke highlighting)
    # White text that turns red as it's sung.
    style_current = pysubs2.SSAStyle(
        fontname=font_name, fontsize=font_size,
        primarycolor=pysubs2.Color(255, 255, 255),  # Upcoming part of the line (white)
        secondarycolor=pysubs2.Color(255, 255, 0),      # Sung part of the line (red)
        outlinecolor=pysubs2.Color(0, 0, 0),
        alignment=alignment, marginv=margin_v,
        outline=2, shadow=1
    )

    # Style for the NEXT line (the preview line)
    # Dimmer, grey text. No karaoke effect.
    style_next = pysubs2.SSAStyle(
        fontname=font_name, fontsize=font_size - 8, # Slightly smaller
        primarycolor=pysubs2.Color(128, 128, 128), # Dim grey color
        outlinecolor=pysubs2.Color(0, 0, 0),
        alignment=alignment, marginv=margin_v,
        outline=2, shadow=1
    )

    subs.styles["Current"] = style_current
    subs.styles["Next"] = style_next

    # Events
    for idx, current_line in enumerate(lines):
        # Determine the start and end time for this combined event
        start_time_sec = current_line.time
        # The event ends when the *next* line is supposed to start
        end_time_sec = lines[idx + 1].time if idx + 1 < len(lines) else start_time_sec + 5.0

        # 1. Prepare the CURRENT line text with karaoke tags
        tokens = _parse_inline_timings(current_line.text)
        if tokens:
            words, starts = zip(*tokens)
            durations = [
                starts[i + 1] - t_start if i + 1 < len(starts) else max(0.1, end_time_sec - t_start)
                for i, t_start in enumerate(starts)
            ]
            karaoke_tokens = [f"{{\\K{max(1, int(round(dur * 100)))}}}{word}" for word, dur in zip(words, durations)]
            current_line_text = " ".join(karaoke_tokens)
        else:
            # Fallback for lines without word-by-word timings
            current_line_text = TIMESTAMP_INLINE_RE.sub("", current_line.text).strip()

        # 2. Prepare the NEXT line text (plain, no karaoke tags)
        next_line_text = ""
        if idx + 1 < len(lines):
            # Get the clean text of the next line
            next_line = lines[idx + 1]
            next_line_text = TIMESTAMP_INLINE_RE.sub("", next_line.text).strip()

        # 3. Combine them into a single text block for the SSAEvent
        #    {\rStyleName} applies a style. \N is a hard newline.
        #    The result is two lines of text, stacked vertically, each with its own style.
        if next_line_text:
            combined_text = f"{{\\fad(250, 250)}}{{\\rCurrent}}{current_line_text}{{\\rNext}}\\N{next_line_text}"
        else:
            # Handle the very last line, which has no "next" line
            combined_text = f"{{\\fad(250, 250)}}{{\\rCurrent}}{current_line_text}"

        # 4. Create and append the event
        event = pysubs2.SSAEvent(
            start=pysubs2.make_time(s=start_time_sec),
            end=pysubs2.make_time(s=end_time_sec),
            text=combined_text,
            # The style here is just a default; the \r tags in the text override it.
            # We can remove the explicit style parameter if we want.
        )
        subs.events.append(event)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    subs.save(str(output_path))
    
    # Cache the generated subtitles (with error handling)
    try:
        cache_manager.cache_subtitles(lrc_path, output_path)
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Failed to cache subtitles, but generation was successful: {e}")
    
    return output_path
 