"""
Lyrics fetching functionality using various providers.

This module handles fetching synchronized lyrics from multiple sources
and processing them for karaoke use.
"""

import os
import re
from typing import Optional

import syncedlyrics

from ...models.song_info import SongInfo, ProcessingResult, Lyrics, LyricLine, WordSegment
from ...utils.logging import LoggerMixin, log_performance
from ...utils.config import Config
from ...utils.file_utils import ensure_directory_exists, generate_safe_filename


class LyricsFetchError(Exception):
    """Exception raised when lyrics fetching fails."""
    pass


class LyricsFetcher(LoggerMixin):
    """
    Handles fetching and processing synchronized lyrics.
    
    This class provides functionality to fetch lyrics from various providers
    and process them into structured format for karaoke generation.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the lyrics fetcher.
        
        Args:
            config: Configuration object with lyrics settings
        """
        self.config = config or Config()
        
        # Supported providers (in order of preference)
        self.providers = [
            'lrclib',
            'musixmatch',
            'genius',
            'azlyrics',
        ]
    
    @log_performance
    def fetch_lyrics(
        self,
        song_info: SongInfo,
        output_dir: str,
        force_line_level: Optional[bool] = None
    ) -> ProcessingResult:
        """
        Fetch synchronized lyrics for a song.
        
        Args:
            song_info: Song information
            output_dir: Directory to save lyrics file
            force_line_level: Force line-level lyrics even if word-level available
            
        Returns:
            ProcessingResult with lyrics file path and metadata
            
        Raises:
            LyricsFetchError: If lyrics fetching fails
        """
        self.logger.info(f"Fetching lyrics for: {song_info.artist} - {song_info.track}")
        
        # Ensure output directory exists
        ensure_directory_exists(output_dir)
        
        # Check if lyrics file already exists
        expected_files = self._get_expected_lyrics_files(song_info, output_dir)
        existing_file = self._find_existing_lyrics_file(expected_files)
        
        if existing_file:
            self.logger.info(f"Lyrics file already exists, skipping fetch: {existing_file}")
            
            # Parse and validate existing lyrics
            try:
                with open(existing_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lyrics = self._parse_lrc_content(content)
                lyrics_type = "word-level" if lyrics.is_word_level else "line-level"
                
                return ProcessingResult.success_result(
                    output_file=existing_file,
                    lyrics_type=lyrics_type,
                    line_count=lyrics.line_count,
                    is_word_level=lyrics.is_word_level,
                    total_duration=lyrics.total_duration,
                    language=lyrics.language,
                    cached=True,  # Indicate this was from cache
                )
            except Exception as e:
                self.logger.warning(f"Existing lyrics file is corrupted, will re-fetch: {e}")
        
        # Determine lyrics preference
        prefer_line_level = (
            force_line_level if force_line_level is not None 
            else not self.config.lyrics.prefer_word_level
        )
        
        try:
            lyrics_content = None
            lyrics_type = None
            provider_used = None
            search_query = f"{song_info.artist} {song_info.track}"
            
            # First try word-level if not preferring line-level
            if not prefer_line_level:
                self.logger.debug("Attempting to fetch word-level lyrics")
                for provider in self.providers:
                    lyrics_content = syncedlyrics.search(
                        search_query,
                        enhanced=True,
                        providers=[provider]
                    )
                    if lyrics_content:
                        lyrics_type = "word-level"
                        provider_used = provider
                        self.logger.info(f"Successfully fetched word-level lyrics from {provider}")
                        break
            
            # If not found or preferring line-level, try line-level
            if not lyrics_content and self.config.lyrics.fallback_to_line_level:
                self.logger.debug("Attempting to fetch line-level lyrics")
                for provider in self.providers:
                    lyrics_content = syncedlyrics.search(
                        search_query,
                        enhanced=False,
                        providers=[provider]
                    )
                    if lyrics_content:
                        lyrics_type = "line-level"
                        provider_used = provider
                        self.logger.info(f"Successfully fetched line-level lyrics from {provider}")
                        break
            
            # Check if we got any lyrics
            if not lyrics_content:
                error_msg = f"No synchronized lyrics found for {song_info.artist} - {song_info.track}"
                self.logger.error(error_msg)
                raise LyricsFetchError(error_msg)
            
            # Generate output filename
            filename_base = generate_safe_filename(song_info.artist, song_info.track)
            lrc_filename = f"{lyrics_type}_{filename_base}.lrc"
            lrc_path = os.path.join(output_dir, lrc_filename)
            
            # Save lyrics to file
            with open(lrc_path, 'w', encoding='utf-8') as f:
                f.write(lyrics_content)
            
            # Parse and validate lyrics
            lyrics = self._parse_lrc_content(lyrics_content)
            
            self.logger.info(f"Lyrics saved to: {lrc_path}")
            self.logger.debug(f"Lyrics info - Lines: {lyrics.line_count}, Type: {lyrics_type}")
            
            return ProcessingResult.success_result(
                output_file=lrc_path,
                lyrics_type=lyrics_type,
                line_count=lyrics.line_count,
                is_word_level=lyrics.is_word_level,
                total_duration=lyrics.total_duration,
                language=lyrics.language,
            )
            
        except Exception as e:
            if isinstance(e, LyricsFetchError):
                raise
            
            error_msg = f"Unexpected error fetching lyrics: {e}"
            self.logger.error(error_msg)
            raise LyricsFetchError(error_msg) from e
    
    def _parse_lrc_content(self, lrc_content: str) -> Lyrics:
        """
        Parse LRC content into structured lyrics object.
        
        Args:
            lrc_content: Raw LRC file content
            
        Returns:
            Parsed Lyrics object
        """
        lyrics = Lyrics()
        
        for line in lrc_content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Skip metadata lines like [ti:], [ar:], etc.
            if re.match(r'^\[[a-zA-Z]{2,}:.*\]$', line):
                continue
            
            # Match line timestamp pattern
            match = re.match(r'\[(\d+:\d+\.\d+)\](.*)', line)
            if not match:
                continue
            
            line_timestamp = match.group(1)
            text_content = match.group(2).strip()
            
            # Parse word-level segments if present
            word_segments = []
            word_matches = re.findall(r'<(\d+:\d+\.\d+)>([^<]*)', text_content)
            
            if word_matches:
                # Word-level lyrics
                for ts, word in word_matches:
                    word = word.strip()
                    if word:
                        word_segments.append((ts, word))
            else:
                # Line-level lyrics
                if text_content:
                    word_segments = [('', text_content)]
            
            if word_segments:
                lyrics.add_line(line_timestamp, text_content, word_segments)
        
        return lyrics
    
    def validate_lrc_file(self, lrc_path: str) -> bool:
        """
        Validate that an LRC file has proper format and timing.
        
        Args:
            lrc_path: Path to LRC file
            
        Returns:
            True if file is valid
        """
        try:
            with open(lrc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lyrics = self._parse_lrc_content(content)
            
            # Check basic requirements
            if lyrics.line_count == 0:
                self.logger.warning(f"LRC file has no lyric lines: {lrc_path}")
                return False
            
            # Check timing consistency
            prev_time = 0.0
            for line in lyrics.lines:
                if line.start_seconds is not None:
                    if line.start_seconds < prev_time:
                        self.logger.warning(f"Timing inconsistency in LRC file: {lrc_path}")
                        return False
                    prev_time = line.start_seconds
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating LRC file {lrc_path}: {e}")
            return False
    
    def get_lyrics_info(self, lrc_path: str) -> dict:
        """
        Get information about a lyrics file.
        
        Args:
            lrc_path: Path to LRC file
            
        Returns:
            Dictionary with lyrics information
        """
        try:
            with open(lrc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lyrics = self._parse_lrc_content(content)
            
            return {
                'file_path': lrc_path,
                'line_count': lyrics.line_count,
                'is_word_level': lyrics.is_word_level,
                'total_duration': lyrics.total_duration,
                'language': lyrics.language,
                'file_size': os.path.getsize(lrc_path),
                'encoding': 'utf-8',
            }
            
        except Exception as e:
            self.logger.error(f"Error getting lyrics info for {lrc_path}: {e}")
            return {
                'file_path': lrc_path,
                'error': str(e),
            }
    
    def search_multiple_queries(self, queries: list[str]) -> Optional[str]:
        """
        Try multiple search queries to find lyrics.
        
        Args:
            queries: List of search queries to try
            
        Returns:
            Lyrics content if found, None otherwise
        """
        for query in queries:
            self.logger.debug(f"Trying query: {query}")
            
            try:
                # Try word-level first
                lyrics = syncedlyrics.search(
                    query,
                    enhanced=True,
                    providers=self.providers
                )
                
                if lyrics:
                    self.logger.info(f"Found word-level lyrics with query: {query}")
                    return lyrics
                
                # Try line-level
                lyrics = syncedlyrics.search(
                    query,
                    enhanced=False,
                    providers=self.providers
                )
                
                if lyrics:
                    self.logger.info(f"Found line-level lyrics with query: {query}")
                    return lyrics
                    
            except Exception as e:
                self.logger.debug(f"Query failed: {query} - {e}")
                continue
        
        return None
    
    def generate_search_queries(self, song_info: SongInfo) -> list[str]:
        """
        Generate multiple search query variations.
        
        Args:
            song_info: Song information
            
        Returns:
            List of search queries to try
        """
        artist = song_info.artist
        track = song_info.track
        
        queries = [
            f"{artist} {track}",
            f"{track} {artist}",
            f'"{artist}" "{track}"',
            f"{artist} - {track}",
            f"{track} - {artist}",
        ]
        
        # Add variations without common suffixes
        clean_track = re.sub(
            r'\s*[\(\[](?:official|lyrics?|audio|video|music video|live|acoustic|remix).*?[\)\]]\s*',
            '',
            track,
            flags=re.IGNORECASE
        ).strip()
        
        if clean_track != track:
            queries.extend([
                f"{artist} {clean_track}",
                f"{clean_track} {artist}",
            ])
        
        return queries
    
    def _get_expected_lyrics_files(self, song_info: SongInfo, output_dir: str) -> list[str]:
        """
        Get list of expected lyrics file paths.
        
        Args:
            song_info: Song information
            output_dir: Output directory
            
        Returns:
            List of possible lyrics file paths
        """
        filename_base = generate_safe_filename(song_info.artist, song_info.track)
        
        return [
            os.path.join(output_dir, f"word-level_{filename_base}.lrc"),
            os.path.join(output_dir, f"line-level_{filename_base}.lrc"),
            os.path.join(output_dir, f"{filename_base}.lrc"),
        ]
    
    def _find_existing_lyrics_file(self, expected_files: list[str]) -> Optional[str]:
        """
        Find the first existing lyrics file from the expected files list.
        
        Args:
            expected_files: List of expected file paths
            
        Returns:
            Path to existing file or None
        """
        for file_path in expected_files:
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                self.logger.debug(f"Found existing lyrics file: {file_path}")
                return file_path
        
        return None


def fetch_lyrics(
    song_info: SongInfo,
    output_dir: str,
    config: Optional[Config] = None,
    force_line_level: Optional[bool] = None
) -> ProcessingResult:
    """
    Convenience function to fetch lyrics.
    
    Args:
        song_info: Song information
        output_dir: Output directory
        config: Optional configuration
        force_line_level: Force line-level lyrics
        
    Returns:
        ProcessingResult with lyrics information
    """
    fetcher = LyricsFetcher(config)
    return fetcher.fetch_lyrics(song_info, output_dir, force_line_level)