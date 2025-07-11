import os
from song_search import search_song
from audio import download_mp3
from lyrics import get_lyrics
from subtitles import convert_lrc_to_ass
from video import create_karaoke_video
import re  # For sanitizing filenames

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
    song_info = search_song(search_term)
    if not song_info:
        print(f"No song info found for '{search_term}'")
        return None
    artist = song_info['artist']
    track = song_info['track']
    safe_artist = re.sub(r'[^\w\s-]', '', artist).strip().replace(' ', '_')
    safe_track = re.sub(r'[^\w\s-]', '', track).strip().replace(' ', '_')
    youtube_url = song_info['youtube_url']
    print(f"Found: {artist} - {track} ({youtube_url})")

    # Step 2: Download MP3
    try:
        download_mp3(youtube_url, output_dir)
        audio_file = os.path.join(output_dir, f"{track}.mp3")  # Assuming title matches track
        if not os.path.exists(audio_file):
            # Fallback: find the downloaded file
            for f in os.listdir(output_dir):
                if f.endswith('.mp3'):
                    audio_file = os.path.join(output_dir, f)
                    break
    except Exception as e:
        print(f"Failed to download audio: {e}")
        return None

    # Step 3: Fetch LRC
    lrc_file = get_lyrics(artist, track, output_dir)
    if not lrc_file:
        print("Failed to fetch lyrics")
        return None

    # Step 4: Convert to ASS
    ass_file = convert_lrc_to_ass(lrc_file, output_dir)
    if not ass_file:
        print("Failed to convert to ASS")
        return None

    # Step 5: Create video
    video_filename = f"{safe_artist}_{safe_track}_karaoke.mp4"
    video_file = create_karaoke_video(audio_file, ass_file, output_file=os.path.join(output_dir, video_filename))
    if not video_file:
        print("Failed to create video")
        return None

    print(f"Karaoke video created: {video_file}")
    return video_file

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py 'search term'")
        sys.exit(1)
    search_term = sys.argv[1]
    create_karaoke_from_search(search_term) 