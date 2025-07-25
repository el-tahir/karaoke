# Configuration Examples

This directory contains sample configuration files for different use cases.

## Available Configurations

### basic_config.json
A basic configuration suitable for most users:
- 1080p resolution
- 192k audio quality
- GPU acceleration enabled
- Word-level lyrics preferred

Usage:
```bash
python main.py "song title artist" --config examples/basic_config.json
```

### high_quality_config.json
High-quality configuration for professional use:
- 4K resolution (3840x2160)
- 320k audio quality
- 60 FPS video
- Larger font size for better readability

Usage:
```bash
python main.py "song title artist" --config examples/high_quality_config.json
```

## Creating Custom Configurations

You can create your own configuration files by copying one of these examples and modifying the values to suit your needs. All configuration options are documented in the main README.md file.

### Configuration Structure

```json
{
  "audio": {
    "quality": "192k|320k|128k",
    "format": "mp3|wav",
    "enable_gpu": true|false,
    "separation_model": "model_name.onnx"
  },
  "video": {
    "resolution": "1920x1080|3840x2160|1280x720",
    "fps": 30|60,
    "font_size": 48|96|72,
    "font_name": "Arial|Helvetica|...",
    "background_color": "#000000|#1a1a1a|..."
  },
  "lyrics": {
    "prefer_word_level": true|false,
    "enable_romanization": true|false,
    "fallback_to_line_level": true|false
  },
  "processing": {
    "cleanup_temp_files": true|false,
    "create_both_versions": true|false,
    "skip_existing": true|false
  }
}
```