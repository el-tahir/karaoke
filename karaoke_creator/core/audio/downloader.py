"""
Audio downloading functionality using yt-dlp.

This module handles downloading audio from YouTube URLs and converting
to the desired format.
"""

import os
import yt_dlp
from pathlib import Path
from typing import Optional, Dict, Any

from ...models.song_info import SongInfo, ProcessingResult
from ...utils.logging import LoggerMixin, log_performance
from ...utils.config import Config
from ...utils.file_utils import ensure_directory_exists, find_newest_file


class AudioDownloadError(Exception):
    """Exception raised when audio download fails."""
    pass


class AudioDownloader(LoggerMixin):
    """
    Handles downloading audio from YouTube URLs.
    
    This class provides functionality to download and convert audio from
    YouTube videos to various formats.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the audio downloader.
        
        Args:
            config: Configuration object with audio settings
        """
        self.config = config or Config()
        
        # Create base yt-dlp options
        self.base_opts = self._create_ydl_options()
    
    def _create_ydl_options(self) -> Dict[str, Any]:
        """
        Create yt-dlp options based on configuration.
        
        Returns:
            Dictionary of yt-dlp options
        """
        # Audio format and quality settings
        audio_format = self.config.audio.audio_format
        audio_quality = self.config.audio.audio_quality
        
        # Post-processor configuration for audio extraction
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format,
            'preferredquality': audio_quality.replace('k', '') if 'k' in audio_quality else audio_quality,
        }]
        
        # Note: Audio normalization disabled for compatibility
        # if self.config.audio.normalize_audio:
        #     postprocessors.append({
        #         'key': 'FFmpegNormalize',
        #         'when': 'post_process',
        #     })
        
        return {
            # Select best audio quality available
            'format': 'bestaudio/best',
            
            # Post-processing for audio extraction
            'postprocessors': postprocessors,
            
            # Output filename template
            'outtmpl': '%(title)s.%(ext)s',
            
            # Disable verbose output
            'quiet': True,
            
            # Continue on download errors
            'ignoreerrors': False,
            
            # Retry settings
            'retries': 3,
            'fragment_retries': 3,
        }
    
    @log_performance
    def download_audio(
        self,
        song_info: SongInfo,
        output_dir: str,
        custom_filename: Optional[str] = None
    ) -> ProcessingResult:
        """
        Download audio from YouTube URL.
        
        Args:
            song_info: Song information containing YouTube URL
            output_dir: Directory to save the audio file
            custom_filename: Optional custom filename (without extension)
            
        Returns:
            ProcessingResult with download information
            
        Raises:
            AudioDownloadError: If download fails
        """
        self.logger.info(f"Downloading audio for: {song_info.artist} - {song_info.track} from {song_info.youtube_url}")
        
        # Ensure output directory exists
        ensure_directory_exists(output_dir)
        
        # Check if audio file already exists
        expected_file = self._get_expected_audio_file(song_info, output_dir, custom_filename)
        if expected_file and os.path.exists(expected_file) and os.path.getsize(expected_file) > 0:
            self.logger.info(f"Audio file already exists, skipping download: {expected_file}")
            
            # Get file size for metadata
            file_size = os.path.getsize(expected_file)
            
            return ProcessingResult.success_result(
                output_file=expected_file,
                file_size_bytes=file_size,
                file_size_mb=file_size / (1024 * 1024),
                audio_format=self.config.audio.audio_format,
                audio_quality=self.config.audio.audio_quality,
                cached=True,  # Indicate this was from cache
            )
        
        # Get list of existing files before download
        existing_files = set(os.listdir(output_dir))
        
        # Configure output filename
        ydl_opts = self.base_opts.copy()
        
        if custom_filename:
            # Use custom filename
            output_template = os.path.join(output_dir, f"{custom_filename}.%(ext)s")
        else:
            # Use safe filename based on song info
            safe_filename = song_info.safe_filename_base
            output_template = os.path.join(output_dir, f"{safe_filename}.%(ext)s")
        
        ydl_opts['outtmpl'] = output_template
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download the audio
                ydl.download([song_info.youtube_url])
            
            # Find the downloaded file
            output_file = self._find_downloaded_file(
                output_dir,
                existing_files,
                song_info,
                custom_filename
            )
            
            if not output_file or not os.path.exists(output_file):
                raise AudioDownloadError("Downloaded file not found after download")
            
            self.logger.info(f"Audio downloaded successfully: {output_file}")
            
            # Get file size for metadata
            file_size = os.path.getsize(output_file)
            
            return ProcessingResult.success_result(
                output_file=output_file,
                file_size_bytes=file_size,
                file_size_mb=file_size / (1024 * 1024),
                audio_format=self.config.audio.audio_format,
                audio_quality=self.config.audio.audio_quality
            )
            
        except yt_dlp.utils.DownloadError as e:
            error_msg = f"yt-dlp download failed: {e}"
            self.logger.error(error_msg)
            raise AudioDownloadError(error_msg) from e
        except FileNotFoundError as e:
            # Handle rare yt-dlp rename race condition where the temp file
            # disappears before the final rename (observed with .webm files).
            self.logger.warning(
                "Initial download hit FileNotFoundError (%s). Retrying with simplified template…",
                e,
            )

            # Retry with a very simple template to avoid edge-case characters
            retry_template = os.path.join(output_dir, "%(title)s.%(ext)s")
            if ydl_opts.get("outtmpl") == retry_template:
                # Already using simplified template – give up.
                raise AudioDownloadError(f"Unexpected error during audio download: {e}") from e

            ydl_opts["outtmpl"] = retry_template

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([song_info.youtube_url])

                output_file = self._find_downloaded_file(
                    output_dir,
                    existing_files,
                    song_info,
                    None,
                )

                if output_file and os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    return ProcessingResult.success_result(
                        output_file=output_file,
                        file_size_bytes=file_size,
                        file_size_mb=file_size / (1024 * 1024),
                        audio_format=self.config.audio.audio_format,
                        audio_quality=self.config.audio.audio_quality,
                    )

            except Exception as retry_exc:
                self.logger.error("Retry after FileNotFoundError failed: %s", retry_exc)
                raise AudioDownloadError(
                    f"Unexpected error during audio download: {retry_exc}"
                ) from retry_exc

        except Exception as e:
            error_msg = f"Unexpected error during audio download: {e}"
            self.logger.error(error_msg)
            raise AudioDownloadError(error_msg) from e
    
    def _find_downloaded_file(
        self,
        output_dir: str,
        existing_files: set,
        song_info: SongInfo,
        custom_filename: Optional[str]
    ) -> Optional[str]:
        """
        Find the downloaded audio file.
        
        Args:
            output_dir: Output directory
            existing_files: Set of files that existed before download
            song_info: Song information
            custom_filename: Custom filename used
            
        Returns:
            Path to the downloaded file, or None if not found
        """
        audio_format = self.config.audio.audio_format
        
        # Strategy 1: Check for expected filename
        if custom_filename:
            expected_file = os.path.join(output_dir, f"{custom_filename}.{audio_format}")
        else:
            safe_filename = song_info.safe_filename_base
            expected_file = os.path.join(output_dir, f"{safe_filename}.{audio_format}")
        
        if os.path.exists(expected_file):
            return expected_file
        
        # Strategy 2: Find new files with correct extension
        current_files = set(os.listdir(output_dir))
        new_files = current_files - existing_files
        
        audio_files = [
            f for f in new_files 
            if f.lower().endswith(f'.{audio_format}')
        ]
        
        if audio_files:
            # Return the most recently created file
            audio_paths = [os.path.join(output_dir, f) for f in audio_files]
            newest_file = max(audio_paths, key=os.path.getmtime)
            return newest_file
        
        # Strategy 3: Find any new audio file
        audio_extensions = ['mp3', 'wav', 'flac', 'm4a', 'ogg', 'aac']
        for ext in audio_extensions:
            audio_files = [
                f for f in new_files 
                if f.lower().endswith(f'.{ext}')
            ]
            if audio_files:
                audio_paths = [os.path.join(output_dir, f) for f in audio_files]
                newest_file = max(audio_paths, key=os.path.getmtime)
                return newest_file
        
        return None
    
    def _get_expected_audio_file(
        self,
        song_info: SongInfo,
        output_dir: str,
        custom_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the expected audio file path.
        
        Args:
            song_info: Song information
            output_dir: Output directory
            custom_filename: Custom filename if specified
            
        Returns:
            Expected file path or None
        """
        audio_format = self.config.audio.audio_format
        
        if custom_filename:
            return os.path.join(output_dir, f"{custom_filename}.{audio_format}")
        else:
            safe_filename = song_info.safe_filename_base
            return os.path.join(output_dir, f"{safe_filename}.{audio_format}")
    
    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported audio formats.
        
        Returns:
            List of supported format extensions
        """
        return ['mp3', 'wav', 'flac', 'm4a', 'ogg', 'aac']
    
    def validate_url(self, url: str) -> None:
        """
        Validate that a URL can be processed by yt-dlp.
        
        Args:
            url: URL to validate
            
        Raises:
            AudioDownloadError: If URL is not valid
        """
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                ydl.extract_info(url, download=False)
        except Exception as e:
            raise AudioDownloadError(f"Invalid or inaccessible URL: {e}") from e


def download_audio(
    song_info: SongInfo,
    output_dir: str,
    config: Optional[Config] = None,
    custom_filename: Optional[str] = None
) -> ProcessingResult:
    """
    Convenience function to download audio.
    
    Args:
        song_info: Song information
        output_dir: Output directory
        config: Optional configuration
        custom_filename: Optional custom filename
        
    Returns:
        ProcessingResult with download information
    """
    downloader = AudioDownloader(config)
    return downloader.download_audio(song_info, output_dir, custom_filename)