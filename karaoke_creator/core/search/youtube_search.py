"""
YouTube search functionality for finding songs.

This module provides functionality to search YouTube Music and extract
song metadata from search results or direct URLs.
"""

import re
import yt_dlp
from typing import Optional, Dict, Any

from ...models.song_info import SongInfo
from ...utils.logging import LoggerMixin, log_performance
from ...utils.config import Config


class YouTubeSearchError(Exception):
    """Exception raised when YouTube search fails."""
    pass


class YouTubeSearcher(LoggerMixin):
    """
    Handles searching YouTube Music and extracting song information.
    
    This class provides methods to search for songs by query string or
    extract information from direct YouTube URLs.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the YouTube searcher.
        
        Args:
            config: Configuration object with search settings
        """
        self.config = config or Config()
        
        # Base yt-dlp options for search operations
        self.search_opts = {
            'quiet': True,
            'extract_flat': True,
            'playlistend': 1,
        }
        
        # Base yt-dlp options for metadata extraction
        self.extract_opts = {
            'quiet': True,
            'download': False,
        }
    
    @log_performance
    def search_song(self, search_term: str) -> SongInfo:
        """
        Search YouTube Music for a song and return song information.
        
        This method performs a YouTube Music search using the provided search term
        and extracts metadata from the top result.
        
        Args:
            search_term: Search query (e.g., 'hello adele')
            
        Returns:
            SongInfo object with extracted metadata
            
        Raises:
            YouTubeSearchError: If search fails or no results found
            
        Example:
            searcher = YouTubeSearcher()
            song_info = searcher.search_song('hello adele')
            print(f"{song_info.artist} - {song_info.track}")
        """
        self.logger.info(f"Searching YouTube Music for: {search_term}")
        
        try:
            with yt_dlp.YoutubeDL(self.search_opts) as ydl:
                # Perform YouTube Music search
                search_url = f'https://music.youtube.com/search?q={search_term}'
                search_results = ydl.extract_info(search_url, download=False)
                
                if 'entries' not in search_results or not search_results['entries']:
                    raise YouTubeSearchError(f"No results found for '{search_term}' on YouTube Music")
                
                # Get the first result
                entry = search_results['entries'][0]
                video_url = entry['url']
                
                self.logger.debug(f"Top search result URL: {video_url}")
                
                # Extract full metadata from the video
                return self._extract_song_info_from_url(video_url)
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = f"YouTube search failed: {e}"
            self.logger.error(error_msg)
            raise YouTubeSearchError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during search: {e}"
            self.logger.error(error_msg)
            raise YouTubeSearchError(error_msg) from e
    
    @log_performance
    def extract_song_info_from_url(self, youtube_url: str) -> SongInfo:
        """
        Extract song information from a direct YouTube URL.
        
        This method takes a YouTube URL and extracts metadata including
        artist, track name, and other information.
        
        Args:
            youtube_url: Direct YouTube or youtu.be URL
            
        Returns:
            SongInfo object with extracted metadata
            
        Raises:
            YouTubeSearchError: If URL extraction fails
            
        Example:
            searcher = YouTubeSearcher()
            song_info = searcher.extract_song_info_from_url(
                'https://www.youtube.com/watch?v=YQHsXMglC9A'
            )
        """
        self.logger.info(f"Extracting metadata from YouTube URL: {youtube_url}")
        return self._extract_song_info_from_url(youtube_url)
    
    def _extract_song_info_from_url(self, youtube_url: str) -> SongInfo:
        """
        Internal method to extract song info from URL.
        
        Args:
            youtube_url: YouTube URL to extract from
            
        Returns:
            SongInfo object with extracted metadata
            
        Raises:
            YouTubeSearchError: If extraction fails
        """
        try:
            with yt_dlp.YoutubeDL(self.extract_opts) as ydl:
                # Extract video information
                video_info = ydl.extract_info(youtube_url, download=False)
                
                # Extract artist and track information using multiple strategies
                artist, track = self._parse_artist_and_track(video_info)
                
                if not artist or not track:
                    raise YouTubeSearchError(
                        "Unable to parse artist/track information from the provided URL"
                    )
                
                # Create SongInfo object with extracted data
                song_info = SongInfo(
                    artist=artist,
                    track=track,
                    youtube_url=video_info.get('webpage_url') or youtube_url,
                    duration=video_info.get('duration'),
                    title=video_info.get('title'),
                    uploader=video_info.get('uploader'),
                    upload_date=video_info.get('upload_date'),
                    view_count=video_info.get('view_count'),
                )
                
                self.logger.info(
                    f"Extracted song info - Artist: {song_info.artist}, "
                    f"Track: {song_info.track}"
                )
                
                return song_info
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = f"Failed to extract info from URL: {e}"
            self.logger.error(error_msg)
            raise YouTubeSearchError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error extracting from URL: {e}"
            self.logger.error(error_msg)
            raise YouTubeSearchError(error_msg) from e
    
    def _parse_artist_and_track(self, video_info: Dict[str, Any]) -> tuple[str, str]:
        """
        Parse artist and track information from video metadata.
        
        Uses multiple strategies in order of preference:
        1. YouTube Music metadata fields (artist/track)
        2. Uploader/channel as artist, title as track
        3. Regex parsing of title in "track - artist" format
        
        Args:
            video_info: Video metadata from yt-dlp
            
        Returns:
            Tuple of (artist, track)
        """
        # Strategy 1: Use YouTube Music metadata fields
        artist = video_info.get('artist')
        track = video_info.get('track')
        
        if artist and track:
            self.logger.debug("Using YouTube Music metadata fields")
            return artist.strip(), track.strip()
        
        # Strategy 2: Use uploader as artist, title as track
        artist = artist or video_info.get('uploader') or video_info.get('channel')
        track = track or video_info.get('title')
        
        # Strategy 3: Parse title for "track - artist" pattern
        if not artist or not track:
            title = video_info.get('title', '')
            parsed_artist, parsed_track = self._parse_title_format(title)
            
            artist = artist or parsed_artist
            track = track or parsed_track
        
        # Clean up the results
        artist = artist.strip() if artist else ""
        track = track.strip() if track else ""
        
        self.logger.debug(f"Parsed artist: '{artist}', track: '{track}'")
        
        return artist, track
    
    def _parse_title_format(self, title: str) -> tuple[str, str]:
        """
        Parse title in various common formats.
        
        Supports formats like:
        - "Track Name - Artist Name"
        - "Artist Name - Track Name"
        - "Track Name (Artist Name)"
        - "Artist Name: Track Name"
        
        Args:
            title: Video title to parse
            
        Returns:
            Tuple of (artist, track) or ("", "") if parsing fails
        """
        if not title:
            return "", ""
        
        # Remove common suffixes like (Official Video), [Lyrics], etc.
        clean_title = re.sub(
            r'\s*[\(\[](?:official|lyrics?|audio|video|music video|live|acoustic|remix).*?[\)\]]\s*',
            '',
            title,
            flags=re.IGNORECASE
        )
        
        # Pattern 1: "Track - Artist" or "Artist - Track"
        match = re.match(r'^(.+?)\s*-\s*(.+?)$', clean_title.strip())
        if match:
            part1, part2 = match.groups()
            part1, part2 = part1.strip(), part2.strip()
            
            # Heuristic: if part1 looks like an artist name (has "feat", "&", etc.)
            # then assume part1 is artist, part2 is track
            if any(keyword in part1.lower() for keyword in ['feat', '&', 'and', 'x ']):
                return part1, part2
            else:
                # Otherwise assume part1 is track, part2 is artist
                return part2, part1
        
        # Pattern 2: "Track (Artist)" or "Artist (Track)"
        match = re.match(r'^(.+?)\s*\((.+?)\)$', clean_title.strip())
        if match:
            main_part, paren_part = match.groups()
            main_part, paren_part = main_part.strip(), paren_part.strip()
            
            # Usually the main part is the track, parentheses contain artist
            return paren_part, main_part
        
        # Pattern 3: "Artist: Track" or "Track: Artist"
        match = re.match(r'^(.+?)\s*:\s*(.+?)$', clean_title.strip())
        if match:
            part1, part2 = match.groups()
            part1, part2 = part1.strip(), part2.strip()
            
            # Usually format is "Artist: Track"
            return part1, part2
        
        # If no pattern matches, return empty strings
        return "", ""
    
    def is_youtube_url(self, url: str) -> bool:
        """
        Check if a string is a valid YouTube URL.
        
        Args:
            url: String to check
            
        Returns:
            True if it's a valid YouTube URL
        """
        youtube_pattern = re.compile(
            r'^https?://(?:[\w.-]+\.)?(?:youtube\.com|youtu\.be)/',
            re.IGNORECASE
        )
        return bool(youtube_pattern.match(url))
    
    def validate_youtube_url(self, url: str) -> None:
        """
        Validate that a URL is a proper YouTube URL.
        
        Args:
            url: URL to validate
            
        Raises:
            YouTubeSearchError: If URL is not valid
        """
        if not self.is_youtube_url(url):
            raise YouTubeSearchError(f"Invalid YouTube URL: {url}")


def search_song(search_term: str, config: Optional[Config] = None) -> SongInfo:
    """
    Convenience function to search for a song.
    
    Args:
        search_term: Search query
        config: Optional configuration
        
    Returns:
        SongInfo object
    """
    searcher = YouTubeSearcher(config)
    return searcher.search_song(search_term)


def extract_song_info_from_url(youtube_url: str, config: Optional[Config] = None) -> SongInfo:
    """
    Convenience function to extract song info from URL.
    
    Args:
        youtube_url: YouTube URL
        config: Optional configuration
        
    Returns:
        SongInfo object
    """
    searcher = YouTubeSearcher(config)
    return searcher.extract_song_info_from_url(youtube_url)