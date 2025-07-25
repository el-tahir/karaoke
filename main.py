#!/usr/bin/env python3
"""
Main entry point for the refactored karaoke creator.

This script provides a command-line interface for creating karaoke videos
using the new modular architecture.
"""

import sys
import argparse
import re
from pathlib import Path

# Add the package to the path if running as script
sys.path.insert(0, str(Path(__file__).parent))

from karaoke_creator import KaraokeCreator, Config
from karaoke_creator.utils.logging import setup_logging
from karaoke_creator.core.search.youtube_search import YouTubeSearcher


def is_youtube_url(url: str) -> bool:
    """Check if the input is a YouTube URL."""
    youtube_pattern = re.compile(
        r'^https?://(?:[\w.-]+\.)?(?:youtube\.com|youtu\.be)/',
        re.IGNORECASE
    )
    return bool(youtube_pattern.match(url))


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Generate karaoke videos from YouTube songs or search terms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "hello adele"
  %(prog)s "https://www.youtube.com/watch?v=YQHsXMglC9A"
  %(prog)s "radiohead creep" --output-dir ./my_karaoke
  %(prog)s "song title artist" --word-level --verbose
  %(prog)s "https://www.youtube.com/watch?v=INSTRUMENTAL_URL" --instrumental-only
  %(prog)s --config my_config.json "search term"

For more information, see the documentation at:
https://github.com/your-repo/karaoke-creator
        """
    )
    
    # Positional arguments
    parser.add_argument(
        'input',
        help='Search term (e.g., "hello adele") or YouTube URL'
    )
    
    # Output options
    parser.add_argument(
        'output_dir',
        nargs='?',
        default='downloads',
        help='Directory to store output files (default: downloads)'
    )
    
    parser.add_argument(
        '--final-videos-dir',
        default='final_videos',
        help='Directory for final video outputs (default: final_videos)'
    )
    
    # Processing options
    parser.add_argument(
        '-w', '--word-level',
        action='store_true',
        help='Prefer word-level lyric syncing over line-level'
    )
    
    parser.add_argument(
        '--line-level-only',
        action='store_true',
        help='Force line-level lyrics even if word-level available'
    )
    
    parser.add_argument(
        '--no-separation',
        action='store_true',
        help='Skip vocal/instrumental separation'
    )
    
    parser.add_argument(
        '--karaoke-only',
        action='store_true',
        help='Create only karaoke version (not original with vocals)'
    )
    
    parser.add_argument(
        '--instrumental-only',
        action='store_true',
        help='Input URL is already instrumental - skip audio separation and create only karaoke version'
    )
    
    # Audio options
    parser.add_argument(
        '--audio-format',
        choices=['mp3', 'wav', 'flac', 'm4a'],
        default='mp3',
        help='Audio format for downloads (default: mp3)'
    )
    
    parser.add_argument(
        '--audio-quality',
        default='320k',
        help='Audio quality (default: 320k)'
    )
    
    parser.add_argument(
        '--separation-model',
        default='UVR_MDXNET_KARA_2.onnx',
        help='Model for vocal separation (default: UVR_MDXNET_KARA_2.onnx)'
    )
    
    # Video options
    parser.add_argument(
        '--resolution',
        default='1920x1080',
        help='Video resolution (default: 1920x1080)'
    )
    
    parser.add_argument(
        '--background-color',
        default='black',
        help='Video background color (default: black)'
    )
    
    # Configuration
    parser.add_argument(
        '--config',
        help='Path to configuration file (JSON format)'
    )

    # LRC content option
    parser.add_argument(
        '--lrc-content',
        help='Paste LRC lyrics content directly (overrides lyric fetching)'
    )
    # LRC file option
    parser.add_argument(
        '--lrc-file',
        help='Path to LRC file to use for lyrics (overrides --lrc-content and lyric fetching)'
    )
    
    parser.add_argument(
        '--save-config',
        help='Save current settings to configuration file'
    )
    
    # Logging and debugging
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--log-file',
        help='Log to file instead of console'
    )
    
    # Utility options
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually processing'
    )
    
    parser.add_argument(
        '--estimate-time',
        action='store_true',
        help='Estimate processing time and exit'
    )
    
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Clean up temporary files after processing'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Create configuration
    if args.config:
        try:
            config = Config.load_from_file(args.config)
            print(f"Loaded configuration from: {args.config}")
        except Exception as e:
            print(f"Error loading config file: {e}")
            return 1
    else:
        config = Config()
    
    # Override config with command line arguments
    config.output_dir = args.output_dir
    config.final_videos_dir = args.final_videos_dir

    # LRC content override (file takes precedence over content)
    lrc_content = None
    if args.lrc_file:
        try:
            with open(args.lrc_file, 'r', encoding='utf-8') as f:
                lrc_content = f.read()
            if not lrc_content.strip():
                print(f"Error: --lrc-file '{args.lrc_file}' is empty.")
                return 1
        except Exception as e:
            print(f"Error reading LRC file '{args.lrc_file}': {e}")
            return 1
    elif args.lrc_content is not None:
        if not args.lrc_content.strip():
            print("Error: --lrc-content provided but is empty.")
            return 1
        lrc_content = args.lrc_content
    config.lyrics.lrc_content = lrc_content
    
    # Audio settings
    config.audio.audio_format = args.audio_format
    config.audio.audio_quality = args.audio_quality
    config.audio.separation_model = args.separation_model
    
    # Video settings
    config.video.resolution = args.resolution
    config.video.background_color = args.background_color
    
    # Lyrics settings
    config.lyrics.prefer_word_level = args.word_level
    if args.line_level_only:
        config.lyrics.prefer_word_level = False
        config.lyrics.fallback_to_line_level = True
    
    # Processing settings
    config.create_both_versions = not args.karaoke_only and not args.instrumental_only
    config.cleanup_temp_files = args.cleanup
    
    # Instrumental-only mode validation and setup
    if args.instrumental_only:
        if not is_youtube_url(args.input):
            print("Error: --instrumental-only can only be used with YouTube URLs, not search terms")
            return 1
        # Force karaoke-only mode when using instrumental input
        config.create_both_versions = False
        # Skip separation since input is already instrumental
        config.skip_separation = True
    
    # Logging settings
    if args.debug:
        config.log_level = 'DEBUG'
    elif args.verbose:
        config.log_level = 'INFO'
    else:
        config.log_level = 'WARNING'
    
    # Save configuration if requested
    if args.save_config:
        try:
            config.save_to_file(args.save_config)
            print(f"Configuration saved to: {args.save_config}")
        except Exception as e:
            print(f"Error saving config: {e}")
            return 1
    
    # Setup logging
    setup_logging(
        level=config.log_level,
        format_string=config.log_format,
        log_file=args.log_file
    )
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        return 1
    
    # Handle dry run
    if args.dry_run:
        print("DRY RUN MODE - No actual processing will be performed")
        print(f"Input: {args.input}")
        print(f"Output directory: {config.output_dir}")
        print(f"Final videos directory: {config.final_videos_dir}")
        print(f"Audio format: {config.audio.audio_format}")
        print(f"Video resolution: {config.video.resolution}")
        print(f"Prefer word-level lyrics: {config.lyrics.prefer_word_level}")
        print(f"Create both versions: {config.create_both_versions}")
        print(f"Skip audio separation: {config.skip_separation}")
        if args.instrumental_only:
            print("Instrumental-only mode: Input URL will be treated as instrumental audio")
        return 0
    
    try:
        # Initialize karaoke creator
        creator = KaraokeCreator(config)
        
        # Handle time estimation
        if args.estimate_time:
            print("Analyzing input to estimate processing time...")
            
            # First get song info
            if is_youtube_url(args.input):
                song_info = creator.searcher.extract_song_info_from_url(args.input)
            else:
                song_info = creator.searcher.search_song(args.input)
            
            estimated_time = creator.estimate_processing_time(song_info)
            
            print(f"Song: {song_info.artist} - {song_info.track}")
            if song_info.duration:
                print(f"Duration: {song_info.duration / 60:.1f} minutes")
            print(f"Estimated processing time: {estimated_time / 60:.1f} minutes")
            return 0
        
        # Process the input
        print(f"Starting karaoke creation for: {args.input}")
        print("This may take several minutes depending on the song length...")
        
        if is_youtube_url(args.input):
            result = creator.create_karaoke_from_url(args.input, config.output_dir, lrc_content=config.lyrics.lrc_content)
        else:
            result = creator.create_karaoke_from_search(args.input, config.output_dir, lrc_content=config.lyrics.lrc_content)
        
        if result.success:
            print("\n✅ Karaoke creation completed successfully!")
            print(f"Main output: {result.output_file}")
            
            if 'karaoke_video' in result.metadata:
                print(f"Karaoke video: {result.metadata['karaoke_video']}")
            
            if 'original_video' in result.metadata:
                print(f"Original video: {result.metadata['original_video']}")
            
            if result.processing_time:
                print(f"Total processing time: {result.processing_time / 60:.1f} minutes")
            
            # Show processing status
            status = creator.get_processing_status()
            completed_steps = status.get('completed_steps', [])
            print(f"Completed steps: {', '.join(completed_steps)}")
            
        else:
            print(f"\n❌ Karaoke creation failed: {result.error_message}")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())