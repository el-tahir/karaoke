# Karaoke Creator

Generate your own karaoke videos in minutes — given **any YouTube link or search term**.  
The tool automatically downloads high-quality audio, separates vocals, fetches synchronised lyrics, and renders a polished MP4 with ASS subtitles.

[![CI](https://github.com/eltahhan/karaoke-creator/actions/workflows/ci.yml/badge.svg)](https://github.com/eltahhan/karaoke-creator/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Features

• **AI-powered vocal separation** (GPU & CPU)  
• **Multi-provider lyrics** — line or word level  
• **Japanese romanisation** support  
• **One-command workflow**: search ▶ download ▶ separate ▶ sync ▶ render  
• Outputs **MP4** video + all intermediate assets (MP3, LRC, ASS)

---

## Quick Start

```bash
# Clone & enter project
$ git clone https://github.com/eltahhan/karaoke-creator.git
$ cd karaoke-creator

# (Optional) Create virtual environment
$ python -m venv venv
$ source venv/bin/activate  # Windows: venv\Scripts\activate

# Install requirements
$ pip install -r requirements.txt

# Create karaoke video!
$ python main.py "hello adele"
```

The final MP4 will appear in `final_videos/`.

---

## Command-line Usage

```bash
python main.py "<search term or YouTube URL>" [options]
```

Common options:

| Option | Description |
| ------ | ----------- |
| `--output DIR` | Custom output directory |
| `--word-level` | Prefer word-level LRC when available |
| `--instrumental-only` | Skip separation when audio is already instrumental |
| `--config FILE` | Load settings from JSON file |
| `--save-config FILE` | Write current settings to JSON file |
| `--debug` | Verbose logging & keep all temp files |

Examples:

```bash
# Use direct YouTube link
python main.py "https://youtu.be/YQHsXMglC9A"

# Save video in ./my_karaoke
python main.py "radiohead creep" --output ./my_karaoke
```

---

## Requirements

* **Python 3.9+**  
* **ffmpeg** & **ffprobe** in your `PATH`

All Python dependencies are pinned in `requirements.txt` and installed via:

```bash
pip install -r requirements.txt
```

GPU acceleration for separation is automatically detected; CPU fallback is seamless.

---

## Project Layout

```
karaoke_creator/
├── core/           # audio, lyrics, video pipelines
├── models/         # pydantic data models
├── utils/          # helpers & config
└── main.py         # CLI entry-point
```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
