import os
import subprocess
import json

def get_audio_duration(audio_file: str) -> float:
    """
    Gets the duration of the audio file in seconds using ffprobe.
    """
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', audio_file]
    output = subprocess.check_output(cmd)
    data = json.loads(output)
    return float(data['format']['duration'])

def create_karaoke_video(audio_file: str, ass_file: str, output_file: str = None, resolution: str = '1280x720', background_color: str = 'black') -> str:
    """
    Creates a karaoke video by burning ASS subtitles into a blank video with the given audio.

    Args:
        audio_file (str): Path to the input audio file (e.g., MP3).
        ass_file (str): Path to the input ASS subtitle file.
        output_file (str, optional): Path to save the output video. Defaults to '{audio_basename}_karaoke.mp4'.
        resolution (str, optional): Video resolution, e.g., '1280x720'.
        background_color (str, optional): Background color for the video.

    Returns:
        str: Path to the created video file.

    Requires ffmpeg to be installed.

    Example:
        create_karaoke_video('song.mp3', 'subtitles.ass')
    """
    if output_file is None:
        base = os.path.splitext(os.path.basename(audio_file))[0]
        output_file = f"{base}_karaoke.mp4"

    # Get audio duration
    duration = get_audio_duration(audio_file)

    # ffmpeg command to create blank video, attach audio, burn subs
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', f'color=c={background_color}:s={resolution}:d={duration}',
        '-i', audio_file,
        '-vf', f'subtitles={ass_file}',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-shortest',
        output_file
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"Created karaoke video: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error creating video: {e}")
        raise 