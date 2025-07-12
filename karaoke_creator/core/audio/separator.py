"""
Audio separation functionality for vocals and instrumental tracks.

This module handles separating audio into vocal and instrumental components
using various AI models.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple

from audio_separator.separator import Separator

from ...models.song_info import ProcessingResult
from ...utils.logging import LoggerMixin, log_performance
from ...utils.config import Config
from ...utils.file_utils import ensure_directory_exists, get_file_info


class AudioSeparationError(Exception):
    """Exception raised when audio separation fails."""
    pass


class AudioSeparator(LoggerMixin):
    """
    Handles separation of audio into vocal and instrumental tracks.
    
    Uses the audio-separator library with various pre-trained models
    to separate vocals from instrumentals.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the audio separator.
        
        Args:
            config: Configuration object with separation settings
        """
        self.config = config or Config()
        self.separator = None
        
        # Available separation models
        self.available_models = {
            'UVR_MDXNET_KARA_2.onnx': 'High quality karaoke separation',
            'UVR-MDX-NET-Inst_HQ_3.onnx': 'High quality instrumental separation',
            'Kim_Vocal_2.onnx': 'Vocal-focused separation',
            'UVR_MDXNET_Main.onnx': 'General purpose separation',
        }
        
        self.current_model = None
    
    def _initialize_separator(self, output_dir: str) -> None:
        """
        Initialize the separator with current configuration.
        
        Args:
            output_dir: Directory for output files
        """
        # Create separator with optimal settings
        self.separator = Separator(
            output_dir=output_dir,
            use_autocast=self.config.audio.use_gpu,
            log_level=logging.WARNING,  # Reduce noise in logs
        )
        
        self.logger.debug(f"Initialized separator with model: {self.config.audio.separation_model}")
    
    @log_performance
    def separate_audio(
        self,
        input_file: str,
        output_dir: str,
        model_name: Optional[str] = None
    ) -> ProcessingResult:
        """
        Separate audio file into vocal and instrumental tracks.
        
        Args:
            input_file: Path to input audio file
            output_dir: Directory to save separated files
            model_name: Optional model name to use (overrides config)
            
        Returns:
            ProcessingResult with paths to separated files
            
        Raises:
            AudioSeparationError: If separation fails
        """
        self.logger.info(f"Starting audio separation for: {input_file}")
        
        # Validate input file
        if not os.path.exists(input_file):
            raise AudioSeparationError(f"Input file not found: {input_file}")
        
        # Ensure output directory exists
        ensure_directory_exists(output_dir)
        
        # Check if separated files already exist
        expected_files = self._get_expected_output_files(input_file, output_dir, model_name)
        if expected_files and self._all_files_exist(expected_files):
            self.logger.info("Separated audio files already exist, skipping separation")
            instrumental_file, vocals_file = expected_files
            
            # Get file information for metadata
            instrumental_info = get_file_info(instrumental_file)
            vocals_info = get_file_info(vocals_file)
            
            return ProcessingResult.success_result(
                output_file=instrumental_file,  # Primary output is instrumental
                instrumental_file=instrumental_file,
                vocals_file=vocals_file,
                model_used=model_name or self.config.audio.separation_model,
                instrumental_size_mb=instrumental_info.get('size_mb', 0),
                vocals_size_mb=vocals_info.get('size_mb', 0),
                cached=True,  # Indicate this was from cache
            )
        
        # Use specified model or default from config
        model_to_use = model_name or self.config.audio.separation_model
        
        try:
            # Initialize separator if needed or if model changed
            if (self.separator is None or 
                self.current_model != model_to_use):
                
                # Update config temporarily if using different model
                original_model = self.config.audio.separation_model
                if model_name:
                    self.config.audio.separation_model = model_name
                
                self._initialize_separator(output_dir)
                self.current_model = model_to_use
                
                # Load the model
                self.separator.load_model(model_filename=model_to_use)
                
                # Restore original config
                if model_name:
                    self.config.audio.separation_model = original_model
            
            # Perform separation
            self.logger.info(f"Separating audio using model: {model_to_use}")
            output_files = self.separator.separate(input_file)

            self.logger.debug(f"Separator returned {len(output_files)} files: {output_files}")

            # Find instrumental and vocals files. Ensure paths are resolved relative
            # to the configured output directory so subsequent existence checks work
            instrumental_file, vocals_file = self._find_separated_files(
                output_files, input_file, output_dir
            )
            
            # Validate output files
            self.logger.debug(f"Validating instrumental file: {instrumental_file}")
            self.logger.debug(f"File exists check: {os.path.exists(instrumental_file) if instrumental_file else 'N/A'}")
            
            if not instrumental_file:
                raise AudioSeparationError("Instrumental file path not determined after separation")
            if not os.path.exists(instrumental_file):
                raise AudioSeparationError(f"Instrumental file not found at: {instrumental_file}")
            
            self.logger.debug(f"Validating vocals file: {vocals_file}")
            self.logger.debug(f"File exists check: {os.path.exists(vocals_file) if vocals_file else 'N/A'}")
            
            if not vocals_file:
                raise AudioSeparationError("Vocals file path not determined after separation")
            if not os.path.exists(vocals_file):
                raise AudioSeparationError(f"Vocals file not found at: {vocals_file}")
            
            self.logger.info(f"Audio separation completed successfully")
            self.logger.debug(f"Instrumental: {instrumental_file}")
            self.logger.debug(f"Vocals: {vocals_file}")
            
            # Get file information for metadata
            instrumental_info = get_file_info(instrumental_file)
            vocals_info = get_file_info(vocals_file)
            
            return ProcessingResult.success_result(
                output_file=instrumental_file,  # Primary output is instrumental
                instrumental_file=instrumental_file,
                vocals_file=vocals_file,
                model_used=model_to_use,
                instrumental_size_mb=instrumental_info.get('size_mb', 0),
                vocals_size_mb=vocals_info.get('size_mb', 0),
            )
            
        except Exception as e:
            error_msg = f"Audio separation failed: {e}"
            self.logger.error(error_msg)
            raise AudioSeparationError(error_msg) from e
    
    def _find_separated_files(
        self,
        output_files: list,
        input_file: str,
        output_dir: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the instrumental and vocals files from separation output.
        
        Args:
            output_files: List of output files from separator
            input_file: Original input file path
            
        Returns:
            Tuple of (instrumental_file, vocals_file)
        """
        instrumental_file = None
        vocals_file = None
        
        self.logger.debug(f"Looking for separated files in: {output_files}")
        
        for file_path_original in output_files:
            # If the path is absolute or already starts with the output_dir, keep as is
            if os.path.isabs(file_path_original):
                file_path = file_path_original
            else:
                normalized_original = os.path.normpath(file_path_original)
                normalized_output = os.path.normpath(output_dir)

                if normalized_original.startswith(normalized_output):
                    file_path = file_path_original  # already contains output_dir
                else:
                    file_path = os.path.join(output_dir, file_path_original)

            file_path_lower = file_path.lower()
            self.logger.debug(f"Checking file: {file_path}")
            
            # Check for instrumental file patterns
            if any(pattern in file_path_lower for pattern in [
                'instrumental', 'inst', 'karaoke', 'backing'
            ]):
                instrumental_file = file_path
                self.logger.debug(f"Found instrumental file: {file_path}")
            
            # Check for vocals file patterns
            elif any(pattern in file_path_lower for pattern in [
                'vocals', 'voice', 'singing'
            ]):
                vocals_file = file_path
                self.logger.debug(f"Found vocals file: {file_path}")
        
        # If we couldn't identify by name patterns, use file order/size heuristics
        if not instrumental_file or not vocals_file:
            self.logger.warning("Could not identify files by name patterns, using fallback method")
            
            # Sort files by name to ensure consistent ordering
            # Ensure we resolve the sorted files as well
            sorted_files = []
            for f in sorted(output_files):
                if os.path.isabs(f):
                    sorted_files.append(f)
                else:
                    normalized_f = os.path.normpath(f)
                    if normalized_f.startswith(os.path.normpath(output_dir)):
                        sorted_files.append(f)
                    else:
                        sorted_files.append(os.path.join(output_dir, f))
            
            if len(sorted_files) >= 2:
                # Usually the first file is instrumental, second is vocals (alphabetically)
                if not instrumental_file:
                    instrumental_file = sorted_files[0]
                    self.logger.debug(f"Fallback: using {instrumental_file} as instrumental")
                if not vocals_file:
                    vocals_file = sorted_files[1]  
                    self.logger.debug(f"Fallback: using {vocals_file} as vocals")
        
        self.logger.info(f"File detection result - Instrumental: {instrumental_file}, Vocals: {vocals_file}")
        return instrumental_file, vocals_file
    
    def _get_expected_output_files(
        self,
        input_file: str,
        output_dir: str,
        model_name: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Generate expected output file paths based on naming conventions.
        
        Args:
            input_file: Original input file path
            output_dir: Output directory
            model_name: Model name being used
            
        Returns:
            Tuple of (instrumental_path, vocals_path) or None if cannot determine
        """
        input_path = Path(input_file)
        base_name = input_path.stem
        
        # Use the model name or default from config
        model = model_name or self.config.audio.separation_model
        
        # Generate expected filenames based on audio-separator naming convention
        # Format: {base_name}_(Instrumental)_{model}.wav
        instrumental_file = os.path.join(
            output_dir, 
            f"{base_name}_(Instrumental)_{model.replace('.onnx', '')}.wav"
        )
        vocals_file = os.path.join(
            output_dir,
            f"{base_name}_(Vocals)_{model.replace('.onnx', '')}.wav"
        )
        
        self.logger.debug(f"Expected instrumental file: {instrumental_file}")
        self.logger.debug(f"Expected vocals file: {vocals_file}")
        
        return instrumental_file, vocals_file
    
    def _all_files_exist(self, file_paths: Tuple[str, str]) -> bool:
        """
        Check if all files in the tuple exist.
        
        Args:
            file_paths: Tuple of file paths to check
            
        Returns:
            True if all files exist and are not empty
        """
        for file_path in file_paths:
            if not os.path.exists(file_path):
                self.logger.debug(f"File does not exist: {file_path}")
                return False
            
            # Check if file is not empty (size > 0)
            if os.path.getsize(file_path) == 0:
                self.logger.debug(f"File is empty: {file_path}")
                return False
        
        self.logger.debug("All expected files exist and are non-empty")
        return True
    
    def get_available_models(self) -> dict:
        """
        Get available separation models.
        
        Returns:
            Dictionary mapping model names to descriptions
        """
        return self.available_models.copy()
    
    def validate_model(self, model_name: str) -> None:
        """
        Validate that a model is available.
        
        Args:
            model_name: Name of the model to validate
            
        Raises:
            AudioSeparationError: If model is not available
        """
        if model_name not in self.available_models:
            available = ', '.join(self.available_models.keys())
            raise AudioSeparationError(
                f"Model '{model_name}' not available. "
                f"Available models: {available}"
            )
    
    def estimate_processing_time(self, input_file: str) -> float:
        """
        Estimate processing time for audio separation.
        
        Args:
            input_file: Path to input file
            
        Returns:
            Estimated processing time in seconds
        """
        file_info = get_file_info(input_file)
        file_size_mb = file_info.get('size_mb', 0)
        
        # Rough estimate: ~10-30 seconds per MB depending on model and hardware
        if self.config.audio.use_gpu:
            time_per_mb = 10  # Faster with GPU
        else:
            time_per_mb = 30  # Slower with CPU
        
        return file_size_mb * time_per_mb
    
    def cleanup_temp_files(self, output_dir: str) -> None:
        """
        Clean up temporary files created during separation.
        
        Args:
            output_dir: Directory to clean up
        """
        temp_patterns = ['*.tmp', '*.temp', '*.log']
        
        output_path = Path(output_dir)
        for pattern in temp_patterns:
            for temp_file in output_path.glob(pattern):
                try:
                    temp_file.unlink()
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up {temp_file}: {e}")


def separate_audio(
    input_file: str,
    output_dir: str,
    config: Optional[Config] = None,
    model_name: Optional[str] = None
) -> ProcessingResult:
    """
    Convenience function to separate audio.
    
    Args:
        input_file: Path to input audio file
        output_dir: Output directory
        config: Optional configuration
        model_name: Optional model name
        
    Returns:
        ProcessingResult with separation information
    """
    separator = AudioSeparator(config)
    return separator.separate_audio(input_file, output_dir, model_name)