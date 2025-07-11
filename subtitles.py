import os
import re
from typing import List, Tuple

# Default ASS header and style
def get_ass_header() -> str:
    return '''[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KaraokeCurrent,Arial,80,&H00FFFFFF,&H00FF00FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1
Style: KaraokeNext,Arial,60,&H88FFFFFF,&H00FF00FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,1,2,10,10,10,1
Style: KaraokeNext2,Arial,50,&H66FFFFFF,&H00FF00FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,1,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
''' 

# Function to parse LRC file
def parse_lrc(lrc_path: str) -> List[Tuple[str, List[Tuple[str, str]]]]:
    lines = []
    with open(lrc_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Match line timestamp
            match = re.match(r'\[(\d+:\d+\.\d+)\](.*)', line)
            if match:
                line_time = match.group(1)
                text = match.group(2).strip()
                # Parse word-level segments
                word_segments = []
                word_matches = re.findall(r'<(\d+:\d+\.\d+)>([^<]*)', text)
                for ts, word in word_matches:
                    word = word.strip()
                    if word:
                        word_segments.append((ts, word))
                if not word_segments:
                    # Fallback to plain text if no word tags
                    word_segments = [('', text)]
                lines.append((line_time, word_segments))
    return lines

# Function to convert timestamp to ASS time format (H:MM:SS.cs)
def lrc_to_ass_time(lrc_time: str) -> str:
    if not lrc_time:
        return '0:00:00.00'
    minutes, rest = lrc_time.split(':')
    seconds, cents = rest.split('.')
    hours = int(minutes) // 60
    minutes = int(minutes) % 60
    return f"{hours}:{minutes:02d}:{seconds}.{cents.zfill(2)}"

def time_to_seconds(time_str: str) -> float:
    if not time_str:
        return 0.0
    minutes, rest = time_str.split(':')
    seconds, cents = rest.split('.')
    return int(minutes) * 60 + int(seconds) + int(cents) / 100

# Function to create karaoke effect for word-level
def create_karaoke_text(word_segments: List[Tuple[str, str]], line_end_seconds: float) -> str:
    if not word_segments:
        return ''
    karaoke_parts = []
    for i, (ts, word) in enumerate(word_segments):
        start_sec = time_to_seconds(ts)
        if i + 1 < len(word_segments):
            end_sec = time_to_seconds(word_segments[i+1][0])
        else:
            end_sec = line_end_seconds
        duration_cs = int((end_sec - start_sec) * 100)
        karaoke_parts.append(f'{{\k{duration_cs}}}{word} ')
    return ''.join(karaoke_parts).strip()

def create_plain_text(word_segments: List[Tuple[str, str]]) -> str:
    return ' '.join(word for _, word in word_segments)

def convert_lrc_to_ass(lrc_path: str, output_dir: str = '.') -> str:
    """
    Converts an LRC file to an ASS subtitle file with scrolling preview.

    Displays current line highlighted in center with karaoke if word-level.
    Shows up to two upcoming lines below in dimmer styles.
    Updates at each line change.

    Args:
        lrc_path (str): Path to the input LRC file.
        output_dir (str, optional): Directory to save the ASS file.

    Returns:
        str: Path to the saved ASS file.
    """
    # Infer type from filename
    filename = os.path.basename(lrc_path)
    is_word_level = 'word-level' in filename

    # Parse LRC
    lrc_lines = parse_lrc(lrc_path)

    # Extract artist and track from filename (assuming format kind_artist_track.lrc)
    parts = filename.replace('.lrc', '').split('_', 2)
    if len(parts) >= 3:
        artist = parts[1]
        track = parts[2]
    else:
        artist = 'Unknown'
        track = 'Unknown'

    # Output ASS path
    ass_filename = f"{artist}_{track}.ass"
    ass_path = os.path.join(output_dir, ass_filename)

    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(get_ass_header())

        num_lines = len(lrc_lines)
        for i in range(num_lines):
            # Current line timing
            line_start = lrc_to_ass_time(lrc_lines[i][0])
            if i + 1 < num_lines:
                line_end = lrc_to_ass_time(lrc_lines[i+1][0])
                line_end_seconds = time_to_seconds(lrc_lines[i+1][0])
            else:
                line_end = '99:59.99'
                line_end_seconds = time_to_seconds('99:59.99')

            # Current line
            word_segments = lrc_lines[i][1]
            if is_word_level and len(word_segments) > 1:
                ass_text = create_karaoke_text(word_segments, line_end_seconds)
            else:
                ass_text = create_plain_text(word_segments)
            f.write(f'Dialogue: 0,{line_start},{line_end},KaraokeCurrent,,0,0,0,,{{\pos(960,540)}}{ass_text}\n')

            # Next line if exists
            if i + 1 < num_lines:
                next_segments = lrc_lines[i+1][1]
                next_text = create_plain_text(next_segments)
                f.write(f'Dialogue: 0,{line_start},{line_end},KaraokeNext,,0,0,0,,{{\pos(960,640)}}{next_text}\n')

            # Next next line if exists
            if i + 2 < num_lines:
                next2_segments = lrc_lines[i+2][1]
                next2_text = create_plain_text(next2_segments)
                f.write(f'Dialogue: 0,{line_start},{line_end},KaraokeNext2,,0,0,0,,{{\pos(960,740)}}{next2_text}\n')

    print(f"Converted {lrc_path} to {ass_path}")
    return ass_path 