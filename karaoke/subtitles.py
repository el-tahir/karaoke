"""Subtitle generation utility – *enhanced version*.

This module converts an LRC lyrics file into an Advanced SubStation Alpha
(.ass) subtitle file with word‑by‑word karaoke highlighting and extra
polish for a YouTube‑ready karaoke experience.

Key **enhancements** vs. the previous revision:
    • Explicit PlayResX/PlayResY and WrapStyle ASS headers so libass scales
      fonts correctly at any resolution.
    • Config‑driven theme (font, highlight colour, resolution) with sensible
      fall‑backs.
    • Swapped display order so the **current** line anchors to the bottom
      while the preview line sits above it (intuitive reading order).
    • Graceful per‑word highlighting *even when* inline word timings are
      missing – we fall back to an even split or whole‑line wipe.
    • Fade‑in/out retained; optional overlap handled by video.py.

Only standard dependencies (pylrc, pysubs2) are used.
"""
from __future__ import annotations

import re
import math
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import pylrc
import pysubs2

from . import config
from .cache import cache_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------
TIMESTAMP_BRACKET_RE = re.compile(r"[(\d{2}):(\d{2})\.(\d{2})]")
TIMESTAMP_INLINE_RE = re.compile(r"<(\d{2}):(\d{2})\.(\d{2})>")

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _components_to_seconds(mins: str, secs: str, centis: str) -> float:
    """Convert mm:ss.xx components to a seconds float."""
    return int(mins) * 60 + int(secs) + int(centis) / 100.0


def _parse_inline_timings(text: str) -> Optional[List[Tuple[str, float]]]:
    """Parse <mm:ss.xx> inline time codes -> list of (word, start_sec)."""
    matches = list(TIMESTAMP_INLINE_RE.finditer(text))
    if not matches:
        return None

    tokens: List[Tuple[str, float]] = []
    for idx, match in enumerate(matches):
        start_sec = _components_to_seconds(*match.groups())
        start_idx = match.end()
        end_idx = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        word_text = text[start_idx:end_idx].strip()
        if word_text:
            tokens.append((word_text, start_sec))
    return tokens


# ---------------------------------------------------------------------------
# Main conversion routine
# ---------------------------------------------------------------------------

def lrc_to_ass(lrc_path: Path, output_path: Path) -> Path:
    """Convert an LRC file to an ASS subtitle file, with caching."""

    # -------------------------------------------------------------------
    # Attempt to retrieve from cache first
    # -------------------------------------------------------------------
    try:
        cached_subtitles = cache_manager.get_cached_subtitles(lrc_path)
        if cached_subtitles:
            return cached_subtitles
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Cache check failed – regenerating subtitles: {e}")

    # Parse LRC
    lrc = pylrc.parse(lrc_path.read_text(encoding="utf-8"))
    lines = sorted(lrc, key=lambda l: l.time)

    subs = pysubs2.SSAFile()

    # -------------------------------------------------------------------
    # ASS header tweaks – *Enhancement*
    # -------------------------------------------------------------------
    # Determine play‑res from config or fall‑back to 1920×1080
    res = getattr(config, "DEFAULT_RESOLUTION", "1920x1080")
    try:
        play_res_x, play_res_y = map(int, res.split("x"))
    except ValueError:
        play_res_x, play_res_y = 1920, 1080  # sensible fall‑back
    subs.info["PlayResX"] = str(play_res_x)
    subs.info["PlayResY"] = str(play_res_y)
    # Smart wrapping – breaks long lines on spaces rather than cut‑off
    subs.info["WrapStyle"] = "0"

    # -------------------------------------------------------------------
    # Style definitions
    # -------------------------------------------------------------------
    font_name = getattr(config, "KARAOKE_FONT", "Arial")
    base_font_size = getattr(config, "KARAOKE_FONT_SIZE", 72)

    # Colours (ASS expects BGR). We let config override but provide defaults.
    primary_colour = getattr(config, "KARAOKE_PRIMARY", pysubs2.Color(255, 255, 255))
    highlight_colour = getattr(config, "KARAOKE_HIGHLIGHT", pysubs2.Color(255, 128, 0))  # orange‑gold

    style_current = pysubs2.SSAStyle(
        fontname=font_name,
        fontsize=base_font_size,
        primarycolor=primary_colour,         # *before* being sung
        secondarycolor=highlight_colour,     # fills as sung
        outlinecolor=pysubs2.Color(0, 0, 0),
        alignment=pysubs2.Alignment.MIDDLE_CENTER,
        marginv=50,
        outline=3,
        shadow=1,
    )

    style_next = pysubs2.SSAStyle(
        fontname=font_name,
        fontsize=base_font_size - 8,
        primarycolor=pysubs2.Color(160, 160, 160),  # dim grey
        outlinecolor=pysubs2.Color(0, 0, 0),
        alignment=pysubs2.Alignment.MIDDLE_CENTER,
        marginv=50,
        outline=3,
        shadow=1,
    )

    subs.styles["Current"] = style_current
    subs.styles["Next"] = style_next

    # -------------------------------------------------------------------
    # Build events (one per lyric line)
    # -------------------------------------------------------------------
    for idx, current_line in enumerate(lines):
        start_time_sec = current_line.time
        next_start_time = lines[idx + 1].time if idx + 1 < len(lines) else None
        end_time_sec = (next_start_time or (start_time_sec + 5.0))

        # ---------------------------------------------
        # 1. Prepare CURRENT line text with \K tags
        # ---------------------------------------------
        tokens = _parse_inline_timings(current_line.text)
        if tokens:
            words, starts = zip(*tokens)
            durations = [
                (starts[i + 1] - st) if i + 1 < len(starts) else max(0.1, end_time_sec - st)
                for i, st in enumerate(starts)
            ]
        else:
            # *Enhancement*: fallback – even split (or single wipe) when no timings
            clean_text = TIMESTAMP_INLINE_RE.sub("", current_line.text).strip()
            words = clean_text.split()
            if not words:  # skip empty
                continue
            total_dur = max(0.2, end_time_sec - start_time_sec)
            per_word = total_dur / len(words)
            starts = [start_time_sec + i * per_word for i in range(len(words))]
            durations = [per_word] * len(words)

        karaoke_tokens = [
            f"{{\\K{max(1, int(round(d * 100)))}}}{w}" for w, d in zip(words, durations)
        ]
        current_line_text = " ".join(karaoke_tokens)

        # ---------------------------------------------
        # 2. NEXT line preview (plain text)
        # ---------------------------------------------
        next_line_text = ""
        if idx + 1 < len(lines):
            next_raw = TIMESTAMP_INLINE_RE.sub("", lines[idx + 1].text).strip()
            next_line_text = next_raw

        # ---------------------------------------------
        # 3. Combine into ASS text (preview above, current bottom)
        #    *Enhancement*: preview first so current anchors at bottom.
        # ---------------------------------------------
        fade_tag = "{\\fad(250,250)}"
        if next_line_text:
            combined_text = (
                f"{fade_tag}{{\\rNext}}{next_line_text}\\N{{\\rCurrent}}{current_line_text}"
            )
        else:
            combined_text = f"{fade_tag}{{\\rCurrent}}{current_line_text}"

        # ---------------------------------------------
        # 4. Event creation
        # ---------------------------------------------
        subs.events.append(
            pysubs2.SSAEvent(
                start=pysubs2.make_time(s=start_time_sec),
                end=pysubs2.make_time(s=end_time_sec),
                text=combined_text,
            )
        )

    # -------------------------------------------------------------------
    # Save & cache
    # -------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subs.save(str(output_path))
    try:
        cache_manager.cache_subtitles(lrc_path, output_path)
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Subtitle caching failed (non‑fatal): {e}")

    return output_path
