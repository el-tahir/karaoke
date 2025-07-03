"""Karaoke-O-Matic CLI

End-to-end pipeline for generating karaoke videos.
"""
import argparse
import sys

from .pipeline import KaraokePipeline
from . import config
from .cache_cli import print_cache_stats, clear_cache, list_cache_contents, test_cache, test_separation

def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Run the full karaoke pipeline or manage cache.")
    subparsers = p.add_subparsers(dest="command", help="Available commands")
    
    # Pipeline command (default)
    pipeline_parser = subparsers.add_parser("run", help="Run the karaoke pipeline")
    
    g = pipeline_parser.add_mutually_exclusive_group()
    g.add_argument("--file", help="Path to a local audio file")
    g.add_argument("--youtube-url", help="YouTube URL to download audio from")

    pipeline_parser.add_argument("--track", help="Track title")
    pipeline_parser.add_argument("--artist", help="Artist name")
    pipeline_parser.add_argument("--resolution", default=config.DEFAULT_RESOLUTION, help="Video resolution (e.g., 1280x720)")
    pipeline_parser.add_argument("--background", default=config.DEFAULT_BACKGROUND, help="Background color")
    pipeline_parser.add_argument("--no-cache", action="store_true", help="Disable caching for this run")
    
    # Cache management commands
    cache_parser = subparsers.add_parser("cache", help="Manage cache")
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command", help="Cache commands")
    
    cache_subparsers.add_parser("stats", help="Show cache statistics")
    
    clear_parser = cache_subparsers.add_parser("clear", help="Clear cache")
    clear_parser.add_argument("--type", choices=["audio", "stems", "lyrics", "subtitles", "videos"],
                             help="Specific cache type to clear (clears all if not specified)")
    
    list_parser = cache_subparsers.add_parser("list", help="List cache contents")
    list_parser.add_argument("type", choices=["audio", "stems", "lyrics", "subtitles", "videos"],
                            help="Cache type to list")
    
    cache_subparsers.add_parser("test", help="Test cache functionality")
    
    debug_parser = cache_subparsers.add_parser("debug-separation", help="Test audio separation with debugging")
    debug_parser.add_argument("audio_file", help="Path to audio file to test")

    args = p.parse_args(argv)

    # Handle cache commands
    if args.command == "cache":
        if args.cache_command == "stats":
            print_cache_stats()
        elif args.cache_command == "clear":
            clear_cache(args.type)
        elif args.cache_command == "list":
            list_cache_contents(args.type)
        elif args.cache_command == "test":
            test_cache()
        elif args.cache_command == "debug-separation":
            test_separation(args.audio_file)
        else:
            cache_parser.print_help()
        return
    
    # Handle pipeline command (default if no command specified)
    if args.command is None or args.command == "run":
        # Use pipeline_parser args if we're in a subcommand, otherwise use main args
        if args.command == "run":
            pipeline_args = args
        else:
            # For backward compatibility, treat no subcommand as run command
            # Re-parse with pipeline parser to get all the pipeline-specific args
            pipeline_args = pipeline_parser.parse_args(argv or sys.argv[1:])
        
        try:
            # Temporarily disable caching if requested
            if getattr(pipeline_args, 'no_cache', False):
                original_cache_setting = config.ENABLE_CACHE
                config.ENABLE_CACHE = False
                print("🚫 Caching disabled for this run")
            
            pipeline = KaraokePipeline(
                track=getattr(pipeline_args, 'track', None),
                artist=getattr(pipeline_args, 'artist', None),
                file_path=getattr(pipeline_args, 'file', None),
                youtube_url=getattr(pipeline_args, 'youtube_url', None),
                resolution=getattr(pipeline_args, 'resolution', config.DEFAULT_RESOLUTION),
                background=getattr(pipeline_args, 'background', config.DEFAULT_BACKGROUND),
            )
            karaoke_video, full_video = pipeline.run()
            print(f"✅ Karaoke video created: {karaoke_video}")
            print(f"✅ Full-song video created: {full_video}")
            
            # Restore original cache setting
            if getattr(pipeline_args, 'no_cache', False):
                config.ENABLE_CACHE = original_cache_setting
                
        except Exception as e:
            print(f"❌ Pipeline failed: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        p.print_help()

if __name__ == "__main__":
    main()
 