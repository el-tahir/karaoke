import yt_dlp

def download_mp3(url: str, output_dir: str = '.') -> None:
    """
    Downloads the audio from a given YouTube URL and saves it as an MP3 file.

    This function uses yt-dlp to extract the best available audio and convert it to MP3 format.
    Requires yt-dlp and ffmpeg to be installed.

    Args:
        url (str): The YouTube video URL to download audio from.
        output_dir (str, optional): The directory to save the MP3 file. Defaults to current directory.

    Returns:
        None

    Raises:
        Exception: If the download or conversion fails.

    Example:
        download_mp3('https://www.youtube.com/watch?v=BaW_jenozKc', output_dir='/path/to/save')
    """
    # Configuration options for yt-dlp
    ydl_opts = {
        # Select the best audio format
        'format': 'bestaudio/best',
        # Post-processing to extract audio as MP3
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            # Set quality to 192 kbps (adjustable)
            'preferredquality': '192',
        }],
        # Output template: save in specified directory with title as filename
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        # Quiet mode to suppress unnecessary output
        'quiet': True,
        # Continue on errors, but we'll handle exceptions
        'ignoreerrors': False,
    }

    # Create YoutubeDL instance and download
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            print(f"Successfully downloaded MP3 for: {url}")
        except Exception as e:
            print(f"Error downloading {url}: {str(e)}")
            raise 