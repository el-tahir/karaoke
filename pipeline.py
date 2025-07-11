import os
import logging
from song_search import search_song
from audio import download_mp3
from lyrics import get_lyrics
from subtitles import convert_lrc_to_ass
from video import create_karaoke_video
from separate import separate_audio
import re  # For sanitizing filenames
import yt_dlp  # For extracting metadata when a direct YouTube URL is supplied

# ------------------------------------------------------------
# Helper: Extract song metadata directly from a YouTube URL
# ------------------------------------------------------------
def get_song_info_from_url(youtube_url: str) -> dict:
    """Extracts artist, track and canonical YouTube URL from a direct link.

    This mirrors the heuristics in ``song_search.search_song`` but skips the
    search step. We rely on yt-dlp to pull full metadata for the video and then
    attempt, in order of preference:

    1. ``artist`` / ``track`` fields provided by YouTube Music
    2. Fallback to the uploader/channel as *artist* and video title as *track*
    3. Regex parsing of the title in the form "<track> - <artist>"

    Args:
        youtube_url (str): A full YouTube or youtu.be URL.

    Returns:
        dict: {"artist": str, "track": str, "youtube_url": str}

    Raises:
        ValueError: If the metadata could not be parsed.
    """
    logging.info(f"Extracting metadata from YouTube URL: {youtube_url}")

    ydl_opts = {
        'quiet': True,
        'download': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            full_info = ydl.extract_info(youtube_url, download=False)
        except Exception as e:
            logging.exception("yt-dlp failed to extract info for the provided URL")
            raise ValueError(f"Could not extract info from URL: {e}") from e

    # Preferred fields supplied by YT Music
    artist = (full_info.get('artist') or
              full_info.get('uploader') or
              full_info.get('channel'))
    track = full_info.get('track') or full_info.get('title')

    # If artist/track still missing, try to parse from the title
    if not (artist and track):
        title = full_info.get('title', '')
        match = re.match(r'^(?P<track>.+?)\s*-\s*(?P<artist>.+?)\s*(?:\(.*?\)|\[.*?\])?$', title)
        if match:
            track = track or match.group('track').strip()
            artist = artist or match.group('artist').strip()

    if not (artist and track):
        raise ValueError("Unable to parse artist/track information from the provided URL")

    result = {
        'artist': artist.strip(),
        'track': track.strip(),
        'youtube_url': full_info.get('webpage_url') or youtube_url,
    }

    logging.info(f"Extracted info – Artist: {result['artist']} | Track: {result['track']}")
    return result


# ------------------------------------------------------------
# Internal: Shared karaoke creation logic (steps 2 ➜ 5)
# ------------------------------------------------------------
def _create_karaoke_from_info(song_info: dict, output_dir: str = 'downloads') -> str:
    """Shared implementation that takes a *parsed* ``song_info`` dict and runs
    the remaining karaoke pipeline steps (download → separation → lyrics →
    ASS → video).
    """

    # Unpack and sanitise
    artist = song_info['artist']
    track = song_info['track']
    youtube_url = song_info['youtube_url']

    safe_artist = re.sub(r'[^\w\s-]', '', artist).strip().replace(' ', '_')
    safe_track = re.sub(r'[^\w\s-]', '', track).strip().replace(' ', '_')

    os.makedirs(output_dir, exist_ok=True)

    # --------------------------------------------------------
    # Step 2: Download MP3
    # --------------------------------------------------------
    try:
        pre_dl_mp3s = {f for f in os.listdir(output_dir) if f.lower().endswith('.mp3')}
        download_mp3(youtube_url, output_dir)

        # First, optimistic filename match
        audio_file = os.path.join(output_dir, f"{track}.mp3")

        if not os.path.exists(audio_file):
            # Identify the newly downloaded file
            post_dl_mp3s = [f for f in os.listdir(output_dir) if f.lower().endswith('.mp3')]
            new_files = [f for f in post_dl_mp3s if f not in pre_dl_mp3s]
            if new_files:
                audio_file = os.path.join(output_dir, new_files[0])
            else:
                mp3_paths = [os.path.join(output_dir, f) for f in post_dl_mp3s]
                if not mp3_paths:
                    raise FileNotFoundError("No MP3 file located after download")
                audio_file = max(mp3_paths, key=os.path.getmtime)
    except Exception as e:
        logging.error(f"Failed to download audio: {e}")
        return None

    # --------------------------------------------------------
    # Step 2.5: Separate Vocals / Instrumental
    # --------------------------------------------------------
    try:
        instrumental, _ = separate_audio(audio_file, output_dir)
    except Exception as e:
        logging.error(f"Failed to separate audio: {e}")
        return None

    # --------------------------------------------------------
    # Step 3: Fetch Synced Lyrics
    # --------------------------------------------------------
    lrc_file = get_lyrics(artist, track, output_dir)
    if not lrc_file:
        logging.error("Failed to fetch lyrics")
        return None

    # --------------------------------------------------------
    # Step 4: Convert LRC ➜ ASS
    # --------------------------------------------------------
    ass_file = convert_lrc_to_ass(lrc_file, output_dir)
    if not ass_file:
        logging.error("Failed to convert to ASS")
        return None

    # --------------------------------------------------------
    # Step 5: Create Video
    # --------------------------------------------------------
    video_filename = f"{safe_artist}_{safe_track}_karaoke.mp4"
    video_path = create_karaoke_video(
        instrumental,
        ass_file,
        output_file=os.path.join(output_dir, video_filename),
    )

    if not video_path:
        logging.error("Failed to create karaoke video")
        return None

    # --------------------------------------------------------
    # Additional Step: Create video WITH original vocals
    # --------------------------------------------------------
    try:
        original_video_filename = f"{safe_artist}_{safe_track}_original.mp4"
        original_video_path = create_karaoke_video(
            audio_file,
            ass_file,
            output_file=os.path.join(output_dir, original_video_filename),
        )
        if original_video_path:
            logging.info(f"Original song video created successfully: {original_video_path}")
        else:
            logging.error("Failed to create original song video")
    except Exception as e:
        logging.error(f"Failed to create original song video: {e}")
    
    logging.info(f"Karaoke video created successfully: {video_path}")
    return video_path


# ------------------------------------------------------------
# Public: Create karaoke directly from a YouTube URL
# ------------------------------------------------------------
def create_karaoke_from_url(youtube_url: str, output_dir: str = 'downloads') -> str:
    """Alternate entry-point that accepts a direct YouTube link instead of a
    textual search query.
    """
    try:
        song_info = get_song_info_from_url(youtube_url)
    except ValueError as e:
        logging.error(str(e))
        return None

    return _create_karaoke_from_info(song_info, output_dir)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_karaoke_from_search(search_term: str, output_dir: str = 'downloads') -> str:
    """High-level helper that *searches* YouTube Music and then delegates to the
    shared pipeline implementation.
    """
    try:
        song_info = search_song(search_term)
    except ValueError as e:
        logging.error(f"Error finding song info for '{search_term}': {str(e)}")
        return None

    return _create_karaoke_from_info(song_info, output_dir)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        logging.error("Usage: python pipeline.py <search term|YouTube URL> [output_dir]")
        sys.exit(1)

    user_input = sys.argv[1]
    custom_output_dir = sys.argv[2] if len(sys.argv) >= 3 else 'downloads'

    # Basic heuristic: does the input look like a YT link?
    if re.match(r'^https?://(?:www\.)?(?:youtube\.com|youtu\.be)/', user_input, re.IGNORECASE):
        create_karaoke_from_url(user_input, custom_output_dir)
    else:
        create_karaoke_from_search(user_input, custom_output_dir) 