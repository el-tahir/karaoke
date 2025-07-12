"""
Data models for song information and lyrics.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import json


@dataclass
class SongInfo:
    """Information about a song."""
    
    artist: str
    track: str
    youtube_url: str
    duration: Optional[float] = None
    title: Optional[str] = None
    uploader: Optional[str] = None
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    
    def __post_init__(self):
        """Validate and clean up song info after initialization."""
        self.artist = self.artist.strip()
        self.track = self.track.strip()
        
        if not self.artist:
            raise ValueError("Artist name cannot be empty")
        if not self.track:
            raise ValueError("Track name cannot be empty")
        if not self.youtube_url:
            raise ValueError("YouTube URL cannot be empty")
    
    @property
    def safe_artist(self) -> str:
        """Get filesystem-safe artist name."""
        from ..utils.file_utils import sanitize_filename
        return sanitize_filename(self.artist)
    
    @property
    def safe_track(self) -> str:
        """Get filesystem-safe track name."""
        from ..utils.file_utils import sanitize_filename
        return sanitize_filename(self.track)
    
    @property
    def safe_filename_base(self) -> str:
        """Get a safe base filename for this song."""
        return f"{self.safe_artist}_{self.safe_track}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "artist": self.artist,
            "track": self.track,
            "youtube_url": self.youtube_url,
            "duration": self.duration,
            "title": self.title,
            "uploader": self.uploader,
            "upload_date": self.upload_date,
            "view_count": self.view_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SongInfo":
        """Create SongInfo from dictionary."""
        return cls(**data)
    
    def save_to_file(self, file_path: str) -> None:
        """Save song info to JSON file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> "SongInfo":
        """Load song info from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class WordSegment:
    """A word segment with timing information."""
    
    timestamp: str  # In MM:SS.cc format
    text: str
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    duration_seconds: Optional[float] = None
    
    def __post_init__(self):
        """Calculate timing information."""
        if self.timestamp:
            self.start_seconds = self._timestamp_to_seconds(self.timestamp)
    
    @staticmethod
    def _timestamp_to_seconds(timestamp: str) -> float:
        """Convert MM:SS.cc timestamp to seconds."""
        if not timestamp:
            return 0.0
        
        try:
            minutes, rest = timestamp.split(':')
            seconds, centiseconds = rest.split('.')
            return int(minutes) * 60 + int(seconds) + int(centiseconds.ljust(2, '0')) / 100
        except (ValueError, IndexError):
            return 0.0
    
    def set_end_time(self, end_timestamp: str) -> None:
        """Set the end time and calculate duration."""
        self.end_seconds = self._timestamp_to_seconds(end_timestamp)
        if self.start_seconds is not None and self.end_seconds is not None:
            self.duration_seconds = self.end_seconds - self.start_seconds


@dataclass
class LyricLine:
    """A line of lyrics with timing and word segments."""
    
    timestamp: str  # In MM:SS.cc format
    word_segments: List[WordSegment] = field(default_factory=list)
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    duration_seconds: Optional[float] = None
    
    def __post_init__(self):
        """Calculate timing information."""
        if self.timestamp:
            self.start_seconds = WordSegment._timestamp_to_seconds(self.timestamp)
    
    @property
    def text(self) -> str:
        """Get the full text of this line."""
        return ' '.join(segment.text for segment in self.word_segments)
    
    @property
    def is_word_level(self) -> bool:
        """Check if this line has word-level timing."""
        return len(self.word_segments) > 1 or (
            len(self.word_segments) == 1 and self.word_segments[0].timestamp
        )
    
    def set_end_time(self, end_timestamp: str) -> None:
        """Set the end time and calculate duration."""
        self.end_seconds = WordSegment._timestamp_to_seconds(end_timestamp)
        if self.start_seconds is not None and self.end_seconds is not None:
            self.duration_seconds = self.end_seconds - self.start_seconds
        
        # Update word segment timings
        if self.word_segments and self.end_seconds is not None:
            for i, segment in enumerate(self.word_segments):
                if i + 1 < len(self.word_segments):
                    segment.set_end_time(self.word_segments[i + 1].timestamp)
                else:
                    # Last segment ends when the line ends
                    segment.end_seconds = self.end_seconds
                    if segment.start_seconds is not None:
                        segment.duration_seconds = segment.end_seconds - segment.start_seconds
    
    def add_word_segment(self, timestamp: str, text: str) -> None:
        """Add a word segment to this line."""
        segment = WordSegment(timestamp=timestamp, text=text.strip())
        if segment.text:  # Only add non-empty segments
            self.word_segments.append(segment)


@dataclass
class Lyrics:
    """Complete lyrics with timing information."""
    
    lines: List[LyricLine] = field(default_factory=list)
    is_word_level: bool = False
    language: Optional[str] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        """Process lyrics after initialization."""
        self._calculate_line_endings()
        self._detect_word_level()
    
    def _calculate_line_endings(self) -> None:
        """Calculate end times for all lines."""
        for i, line in enumerate(self.lines):
            if i + 1 < len(self.lines):
                # Line ends when next line starts
                next_line = self.lines[i + 1]
                line.set_end_time(next_line.timestamp)
            else:
                # Last line gets an arbitrary duration
                if line.start_seconds is not None:
                    end_time_seconds = line.start_seconds + 5.0  # 5 second default
                    minutes = int(end_time_seconds // 60)
                    seconds = end_time_seconds % 60
                    end_timestamp = f"{minutes}:{int(seconds):02d}.{int((seconds % 1) * 100):02d}"
                    line.set_end_time(end_timestamp)
    
    def _detect_word_level(self) -> None:
        """Detect if lyrics contain word-level timing."""
        self.is_word_level = any(line.is_word_level for line in self.lines)
    
    def add_line(self, timestamp: str, text: str, word_segments: Optional[List[Tuple[str, str]]] = None) -> None:
        """Add a lyric line."""
        line = LyricLine(timestamp=timestamp)
        
        if word_segments:
            for ts, word in word_segments:
                line.add_word_segment(ts, word)
        elif text.strip():
            # Add as single segment with empty timestamp for line-level lyrics
            line.add_word_segment('', text.strip())
        
        if line.word_segments:  # Only add lines with content
            self.lines.append(line)
    
    @property
    def total_duration(self) -> Optional[float]:
        """Get total duration of lyrics."""
        if not self.lines:
            return None
        
        last_line = self.lines[-1]
        return last_line.end_seconds if last_line.end_seconds else None
    
    @property
    def line_count(self) -> int:
        """Get number of lyric lines."""
        return len(self.lines)
    
    def get_lines_at_time(self, time_seconds: float) -> List[LyricLine]:
        """Get lyrics lines that should be displayed at a given time."""
        return [line for line in self.lines 
                if line.start_seconds is not None 
                and line.end_seconds is not None
                and line.start_seconds <= time_seconds < line.end_seconds]


@dataclass
class ProcessingResult:
    """Result of a processing step in the pipeline."""
    
    success: bool
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success_result(cls, output_file: str, processing_time: Optional[float] = None, **metadata) -> "ProcessingResult":
        """Create a successful result."""
        return cls(
            success=True,
            output_file=output_file,
            processing_time=processing_time,
            metadata=metadata
        )
    
    @classmethod
    def error_result(cls, error_message: str, processing_time: Optional[float] = None) -> "ProcessingResult":
        """Create an error result."""
        return cls(
            success=False,
            error_message=error_message,
            processing_time=processing_time
        )