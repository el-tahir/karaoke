# Karaoke Pipeline Caching System

The karaoke pipeline now includes a comprehensive caching system to avoid repeated expensive operations and significantly speed up subsequent runs.

## 🚀 What Gets Cached

The caching system automatically caches the following expensive operations:

### 1. **Audio Downloads** 🎵
- YouTube downloads by URL or search query
- Avoids re-downloading the same content
- Cache key: Content hash of URL/search query

### 2. **Audio Separation** 🎼  
- Separated instrumental and vocal stems
- Avoids re-running ML model inference
- Cache key: SHA256 hash of source audio file

### 3. **Lyrics Fetching** 🎤
- LRC lyric files by track/artist combination
- Avoids re-querying lyrics APIs
- Cache key: Content hash of "track|artist"

### 4. **Subtitle Generation** 📝
- ASS subtitle files from LRC files
- Avoids re-processing the same lyrics
- Cache key: SHA256 hash of LRC file content

### 5. **Video Rendering** 🎬
- Final MP4 videos with specific parameters
- Avoids re-rendering identical videos
- Cache key: Combined hash of audio, subtitles, resolution, and background

## 📁 Cache Structure

```
.cache/
├── audio/          # YouTube downloads
├── stems/          # Separated audio stems  
├── lyrics/         # LRC lyric files
├── subtitles/      # ASS subtitle files
└── videos/         # Rendered MP4 videos
```

Each cache entry consists of:
- **Metadata file** (`.json`): Contains paths and validation hashes
- **Actual cached files**: Stored in their respective output directories

## 🛠️ Managing the Cache

### View Cache Statistics
```bash
python -m karaoke cache stats
```

### Clear Specific Cache Type
```bash
python -m karaoke cache clear --type audio
python -m karaoke cache clear --type stems
python -m karaoke cache clear --type lyrics
python -m karaoke cache clear --type subtitles
python -m karaoke cache clear --type videos
```

### Clear All Caches
```bash
python -m karaoke cache clear
```

### List Cache Contents
```bash
python -m karaoke cache list audio
python -m karaoke cache list stems
# etc.
```

### Debug Audio Separation
```bash
python -m karaoke cache debug-separation audio.mp3
```

## ⚙️ Configuration

### Enable/Disable Caching
In `karaoke/config.py`:
```python
ENABLE_CACHE = True   # Set to False to disable entirely
CACHE_MAX_SIZE_GB = 10.0  # Maximum cache size (approximate)
```

### Disable Caching for One Run
```bash
python -m karaoke run --no-cache --youtube-url "https://youtube.com/watch?v=..."
```

## 🔍 How It Works

### Cache Key Generation
- **Content-based**: Uses SHA256 hashes of file contents or parameters
- **Deterministic**: Same inputs always generate the same cache key
- **Collision-resistant**: Different inputs are extremely unlikely to collide

### Cache Validation
- **File existence**: Checks if cached files still exist
- **Content integrity**: Validates file hashes when applicable
- **Automatic cleanup**: Removes invalid cache entries

### Cache Hit Logic
1. Generate cache key from inputs
2. Check if cache entry exists
3. Validate cached files exist and are valid
4. Return cached result or proceed with operation
5. Cache new results after successful operations

## 📊 Performance Benefits

| Operation | Time Without Cache | Time With Cache | Speedup |
|-----------|-------------------|-----------------|---------|
| YouTube Download | 30-60s | <1s | 30-60x |
| Audio Separation | 60-120s | <1s | 60-120x |
| Lyrics Fetching | 2-5s | <0.1s | 20-50x |
| Subtitle Generation | 1-3s | <0.1s | 10-30x |
| Video Rendering | 30-90s | <1s | 30-90x |

## 🧹 Cache Maintenance

### Automatic Cleanup
- Invalid cache entries are automatically removed
- Broken file references are cleaned up on access

### Manual Cleanup
- Use `cache clear` commands to free up disk space
- Monitor cache size with `cache stats`
- Consider clearing old caches periodically

## 🔒 Cache Safety

### Thread Safety
- File-based caching with atomic operations
- Safe for concurrent pipeline runs
- No database dependencies

### Data Integrity
- Content hashing prevents corruption issues
- Metadata validation ensures consistency
- Graceful fallback when cache is corrupted

## 💡 Best Practices

### For Development
- Use `--no-cache` when testing changes
- Clear relevant caches when debugging
- Monitor cache stats during development

### For Production
- Set appropriate `CACHE_MAX_SIZE_GB` limit
- Implement periodic cache cleanup
- Monitor disk usage

### For Different Environments
- Cache directories can be moved/shared
- Consider network storage for shared caches
- Backup important cached content

## 🐛 Troubleshooting

### Cache Not Working
1. Check `ENABLE_CACHE = True` in config
2. Verify cache directories are writable
3. Look for error messages in logs

### Cache Taking Too Much Space
1. Run `cache stats` to see usage
2. Clear unnecessary cache types
3. Adjust `CACHE_MAX_SIZE_GB` setting

### Corrupted Cache
1. Run `cache clear` to reset
2. Check file permissions
3. Verify disk space availability

### Performance Issues
1. Ensure cache directories are on fast storage
2. Check if antivirus is scanning cache files
3. Monitor I/O performance during operations

### Audio Separation Issues
If you see errors like "Instrumental file not found":
1. Check logs for debug information about file locations
2. The system now automatically searches multiple locations
3. Files are automatically moved to the correct directory
4. Test separation specifically: `python -m karaoke cache debug-separation audio.mp3`
5. Enable debug logging: `logger.setLevel(logging.DEBUG)`

### File Path Issues
The caching system includes robust error handling:
- **Graceful degradation**: Pipeline continues even if caching fails
- **Automatic cleanup**: Invalid cache entries are removed
- **Smart file location**: Finds files regardless of where they're saved
- **Path normalization**: Handles different path formats correctly

## 🔮 Future Enhancements

- **LRU eviction**: Automatic cleanup of least-recently-used entries
- **Compression**: Compress cached files to save space
- **Remote caching**: Support for shared network caches
- **Cache warming**: Pre-populate cache with common content
- **Analytics**: Detailed cache hit/miss statistics 