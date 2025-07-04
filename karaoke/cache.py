"""Caching utilities for the karaoke pipeline."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable, TypeVar, Union
import shutil

from . import config

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheManager:
    """Manages file-based caching for expensive pipeline operations."""
    
    def __init__(self, cache_base_dir: Optional[Path] = None):
        self.cache_base_dir = cache_base_dir or (config.BASE_DIR / ".cache")
        self.cache_base_dir.mkdir(exist_ok=True, parents=True)
        
        # Cache subdirectories for different types of operations
        self.audio_cache_dir = self.cache_base_dir / "audio"
        self.stems_cache_dir = self.cache_base_dir / "stems" 
        self.lyrics_cache_dir = self.cache_base_dir / "lyrics"
        self.subtitles_cache_dir = self.cache_base_dir / "subtitles"
        self.videos_cache_dir = self.cache_base_dir / "videos"
        
        for cache_dir in [self.audio_cache_dir, self.stems_cache_dir, 
                         self.lyrics_cache_dir, self.subtitles_cache_dir, 
                         self.videos_cache_dir]:
            cache_dir.mkdir(exist_ok=True, parents=True)

    def _get_file_hash(self, file_path: Path) -> str:
        """Generate SHA256 hash of file contents."""
        if not file_path.exists():
            raise FileNotFoundError(f"Cannot hash non-existent file: {file_path}")
        
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except (OSError, IOError) as e:
            raise RuntimeError(f"Failed to read file for hashing: {file_path}") from e

    def _get_content_hash(self, content: Union[str, bytes, Dict[str, Any]]) -> str:
        """Generate SHA256 hash of content."""
        if isinstance(content, dict):
            content = json.dumps(content, sort_keys=True)
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def _get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {"args": args, "kwargs": kwargs}
        return self._get_content_hash(key_data)

    def get_cached_audio(self, url_or_query: str) -> Optional[Path]:
        """Check if audio is cached for a YouTube URL or search query."""
        if not config.ENABLE_AUDIO_CACHE:
            return None
            
        cache_key = self._get_content_hash(url_or_query)
        cache_file = self.audio_cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                cache_data = json.loads(cache_file.read_text())
                audio_path = Path(cache_data["audio_path"])
                if audio_path.exists():
                    logger.info(f"Using cached audio: {audio_path}")
                    return audio_path
                else:
                    # Clean up invalid cache entry
                    cache_file.unlink()
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid cache file {cache_file}: {e}")
                cache_file.unlink()
        
        return None

    def cache_audio(self, url_or_query: str, audio_path: Path) -> None:
        """Cache audio file for a YouTube URL or search query."""
        if not config.ENABLE_AUDIO_CACHE:
            return
            
        cache_key = self._get_content_hash(url_or_query)
        cache_file = self.audio_cache_dir / f"{cache_key}.json"
        
        cache_data = {
            "url_or_query": url_or_query,
            "audio_path": str(audio_path.resolve()),
            "file_hash": self._get_file_hash(audio_path)
        }
        
        cache_file.write_text(json.dumps(cache_data, indent=2))
        logger.info(f"Cached audio for: {url_or_query}")

    def get_cached_stems(self, audio_path: Path) -> Optional[tuple[Path, Path]]:
        """Check if separated stems are cached for an audio file."""
        if not config.ENABLE_STEMS_CACHE:
            return None
            
        file_hash = self._get_file_hash(audio_path)
        cache_file = self.stems_cache_dir / f"{file_hash}.json"
        
        if cache_file.exists():
            try:
                cache_data = json.loads(cache_file.read_text())
                instrumental_path = Path(cache_data["instrumental_path"])
                vocals_path = Path(cache_data["vocals_path"])
                
                if instrumental_path.exists() and vocals_path.exists():
                    logger.info(f"Using cached stems for: {audio_path.name}")
                    return instrumental_path, vocals_path
                else:
                    # Clean up invalid cache entry
                    cache_file.unlink()
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid stems cache file {cache_file}: {e}")
                cache_file.unlink()
        
        return None

    def cache_stems(self, audio_path: Path, instrumental_path: Path, vocals_path: Path) -> None:
        """Cache separated stems for an audio file."""
        if not config.ENABLE_STEMS_CACHE:
            return
            
        file_hash = self._get_file_hash(audio_path)
        cache_file = self.stems_cache_dir / f"{file_hash}.json"
        
        cache_data = {
            "audio_path": str(audio_path.resolve()),
            "audio_hash": file_hash,
            "instrumental_path": str(instrumental_path.resolve()),
            "vocals_path": str(vocals_path.resolve())
        }
        
        cache_file.write_text(json.dumps(cache_data, indent=2))
        logger.info(f"Cached stems for: {audio_path.name}")

    def get_cached_lyrics(self, track: str, artist: str) -> Optional[Path]:
        """Check if lyrics are cached for a track/artist combination."""
        if not config.ENABLE_LYRICS_CACHE:
            return None
            
        cache_key = self._get_content_hash(f"{track}|{artist}")
        cache_file = self.lyrics_cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                cache_data = json.loads(cache_file.read_text())
                lyrics_path = Path(cache_data["lyrics_path"])
                if lyrics_path.exists():
                    logger.info(f"Using cached lyrics for: {track} by {artist}")
                    return lyrics_path
                else:
                    cache_file.unlink()
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid lyrics cache file {cache_file}: {e}")
                cache_file.unlink()
        
        return None

    def cache_lyrics(self, track: str, artist: str, lyrics_path: Path) -> None:
        """Cache lyrics for a track/artist combination."""
        if not config.ENABLE_LYRICS_CACHE:
            return
            
        cache_key = self._get_content_hash(f"{track}|{artist}")
        cache_file = self.lyrics_cache_dir / f"{cache_key}.json"
        
        cache_data = {
            "track": track,
            "artist": artist,
            "lyrics_path": str(lyrics_path.resolve()),
            "content_hash": self._get_file_hash(lyrics_path) if lyrics_path.exists() else None
        }
        
        cache_file.write_text(json.dumps(cache_data, indent=2))
        logger.info(f"Cached lyrics for: {track} by {artist}")

    def get_cached_subtitles(self, lrc_path: Path) -> Optional[Path]:
        """Check if subtitles are cached for an LRC file."""
        if not config.ENABLE_SUBTITLES_CACHE:
            return None
            
        lrc_hash = self._get_file_hash(lrc_path)
        cache_file = self.subtitles_cache_dir / f"{lrc_hash}.json"
        
        if cache_file.exists():
            try:
                cache_data = json.loads(cache_file.read_text())
                subtitles_path = Path(cache_data["subtitles_path"])
                if subtitles_path.exists():
                    logger.info(f"Using cached subtitles for: {lrc_path.name}")
                    return subtitles_path
                else:
                    cache_file.unlink()
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid subtitles cache file {cache_file}: {e}")
                cache_file.unlink()
        
        return None

    def cache_subtitles(self, lrc_path: Path, subtitles_path: Path) -> None:
        """Cache subtitles for an LRC file."""
        if not config.ENABLE_SUBTITLES_CACHE:
            return
            
        lrc_hash = self._get_file_hash(lrc_path)
        cache_file = self.subtitles_cache_dir / f"{lrc_hash}.json"
        
        cache_data = {
            "lrc_path": str(lrc_path.resolve()),
            "lrc_hash": lrc_hash,
            "subtitles_path": str(subtitles_path.resolve())
        }
        
        cache_file.write_text(json.dumps(cache_data, indent=2))
        logger.info(f"Cached subtitles for: {lrc_path.name}")

    def get_cached_video(self, audio_path: Path, subtitles_path: Path, 
                        resolution: str, background_color: str,
                        background_path: Optional[str] = None, 
                        crf: int = 18) -> Optional[Path]:
        """Check if video is cached for given parameters."""
        if not config.ENABLE_VIDEO_CACHE:
            return None
            
        cache_params = {
            "audio_hash": self._get_file_hash(audio_path),
            "subtitles_hash": self._get_file_hash(subtitles_path),
            "resolution": resolution,
            "background_color": background_color,
            "background_path": background_path,
            "crf": crf
        }
        cache_key = self._get_content_hash(cache_params)
        cache_file = self.videos_cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                cache_data = json.loads(cache_file.read_text())
                video_path = Path(cache_data["video_path"])
                if video_path.exists():
                    logger.info(f"Using cached video: {video_path.name}")
                    return video_path
                else:
                    cache_file.unlink()
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid video cache file {cache_file}: {e}")
                cache_file.unlink()
        
        return None

    def cache_video(self, audio_path: Path, subtitles_path: Path, resolution: str, 
                   background_color: str, background_path: Optional[str], 
                   crf: int, video_path: Path) -> None:
        """Cache video for given parameters."""
        if not config.ENABLE_VIDEO_CACHE:
            return
            
        cache_params = {
            "audio_hash": self._get_file_hash(audio_path),
            "subtitles_hash": self._get_file_hash(subtitles_path),
            "resolution": resolution,
            "background_color": background_color,
            "background_path": background_path,
            "crf": crf
        }
        cache_key = self._get_content_hash(cache_params)
        cache_file = self.videos_cache_dir / f"{cache_key}.json"
        
        cache_data = {
            "audio_path": str(audio_path.resolve()),
            "subtitles_path": str(subtitles_path.resolve()),
            "resolution": resolution,
            "background_color": background_color,
            "background_path": background_path,
            "crf": crf,
            "video_path": str(video_path.resolve()),
            "cache_params": cache_params
        }
        
        cache_file.write_text(json.dumps(cache_data, indent=2))
        logger.info(f"Cached video: {video_path.name}")

    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """Clear cache. If cache_type is None, clears all caches."""
        cache_dirs = {
            "audio": self.audio_cache_dir,
            "stems": self.stems_cache_dir,
            "lyrics": self.lyrics_cache_dir,
            "subtitles": self.subtitles_cache_dir,
            "videos": self.videos_cache_dir
        }
        
        if cache_type:
            if cache_type in cache_dirs:
                shutil.rmtree(cache_dirs[cache_type])
                cache_dirs[cache_type].mkdir(exist_ok=True)
                logger.info(f"Cleared {cache_type} cache")
            else:
                logger.warning(f"Unknown cache type: {cache_type}")
        else:
            shutil.rmtree(self.cache_base_dir)
            self.__init__(self.cache_base_dir)
            logger.info("Cleared all caches")

    def get_cache_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics about cache usage."""
        stats = {}
        
        cache_dirs = {
            "audio": self.audio_cache_dir,
            "stems": self.stems_cache_dir,
            "lyrics": self.lyrics_cache_dir,
            "subtitles": self.subtitles_cache_dir,
            "videos": self.videos_cache_dir
        }
        
        for cache_name, cache_dir in cache_dirs.items():
            if cache_dir.exists():
                cache_files = list(cache_dir.glob("*.json"))
                total_size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
                stats[cache_name] = {
                    "entries": len(cache_files),
                    "total_size_mb": round(total_size / (1024 * 1024), 2)
                }
            else:
                stats[cache_name] = {"entries": 0, "total_size_mb": 0}
        
        return stats


# Global cache manager instance
cache_manager = CacheManager() 