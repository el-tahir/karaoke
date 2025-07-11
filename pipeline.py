import os
import logging
from song_search import search_song
from audio import download_mp3
from lyrics import get_lyrics
from subtitles import convert_lrc_to_ass
from video import create_karaoke_video
from separate import separate_audio
import re  # For sanitizing filenames

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_karaoke_from_search(search_term: str, output_dir: str = 'downloads') -> str:
    """
    Pipeline to create a karaoke video from a search term.

    1. Searches for song info (artist, track, youtube_url).
    2. Downloads MP3 audio from YouTube URL.
    3. Fetches LRC lyrics using artist and track.
    4. Converts LRC to ASS subtitles.
    5. Creates video with audio and ASS subtitles.

    Args:
        search_term (str): Search term for the song (e.g., 'hello adele').
        output_dir (str, optional): Directory to save all files. Defaults to 'downloads'.

    Returns:
        str: Path to the final karaoke video file, or None if any step fails.

    Example:
        video_path = create_karaoke_from_search('hello adele')
    """
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Search for song info
    try:
        song_info = search_song(search_term)
    except ValueError as e:
        logging.error(f"Error finding song info for '{search_term}': {str(e)}")
        return None
    artist = song_info['artist']
    track = song_info['track']
    safe_artist = re.sub(r'[^\w\s-]', '', artist).strip().replace(' ', '_')
    safe_track = re.sub(r'[^\w\s-]', '', track).strip().replace(' ', '_')
    youtube_url = song_info['youtube_url']
    logging.info(f"Found: {artist} - {track} ({youtube_url})")

    # Step 2: Download MP3
    try:
        # Capture existing MP3 files before download so we can reliably identify the newly downloaded one
        pre_download_mp3s = set(f for f in os.listdir(output_dir) if f.lower().endswith('.mp3'))

        download_mp3(youtube_url, output_dir)

        # First, try the straightforward approach: track name as filename
        audio_file = os.path.join(output_dir, f"{track}.mp3")

        if not os.path.exists(audio_file):
            # Identify MP3 files after download
            post_download_mp3s = [f for f in os.listdir(output_dir) if f.lower().endswith('.mp3')]
            # Determine what files are new
            new_files = [f for f in post_download_mp3s if f not in pre_download_mp3s]

            if new_files:
                # There should typically be exactly one new file — pick the first
                audio_file = os.path.join(output_dir, new_files[0])
            else:
                # Fallback: choose the most recently modified MP3 file
                mp3_paths = [os.path.join(output_dir, f) for f in post_download_mp3s]
                if not mp3_paths:
                    raise FileNotFoundError("No MP3 file found after download.")
                audio_file = max(mp3_paths, key=os.path.getmtime)
    except Exception as e:
        logging.error(f"Failed to download audio: {e}")
        return None

    # Step 2.5: Separate audio into instrumental and vocals
    try:
        instrumental, vocals = separate_audio(audio_file, output_dir)
    except Exception as e:
        logging.error(f"Failed to separate audio: {e}")
        return None

    # Step 3: Fetch LRC
    lrc_file = get_lyrics(artist, track, output_dir)
    if not lrc_file:
        logging.error("Failed to fetch lyrics")
        return None

    # Step 4: Convert to ASS
    ass_file = convert_lrc_to_ass(lrc_file, output_dir)
    if not ass_file:
        logging.error("Failed to convert to ASS")
        return None

    # Step 5: Create video
    video_filename = f"{safe_artist}_{safe_track}_karaoke.mp4"
    video_file = create_karaoke_video(instrumental, ass_file, output_file=os.path.join(output_dir, video_filename))
    if not video_file:
        logging.error("Failed to create video")
        return None

    logging.info(f"Karaoke video created: {video_file}")
    return video_file

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        logging.error("Usage: python pipeline.py 'search term'")
        sys.exit(1)
    search_term = sys.argv[1]
    create_karaoke_from_search(search_term) 