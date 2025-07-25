"""
ASS subtitle conversion functionality for karaoke videos.

This module handles converting LRC lyrics files to ASS subtitle format
with karaoke effects and animations.
"""

import os
import re
import json
import hashlib
from typing import List, Tuple, Optional
from pathlib import Path

from ...models.song_info import SongInfo, ProcessingResult
from ...utils.logging import LoggerMixin, log_performance
from ...utils.config import Config
from ...utils.file_utils import ensure_directory_exists

__all__ = ["AssConverter", "convert_lrc_to_ass"]


class SubtitleGenerationError(Exception):
    """Exception raised when subtitle generation fails."""
    pass


class AssConverter(LoggerMixin):
    """
    Handles converting LRC lyrics to ASS subtitle format.
    
    This class provides functionality to convert LRC files to ASS format
    with karaoke effects, animations, and customizable styling.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the ASS converter.
        
        Args:
            config: Configuration object with video/subtitle settings
        """
        self.config = config or Config()
    
    @log_performance
    def convert_lrc_to_ass(
        self,
        lrc_path: str,
        output_dir: str,
        song_info: Optional[SongInfo] = None
    ) -> ProcessingResult:
        """
        Convert an LRC file to ASS subtitle format.
        
        Args:
            lrc_path: Path to input LRC file
            output_dir: Directory to save ASS file
            song_info: Optional song information for naming
            
        Returns:
            ProcessingResult with ASS file path and metadata
            
        Raises:
            SubtitleGenerationError: If conversion fails
        """
        self.logger.info(f"Converting LRC to ASS: {lrc_path}")
        
        # Validate input file
        if not os.path.exists(lrc_path):
            raise SubtitleGenerationError(f"LRC file not found: {lrc_path}")
        
        # Ensure output directory exists
        ensure_directory_exists(output_dir)
        
        # Check for cached ASS file
        expected_ass_file = self._get_expected_ass_file(lrc_path, output_dir, song_info)
        if expected_ass_file and os.path.exists(expected_ass_file) and os.path.getsize(expected_ass_file) > 0:
            # Check if ASS file is newer than LRC file
            ass_mtime = os.path.getmtime(expected_ass_file)
            lrc_mtime = os.path.getmtime(lrc_path)
            
            if ass_mtime >= lrc_mtime:
                self.logger.info(f"ASS file already exists and is up-to-date: {expected_ass_file}")
                
                return ProcessingResult.success_result(
                    output_file=expected_ass_file,
                    cached=True,
                    lrc_source=lrc_path
                )
        
        try:
            # Convert LRC to ASS
            ass_path = self._convert_lrc_to_ass_internal(lrc_path, output_dir, song_info)
            
            self.logger.info(f"Successfully converted LRC to ASS: {ass_path}")
            
            # Get file information
            file_size = os.path.getsize(ass_path)
            
            return ProcessingResult.success_result(
                output_file=ass_path,
                file_size_bytes=file_size,
                file_size_mb=file_size / (1024 * 1024),
                lrc_source=lrc_path,
                subtitle_format="ass"
            )
            
        except Exception as e:
            error_msg = f"Failed to convert LRC to ASS: {e}"
            self.logger.error(error_msg)
            raise SubtitleGenerationError(error_msg) from e
    
    def _get_expected_ass_file(
        self,
        lrc_path: str,
        output_dir: str,
        song_info: Optional[SongInfo] = None
    ) -> Optional[str]:
        """
        Get the expected ASS file path.
        
        Args:
            lrc_path: Input LRC file path
            output_dir: Output directory
            song_info: Optional song information
            
        Returns:
            Expected ASS file path
        """
        if song_info:
            # Use song info for consistent naming
            ass_filename = f"{song_info.safe_filename_base}.ass"
        else:
            # Derive from LRC filename
            lrc_filename = os.path.basename(lrc_path)
            base_name = lrc_filename.replace('.lrc', '')
            
            # Remove word-level/line-level prefixes if present
            if base_name.startswith(('word-level_', 'line-level_')):
                parts = base_name.split('_', 1)
                if len(parts) > 1:
                    base_name = parts[1]
            
            ass_filename = f"{base_name}.ass"
        
        return os.path.join(output_dir, ass_filename)
    
    def _convert_lrc_to_ass_internal(
        self,
        lrc_path: str,
        output_dir: str,
        song_info: Optional[SongInfo] = None
    ) -> str:
        """
        Internal method to perform the actual LRC to ASS conversion.
        
        Args:
            lrc_path: Input LRC file path
            output_dir: Output directory
            song_info: Optional song information
            
        Returns:
            Path to generated ASS file
        """
        # Use the original conversion logic but with config integration
        if not os.path.isfile(lrc_path):
            raise SubtitleGenerationError(f"LRC file not found: {lrc_path}")

        filename = os.path.basename(lrc_path)
        is_word_level = "word-level" in filename

        lrc_lines = _parse_lrc(lrc_path)
        if not lrc_lines:
            raise SubtitleGenerationError("No timestamped lyrics found in LRC file")

        # Generate output filename
        ass_path = self._get_expected_ass_file(lrc_path, output_dir, song_info)

        with open(ass_path, "w", encoding="utf-8") as fp:
            fp.write(self._get_ass_header())

            trans_dur_sec = self.config.video.transition_duration
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
                current_tag = f"{{\\move(960,520,960,400,{move_start_ms},{dur_ms})\\fad(0,{trans_ms})}}"
                fp.write(
                    f"Dialogue: 0,{start_ts},{end_ts},KaraokeCurrent,,0,0,0,,{current_tag}{ass_text}\n"
                )

                # Next line (if exists)
                if idx + 1 < len(lrc_lines):
                    next_text = _plain_text(lrc_lines[idx + 1][1])
                    next_tag = f"{{\\move(960,660,960,520,{move_start_ms},{dur_ms})}}"
                    fp.write(
                        f"Dialogue: 0,{start_ts},{end_ts},KaraokeNext,,0,0,0,,{next_tag}{next_text}\n"
                    )

                # Next2 line (if exists)
                if idx + 2 < len(lrc_lines):
                    next2_text = _plain_text(lrc_lines[idx + 2][1])
                    next2_tag = f"{{\\move(960,800,960,660,{move_start_ms},{dur_ms})\\fad({trans_ms},0)}}"
                    fp.write(
                        f"Dialogue: 0,{start_ts},{end_ts},KaraokeNext2,,0,0,0,,{next2_tag}{next2_text}\n"
                    )

        return ass_path
    
    def _get_ass_header(self) -> str:
        """
        Generate ASS header with configured styles.
        
        Returns:
            ASS header string with style definitions
        """
        video_config = self.config.video
        
        return (
            "[Script Info]\n"
            "Title: Karaoke Subtitles\n"
            "ScriptType: v4.00+\n"
            "WrapStyle: 0\n"
            "ScaledBorderAndShadow: yes\n"
            "YCbCr Matrix: TV.601\n"
            f"PlayResX: {video_config.resolution.split('x')[0]}\n"
            f"PlayResY: {video_config.resolution.split('x')[1]}\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: KaraokeCurrent,{video_config.font_name},{video_config.current_line_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,3,2,10,10,10,1\n"
            f"Style: KaraokeNext,{video_config.font_name},{video_config.preview_line_size},&H88FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1\n"
            f"Style: KaraokeNext2,{video_config.font_name},{video_config.preview_line2_size},&H66FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,1,2,10,10,10,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )


# ============================== Helpers ===================================




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


def convert_lrc_to_ass(
    lrc_path: str, 
    output_dir: str = ".", 
    config: Optional[Config] = None,
    song_info: Optional[SongInfo] = None
) -> ProcessingResult:
    """
    Convenience function to convert LRC to ASS.
    
    Args:
        lrc_path: Path to input LRC file
        output_dir: Output directory
        config: Optional configuration
        song_info: Optional song information
        
    Returns:
        ProcessingResult with ASS file information
    """
    converter = AssConverter(config)
    return converter.convert_lrc_to_ass(lrc_path, output_dir, song_info) 