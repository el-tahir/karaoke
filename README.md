# Karaoke Creator 🎤

Generate your own karaoke videos in minutes – given *any* song on YouTube.

---

## Table of Contents
1. [Overview](#overview)
2. [Pipeline](#pipeline)
3. [Quick Start](#quick-start)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Project Structure](#project-structure)
7. [Troubleshooting](#troubleshooting)

---

## Overview
Karaoke Creator is a comprehensive Python toolkit that takes a simple search term or YouTube URL such as:

```bash
python main.py "hello adele"
```

and produces a full-blown **karaoke video** (`.mp4`) containing:

* high-quality **audio** downloaded from YouTube
* **AI-powered vocal separation** for instrumental tracks
* perfectly **synchronised lyrics** (word- or line-level)
* a clean **subtitle track** with karaoke effects
* **Japanese romanization** support

All heavy lifting (searching, downloading, separating, syncing, rendering) is automated so you can sit back and sing along.

---

## Pipeline
The process is orchestrated by the modular `KaraokeCreator` class and consists of seven clear stages:

1. **Search/URL Processing** (`youtube_search.py`)
   * Finds the best audio match and extracts comprehensive song metadata.
2. **Download Audio** (`downloader.py`)
   * Uses `yt-dlp` + `ffmpeg` to download and convert audio.
3. **Audio Separation** (`separator.py`)
   * Uses AI models to separate vocals from instrumental tracks.
4. **Fetch Synced Lyrics** (`fetcher.py`)
   * Queries multiple providers for enhanced (word-level) or fallback (line-level) `.lrc` files.
5. **Lyrics Processing** (`japanese_romanizer.py`)
   * Handles Japanese romanization and timing adjustments.
6. **Convert to ASS** (`ass_converter.py`)
   * Converts `.lrc` files into stylized `.ass` subtitle format with karaoke effects.
7. **Render Video** (`simple_renderer.py`)
   * Creates final videos with subtitles and audio tracks.

---

## Quick Start
```bash
# 1. Clone the repo
$ git clone https://github.com/your-user/karaoke.git
$ cd karaoke

# 2. Create & activate a virtual env (optional but recommended)
$ python -m venv venv
$ source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
$ pip install -r requirements.txt

# 4. Generate a karaoke video!
$ python main.py "hello adele"

# 5. Check the final_videos/ folder for the resulting MP4 files
#    and downloads/ folder for intermediate files (MP3, LRC, ASS)
```

---

## Installation

### Prerequisites
* **Python 3.9+** (tested on 3.12)
* **ffmpeg** – make sure the executable is discoverable via `$PATH`
* **ffprobe** (bundled with ffmpeg) – used for duration detection

### Python Packages
All required packages are listed in `requirements.txt`. The key ones are:

| Package | Purpose |
|---------|---------|
| [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) | YouTube downloading & metadata |
| [`audio-separator`](https://github.com/nomadkaraoke/python-audio-separator) | AI-powered vocal separation with GPU support |
| [`syncedlyrics`](https://github.com/MauroB0/syncedlyrics) | Retrieve synced `.lrc` lyrics |
| [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/) | HTML parsing |
| [`rapidfuzz`](https://github.com/maxbachmann/RapidFuzz) | Fuzzy string matching |
| [`cutlet`](https://github.com/polm/cutlet) | Japanese romanization (optional) |

Install everything with:

```bash
pip install -r requirements.txt
```

---

## Usage

### Command Line
```bash
python main.py "<search term or YouTube URL>"
```

Examples:
```bash
# Search term
python main.py "hello adele"

# YouTube URL  
python main.py "https://www.youtube.com/watch?v=YQHsXMglC9A"

# Custom output directory
python main.py "radiohead creep" ./my_karaoke

# Word-level lyrics preferred
python main.py "song title artist" --word-level

# Instrumental-only mode (for pre-separated tracks)
python main.py "https://www.youtube.com/watch?v=INSTRUMENTAL_URL" --instrumental-only

# Debug mode
python main.py "song title" --debug
```

All intermediate files are written to the `downloads/` directory and final videos to `final_videos/` by default.

### As a Library
You can also import and use the components programmatically:

```python
from karaoke_creator import KaraokeCreator, Config

# Create with default configuration
creator = KaraokeCreator()

# Create karaoke from search term
result = creator.create_karaoke_from_search("hello adele")

# Create karaoke from YouTube URL
result = creator.create_karaoke_from_url("https://www.youtube.com/watch?v=YQHsXMglC9A")
```

### Configuration
The application supports JSON-based configuration files:

```bash
# Use custom configuration
python main.py "song title" --config my_config.json

# Save current settings to file
python main.py "song title" --save-config my_config.json
```

---

## Project Structure
```
karaoke_creator/
├── core/
│   ├── audio/
│   │   ├── downloader.py      # YouTube audio downloading
│   │   └── separator.py       # AI vocal/instrumental separation  
│   ├── lyrics/
│   │   └── fetcher.py         # Multi-provider lyrics fetching
│   ├── search/
│   │   └── youtube_search.py  # YouTube search & metadata
│   ├── video/
│   │   ├── ass_converter.py   # LRC to ASS subtitle conversion
│   │   └── simple_renderer.py # Video rendering
│   └── pipeline.py            # Main orchestration class
├── models/
│   └── song_info.py           # Data models
├── utils/
│   ├── config.py              # Configuration management
│   ├── file_utils.py          # File operations
│   ├── japanese_romanizer.py  # Japanese text processing
│   └── logging.py             # Logging utilities
├── main.py                    # CLI interface
├── downloads/                 # Intermediate files
└── final_videos/              # Final MP4 outputs
```

---

## Troubleshooting
| Issue | Solution |
|-------|----------|
| `ffmpeg` / `ffprobe` not found | Install FFmpeg from https://ffmpeg.org/ and ensure it is on your PATH |
| No synced lyrics found | Some songs don't have public `.lrc` files. Try a different search term or use `--lrc-file` to provide your own |
| Audio separation fails | Try CPU-only mode if GPU fails, or use `--instrumental-only` with pre-separated tracks |
| Wrong artist/track detected | The YouTube parser is heuristic – try using direct YouTube URLs instead of search terms |
| Out of memory during processing | Reduce audio quality with `--audio-quality 128k` or use shorter songs for testing |
| Japanese text not romanized | Install the optional `cutlet` package: `pip install cutlet` |

---

---
