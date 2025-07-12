"""
File handling utilities for karaoke creator.

Provides common file operations and utilities.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import tempfile
from contextlib import contextmanager

from .logging import get_logger

logger = get_logger(__name__)


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    Sanitize a filename by removing/replacing invalid characters.
    
    Args:
        filename: The filename to sanitize
        replacement: Character to use as replacement for invalid chars
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove/replace characters that are invalid in filenames
    # Keep alphanumeric, spaces, hyphens, underscores, and dots
    sanitized = re.sub(r'[^\w\s\-_.]', replacement, filename)
    
    # Replace multiple consecutive spaces/replacements with single replacement
    sanitized = re.sub(rf'[{replacement}\s]+', replacement, sanitized)
    
    # Remove leading/trailing spaces and replacement characters
    sanitized = sanitized.strip(f' {replacement}')
    
    # Ensure we don't have an empty filename
    if not sanitized:
        sanitized = "untitled"
    
    return sanitized


def generate_safe_filename(artist: str, track: str, suffix: str = "") -> str:
    """
    Generate a safe filename from artist and track names.
    
    Args:
        artist: Artist name
        track: Track name
        suffix: Optional suffix to add
        
    Returns:
        Safe filename string
    """
    safe_artist = sanitize_filename(artist)
    safe_track = sanitize_filename(track)
    
    base_name = f"{safe_artist}_{safe_track}"
    if suffix:
        base_name += f"_{suffix}"
    
    return base_name


def find_newest_file(directory: str, pattern: str = "*") -> Optional[str]:
    """
    Find the newest file in a directory matching the given pattern.
    
    Args:
        directory: Directory to search in
        pattern: Glob pattern to match files
        
    Returns:
        Path to the newest file, or None if no files found
    """
    directory_path = Path(directory)
    if not directory_path.exists():
        return None
    
    files = list(directory_path.glob(pattern))
    if not files:
        return None
    
    # Sort by modification time (newest first)
    newest_file = max(files, key=lambda f: f.stat().st_mtime)
    return str(newest_file)


def find_files_by_extension(directory: str, extension: str) -> List[str]:
    """
    Find all files with a specific extension in a directory.
    
    Args:
        directory: Directory to search in
        extension: File extension to search for (with or without dot)
        
    Returns:
        List of file paths
    """
    if not extension.startswith('.'):
        extension = '.' + extension
    
    directory_path = Path(directory)
    if not directory_path.exists():
        return []
    
    return [str(f) for f in directory_path.glob(f"*{extension}")]


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in MB
    """
    try:
        size_bytes = Path(file_path).stat().st_size
        return size_bytes / (1024 * 1024)
    except (OSError, FileNotFoundError):
        return 0.0


def ensure_directory_exists(directory: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path to create
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def cleanup_temp_files(temp_dir: str, keep_patterns: Optional[List[str]] = None) -> None:
    """
    Clean up temporary files, optionally keeping files matching certain patterns.
    
    Args:
        temp_dir: Temporary directory to clean
        keep_patterns: List of glob patterns for files to keep
    """
    temp_path = Path(temp_dir)
    if not temp_path.exists():
        return
    
    keep_patterns = keep_patterns or []
    files_to_keep = set()
    
    # Find files to keep
    for pattern in keep_patterns:
        files_to_keep.update(temp_path.glob(pattern))
    
    # Remove all other files
    for file_path in temp_path.iterdir():
        if file_path.is_file() and file_path not in files_to_keep:
            try:
                file_path.unlink()
                logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {e}")


@contextmanager
def temporary_directory(cleanup: bool = True):
    """
    Context manager for creating and optionally cleaning up a temporary directory.
    
    Args:
        cleanup: Whether to clean up the directory when exiting context
        
    Yields:
        Path to the temporary directory
    """
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    try:
        yield temp_path
    finally:
        if cleanup and temp_path.exists():
            try:
                shutil.rmtree(temp_path)
                logger.debug(f"Cleaned up temporary directory: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory {temp_path}: {e}")


def backup_file(file_path: str, backup_dir: Optional[str] = None) -> str:
    """
    Create a backup of a file.
    
    Args:
        file_path: Path to the file to backup
        backup_dir: Directory to store backup (defaults to same directory)
        
    Returns:
        Path to the backup file
    """
    source_path = Path(file_path)
    if not source_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if backup_dir:
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        backup_file_path = backup_path / f"{source_path.stem}_backup{source_path.suffix}"
    else:
        backup_file_path = source_path.with_stem(f"{source_path.stem}_backup")
    
    shutil.copy2(source_path, backup_file_path)
    logger.debug(f"Created backup: {backup_file_path}")
    
    return str(backup_file_path)


def get_available_filename(base_path: str) -> str:
    """
    Get an available filename by adding a number suffix if the file already exists.
    
    Args:
        base_path: Base file path
        
    Returns:
        Available file path
    """
    path = Path(base_path)
    if not path.exists():
        return base_path
    
    counter = 1
    while True:
        new_path = path.with_stem(f"{path.stem}_{counter}")
        if not new_path.exists():
            return str(new_path)
        counter += 1


def validate_file_exists(file_path: str, file_type: str = "file") -> None:
    """
    Validate that a file exists and raise a descriptive error if not.
    
    Args:
        file_path: Path to check
        file_type: Description of file type for error message
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"{file_type.capitalize()} not found: {file_path}")


def get_file_info(file_path: str) -> dict:
    """
    Get comprehensive information about a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information
    """
    path = Path(file_path)
    
    if not path.exists():
        return {"exists": False}
    
    stat = path.stat()
    
    return {
        "exists": True,
        "name": path.name,
        "stem": path.stem,
        "suffix": path.suffix,
        "size_bytes": stat.st_size,
        "size_mb": stat.st_size / (1024 * 1024),
        "modified_time": stat.st_mtime,
        "is_file": path.is_file(),
        "is_directory": path.is_dir(),
        "absolute_path": str(path.absolute()),
    }