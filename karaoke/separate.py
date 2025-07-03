"""Vocal separation utility.

Uses the `audio-separator` library to split an audio file into instrumental and vocal stems.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple
import shutil
import logging
import os

from audio_separator.separator import Separator

from . import config
from .cache import cache_manager

logger = logging.getLogger(__name__)

def separate(audio_path: Path, output_dir: Path = config.STEMS_DIR) -> Tuple[Path, Path]:
    """Run audio separation and return (instrumental_path, vocals_path)."""
    # Check cache first (with error handling)
    try:
        cached_stems = cache_manager.get_cached_stems(audio_path)
        if cached_stems:
            return cached_stems
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Cache check failed, proceeding with separation: {e}")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Store current working directory to restore later
    original_cwd = Path.cwd()
    
    try:
        # Change to output directory to ensure files are saved there
        os.chdir(str(output_dir))
        
        separator = Separator(output_dir=str(output_dir))
        separator.load_model()

        # Log before separation to help debug file locations
        logger.info(f"Running separation with output_dir: {output_dir}")
        logger.info(f"Current working directory: {Path.cwd()}")
        logger.info(f"Audio file: {audio_path}")

        result_paths = separator.separate(str(audio_path))
        if not isinstance(result_paths, (list, tuple)) or len(result_paths) != 2:
            raise RuntimeError(f"Unexpected result from audio-separator: {result_paths}")

        instrumental_path, vocals_path = result_paths
        
        # Log what the separator returned
        logger.info(f"Separator returned paths: {result_paths}")
        
        # Convert to Path objects
        instrumental_path = Path(instrumental_path)
        vocals_path = Path(vocals_path)
        
        # Find the actual files - they might be in various locations
        possible_locations = [
            output_dir,  # Where we want them
            original_cwd,  # Project root
            Path.cwd(),   # Current directory (output_dir)
            Path(audio_path).parent,  # Same directory as source audio
        ]
        
        # Debug: List all .wav files in each location
        for i, location in enumerate(possible_locations):
            if location.exists():
                wav_files = list(location.glob("*.wav"))
                logger.info(f"Location {i} ({location}): {[f.name for f in wav_files]}")
            else:
                logger.info(f"Location {i} ({location}): does not exist")
        
        actual_instrumental = None
        actual_vocals = None
        
        # Search for instrumental file
        for location in possible_locations:
            candidate = location / instrumental_path.name
            if candidate.exists():
                actual_instrumental = candidate.resolve()
                break
        
        # Search for vocals file  
        for location in possible_locations:
            candidate = location / vocals_path.name
            if candidate.exists():
                actual_vocals = candidate.resolve()
                break
        
        # Validate we found the files
        if not actual_instrumental:
            # Try some common variations
            base_name = audio_path.stem
            common_patterns = [
                f"{base_name}*(Instrumental)*.wav",
                f"*{base_name}*(Instrumental)*.wav",
                f"*Instrumental*.wav"
            ]
            
            for location in possible_locations:
                for pattern in common_patterns:
                    candidates = list(location.glob(pattern))
                    if candidates:
                        actual_instrumental = candidates[0].resolve()
                        break
                if actual_instrumental:
                    break
            
            if not actual_instrumental:
                raise RuntimeError(f"Instrumental file not found in any expected location. Searched: {[str(loc) for loc in possible_locations]}")
        
        if not actual_vocals:
            # Try some common variations
            base_name = audio_path.stem
            common_patterns = [
                f"{base_name}*(Vocals)*.wav",
                f"*{base_name}*(Vocals)*.wav", 
                f"*Vocals*.wav"
            ]
            
            for location in possible_locations:
                for pattern in common_patterns:
                    candidates = list(location.glob(pattern))
                    if candidates:
                        actual_vocals = candidates[0].resolve()
                        break
                if actual_vocals:
                    break
            
            if not actual_vocals:
                raise RuntimeError(f"Vocals file not found in any expected location. Searched: {[str(loc) for loc in possible_locations]}")

        # Move files to correct output directory if they're not already there
        target_instrumental = output_dir / actual_instrumental.name
        target_vocals = output_dir / actual_vocals.name
        
        if actual_instrumental != target_instrumental:
            if target_instrumental.exists():
                target_instrumental.unlink()  # Remove existing file
            shutil.move(str(actual_instrumental), str(target_instrumental))
            actual_instrumental = target_instrumental
            
        if actual_vocals != target_vocals:
            if target_vocals.exists():
                target_vocals.unlink()  # Remove existing file
            shutil.move(str(actual_vocals), str(target_vocals))
            actual_vocals = target_vocals

        print("Instrumental saved to:", actual_instrumental)
        print("Vocals saved to:", actual_vocals)

        # Final validation
        if not actual_instrumental.exists() or not actual_vocals.exists():
            raise RuntimeError("Failed to properly save separated audio files")

        # Cache the separated stems (with error handling)
        try:
            cache_manager.cache_stems(audio_path, actual_instrumental, actual_vocals)
        except (FileNotFoundError, RuntimeError) as e:
            logger.warning(f"Failed to cache stems, but separation was successful: {e}")

        return actual_instrumental, actual_vocals
        
    finally:
        # Always restore the original working directory
        os.chdir(str(original_cwd))
 