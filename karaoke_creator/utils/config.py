"""
Configuration management for karaoke creator.

Provides centralized configuration handling with defaults and validation.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class AudioConfig:
    """Configuration for audio processing."""
    
    # Audio separation model
    separation_model: str = "UVR_MDXNET_KARA_2.onnx"
    
    # Audio format settings
    audio_format: str = "mp3"
    audio_quality: str = "320k"
    
    # Processing options
    use_gpu: bool = True
    normalize_audio: bool = True


@dataclass
class VideoConfig:
    """Configuration for video generation."""
    
    # Video output settings
    resolution: str = "1280x720"
    background_color: str = "black"
    fps: int = 30
    
    # Subtitle styling
    font_name: str = "Arial"
    current_line_size: int = 80
    preview_line_size: int = 60
    preview_line2_size: int = 50
    
    # Animation settings
    transition_duration: float = 0.3
    fade_in_duration: float = 0.1
    fade_out_duration: float = 0.3


@dataclass
class LyricsConfig:
    """Configuration for lyrics processing."""
    
    # Lyrics search preferences
    prefer_word_level: bool = False
    fallback_to_line_level: bool = True
    
    # Language processing
    romanize_japanese: bool = True
    japanese_romanization_style: str = "hepburn"
    
    # Timing adjustments
    minimum_word_duration: float = 0.1
    line_gap_padding: float = 0.5


@dataclass
class Config:
    """Main configuration class for karaoke creator."""
    
    # Directory settings
    output_dir: str = "downloads"
    final_videos_dir: str = "final_videos"
    temp_dir: str = "temp"
    
    # Processing configurations
    audio: AudioConfig = field(default_factory=AudioConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    lyrics: LyricsConfig = field(default_factory=LyricsConfig)
    
    # External tool paths
    ffmpeg_path: Optional[str] = None
    ffprobe_path: Optional[str] = None
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Processing options
    cleanup_temp_files: bool = True
    create_both_versions: bool = True  # Create both karaoke and original versions
    skip_separation: bool = False  # Skip audio separation (for instrumental-only mode)
    
    @classmethod
    def load_from_file(cls, config_path: str) -> "Config":
        """Load configuration from a JSON or YAML file."""
        import json
        
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {config_path.suffix}")
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create configuration from dictionary."""
        audio_data = data.get('audio', {})
        video_data = data.get('video', {})
        lyrics_data = data.get('lyrics', {})
        
        return cls(
            output_dir=data.get('output_dir', 'downloads'),
            final_videos_dir=data.get('final_videos_dir', 'final_videos'),
            temp_dir=data.get('temp_dir', 'temp'),
            audio=AudioConfig(**audio_data),
            video=VideoConfig(**video_data),
            lyrics=LyricsConfig(**lyrics_data),
            ffmpeg_path=data.get('ffmpeg_path'),
            ffprobe_path=data.get('ffprobe_path'),
            log_level=data.get('log_level', 'INFO'),
            log_format=data.get('log_format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            cleanup_temp_files=data.get('cleanup_temp_files', True),
            create_both_versions=data.get('create_both_versions', True),
            skip_separation=data.get('skip_separation', False),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'output_dir': self.output_dir,
            'final_videos_dir': self.final_videos_dir,
            'temp_dir': self.temp_dir,
            'audio': {
                'separation_model': self.audio.separation_model,
                'audio_format': self.audio.audio_format,
                'audio_quality': self.audio.audio_quality,
                'use_gpu': self.audio.use_gpu,
                'normalize_audio': self.audio.normalize_audio,
            },
            'video': {
                'resolution': self.video.resolution,
                'background_color': self.video.background_color,
                'fps': self.video.fps,
                'font_name': self.video.font_name,
                'current_line_size': self.video.current_line_size,
                'preview_line_size': self.video.preview_line_size,
                'preview_line2_size': self.video.preview_line2_size,
                'transition_duration': self.video.transition_duration,
                'fade_in_duration': self.video.fade_in_duration,
                'fade_out_duration': self.video.fade_out_duration,
            },
            'lyrics': {
                'prefer_word_level': self.lyrics.prefer_word_level,
                'fallback_to_line_level': self.lyrics.fallback_to_line_level,
                'romanize_japanese': self.lyrics.romanize_japanese,
                'japanese_romanization_style': self.lyrics.japanese_romanization_style,
                'minimum_word_duration': self.lyrics.minimum_word_duration,
                'line_gap_padding': self.lyrics.line_gap_padding,
            },
            'ffmpeg_path': self.ffmpeg_path,
            'ffprobe_path': self.ffprobe_path,
            'log_level': self.log_level,
            'log_format': self.log_format,
            'cleanup_temp_files': self.cleanup_temp_files,
            'create_both_versions': self.create_both_versions,
            'skip_separation': self.skip_separation,
        }
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to a JSON file."""
        import json
        
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def validate(self) -> None:
        """Validate configuration settings."""
        errors = []
        
        # Check required directories
        if not self.output_dir:
            errors.append("output_dir cannot be empty")
        
        if not self.final_videos_dir:
            errors.append("final_videos_dir cannot be empty")
        
        # Validate video settings
        if self.video.fps <= 0:
            errors.append("video.fps must be positive")
        
        if self.video.current_line_size <= 0:
            errors.append("video.current_line_size must be positive")
        
        # Validate audio settings
        if self.audio.audio_format not in ["mp3", "wav", "flac", "m4a"]:
            errors.append(f"Unsupported audio format: {self.audio.audio_format}")
        
        # Validate lyrics settings
        if self.lyrics.minimum_word_duration < 0:
            errors.append("lyrics.minimum_word_duration cannot be negative")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [self.output_dir, self.final_videos_dir, self.temp_dir]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)