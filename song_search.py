import re
import yt_dlp
import logging

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def search_song(search_term: str) -> dict:
    """
    Searches YouTube Music for a song based on the search term and extracts the track name and artist from the top result.

    This function uses yt-dlp to perform a YouTube Music search and parses the metadata or title of the first result.

    Args:
        search_term (str): The search term for the song (e.g., 'hello adele').

    Returns:
        dict: A dictionary with 'artist' and 'track' keys.

    Raises:
        ValueError: If no results found or cannot parse song info.

    Example:
        info = search_song('hello adele')
        print(info)  # {'artist': 'Adele', 'track': 'Hello'}
    """
    logger.info(f"Starting search for: {search_term}")
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': 1,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            logger.debug("Performing YouTube Music search")
            search_results = ydl.extract_info(f'https://music.youtube.com/search?q={search_term}', download=False)

            if 'entries' not in search_results or not search_results['entries']:
                logger.error(f"No results found for '{search_term}' on YouTube Music")
                raise ValueError(f"No results found for '{search_term}' on YouTube Music")

            entry = search_results['entries'][0]
            video_url = entry['url']
            logger.debug(f"Top result URL: {video_url}")

            # Now extract full info from the specific video
            full_opts = {
                'quiet': True,
                'download': False,  # Explicitly prevent download
            }
            with yt_dlp.YoutubeDL(full_opts) as full_ydl:
                full_info = full_ydl.extract_info(video_url, download=False)

            # Try to extract from full metadata
            artist = full_info.get('artist') or full_info.get('uploader') or full_info.get('channel')
            track = full_info.get('track') or full_info.get('title')
            logger.debug(f"Full metadata extraction: artist={artist}, track={track}")

            if artist and track:
                result = {
                    'artist': artist.strip(),
                    'track': track.strip(),
                    'youtube_url': full_info['webpage_url'] or video_url
                }
                logger.info(f"Successfully extracted from full metadata: {result}")
                return result

            # If still no artist, try parsing title
            title = full_info.get('title', '')
            logger.debug(f"Fallback to title parsing: {title}")
            match = re.match(r'^(?P<track>.+?)\s*-\s*(?P<artist>.+?)(?:\s*\(Official.*\)|\s*\[Official.*\])?$', title, re.IGNORECASE)
            if match:
                result = {
                    'artist': match.group('artist').strip(),
                    'track': match.group('track').strip(),
                    'youtube_url': full_info['webpage_url'] or video_url
                }
                logger.info(f"Successfully parsed title (regex): {result}")
                return result
            else:
                # Alternative split
                parts = title.split(' - ', 1)
                if len(parts) == 2:
                    result = {
                        'artist': parts[1].strip(),
                        'track': parts[0].strip(),
                        'youtube_url': full_info['webpage_url'] or video_url
                    }
                    logger.info(f"Successfully parsed title (split): {result}")
                    return result

                # Fallback: Use uploader/channel from full info
                uploader = full_info.get('uploader') or full_info.get('channel')
                logger.debug(f"Fallback to uploader/channel: {uploader}")
                if uploader:
                    artist = re.sub(r'\s*-\s*Topic$', '', uploader).strip()
                    track = title.strip()
                    result = {
                        'artist': artist,
                        'track': track,
                        'youtube_url': full_info['webpage_url'] or video_url
                    }
                    logger.info(f"Successfully used uploader as artist: {result}")
                    return result

                logger.error(f"Could not parse song info from title: '{title}'")
                raise ValueError(f"Could not parse song info from title: '{title}'")

        except Exception as e:
            logger.exception(f"Error searching for '{search_term}'")
            raise ValueError(f"Error searching for '{search_term}': {str(e)}") 