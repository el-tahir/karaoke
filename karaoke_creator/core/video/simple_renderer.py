"""
Simple video rendering functionality for karaoke videos.

This module handles creating karaoke videos by combining audio with 
ASS subtitles using FFmpeg.
"""

import os
import subprocess
import json
import hashlib
from pathlib import Path
from typing import Optional

from ...models.song_info import SongInfo, ProcessingResult
from ...utils.logging import LoggerMixin, log_performance
from ...utils.config import Config
from ...utils.file_utils import ensure_directory_exists

__all__ = ["VideoRenderer", "create_karaoke_video"]


class VideoRenderingError(Exception):
    """Exception raised when video rendering fails."""
    pass


class VideoRenderer(LoggerMixin):
    """
    Handles creating karaoke videos using FFmpeg.
    
    This class provides functionality to render videos by combining
    audio with ASS subtitles and configurable video settings.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the video renderer.
        
        Args:
            config: Configuration object with video settings
        """
        self.config = config or Config()
    
    @log_performance
    def create_karaoke_video(
        self,
        audio_file: str,
        ass_file: str,
        output_file: Optional[str] = None,
        song_info: Optional[SongInfo] = None
    ) -> ProcessingResult:
        """
        Create karaoke video by combining audio with ASS subtitles.
        
        Args:
            audio_file: Path to input audio file
            ass_file: Path to ASS subtitle file
            output_file: Optional output video path
            song_info: Optional song information for naming
            
        Returns:
            ProcessingResult with video file path and metadata
            
        Raises:
            VideoRenderingError: If video creation fails
        """
        self.logger.info(f"Creating karaoke video: {audio_file} + {ass_file}")
        
        # Validate input files
        if not os.path.exists(audio_file):
            raise VideoRenderingError(f"Audio file not found: {audio_file}")
        
        if not os.path.exists(ass_file):
            raise VideoRenderingError(f"ASS file not found: {ass_file}")
        
        # Generate output file path if not provided
        if output_file is None:
            if song_info:
                base_name = song_info.safe_filename_base
            else:
                base_name = Path(audio_file).stem
            output_file = f"{base_name}_karaoke.mp4"
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file) if os.path.dirname(output_file) else "."
        ensure_directory_exists(output_dir)
        
        # Check if video file already exists and is up-to-date
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            # Check if video is newer than source files
            video_mtime = os.path.getmtime(output_file)
            audio_mtime = os.path.getmtime(audio_file)
            ass_mtime = os.path.getmtime(ass_file)
            
            if video_mtime >= max(audio_mtime, ass_mtime):
                self.logger.info(f"Video file already exists and is up-to-date: {output_file}")
                
                file_size = os.path.getsize(output_file)
                duration = self._get_audio_duration(audio_file)
                
                return ProcessingResult.success_result(
                    output_file=output_file,
                    cached=True,
                    file_size_bytes=file_size,
                    file_size_mb=file_size / (1024 * 1024),
                    duration_seconds=duration,
                    video_format="mp4"
                )
        
        try:
            duration = self._get_audio_duration(audio_file)
            
            # Build ffmpeg command with configuration
            cmd = self._build_ffmpeg_command(audio_file, ass_file, output_file, duration)
            
            self.logger.debug(f"Running ffmpeg command: {' '.join(cmd)}")
            
            # Run ffmpeg
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if not os.path.exists(output_file):
                raise VideoRenderingError("Output video file was not created")
            
            file_size = os.path.getsize(output_file)
            
            self.logger.info(f"Successfully created karaoke video: {output_file}")
            
            return ProcessingResult.success_result(
                output_file=output_file,
                file_size_bytes=file_size,
                file_size_mb=file_size / (1024 * 1024),
                duration_seconds=duration,
                video_format="mp4",
                audio_source=audio_file,
                subtitle_source=ass_file
            )
            
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg error creating video: {e.stderr if e.stderr else e}"
            self.logger.error(error_msg)
            raise VideoRenderingError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error creating video: {e}"
            self.logger.error(error_msg)
            raise VideoRenderingError(error_msg) from e
    
    def _build_ffmpeg_command(
        self, 
        audio_file: str, 
        ass_file: str, 
        output_file: str, 
        duration: float
    ) -> list[str]:
        """
        Build the ffmpeg command with configuration.
        
        Args:
            audio_file: Input audio file
            ass_file: Input subtitle file
            output_file: Output video file
            duration: Audio duration in seconds
            
        Returns:
            List of command arguments
        """
        video_config = self.config.video
        
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-f", "lavfi",
            "-i", f"color=c={video_config.background_color}:s={video_config.resolution}:d={duration}",
            "-i", audio_file,
            "-vf", f"subtitles={ass_file}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-r", str(video_config.fps),
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_file,
        ]
        
        return cmd
    
    def _get_audio_duration(self, audio_file: str) -> float:
        """
        Get duration of audio file using ffprobe.
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Duration in seconds
            
        Raises:
            VideoRenderingError: If ffprobe fails
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                audio_file,
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            data = json.loads(result.stdout)
            
            return float(data["format"]["duration"])
            
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, ValueError) as e:
            raise VideoRenderingError(f"Failed to get audio duration: {e}") from e
    
    def render_videos(
        self,
        original_audio: str,
        instrumental_audio: str,
        ass_file: str,
        output_dir: str,
        song_info: SongInfo
    ) -> ProcessingResult:
        """
        Render both karaoke and original versions of the video.
        
        Args:
            original_audio: Path to original audio with vocals
            instrumental_audio: Path to instrumental audio
            ass_file: Path to ASS subtitle file
            output_dir: Output directory
            song_info: Song information
            
        Returns:
            ProcessingResult with video file paths
        """
        ensure_directory_exists(output_dir)
        
        # Create karaoke version (instrumental)
        karaoke_filename = f"{song_info.safe_filename_base}_karaoke.mp4"
        karaoke_path = os.path.join(output_dir, karaoke_filename)
        
        karaoke_result = self.create_karaoke_video(
            instrumental_audio, ass_file, karaoke_path, song_info
        )
        
        if not karaoke_result.success:
            return karaoke_result
        
        # Create original version if configured
        original_video = None
        original_file_size = 0
        if self.config.create_both_versions and original_audio:
            original_filename = f"{song_info.safe_filename_base}_original.mp4"
            original_path = os.path.join(output_dir, original_filename)
            
            original_result = self.create_karaoke_video(
                original_audio, ass_file, original_path, song_info
            )
            
            if original_result.success:
                original_video = original_result.output_file
                original_file_size = original_result.metadata.get('file_size_mb', 0)
        
        return ProcessingResult.success_result(
            output_file=karaoke_result.output_file,
            karaoke_video=karaoke_result.output_file,
            original_video=original_video,
            total_file_size_mb=(
                karaoke_result.metadata.get('file_size_mb', 0) + original_file_size
            )
        )


def create_karaoke_video(
    audio_file: str,
    ass_file: str,
    output_file: Optional[str] = None,
    config: Optional[Config] = None,
    song_info: Optional[SongInfo] = None
) -> ProcessingResult:
    """
    Convenience function to create karaoke video.
    
    Args:
        audio_file: Path to input audio file
        ass_file: Path to ASS subtitle file
        output_file: Optional output video path
        config: Optional configuration
        song_info: Optional song information
        
    Returns:
        ProcessingResult with video information
    """
    renderer = VideoRenderer(config)
    return renderer.create_karaoke_video(audio_file, ass_file, output_file, song_info) 