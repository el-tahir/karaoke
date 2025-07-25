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

# Import video processing modules
from .video.ass_converter import AssConverter, SubtitleGenerationError
from .video.simple_renderer import VideoRenderer, VideoRenderingError

# Import additional processing modules (to be implemented)
try:
    from .lyrics.processor import LyricsProcessor
except ImportError:
    # These will be implemented in the continuation
    LyricsProcessor = None


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
        self.ass_converter = AssConverter(self.config)
        self.video_renderer = VideoRenderer(self.config)
        
        # These will be initialized when modules are available
        self.lyrics_processor = None
        
        # Processing state
        self.current_song_info: Optional[SongInfo] = None
        self.processing_results: Dict[str, ProcessingResult] = {}
    
    @log_performance
    def create_karaoke_from_search(
        self,
        search_term: str,
        output_dir: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None,
        lrc_content: Optional[str] = None
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
            search_result = self.searcher.search_song(search_term)
            self.processing_results['search'] = search_result
            
            if not search_result.success:
                raise KaraokeCreationError(f"Song search failed: {search_result.error_message}")
            
            song_info = search_result.metadata['song_info']
            
            # Continue with the common pipeline, pass lrc_content
            return self._create_karaoke_from_song_info(
                song_info, output_dir, custom_settings, lrc_content=lrc_content
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
        custom_settings: Optional[Dict[str, Any]] = None,
        lrc_content: Optional[str] = None
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
            url_result = self.searcher.extract_song_info_from_url(youtube_url)
            self.processing_results['url_extraction'] = url_result
            
            if not url_result.success:
                raise KaraokeCreationError(f"URL processing failed: {url_result.error_message}")
            
            song_info = url_result.metadata['song_info']
            
            # Continue with the common pipeline, pass lrc_content
            return self._create_karaoke_from_song_info(
                song_info, output_dir, custom_settings, lrc_content=lrc_content
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
        custom_settings: Optional[Dict[str, Any]] = None,
        lrc_content: Optional[str] = None
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
            
            # Step 3: Separate audio (vocals/instrumental) or use provided instrumental
            if self.config.skip_separation:
                self.logger.info("Step 3: Skipping audio separation - using provided instrumental audio")
                # Use the downloaded audio as instrumental since it's already instrumental
                instrumental_file = audio_file
                vocals_file = None
                
                # Create a mock separation result for consistency
                separation_result = ProcessingResult.success_result(
                    output_file=instrumental_file,
                    instrumental_file=instrumental_file,
                    vocals_file=None,
                    skipped=True
                )
                self.processing_results['separation'] = separation_result
            else:
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
            
            # Step 4: Use user-supplied LRC content if provided, else fetch lyrics
            if lrc_content or (self.config.lyrics.lrc_content and self.config.lyrics.lrc_content.strip()):
                self.logger.info("Step 4: Using user-supplied LRC content for lyrics")
                lrc_text = lrc_content if lrc_content else self.config.lyrics.lrc_content
                from ..utils.file_utils import generate_safe_filename
                filename_base = generate_safe_filename(song_info.artist, song_info.track)
                lrc_filename = f"custom_{filename_base}.lrc"
                lrc_path = os.path.join(working_dir, lrc_filename)
                try:
                    with open(lrc_path, 'w', encoding='utf-8') as f:
                        f.write(lrc_text)
                except Exception as e:
                    self.logger.error(f"Failed to write user-supplied LRC file: {e}")
                    raise KaraokeCreationError(f"Failed to write user-supplied LRC file: {e}")
                lyrics_file = lrc_path
                self.processing_results['lyrics'] = {'success': True, 'output_file': lrc_path, 'source': 'user-supplied'}
            else:
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
            self.logger.info("Step 6: Generating subtitles")
            subtitle_result = self.ass_converter.convert_lrc_to_ass(
                lyrics_file, working_dir, song_info
            )
            self.processing_results['subtitles'] = subtitle_result
            
            if not subtitle_result.success:
                raise KaraokeCreationError(f"Subtitle generation failed: {subtitle_result.error_message}")
            
            subtitle_file = subtitle_result.output_file
            
            # Log if using cached file
            if subtitle_result.metadata.get('cached'):
                self.logger.info("Using cached subtitle file")
            
            # Step 7: Render videos
            self.logger.info("Step 7: Rendering videos")
            video_result = self.video_renderer.render_videos(
                audio_file, instrumental_file, subtitle_file,
                self.config.final_videos_dir, song_info
            )
            self.processing_results['video'] = video_result
            
            if not video_result.success:
                raise KaraokeCreationError(f"Video rendering failed: {video_result.error_message}")
            
            # Log if using cached files
            if video_result.metadata.get('cached'):
                self.logger.info("Using cached video files")
            
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