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
8. [Contributing](#contributing)
9. [License](#license)

---

## Overview
`karaoke` is a small Python toolkit that takes a simple search term such as:

```bash
python pipeline.py "jigsaw falling into place radiohead"
```

and produces a full-blown **karaoke video** (`.mp4`) containing:

* high-quality **audio** downloaded from YouTube
* perfectly **synchronised lyrics** (word- or line-level)
* a clean **subtitle track** with karaoke effects

All heavy lifting (searching, downloading, syncing, rendering) is automated so you can sit back and sing along.

---

## Pipeline
The process is orchestrated by `pipeline.py` and consists of five clear stages:

1. **Search YouTube** (`song_search.py`)
   * Finds the first official audio match and extracts the artist, track and video URL.
2. **Download Audio** (`audio.py`)
   * Uses `yt-dlp` + `ffmpeg` to grab & convert the audio into an MP3.
3. **Fetch Synced Lyrics** (`lyrics.py`)
   * Queries the internet (via the `syncedlyrics` package) for enhanced (word-level) or fallback (line-level) `.lrc` files.
4. **Convert to ASS** (`subtitles.py`)
   * Turns the `.lrc` file into a stylised `.ass` subtitle format with karaoke effects.
5. **Render Video** (`video.py`)
   * Creates a blank background, burns in the subtitles and muxes the audio to produce the final `.mp4`.

---

## Quick Start
```bash
# 1. Clone the repo
$ git clone https://github.com/your-user/karaoke.git
$ cd karaoke

# 2. Create & activate a virtual env  (optional but recommended)
$ python -m venv venv
$ source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
$ pip install -r requirements.txt  # or `pip install -e .` if you build a package

# 4. Generate a karaoke video!
$ python pipeline.py "bad romance lady gaga"

# 5. Check the `downloads/` folder for the resulting MP3, LRC, ASS and MP4 files.
```

---

## Installation

### Prerequisites
* **Python 3.9+** (tested on 3.12)
* **ffmpeg** – make sure the executable is discoverable via `$PATH`
* **ffprobe** (bundled with ffmpeg) – used for duration detection

### Python Packages
All required packages are pure-Python and listed in `requirements.txt`. The key ones are:

| Package | Purpose |
|---------|---------|
| [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) | YouTube downloading & metadata |
| [`syncedlyrics`](https://github.com/MauroB0/syncedlyrics) | Retrieve synced `.lrc` lyrics |
| [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/) | HTML parsing (dependency of syncedlyrics) |
| [`rapidfuzz`](https://github.com/maxbachmann/RapidFuzz) | Fuzzy string matching for lyric providers |
| [`requests`](https://docs.python-requests.org/) | HTTP requests for lyric providers |

Install everything with:

```bash
pip install -r requirements.txt
```

---

## Usage

### Command Line
```bash
python pipeline.py "<search term>"
```

Examples:
```bash
python pipeline.py "vienna billy joel"
python pipeline.py "phoebe bridgers motion sickness"
```

All intermediate and final artefacts are written to the `downloads/` directory by default. You can override that by passing a second argument:

```bash
python pipeline.py "money pink floyd" /path/to/output
```

### As a Library
You can also import and reuse individual steps:

```python
from audio import download_mp3
from lyrics import get_lyrics

url = "https://www.youtube.com/watch?v=PrlW9gCiC9c"
download_mp3(url, output_dir="my_music")
```

---

## Project Structure
```
karaoke/
├── audio.py          # Download audio from YouTube as MP3
├── lyrics.py         # Fetch synced lyrics (.lrc)
├── song_search.py    # Search YT & parse artist/track
├── subtitles.py      # Convert LRC ➜ ASS with karaoke effects
├── video.py          # Burn subtitles & mux audio ➜ MP4
├── pipeline.py       # Glue everything together
└── downloads/        # Auto-generated output files
```

---

## Troubleshooting
| Issue | Solution |
|-------|----------|
| `ffmpeg` / `ffprobe` not found | Install FFmpeg from https://ffmpeg.org/ and ensure it is on your PATH |
| No synced lyrics found | Some songs don’t have public `.lrc` files. Try a different search term or add lyrics manually |
| Wrong artist/track detected | The YouTube title parser is heuristic – tweak `song_search.py` or provide your own `artist`/`track` names |

---

## Contributing
Pull requests are welcome! Feel free to open issues for feature requests or bugs. Please follow the existing code style and include docstrings/tests where appropriate.

---

## License
MIT © Your Name Here 