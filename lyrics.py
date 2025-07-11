import os
import re
import syncedlyrics

def get_lyrics(artist: str, track: str, output_dir: str = '.') -> str:
    """
    Fetches LRC lyrics for the given artist and track using syncedlyrics library and saves them to a file.

    Prioritizes enhanced (word-level) synced lyrics if available, falling back to regular synced.
    Determines if the syncing is word-level or line-level based on the content.
    Saves the file as '{kind_of_syncing}_{artist}_{track}.lrc' where kind_of_syncing is 'word-level' or 'line-level'.

    Args:
        artist (str): The artist name.
        track (str): The track name.
        output_dir (str, optional): Directory to save the LRC file. Defaults to current directory.

    Returns:
        str: The path to the saved LRC file, or None if no synced lyrics found.

    Example:
        file_path = get_lyrics('Adele', 'Hello')
    """
    # Sanitize artist and track for filename
    safe_artist = re.sub(r'[^\w\s-]', '', artist).strip().replace(' ', '_')
    safe_track = re.sub(r'[^\w\s-]', '', track).strip().replace(' ', '_')

    # Search term
    search_term = f"{track} {artist}"

    try:
        # First, try to get enhanced (word-level) lyrics
        lrc = syncedlyrics.search(search_term, enhanced=True)

        if not lrc:
            # Fallback to regular synced lyrics
            lrc = syncedlyrics.search(search_term, synced_only=True)

        if not lrc:
            print(f"No synced lyrics found for {artist} - {track}")
            return None

        # Determine syncing level
        # Check for word-level tags like <00:12.34>word
        if re.search(r'\[\d+:\d+\.\d+\]\s*<', lrc):
            kind = 'word-level'
        else:
            kind = 'line-level'

        # Create filename
        filename = f"{kind}_{safe_artist}_{safe_track}.lrc"
        file_path = os.path.join(output_dir, filename)

        # Save the LRC content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(lrc)

        print(f"Saved {kind} lyrics to {file_path}")
        return file_path

    except Exception as e:
        print(f"Error fetching lyrics: {str(e)}")
        return None 