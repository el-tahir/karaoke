# Karaoke Video Creation Pipeline

This repository contains a pipeline that automatically generates a karaoke video with word-by-word highlighted lyrics.

## Features

*   Fetches time-synchronized lyrics (LRC format) with **syncedlyrics**.
*   Converts LRC to ASS subtitles with karaoke effects (word highlighting).
*   Separates vocals to create an instrumental backing track using **audio-separator**.
*   Combines instrumental audio, subtitles, and a background into a final **MP4** karaoke video using **FFmpeg**.
*   Downloads audio from YouTube using **yt-dlp**.

## Quick Start

1.  **Clone the repository** and create a Python virtual environment:
    ```bash
    git clone <repository-url>
    cd karaoke-o3
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install FFmpeg**:
    *   **macOS (Homebrew)**: `brew install ffmpeg`
    *   **Ubuntu/Debian**: `sudo apt-get update && sudo apt-get install ffmpeg`
    *   **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to your PATH.

## Usage

### Running Locally

1.  **Start the Backend Server**:
    ```bash
    python server.py
    ```
    The backend will be running at `http://localhost:8000`.

2.  **Start the Frontend Development Server**:
    In a new terminal, navigate to the `karaoke-ui` directory and start the Next.js app:
    ```bash
    cd karaoke-ui
    npm install
    npm run dev
    ```
    The frontend will be running at `http://localhost:3000`.

3.  **Open the App**:
    Open your browser and go to `http://localhost:3000`.

### Command-Line Interface

You can also use the pipeline directly from the command line.

**Using a local file:**

```bash
python -m karaoke --file "path/to/your/song.mp3" --track "Song Title" --artist "Artist Name"
```

**Using a YouTube URL:**

```bash
python -m karaoke --youtube-url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

If `--track` and `--artist` are not provided, the script will attempt to infer them from the filename (e.g., "Artist - Track.mp3").

### YouTube Cookies

To avoid YouTube's bot detection when running on a server, you can provide your YouTube cookies.

1.  **Extract Cookies**: Use a browser extension like "Get cookies.txt" to export your YouTube cookies in Netscape format.
2.  **Set Environment Variable**: Create an environment variable `YOUTUBE_COOKIES` with the content of the cookies file.

## Configuration

The core pipeline settings can be configured in `karaoke/config.py`. This includes:

*   Output directories for lyrics, subtitles, stems, and final videos.
*   Default video resolution and background color.
*   YouTube downloader options.