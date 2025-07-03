"""Subtitle generation utility.

Converts an LRC lyrics file into an Advanced SubStation Alpha (.ass) subtitle
file with word-by-word karaoke highlighting using \K timing tags.

CLI Usage
---------
python -m karaoke.subtitles --lrc lyrics/Watching\ TV.lrc [--output-dir subtitles]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

import pylrc  # type: ignore
import pysubs2  # type: ignore

DEFAULT_OUTPUT_DIR = Path("subtitles")

TIMESTAMP_BRACKET_RE = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2})]")
TIMESTAMP_INLINE_RE = re.compile(r"<(\d{2}):(\d{2})\.(\d{2})>")


def _components_to_seconds(mins: str, secs: str, centis: str) -> float:
    """Helper converting regex capture groups to seconds float."""
    return int(mins) * 60 + int(secs) + int(centis) / 100.0


def _parse_inline_timings(text: str):
    """Return list[(word, start_time_sec)] if inline <mm:ss.xx> timings exist.

    If the text contains no inline timing tags, returns None.
    """
    matches = list(TIMESTAMP_INLINE_RE.finditer(text))
    if not matches:
        return None

    tokens = []
    for idx, match in enumerate(matches):
        start_sec = _components_to_seconds(*match.groups())
        # The word/segment text is everything after this tag up to the next tag
        start_idx = match.end()
        end_idx = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        word_text = text[start_idx:end_idx].strip()
        if word_text:
            tokens.append((word_text, start_sec))
    return tokens


def lrc_to_ass(lrc_path: Path, output_path: Path) -> Path:
    """Convert an LRC file to an ASS subtitle file.

    Behaviour:
    * If the LRC line contains inline `<mm:ss.xx>` word-level timings, create
      animated karaoke using `\K` tags.
    * Otherwise, render the entire line statically (no animation).
    """

    # Parse LRC
    lrc = pylrc.parse(lrc_path.read_text(encoding="utf-8"))  # type: ignore

    # Sort by start time to guarantee chronological order
    lines = sorted(lrc, key=lambda l: l.time)

    subs = pysubs2.SSAFile()

    # -------------------------- Styles ----------------------------------------
    # Static subtitles
    style_default = pysubs2.SSAStyle("Default")
    # Set text colour to white (RGBA)
    style_default.primarycolor = pysubs2.Color(255, 255, 255, 0)
    # Centre text on both axes (ASS alignment 5)
    style_default.alignment = pysubs2.Alignment.MIDDLE_CENTER
    subs.styles["Default"] = style_default

    # Karaoke (animated) style
    style_karaoke = pysubs2.SSAStyle("Karaoke")
    style_karaoke.primarycolor = pysubs2.Color(255, 255, 255, 0)  # filled colour (white)
    style_karaoke.secondarycolor = pysubs2.Color(255, 0, 0, 0)  # highlight colour (red)
    style_karaoke.alignment = pysubs2.Alignment.MIDDLE_CENTER
    # Enable karaoke effect via event-level override tags, so no style-level change necessary
    subs.styles["Karaoke"] = style_karaoke

    # -------------------------- Events ----------------------------------------
    for idx, line in enumerate(lines):
        start_sec = line.time
        # Use next line's start as this line's end, or +2s fallback
        if idx < len(lines) - 1:
            end_sec = lines[idx + 1].time
        else:
            end_sec = start_sec + 2.0

        tokens = _parse_inline_timings(line.text)

        if tokens:  # Word-level timings available – animated karaoke
            words, starts = zip(*tokens)  # type: ignore

            # Compute per-word durations
            durations: List[float] = []
            for i, t_start in enumerate(starts):
                if i + 1 < len(starts):
                    durations.append(starts[i + 1] - t_start)
                else:
                    durations.append(max(0.1, end_sec - t_start))  # min 0.1s fallback

            # Build ASS text with cumulative \K tags (centiseconds)
            ass_tokens: List[str] = []
            for word, dur in zip(words, durations):
                centi = max(1, int(round(dur * 100)))
                ass_tokens.append(f"{{\\K{centi}}}{word}")

            ass_text = " ".join(ass_tokens)
            style_name = "Karaoke"

        else:  # No word-level timings – static line
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

    # Save ---------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subs.save(str(output_path))
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:  # pragma: no cover
    p = argparse.ArgumentParser(description="Convert LRC to ASS with karaoke highlighting.")
    p.add_argument("--lrc", required=True, help="Path to .lrc file")
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory to save .ass file")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    args = parse_args(argv)
    lrc_path = Path(args.lrc).expanduser().resolve()
    if not lrc_path.exists():
        print(f"LRC file not found: {lrc_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    ass_name = lrc_path.with_suffix(".ass").name
    output_path = out_dir / ass_name
    try:
        lrc_to_ass(lrc_path, output_path)
        print(f"ASS subtitles saved to {output_path}")
    except Exception as e:
        print("Error generating ASS:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main() 