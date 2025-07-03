"""Vocal separation utility.

Uses the `audio-separator` library to split an audio file into instrumental and vocal stems.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple
import shutil
import logging
import os
import torch  # Import torch to check for GPU availability

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
        
        # --- GPU Acceleration Check ---
        gpu_enabled = torch.cuda.is_available()
        if gpu_enabled:
            logger.info("✅ GPU detected! Using PyTorch autocast for faster inference.")
        else:
            logger.warning("⚠️ No GPU detected. Running separation on CPU (this will be much slower).")
        
        # Initialize the separator, enabling autocast if a GPU is present
        separator = Separator(
            output_dir=str(output_dir),
            log_level=logging.INFO,
            use_autocast=gpu_enabled  # This is the key for GPU speed
        )
        
        # Load the default high-quality model (or you can specify another)
        separator.load_model(model_filename='UVR-MDX-NET-Inst_HQ_3.onnx')

        # Log before separation to help debug file locations
        logger.info(f"Running separation with output_dir: {output_dir}")
        logger.info(f"Audio file: {audio_path}")

        result_paths = separator.separate(str(audio_path))
        if not isinstance(result_paths, (list, tuple)) or len(result_paths) != 2:
            raise RuntimeError(f"Unexpected result from audio-separator: {result_paths}")

        # The library returns filenames; we need to resolve them to the output_dir
        instrumental_filename, vocals_filename = result_paths
        actual_instrumental = Path(instrumental_filename).resolve()
        actual_vocals = Path(vocals_filename).resolve()
        
        logger.info(f"Separator returned paths: {result_paths}")

        # Final validation that files exist where we expect them
        if not actual_instrumental.exists():
             raise RuntimeError(f"Instrumental file not found after separation: {actual_instrumental}")
        if not actual_vocals.exists():
            raise RuntimeError(f"Vocals file not found after separation: {actual_vocals}")
            
        print("Instrumental saved to:", actual_instrumental)
        print("Vocals saved to:", actual_vocals)

        # Cache the separated stems (with error handling)
        try:
            cache_manager.cache_stems(audio_path, actual_instrumental, actual_vocals)
        except (FileNotFoundError, RuntimeError) as e:
            logger.warning(f"Failed to cache stems, but separation was successful: {e}")

        return actual_instrumental, actual_vocals
        
    finally:
        # Always restore the original working directory
        os.chdir(str(original_cwd))
 