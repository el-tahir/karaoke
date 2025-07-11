import re
import yt_dlp

def search_song(search_term: str) -> dict:
    """
    Searches YouTube for a song based on the search term and extracts the track name and artist from the top result.

    This function uses yt-dlp to perform a YouTube search and parses the title of the first result,
    assuming it's in the format 'Artist - Track' or similar.

    Args:
        search_term (str): The search term for the song (e.g., 'hello adele').

    Returns:
        dict: A dictionary with 'artist' and 'track' keys, or empty if parsing fails.

    Example:
        info = search_song('hello adele')
        print(info)  # {'artist': 'Adele', 'track': 'Hello'}
    """
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # Don't download, just get info
        'playlistend': 1,      # Only get the first result
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Search YouTube
            search_results = ydl.extract_info(f'ytsearch:{search_term} official audio', download=False)

            if 'entries' not in search_results or not search_results['entries']:
                return {}

            # Get the title of the first entry
            title = search_results['entries'][0]['title']

            # Parse title assuming 'Artist - Track' format
            match = re.match(r'^(?P<artist>.+?)\s*-\s*(?P<track>.+?)(?:\s*\(Official.*\)|\s*\[Official.*\])?$', title, re.IGNORECASE)
            if match:
                return {
                    'artist': match.group('artist').strip(),
                    'track': match.group('track').strip(),
                    'youtube_url': search_results['entries'][0]['url']
                }
            else:
                # Fallback: split on '-' and take first two parts
                parts = title.split(' - ', 1)
                if len(parts) == 2:
                    return {'artist': parts[0].strip(), 'track': parts[1].strip(), 'youtube_url': search_results['entries'][0]['url']}
                return {}

        except Exception as e:
            print(f"Error searching for {search_term}: {str(e)}")
            return {} 