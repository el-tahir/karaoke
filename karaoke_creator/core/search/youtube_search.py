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
        2. Smart title parsing with multiple format support
        3. Uploader/channel as fallback if title parsing fails
        4. Enhanced pattern matching for complex titles
        
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
        
        # Strategy 2: Smart title parsing (prioritized over uploader)
        title = video_info.get('title', '')
        parsed_artist, parsed_track = self._parse_title_format(title)
        
        if parsed_artist and parsed_track:
            self.logger.debug("Using parsed title information")
            return parsed_artist.strip(), parsed_track.strip()
        
        # Strategy 3: Enhanced title parsing for complex cases
        enhanced_artist, enhanced_track = self._enhanced_title_parsing(title)
        
        if enhanced_artist and enhanced_track:
            self.logger.debug("Using enhanced title parsing")
            return enhanced_artist.strip(), enhanced_track.strip()
        
        # Strategy 4: Google search fallback for ambiguous cases
        if title:
            google_artist, google_track = self._google_search_fallback(title)
            
            if google_artist and google_track:
                self.logger.debug("Using Google search fallback")
                return google_artist.strip(), google_track.strip()
        
        # Strategy 5: Use uploader as final fallback
        fallback_artist = artist or video_info.get('uploader') or video_info.get('channel')
        fallback_track = track or title
        
        # Clean up the results
        fallback_artist = fallback_artist.strip() if fallback_artist else ""
        fallback_track = fallback_track.strip() if fallback_track else ""
        
        self.logger.debug(f"Using final fallback - Artist: '{fallback_artist}', track: '{fallback_track}'")
        
        return fallback_artist, fallback_track
    
    def _parse_title_format(self, title: str) -> tuple[str, str]:
        """
        Parse title in various common formats.
        
        Supports formats like:
        - "Artist - Track"
        - "Track - Artist" 
        - "Track (Artist)"
        - "Artist: Track"
        - "Artist | Track"
        
        Args:
            title: Video title to parse
            
        Returns:
            Tuple of (artist, track) or ("", "") if parsing fails
        """
        if not title:
            return "", ""
        
        # Remove common suffixes like (Official Video), [Lyrics], etc.
        clean_title = re.sub(
            r'\s*[\(\[](?:official|lyrics?|audio|video|music video|live|acoustic|remix|instrumental|inst|karaoke|cover|version).*?[\)\]]\s*',
            '',
            title,
            flags=re.IGNORECASE
        )
        
        # Pattern 1: "Artist - Track" (most common format)
        match = re.match(r'^(.+?)\s*-\s*(.+?)$', clean_title.strip())
        if match:
            part1, part2 = match.groups()
            part1, part2 = part1.strip(), part2.strip()
            
            # Enhanced heuristics to determine which is artist vs track
            artist_indicators = ['feat', 'ft', '&', 'and', 'x ', 'vs', 'with']
            track_indicators = ['remix', 'mix', 'edit', 'version', 'instrumental']
            
            part1_lower = part1.lower()
            part2_lower = part2.lower()
            
            # If part1 has artist indicators, it's likely the artist
            if any(keyword in part1_lower for keyword in artist_indicators):
                return part1, part2
            # If part2 has track indicators, part1 is likely the artist
            elif any(keyword in part2_lower for keyword in track_indicators):
                return part1, part2
            # If part1 is all caps (common for artist names in titles)
            elif part1.isupper() and not part2.isupper():
                return part1, part2
            # Default: assume first part is artist
            else:
                return part1, part2
        
        # Pattern 2: "Track (Artist)"
        match = re.match(r'^(.+?)\s*\((.+?)\)$', clean_title.strip())
        if match:
            main_part, paren_part = match.groups()
            main_part, paren_part = main_part.strip(), paren_part.strip()
            
            # Parentheses usually contain artist
            return paren_part, main_part
        
        # Pattern 3: "Artist: Track" or "Artist | Track"
        match = re.match(r'^(.+?)\s*[:|]\s*(.+?)$', clean_title.strip())
        if match:
            part1, part2 = match.groups()
            part1, part2 = part1.strip(), part2.strip()
            
            # Usually format is "Artist: Track"
            return part1, part2
        
        # If no pattern matches, return empty strings
        return "", ""
    
    def _enhanced_title_parsing(self, title: str) -> tuple[str, str]:
        """
        Enhanced parsing for complex title formats that don't match standard patterns.
        
        Handles cases like:
        - "Artist Name Song Title [Type]"
        - "Multiple - Words - In - Title"
        - "Artist feat. Other - Song Title"
        - Mixed case scenarios
        
        Args:
            title: Video title to parse
            
        Returns:
            Tuple of (artist, track) or ("", "") if parsing fails
        """
        if not title:
            return "", ""
        
        # Clean title more aggressively
        clean_title = re.sub(
            r'\s*[\(\[](?:official|lyrics?|audio|video|music video|live|acoustic|remix|instrumental|inst|karaoke|cover|version|remaster|hd|4k|explicit|clean|radio|edit).*?[\)\]]\s*',
            '',
            title,
            flags=re.IGNORECASE
        )
        
        # Remove common prefixes
        clean_title = re.sub(r'^(?:new\s+|latest\s+|best\s+)', '', clean_title, flags=re.IGNORECASE)
        
        # Pattern for multiple dashes - find the most likely split point
        parts = [part.strip() for part in clean_title.split(' - ') if part.strip()]
        
        if len(parts) >= 2:
            # Look for common artist name patterns in the parts
            for i, part in enumerate(parts):
                part_lower = part.lower()
                
                # If this part looks like an artist name
                if any(indicator in part_lower for indicator in ['feat', 'ft.', '&', 'and', 'x ']):
                    # This part is likely the artist, rest is track
                    artist = part
                    track = ' - '.join(parts[:i] + parts[i+1:])
                    return artist, track
                
                # If this part is all caps (common for artist names)
                if part.isupper() and len(part) > 2:
                    artist = part
                    track = ' - '.join(parts[:i] + parts[i+1:])
                    return artist, track
            
            # Default: first part is artist, rest is track
            artist = parts[0]
            track = ' - '.join(parts[1:])
            return artist, track
        
        # Look for artist names that are commonly formatted differently
        # Pattern: "ARTISTNAME songname" (all caps artist)
        match = re.match(r'^([A-Z][A-Z\s&]+)\s+([a-z].*?)$', clean_title.strip())
        if match:
            artist_part, track_part = match.groups()
            return artist_part.strip(), track_part.strip()
        
        # Pattern: "ARTIST NAME Song Title" (mixed case)
        match = re.match(r'^([A-Z][A-Z\s]+[A-Z])\s+([A-Z][a-z].*?)$', clean_title.strip())
        if match:
            artist_part, track_part = match.groups()
            return artist_part.strip(), track_part.strip()
        
        # Pattern: "Artist Name - song title with multiple words"
        # Try to identify if there's a clear artist/track split
        words = clean_title.split()
        if len(words) >= 3:
            # Look for common transition points
            for i, word in enumerate(words[:-1]):
                if word.lower() in ['-', '–', '—'] or (i > 0 and words[i-1].lower() in ['by', 'from']):
                    artist = ' '.join(words[:i])
                    track = ' '.join(words[i+1:])
                    if artist and track:
                        return artist, track
        
        return "", ""
    
    def _google_search_fallback(self, title: str) -> tuple[str, str]:
        """
        Use Google search as a fallback to identify artist and track from ambiguous titles.
        
        This method performs a simple web search to try to identify the correct
        artist and track when title parsing fails.
        
        Args:
            title: Video title to search for
            
        Returns:
            Tuple of (artist, track) or ("", "") if search fails
        """
        try:
            # Clean the title for search
            search_query = re.sub(
                r'\s*[\(\[](?:official|lyrics?|audio|video|music video|live|acoustic|remix|instrumental|inst|karaoke|cover|version|remaster|hd|4k|explicit|clean|radio|edit).*?[\)\]]\s*',
                '',
                title,
                flags=re.IGNORECASE
            )
            
            # Add "song lyrics" to help identify it as a music search
            search_query = f'"{search_query}" song lyrics artist'
            
            self.logger.debug(f"Attempting Google search fallback for: {search_query}")
            
            # Import here to avoid dependency issues if not available
            try:
                import requests
                from urllib.parse import quote
            except ImportError:
                self.logger.debug("requests not available for Google search fallback")
                return "", ""
            
            # Simple Google search (note: this is rate-limited and may not always work)
            search_url = f"https://www.google.com/search?q={quote(search_query)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                content = response.text.lower()
                
                # Look for common patterns in search results
                # This is a simple heuristic - could be improved with proper HTML parsing
                if 'artist' in content or 'song' in content:
                    # Try to extract patterns like "artist - song" from search results
                    lines = content.split('\n')
                    for line in lines:
                        if ' - ' in line and any(word in line for word in ['artist', 'song', 'music']):
                            # Basic extraction - this could be improved
                            match = re.search(r'([^-]+)\s*-\s*([^-]+)', line)
                            if match:
                                potential_artist, potential_track = match.groups()
                                potential_artist = potential_artist.strip()
                                potential_track = potential_track.strip()
                                
                                # Basic validation
                                if len(potential_artist) > 1 and len(potential_track) > 1:
                                    return potential_artist, potential_track
            
        except Exception as e:
            self.logger.debug(f"Google search fallback failed: {e}")
        
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