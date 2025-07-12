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

# Try to import cutlet for optional Japanese→romaji conversion
try:
    import cutlet  # type: ignore
except ImportError:
    cutlet = None  # Will be checked at runtime

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
# Helper: Romanize Japanese lyrics in an LRC file (in-place)
# ------------------------------------------------------------

def _romanize_lrc_inplace(lrc_path: str) -> bool:
    """Detects Japanese characters in *lrc_path* and rewrites the file with
    romaji lyrics using *cutlet*.

    Timestamp tags (both line-level ``[mm:ss.xx]`` and word-level
    ``<mm:ss.xx>``) are preserved verbatim – only the lyric text segments are
    transformed. Returns **True** if the file was modified, **False** if no
    Japanese text was found or *cutlet* is unavailable.
    """
    import re

    # Fast exit if cutlet isn't installed
    if cutlet is None:
        logging.warning("cutlet not available – skipping romanization step")
        return False

    # Load file
    try:
        with open(lrc_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        logging.error(f"Could not read LRC for romanization: {e}")
        return False

    jp_char_re = re.compile(r'[\u3040-\u30ff\u4e00-\u9FFF]')  # Hiragana|Katakana|Kanji
    if not any(jp_char_re.search(line) for line in lines):
        # No Japanese text detected – nothing to do
        return False

    katsu = cutlet.Cutlet()
    tag_re = re.compile(r'(<\d+:\d+\.\d+>)')
    new_lines = []

    for raw in lines:
        line = raw.rstrip('\n')

        # Skip possible metadata/id tags like [ti:], [ar:], etc.
        if re.match(r'^\[[a-zA-Z]{2,}:.*\]$', line):
            new_lines.append(raw)
            continue

        # Split off the first closing bracket to get line-level timestamps
        if ']' in line:
            prefix, rest = line.split(']', 1)
            prefix += ']'
        else:
            prefix, rest = '', line

        parts = tag_re.split(rest)
        transformed_segments = []
        for part in parts:
            if tag_re.match(part):
                # Word-level timestamp – keep as is
                transformed_segments.append(part)
            else:
                transformed_segments.append(
                    katsu.romaji(part) if jp_char_re.search(part) else part
                )

        new_lines.append(prefix + ''.join(transformed_segments) + '\n')

    # Write back
    try:
        with open(lrc_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        logging.info(f"Romanized Japanese lyrics in {lrc_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to write romanized LRC: {e}")
        return False


# ------------------------------------------------------------
# Internal: Shared karaoke creation logic (steps 2 ➜ 5)
# ------------------------------------------------------------
def _create_karaoke_from_info(song_info: dict, output_dir: str = 'downloads', line_level_only: bool = True) -> str:
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
    lrc_file = get_lyrics(artist, track, output_dir, line_level_only=line_level_only)
    if not lrc_file:
        logging.error("Failed to fetch lyrics")
        return None

    # --------------------------------------------------------
    # NEW: Romanize Japanese lyrics (if applicable)
    # --------------------------------------------------------
    try:
        _romanize_lrc_inplace(lrc_file)
    except Exception as e:
        logging.warning(f"Romanization step failed: {e}")

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
    # Ensure a dedicated directory exists for all final karaoke videos
    final_videos_dir = 'final_videos'
    os.makedirs(final_videos_dir, exist_ok=True)

    video_filename = f"{safe_artist}_{safe_track}_karaoke.mp4"
    video_path = create_karaoke_video(
        instrumental,
        ass_file,
        output_file=os.path.join(final_videos_dir, video_filename),
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
            output_file=os.path.join(final_videos_dir, original_video_filename),
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
def create_karaoke_from_url(youtube_url: str, output_dir: str = 'downloads', line_level_only: bool = True) -> str:
    """Alternate entry-point that accepts a direct YouTube link instead of a
    textual search query.
    """
    try:
        song_info = get_song_info_from_url(youtube_url)
    except ValueError as e:
        logging.error(str(e))
        return None

    return _create_karaoke_from_info(song_info, output_dir, line_level_only=line_level_only)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_karaoke_from_search(search_term: str, output_dir: str = 'downloads', line_level_only: bool = True) -> str:
    """High-level helper that *searches* YouTube Music and then delegates to the
    shared pipeline implementation.
    """
    try:
        song_info = search_song(search_term)
    except ValueError as e:
        logging.error(f"Error finding song info for '{search_term}': {str(e)}")
        return None

    return _create_karaoke_from_info(song_info, output_dir, line_level_only=line_level_only)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Generate karaoke videos (instrumental & original) from a YouTube link or song search term.")
    parser.add_argument('input', help='Search term or YouTube URL')
    parser.add_argument('output_dir', nargs='?', default='downloads', help='Directory to store output files (default: downloads)')
    parser.add_argument('-w', '--word-level', action='store_true', help='Enable word-level lyric syncing (default: line-level)')

    args = parser.parse_args()

    # Accept any sub-domain of youtube.com (e.g. www., music., m.) in addition to youtu.be short links
    if re.match(r'^https?://(?:[\w.-]+\.)?(?:youtube\.com|youtu\.be)/', args.input, re.IGNORECASE):
        create_karaoke_from_url(args.input, args.output_dir, line_level_only=not args.word_level)
    else:
        create_karaoke_from_search(args.input, args.output_dir, line_level_only=not args.word_level) 