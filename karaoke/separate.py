# /karaoke/separate.py

"""Vocal separation utility.

Uses the `audio-separator` library to split an audio file into instrumental and vocal stems.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple
import shutil
import logging
import os
import torch

from audio_separator.separator import Separator

from . import config
from .cache import cache_manager

logger = logging.getLogger(__name__)

def separate(audio_path: Path, output_dir: Path = config.STEMS_DIR) -> Tuple[Path, Path]:
    """Run audio separation and return (instrumental_path, vocals_path)."""
    try:
        cached_stems = cache_manager.get_cached_stems(audio_path)
        if cached_stems:
            return cached_stems
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Cache check failed, proceeding with separation: {e}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    original_cwd = Path.cwd()
    
    try:
        os.chdir(str(output_dir))
        
        gpu_enabled = torch.cuda.is_available()
        if gpu_enabled:
            logger.info("✅ GPU detected! Using PyTorch autocast for faster inference.")
        else:
            logger.warning("⚠️ No GPU detected. Running separation on CPU (this will be much slower).")
        
        separator = Separator(
            output_dir=str(output_dir),
            log_level=logging.INFO,
            use_autocast=gpu_enabled
        )
        
        separator.load_model(model_filename='UVR-MDX-NET-Inst_HQ_3.onnx')

        logger.info(f"Running separation with output_dir: {output_dir}")
        logger.info(f"Audio file: {audio_path}")

        result_paths = separator.separate(str(audio_path))
        if not isinstance(result_paths, (list, tuple)) or len(result_paths) != 2:
            raise RuntimeError(f"Unexpected result from audio-separator: {result_paths}")

        # --- THIS IS THE FIX ---
        # The library returns paths in [primary_stem, secondary_stem] order.
        # For an instrumental model, primary is instrumental, secondary is vocals.
        # However, logs showed the opposite. We explicitly find the files to be safe.
        instrumental_path = None
        vocals_path = None
        for path_str in result_paths:
            if "(Instrumental)" in path_str:
                instrumental_path = Path(path_str).resolve()
            elif "(Vocals)" in path_str:
                vocals_path = Path(path_str).resolve()

        if not instrumental_path or not vocals_path:
            raise RuntimeError(f"Could not identify instrumental and vocal paths from separator result: {result_paths}")

        # Final validation
        if not instrumental_path.exists() or not vocals_path.exists():
             raise RuntimeError("Instrumental or Vocals file not found after separation.")

        print("Instrumental saved to:", instrumental_path)
        print("Vocals saved to:", vocals_path)

        try:
            cache_manager.cache_stems(audio_path, instrumental_path, vocals_path)
        except (FileNotFoundError, RuntimeError) as e:
            logger.warning(f"Failed to cache stems, but separation was successful: {e}")

        return instrumental_path, vocals_path
        
    finally:
        os.chdir(str(original_cwd))