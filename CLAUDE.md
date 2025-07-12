# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start Commands

**Main execution:**
```bash
# Basic usage with search term
python main.py "song title artist"

# Using a YouTube URL
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Using an instrumental YouTube URL (skips audio separation)
python main.py "https://www.youtube.com/watch?v=INSTRUMENTAL_URL" --instrumental-only

# With custom output directory
python main.py "song title" output_folder

# Word-level lyrics preferred
python main.py "song title" --word-level

# Debug mode
python main.py "song title" --debug
```

**Development setup:**
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Run with verbose output
python main.py "test song" --verbose
```

**External dependency check:**
```bash
# Verify ffmpeg is installed (required)
ffmpeg -version
ffprobe -version
```

## High-Level Architecture

### Pipeline Overview
The application follows a **modular pipeline architecture** that processes songs through these stages:

1. **Search/URL Processing** → Extract song metadata
2. **Audio Download** → Download from YouTube using yt-dlp
3. **Audio Separation** → Split vocals/instrumental using AI models
4. **Lyrics Fetching** → Get synchronized lyrics from multiple providers
5. **Lyrics Processing** → Romanization, timing adjustments
6. **Subtitle Generation** → Convert to ASS format with karaoke effects
7. **Video Rendering** → Create final MP4 files with subtitles

### Core Components

**Main Entry Points:**
- `main.py` - CLI interface with comprehensive argument parsing
- `karaoke_creator.core.pipeline.KaraokeCreator` - Main orchestrator class

**Key Data Models:**
- `SongInfo` - Core song metadata with filesystem-safe naming
- `ProcessingResult` - Standardized result object for all pipeline steps
- `Config` - Hierarchical configuration system (AudioConfig, VideoConfig, LyricsConfig)

**Processing Modules:**
- `karaoke_creator.core.search.youtube_search.YouTubeSearcher` - YouTube search and metadata extraction
- `karaoke_creator.core.audio.downloader.AudioDownloader` - Audio download via yt-dlp
- `karaoke_creator.core.audio.separator.AudioSeparator` - Vocal/instrumental separation
- `karaoke_creator.core.lyrics.fetcher.LyricsFetcher` - Multi-provider lyrics fetching

### Configuration System

The application uses a hierarchical JSON-based configuration system. Configuration can be:
- Loaded from JSON files (`--config path/to/config.json`)
- Overridden by command-line arguments
- Saved for reuse (`--save-config path/to/save.json`)

**Key configuration areas:**
- Audio processing settings (quality, separation model, GPU usage)
- Video output settings (resolution, fonts, background)  
- Lyrics preferences (word-level vs line-level, romanization)
- Directory management and cleanup options
- Processing modes (skip separation, create both versions)

### Error Handling Patterns

**Consistent error hierarchy:**
- Module-specific exceptions (e.g., `AudioDownloadError`, `LyricsFetchError`)
- Main pipeline wraps exceptions with context as `KaraokeCreationError`
- All operations return `ProcessingResult` objects with success/error status

**Recovery mechanisms:**
- Automatic file caching to avoid re-processing
- Fallback strategies (line-level lyrics if word-level unavailable)
- Graceful degradation for optional features (romanization, GPU acceleration)

### File Organization

```
downloads/          # Default working directory for intermediate files
final_videos/       # Default output directory for final MP4 videos
temp/              # Temporary files during processing
```

**Filename patterns:**
- Audio: `{artist}_{track}.mp3`, `{artist}_{track}_(Vocals|Instrumental).wav`
- Lyrics: `{artist}_{track}.lrc`, `line-level_{artist}_{track}.lrc`
- Subtitles: `{artist}_{track}.ass`
- Videos: `{artist}_{track}_karaoke.mp4`, `{artist}_{track}_original.mp4`

### Development Workflow

**When implementing new features:**
1. Follow the existing module structure in `karaoke_creator/core/`
2. Create module-specific exception classes
3. Return `ProcessingResult` objects from processing functions
4. Use the `LoggerMixin` for consistent logging
5. Add configuration options to the appropriate Config class
6. Implement caching where appropriate
7. Add both success and error test cases

**When debugging:**
- Use `--debug` flag for detailed logging
- Check `downloads/` directory for intermediate files
- Use `--dry-run` to see what would be processed without execution
- Use `--estimate-time` to get processing time estimates

### Integration Points

**External dependencies:**
- **ffmpeg/ffprobe** - Required system dependency for audio/video processing
- **yt-dlp** - YouTube downloading and metadata
- **audio-separator** - AI vocal separation (supports GPU acceleration)
- **syncedlyrics** - Multi-provider lyrics fetching
- **cutlet** - Japanese romanization (optional)

**API compatibility:**
- Both search terms and direct YouTube URLs supported
- YouTube Music URLs supported
- Handles various YouTube URL formats (youtube.com, youtu.be, music.youtube.com)

### Special Features

**Instrumental-only mode:**
- Use `--instrumental-only` with YouTube URLs that are already instrumental versions
- Skips AI-powered audio separation completely
- Only creates karaoke version (no original with vocals)
- Significantly faster processing for pre-separated instrumental tracks
- Requires YouTube URL input (not compatible with search terms)

**Japanese language support:**
- Automatic detection and romanization of Japanese lyrics
- Uses cutlet library for romanization when available
- Configurable romanization preferences

**Audio separation:**
- Multiple UVR model support (default: UVR_MDXNET_KARA_2.onnx)
- GPU acceleration when available
- Fallback to CPU processing
- Instrumental-only mode to skip separation entirely (`--instrumental-only`)

**Lyrics synchronization:**
- Preference for word-level timing when available
- Automatic fallback to line-level timing
- Multiple provider support (LRCLib, Musixmatch, etc.)

### Testing Approach

The codebase doesn't include a formal test suite but can be tested using:
- Direct CLI execution with known songs
- `--dry-run` mode for pipeline validation
- `--estimate-time` for performance analysis
- Different input types (search terms vs URLs)
- Various configuration combinations

**Common test scenarios:**
```bash
# Test basic functionality
python main.py "hello adele" --dry-run

# Test URL processing
python main.py "https://www.youtube.com/watch?v=YQHsXMglC9A" --dry-run

# Test instrumental-only mode
python main.py "https://www.youtube.com/watch?v=INSTRUMENTAL_URL" --instrumental-only --dry-run

# Test Japanese romanization
python main.py "japanese song" --debug

# Test configuration
python main.py "test" --config custom_config.json --dry-run
```