import os
import re
from typing import List, Tuple

__all__ = ["convert_lrc_to_ass"]

# ============================== Helpers ===================================


def _get_ass_header() -> str:
    """Return a default ASS header with three styles for karaoke display."""
    return (
        "[Script Info]\n"
        "Title: Karaoke Subtitles\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "YCbCr Matrix: TV.601\n"
        "PlayResX: 1920\n"
        "PlayResY: 1080\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: KaraokeCurrent,Arial,80,&H00FFFFFF,&H00FF00FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1\n"
        "Style: KaraokeNext,Arial,60,&H88FFFFFF,&H00FF00FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,1,2,10,10,10,1\n"
        "Style: KaraokeNext2,Arial,50,&H66FFFFFF,&H00FF00FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,1,2,10,10,10,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )


# =========================== Parsing utilities ============================


def _parse_lrc(lrc_path: str) -> List[Tuple[str, List[Tuple[str, str]]]]:
    """Parse an LRC file into timestamped lyric + optional word-level data."""
    lines: List[Tuple[str, List[Tuple[str, str]]]] = []
    with open(lrc_path, "r", encoding="utf-8", errors="ignore") as fp:
        for raw_line in fp:
            line = raw_line.strip()
            if not line:
                continue
            match = re.match(r"\[(\d+:\d+\.\d+)\](.*)", line)
            if not match:
                continue
            line_time, text = match.groups()
            text = text.strip()
            # Extract word-level segments if present ( <mm:ss.xx>word )
            word_segments: List[Tuple[str, str]] = re.findall(r"<(\d+:\d+\.\d+)>([^<]*)", text)
            if not word_segments:
                word_segments = [("", text)]
            lines.append((line_time, [(ts, w.strip()) for ts, w in word_segments if w.strip()]))
    return lines


def _time_to_seconds(time_str: str) -> float:
    if not time_str:
        return 0.0
    minutes, rest = time_str.split(":")
    seconds, cents = rest.split(".")
    return int(minutes) * 60 + int(seconds) + int(cents.ljust(2, "0")) / 100


def _seconds_to_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# ============================= Main logic ================================


def _create_karaoke_text(word_segments: List[Tuple[str, str]], line_end_seconds: float) -> str:
    """Build ASS karaoke control codes for word-level timing."""
    if not word_segments:
        return ""
    parts = []
    for idx, (ts, word) in enumerate(word_segments):
        start_sec = _time_to_seconds(ts) if ts else 0.0
        if idx + 1 < len(word_segments):
            end_sec = _time_to_seconds(word_segments[idx + 1][0])
        else:
            end_sec = line_end_seconds
        duration_cs = int((end_sec - start_sec) * 100)
        parts.append(f"{{\\k{duration_cs}}}{word} ")
    return "".join(parts).strip()


def _plain_text(word_segments: List[Tuple[str, str]]) -> str:
    return " ".join(word for _, word in word_segments)


def convert_lrc_to_ass(lrc_path: str, output_dir: str = ".") -> str:
    """Convert an LRC file to an ASS subtitle file.

    The resulting ASS displays the current line in the center with karaoke
    effects when word-level timings are available. Two upcoming lines are
    shown underneath with dimmed styles. Simple sliding animations are
    added for a smoother experience.
    """
    if not os.path.isfile(lrc_path):
        raise FileNotFoundError(lrc_path)

    filename = os.path.basename(lrc_path)
    is_word_level = "word-level" in filename

    lrc_lines = _parse_lrc(lrc_path)
    if not lrc_lines:
        raise ValueError("No timestamped lyrics found in LRC file")

    # Derive artist/track (fallback if pattern unexpected)
    parts = filename.replace(".lrc", "").split("_", 2)
    artist = parts[1] if len(parts) >= 3 else "Unknown"
    track = parts[2] if len(parts) >= 3 else parts[0]

    ass_filename = f"{artist}_{track}.ass"
    ass_path = os.path.join(output_dir, ass_filename)

    with open(ass_path, "w", encoding="utf-8") as fp:
        fp.write(_get_ass_header())

        trans_dur_sec = 0.3
        for idx, (line_time, word_segments) in enumerate(lrc_lines):
            start_sec = _time_to_seconds(line_time)
            end_sec = (
                _time_to_seconds(lrc_lines[idx + 1][0])
                if idx + 1 < len(lrc_lines)
                else start_sec + 5.0
            )
            dur_sec = max(0.1, end_sec - start_sec)

            start_ts = _seconds_to_ass_time(start_sec)
            end_ts = _seconds_to_ass_time(end_sec)

            dur_ms = int(dur_sec * 1000)
            trans_ms = min(int(trans_dur_sec * 1000), dur_ms // 2)
            move_start_ms = dur_ms - trans_ms if dur_ms > trans_ms else 0

            if is_word_level and len(word_segments) > 1:
                ass_text = _create_karaoke_text(word_segments, end_sec)
            else:
                ass_text = _plain_text(word_segments)

            # Current line
            current_tag = f"{{\\move(960,540,960,440,{move_start_ms},{dur_ms})\\fad(0,{trans_ms})}}"
            fp.write(
                f"Dialogue: 0,{start_ts},{end_ts},KaraokeCurrent,,0,0,0,,{current_tag}{ass_text}\n"
            )

            # Next line (if exists)
            if idx + 1 < len(lrc_lines):
                next_text = _plain_text(lrc_lines[idx + 1][1])
                next_tag = f"{{\\move(960,640,960,540,{move_start_ms},{dur_ms})}}"
                fp.write(
                    f"Dialogue: 0,{start_ts},{end_ts},KaraokeNext,,0,0,0,,{next_tag}{next_text}\n"
                )

            # Next2 line (if exists)
            if idx + 2 < len(lrc_lines):
                next2_text = _plain_text(lrc_lines[idx + 2][1])
                next2_tag = f"{{\\move(960,740,960,640,{move_start_ms},{dur_ms})\\fad({trans_ms},0)}}"
                fp.write(
                    f"Dialogue: 0,{start_ts},{end_ts},KaraokeNext2,,0,0,0,,{next2_tag}{next2_text}\n"
                )

    return ass_path 