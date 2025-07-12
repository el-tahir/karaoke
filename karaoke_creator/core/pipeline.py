"""
Main pipeline for karaoke video creation.

This module provides the main KaraokeCreator class that orchestrates
the entire process from song search to video generation.
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..models.song_info import SongInfo, ProcessingResult
from ..utils.logging import LoggerMixin, log_performance, setup_logging
from ..utils.config import Config
from ..utils.file_utils import ensure_directory_exists, cleanup_temp_files

# Import core processing modules
from .search.youtube_search import YouTubeSearcher, YouTubeSearchError
from .audio.downloader import AudioDownloader, AudioDownloadError
from .audio.separator import AudioSeparator, AudioSeparationError
from .lyrics.fetcher import LyricsFetcher, LyricsFetchError

# Import additional processing modules (to be implemented)
try:
    from .lyrics.processor import LyricsProcessor
    from .video.subtitle_generator import SubtitleGenerator
    from .video.renderer import VideoRenderer
except ImportError:
    # These will be implemented in the continuation
    LyricsProcessor = None
    SubtitleGenerator = None
    VideoRenderer = None


class KaraokeCreationError(Exception):
    """Exception raised when karaoke creation fails."""
    pass


class KaraokeCreator(LoggerMixin):
    """
    Main class for creating karaoke videos.
    
    This class orchestrates the entire pipeline from song search/URL processing
    through video generation, providing a high-level interface for karaoke creation.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the karaoke creator.
        
        Args:
            config: Configuration object for customizing behavior
        """
        self.config = config or Config()
        
        # Validate and setup configuration
        self.config.validate()
        self.config.ensure_directories()
        
        # Setup logging
        setup_logging(
            level=self.config.log_level,
            format_string=self.config.log_format
        )
        
        self.logger.info("KaraokeCreator initialized")
        
        # Initialize processing components
        self.searcher = YouTubeSearcher(self.config)
        self.downloader = AudioDownloader(self.config)
        self.separator = AudioSeparator(self.config)
        self.lyrics_fetcher = LyricsFetcher(self.config)
        
        # These will be initialized when modules are available
        self.lyrics_processor = None
        self.subtitle_generator = None
        self.video_renderer = None
        
        # Processing state
        self.current_song_info: Optional[SongInfo] = None
        self.processing_results: Dict[str, ProcessingResult] = {}
    
    @log_performance
    def create_karaoke_from_search(
        self,
        search_term: str,
        output_dir: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """
        Create karaoke video from a search term.
        
        Args:
            search_term: Song search query
            output_dir: Custom output directory (overrides config)
            custom_settings: Additional settings for this creation
            
        Returns:
            ProcessingResult with final video paths and metadata
            
        Raises:
            KaraokeCreationError: If any step in the pipeline fails
        """
        self.logger.info(f"Starting karaoke creation from search: {search_term}")
        
        try:
            # Step 1: Search for song
            song_info = self.searcher.search_song(search_term)
            
            # Continue with the common pipeline
            return self._create_karaoke_from_song_info(
                song_info, output_dir, custom_settings
            )
            
        except YouTubeSearchError as e:
            error_msg = f"Song search failed: {e}"
            self.logger.error(error_msg)
            raise KaraokeCreationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error in search pipeline: {e}"
            self.logger.error(error_msg)
            raise KaraokeCreationError(error_msg) from e
    
    @log_performance
    def create_karaoke_from_url(
        self,
        youtube_url: str,
        output_dir: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """
        Create karaoke video from a YouTube URL.
        
        Args:
            youtube_url: Direct YouTube URL
            output_dir: Custom output directory (overrides config)
            custom_settings: Additional settings for this creation
            
        Returns:
            ProcessingResult with final video paths and metadata
            
        Raises:
            KaraokeCreationError: If any step in the pipeline fails
        """
        self.logger.info(f"Starting karaoke creation from URL: {youtube_url}")
        
        try:
            # Step 1: Extract song info from URL
            song_info = self.searcher.extract_song_info_from_url(youtube_url)
            
            # Continue with the common pipeline
            return self._create_karaoke_from_song_info(
                song_info, output_dir, custom_settings
            )
            
        except YouTubeSearchError as e:
            error_msg = f"URL processing failed: {e}"
            self.logger.error(error_msg)
            raise KaraokeCreationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error in URL pipeline: {e}"
            self.logger.error(error_msg)
            raise KaraokeCreationError(error_msg) from e
    
    def _create_karaoke_from_song_info(
        self,
        song_info: SongInfo,
        output_dir: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """
        Internal method to create karaoke from song info.
        
        This method handles the common pipeline steps after song information
        has been obtained.
        
        Args:
            song_info: Song information
            output_dir: Custom output directory
            custom_settings: Additional settings
            
        Returns:
            ProcessingResult with final video information
        """
        start_time = time.time()
        
        # Store current song info
        self.current_song_info = song_info
        self.processing_results.clear()
        
        # Determine output directory
        working_dir = output_dir or self.config.output_dir
        ensure_directory_exists(working_dir)
        
        try:
            # Step 2: Download audio
            self.logger.info("Step 2: Downloading audio")
            download_result = self.downloader.download_audio(
                song_info, working_dir
            )
            self.processing_results['download'] = download_result
            
            if not download_result.success:
                raise KaraokeCreationError(f"Audio download failed: {download_result.error_message}")
            
            audio_file = download_result.output_file
            
            # Log if using cached file
            if download_result.metadata.get('cached'):
                self.logger.info("Using cached audio file")
            
            # Step 3: Separate audio (vocals/instrumental)
            self.logger.info("Step 3: Separating audio")
            separation_result = self.separator.separate_audio(
                audio_file, working_dir
            )
            self.processing_results['separation'] = separation_result
            
            if not separation_result.success:
                raise KaraokeCreationError(f"Audio separation failed: {separation_result.error_message}")
            
            instrumental_file = separation_result.metadata.get('instrumental_file')
            vocals_file = separation_result.metadata.get('vocals_file')
            
            # Log if using cached file
            if separation_result.metadata.get('cached'):
                self.logger.info("Using cached separated audio files")
            
            # Step 4: Fetch lyrics
            self.logger.info("Step 4: Fetching lyrics")
            lyrics_result = self.lyrics_fetcher.fetch_lyrics(
                song_info, working_dir
            )
            self.processing_results['lyrics'] = lyrics_result
            
            if not lyrics_result.success:
                raise KaraokeCreationError(f"Lyrics fetching failed: {lyrics_result.error_message}")
            
            lyrics_file = lyrics_result.output_file
            
            # Log if using cached file
            if lyrics_result.metadata.get('cached'):
                self.logger.info("Using cached lyrics file")
            
            # Step 5: Process lyrics (romanization, timing adjustments)
            self.logger.info("Step 5: Processing lyrics (romanization)")
            from ..utils.japanese_romanizer import romanize_lrc_file_inplace
            
            try:
                # Romanize Japanese text in-place if present
                was_romanized = romanize_lrc_file_inplace(lyrics_file, self.config)
                if was_romanized:
                    self.logger.info("Japanese text was romanized in lyrics file")
                else:
                    self.logger.debug("No Japanese text found or romanization not available")
            except Exception as e:
                self.logger.warning(f"Romanization step failed: {e}")
            
            # Store processing result
            self.processing_results['lyrics_processing'] = {
                'success': True,
                'romanized': was_romanized if 'was_romanized' in locals() else False
            }
            
            # Step 6: Generate subtitles
            if self.subtitle_generator:
                self.logger.info("Step 6: Generating subtitles")
                subtitle_result = self.subtitle_generator.generate_subtitles(
                    lyrics_file, working_dir, song_info
                )
                self.processing_results['subtitles'] = subtitle_result
                
                if not subtitle_result.success:
                    raise KaraokeCreationError(f"Subtitle generation failed: {subtitle_result.error_message}")
                
                subtitle_file = subtitle_result.output_file
            else:
                # Fallback: use existing subtitle conversion logic
                subtitle_file = self._convert_lrc_to_ass_fallback(lyrics_file, working_dir)
            
            # Step 7: Render videos
            if self.video_renderer:
                self.logger.info("Step 7: Rendering videos")
                video_result = self.video_renderer.render_videos(
                    audio_file, instrumental_file, subtitle_file,
                    self.config.final_videos_dir, song_info
                )
                self.processing_results['video'] = video_result
                
                if not video_result.success:
                    raise KaraokeCreationError(f"Video rendering failed: {video_result.error_message}")
            else:
                # Fallback: use existing video creation logic
                video_result = self._create_videos_fallback(
                    audio_file, instrumental_file, subtitle_file, song_info
                )
                self.processing_results['video'] = video_result
            
            # Clean up temporary files if configured
            if self.config.cleanup_temp_files:
                self._cleanup_temp_files(working_dir)
            
            # Calculate total processing time
            total_time = time.time() - start_time
            
            self.logger.info(f"Karaoke creation completed in {total_time:.2f} seconds")
            
            # Return final result
            return ProcessingResult.success_result(
                output_file=video_result.output_file,
                processing_time=total_time,
                song_info=song_info.to_dict(),
                steps_completed=list(self.processing_results.keys()),
                **video_result.metadata
            )
            
        except Exception as e:
            if isinstance(e, KaraokeCreationError):
                raise
            
            error_msg = f"Unexpected error in karaoke creation pipeline: {e}"
            self.logger.error(error_msg)
            raise KaraokeCreationError(error_msg) from e
    
    def _convert_lrc_to_ass_fallback(self, lrc_file: str, output_dir: str) -> str:
        """
        Fallback method for LRC to ASS conversion.
        
        This uses the original conversion logic until the new module is ready.
        """
        # Import conversion function from integrated module
        from .video.ass_converter import convert_lrc_to_ass
        
        return convert_lrc_to_ass(lrc_file, output_dir)
    
    def _create_videos_fallback(
        self,
        audio_file: str,
        instrumental_file: str,
        subtitle_file: str,
        song_info: SongInfo
    ) -> ProcessingResult:
        """
        Fallback method for video creation.
        
        This uses the original video creation logic until the new module is ready.
        """
        # Import simple FFmpeg renderer from integrated module
        from .video.simple_renderer import create_karaoke_video
        
        # Ensure final videos directory exists
        ensure_directory_exists(self.config.final_videos_dir)
        
        # Create karaoke version (instrumental)
        karaoke_filename = f"{song_info.safe_filename_base}_karaoke.mp4"
        karaoke_path = os.path.join(self.config.final_videos_dir, karaoke_filename)
        
        karaoke_video = create_karaoke_video(
            instrumental_file, subtitle_file, karaoke_path
        )
        
        # Create original version if configured
        original_video = None
        if self.config.create_both_versions:
            original_filename = f"{song_info.safe_filename_base}_original.mp4"
            original_path = os.path.join(self.config.final_videos_dir, original_filename)
            
            original_video = create_karaoke_video(
                audio_file, subtitle_file, original_path
            )
        
        return ProcessingResult.success_result(
            output_file=karaoke_video,
            karaoke_video=karaoke_video,
            original_video=original_video,
        )
    
    def _cleanup_temp_files(self, working_dir: str) -> None:
        """Clean up temporary files after processing."""
        # Keep final output files
        keep_patterns = [
            '*.mp3',  # Original audio
            '*.wav',  # Separated audio
            '*.lrc',  # Lyrics
            '*.ass',  # Subtitles
        ]
        
        cleanup_temp_files(working_dir, keep_patterns)
        
        # Also clean up the main temp directory
        if hasattr(self.config, 'temp_dir'):
            cleanup_temp_files(self.config.temp_dir)
    
    def get_processing_status(self) -> Dict[str, Any]:
        """
        Get current processing status and results.
        
        Returns:
            Dictionary with processing status information
        """
        return {
            'current_song': self.current_song_info.to_dict() if self.current_song_info else None,
            'completed_steps': list(self.processing_results.keys()),
            'results': {
                step: {
                    'success': result.success,
                    'output_file': result.output_file,
                    'processing_time': result.processing_time,
                    'error': result.error_message,
                }
                for step, result in self.processing_results.items()
            }
        }
    
    def estimate_processing_time(self, song_info: SongInfo) -> float:
        """
        Estimate total processing time for a song.
        
        Args:
            song_info: Song information
            
        Returns:
            Estimated processing time in seconds
        """
        # Base estimates (in seconds)
        estimates = {
            'download': 30,  # Audio download
            'separation': 60,  # Audio separation (varies by file size)
            'lyrics': 10,  # Lyrics fetching
            'subtitles': 5,  # Subtitle generation
            'video': 120,  # Video rendering (varies by duration)
        }
        
        # Adjust based on song duration if available
        if song_info.duration:
            duration_minutes = song_info.duration / 60
            estimates['separation'] *= (duration_minutes / 3)  # Scale with duration
            estimates['video'] *= (duration_minutes / 3)
        
        return sum(estimates.values())
    
    def get_supported_input_types(self) -> List[str]:
        """Get list of supported input types."""
        return [
            'YouTube URLs (youtube.com, youtu.be)',
            'YouTube Music URLs (music.youtube.com)',
            'Search terms ("artist song title")',
        ]
    
    def get_output_formats(self) -> List[str]:
        """Get list of output formats."""
        return [
            'MP4 karaoke video (instrumental + subtitles)',
            'MP4 original video (vocals + subtitles)',
            'MP3 audio file',
            'WAV separated audio (vocals + instrumental)',
            'LRC lyrics file',
            'ASS subtitle file',
        ]


# Convenience functions for backward compatibility and simple usage

def create_karaoke_from_search(
    search_term: str,
    output_dir: str = 'downloads',
    config: Optional[Config] = None
) -> ProcessingResult:
    """
    Convenience function to create karaoke from search term.
    
    Args:
        search_term: Song search query
        output_dir: Output directory
        config: Optional configuration
        
    Returns:
        ProcessingResult with karaoke creation results
    """
    creator = KaraokeCreator(config)
    return creator.create_karaoke_from_search(search_term, output_dir)


def create_karaoke_from_url(
    youtube_url: str,
    output_dir: str = 'downloads',
    config: Optional[Config] = None
) -> ProcessingResult:
    """
    Convenience function to create karaoke from YouTube URL.
    
    Args:
        youtube_url: YouTube URL
        output_dir: Output directory
        config: Optional configuration
        
    Returns:
        ProcessingResult with karaoke creation results
    """
    creator = KaraokeCreator(config)
    return creator.create_karaoke_from_url(youtube_url, output_dir)