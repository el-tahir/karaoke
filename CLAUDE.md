# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based karaoke video generation toolkit that automatically creates karaoke videos from YouTube songs. The system downloads audio, separates vocals from instrumentals, fetches synchronized lyrics, and renders videos with subtitle effects.

## Essential Commands

### Running the Pipeline
```bash
# Generate karaoke from search term
python pipeline.py "jigsaw falling into place radiohead"

# Generate from direct YouTube URL
python pipeline.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Custom output directory
python pipeline.py "hello adele" /path/to/output

# Enable word-level syncing (default is line-level)
python pipeline.py "song name artist" -w
```

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies
- **FFmpeg** must be installed and available in PATH (required for audio processing)
- **yt-dlp** for YouTube downloading
- **audio-separator[gpu]** for vocal/instrumental separation

## Architecture Overview

The system follows a 5-stage pipeline orchestrated by `pipeline.py`:

1. **Song Search** (`song_search.py`): YouTube Music search and metadata extraction
2. **Audio Download** (`audio.py`): Downloads audio as MP3 using yt-dlp
3. **Audio Separation** (`separate.py`): Separates vocals/instrumentals using UVR models
4. **Lyrics Fetching** (`lyrics.py`): Retrieves synchronized LRC files via syncedlyrics
5. **Video Generation** (`video.py`): Creates karaoke videos with ASS subtitles

### Key Architecture Patterns

- **Dual Video Output**: System generates both karaoke (instrumental) and original (with vocals) versions
- **Flexible Input**: Accepts either search terms or direct YouTube URLs
- **Japanese Support**: Optional romanization of Japanese lyrics using cutlet library
- **Lyric Syncing Levels**: Supports both word-level and line-level synchronized lyrics
- **File Naming Convention**: Uses sanitized artist/track names for consistent file organization

### Directory Structure
- `downloads/`: Intermediate files (MP3, LRC, ASS)
- `final_videos/`: Generated karaoke MP4 files
- Individual Python modules handle specific pipeline stages

### Core Data Flow
1. Input → Song metadata extraction
2. YouTube URL → MP3 download
3. MP3 → Vocal/instrumental separation
4. Artist/track → LRC lyrics fetching
5. LRC → ASS subtitle conversion with karaoke effects
6. Audio + ASS → Final MP4 video rendering

### Error Handling Patterns
- Graceful fallbacks for missing lyrics or metadata
- Comprehensive logging throughout pipeline stages
- File existence checks and automatic cleanup
- Support for both enhanced and basic lyric formats

## Development Notes

- The pipeline creates two video versions: `*_karaoke.mp4` (instrumental) and `*_original.mp4` (with vocals)
- Japanese text is automatically detected and romanized if the `cutlet` library is available
- Word-level lyrics provide karaoke highlighting effects; line-level provides simpler scrolling
- Audio separation uses the UVR_MDXNET_KARA_2.onnx model optimized for karaoke separation