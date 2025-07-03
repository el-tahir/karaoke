"""Command-line interface for cache management."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import hashlib
import logging

from .cache import cache_manager
from . import separate, config

def print_cache_stats():
    """Print detailed cache statistics."""
    stats = cache_manager.get_cache_stats()
    
    print("📊 Cache Statistics:")
    print("=" * 50)
    
    total_entries = 0
    total_size_mb = 0.0
    
    for cache_type, data in stats.items():
        entries = data["entries"]
        size_mb = data["total_size_mb"]
        total_entries += entries
        total_size_mb += size_mb
        
        print(f"🗂️  {cache_type.title()} Cache:")
        print(f"   Entries: {entries}")
        print(f"   Size: {size_mb:.2f} MB")
        print()
    
    print("📈 Total:")
    print(f"   Entries: {total_entries}")
    print(f"   Size: {total_size_mb:.2f} MB ({total_size_mb/1024:.2f} GB)")

def clear_cache(cache_type: str = None):
    """Clear cache with confirmation."""
    if cache_type:
        print(f"⚠️  Are you sure you want to clear the {cache_type} cache? (y/N): ", end="")
    else:
        print("⚠️  Are you sure you want to clear ALL caches? (y/N): ", end="")
    
    response = input().strip().lower()
    if response in ('y', 'yes'):
        cache_manager.clear_cache(cache_type)
        if cache_type:
            print(f"✅ Cleared {cache_type} cache")
        else:
            print("✅ Cleared all caches")
    else:
        print("❌ Cache clear cancelled")

def list_cache_contents(cache_type: str):
    """List contents of a specific cache."""
    cache_dirs = {
        "audio": cache_manager.audio_cache_dir,
        "stems": cache_manager.stems_cache_dir,
        "lyrics": cache_manager.lyrics_cache_dir,
        "subtitles": cache_manager.subtitles_cache_dir,
        "videos": cache_manager.videos_cache_dir
    }
    
    if cache_type not in cache_dirs:
        print(f"❌ Unknown cache type: {cache_type}")
        print(f"Available types: {', '.join(cache_dirs.keys())}")
        return
    
    cache_dir = cache_dirs[cache_type]
    cache_files = list(cache_dir.glob("*.json"))
    
    if not cache_files:
        print(f"📭 No entries in {cache_type} cache")
        return
    
    print(f"📋 {cache_type.title()} Cache Contents:")
    print("=" * 50)
    
    for cache_file in sorted(cache_files):
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            if cache_type == "audio":
                print(f"🎵 {data.get('url_or_query', 'Unknown query')}")
                print(f"   File: {Path(data.get('audio_path', '')).name}")
            elif cache_type == "stems":
                print(f"🎼 {Path(data.get('audio_path', '')).name}")
                print(f"   Instrumental: {Path(data.get('instrumental_path', '')).name}")
                print(f"   Vocals: {Path(data.get('vocals_path', '')).name}")
            elif cache_type == "lyrics":
                print(f"🎤 {data.get('track', 'Unknown')} - {data.get('artist', 'Unknown')}")
                print(f"   File: {Path(data.get('lyrics_path', '')).name}")
            elif cache_type == "subtitles":
                print(f"📝 {Path(data.get('lrc_path', '')).name}")
                print(f"   File: {Path(data.get('subtitles_path', '')).name}")
            elif cache_type == "videos":
                print(f"🎬 {data.get('resolution', 'Unknown')} - {data.get('background', 'Unknown')}")
                print(f"   Audio: {Path(data.get('audio_path', '')).name}")
                print(f"   Video: {Path(data.get('video_path', '')).name}")
            
            print()
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️  Invalid cache file: {cache_file.name} ({e})")

def test_cache():
    """Test cache functionality with dummy data."""
    print("🧪 Testing cache functionality...")
    
    # Test file hashing
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content for cache")
            temp_path = Path(f.name)
        
        # Test hashing
        hash1 = cache_manager._get_file_hash(temp_path)
        hash2 = cache_manager._get_file_hash(temp_path)
        
        if hash1 == hash2:
            print("✅ File hashing: PASS")
        else:
            print("❌ File hashing: FAIL - Hashes don't match")
        
        # Test content hashing
        content_hash1 = cache_manager._get_content_hash("test string")
        content_hash2 = cache_manager._get_content_hash("test string")
        
        if content_hash1 == content_hash2:
            print("✅ Content hashing: PASS")
        else:
            print("❌ Content hashing: FAIL - Hashes don't match")
        
        # Test cache directories
        all_dirs_exist = all(d.exists() for d in [
            cache_manager.audio_cache_dir,
            cache_manager.stems_cache_dir,
            cache_manager.lyrics_cache_dir,
            cache_manager.subtitles_cache_dir,
            cache_manager.videos_cache_dir
        ])
        
        if all_dirs_exist:
            print("✅ Cache directories: PASS")
        else:
            print("❌ Cache directories: FAIL - Some directories missing")
        
        temp_path.unlink()  # Clean up
        print("🎉 Cache system test completed!")
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")

def test_separation(audio_file: str):
    """Test audio separation with debugging information."""
    audio_path = Path(audio_file)
    if not audio_path.exists():
        print(f"❌ Audio file not found: {audio_path}")
        return
    
    print(f"🧪 Testing separation for: {audio_path}")
    print(f"📁 Output directory: {config.STEMS_DIR}")
    
    try:
        instrumental, vocals = separate.separate(audio_path)
        print(f"✅ Separation successful!")
        print(f"🎼 Instrumental: {instrumental}")
        print(f"🎤 Vocals: {vocals}")
        
        # Test cache functionality
        print("\n🧪 Testing cache retrieval...")
        cached_result = cache_manager.get_cached_stems(audio_path)
        if cached_result:
            print("✅ Cache retrieval successful!")
            print(f"🎼 Cached Instrumental: {cached_result[0]}")
            print(f"🎤 Cached Vocals: {cached_result[1]}")
        else:
            print("❌ Cache retrieval failed")
            
    except Exception as e:
        print(f"❌ Separation failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Karaoke Pipeline Cache Management",
        epilog="""
Examples:
  python -m karaoke cache stats                    # Show cache statistics
  python -m karaoke cache clear --type audio       # Clear audio cache
  python -m karaoke cache list lyrics              # List lyrics cache contents
  python -m karaoke cache test                     # Test cache functionality
  python -m karaoke cache debug-separation file.mp3 # Test separation with debug info
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Stats command
    subparsers.add_parser("stats", help="Show cache statistics")
    
    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear cache")
    clear_parser.add_argument("--type", choices=["audio", "stems", "lyrics", "subtitles", "videos"],
                             help="Specific cache type to clear (clears all if not specified)")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List cache contents")
    list_parser.add_argument("type", choices=["audio", "stems", "lyrics", "subtitles", "videos"],
                            help="Cache type to list")
    
    # Test command
    subparsers.add_parser("test", help="Test cache functionality")
    
    # Debug separation command
    debug_parser = subparsers.add_parser("debug-separation", help="Test audio separation with debugging")
    debug_parser.add_argument("audio_file", help="Path to audio file to test")
    
    args = parser.parse_args()
    
    if args.command == "stats":
        print_cache_stats()
    elif args.command == "clear":
        clear_cache(args.type)
    elif args.command == "list":
        list_cache_contents(args.type)
    elif args.command == "test":
        test_cache()
    elif args.command == "debug-separation":
        test_separation(args.audio_file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 