import os
import logging
from audio_separator.separator import Separator
def separate_audio(input_file: str, output_dir: str = '.', model_name: str = 'UVR_MDXNET_KARA_2.onnx') -> tuple[str, str]:
    """
    Separates the given audio file into vocals and instrumental tracks using the specified model.
    
    Args:
        input_file (str): Path to the input audio file.
        output_dir (str, optional): Directory to save the output files. Defaults to current directory.
        model_name (str, optional): Name of the model to use for separation. Defaults to 'UVR_MDXNET_KARA_2.onnx' for karaoke purposes.
    
    Returns:
        tuple[str, str]: Paths to the instrumental and vocals output files.
    
    Raises:
        Exception: If the separation fails.
    """
    # Initialize Separator with output directory and autocast for GPU acceleration
    separator = Separator(output_dir=output_dir, use_autocast=True, log_level=logging.WARNING)
    
    # Load the model
    separator.load_model(model_filename=model_name)
    
    # Perform separation
    output_files = separator.separate(input_file)
    
    # Find instrumental and vocals files
    instrumental = None
    vocals = None
    for file in output_files:
        base = os.path.basename(file)
        if 'Instrumental' in base:
            instrumental = file if os.path.isabs(file) else os.path.join(output_dir, file)
        elif 'Vocals' in base:
            vocals = file if os.path.isabs(file) else os.path.join(output_dir, file)
    
    if not instrumental or not vocals:
        raise ValueError("Could not find instrumental or vocals in output files.")
    
    return instrumental, vocals 