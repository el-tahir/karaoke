"""
Japanese text romanization utilities.

This module provides functionality to detect and romanize Japanese text
in lyrics files, with support for various romanization styles.
"""

import re
from typing import Optional, Tuple

from .logging import LoggerMixin
from .config import Config


class JapaneseRomanizerError(Exception):
    """Exception raised when Japanese romanization fails."""
    pass


class JapaneseRomanizer(LoggerMixin):
    """
    Handles detection and romanization of Japanese text.
    
    This class provides functionality to detect Japanese characters in text
    and convert them to romaji using various romanization systems.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Japanese romanizer.
        
        Args:
            config: Configuration object with romanization settings
        """
        self.config = config or Config()
        self.cutlet = None
        
        # Japanese character ranges
        self.japanese_char_pattern = re.compile(r'[\u3040-\u30ff\u4e00-\u9FFF]')
        
        # Word-level timestamp pattern for LRC files
        self.word_timestamp_pattern = re.compile(r'(<\d+:\d+\.\d+>)')
        
        self._initialize_cutlet()
    
    def _initialize_cutlet(self) -> None:
        """Initialize the cutlet library for romanization."""
        try:
            import cutlet
            self.cutlet = cutlet.Cutlet()
            
            # Configure romanization style if specified
            style = self.config.lyrics.japanese_romanization_style
            if hasattr(self.cutlet, 'use_foreign_spelling'):
                self.cutlet.use_foreign_spelling = (style == 'foreign')
            
            self.logger.debug(f"Initialized cutlet with style: {style}")
            
        except ImportError:
            self.logger.warning(
                "cutlet library not available - Japanese romanization will be skipped. "
                "Install with: pip install cutlet"
            )
            self.cutlet = None
    
    def is_available(self) -> bool:
        """
        Check if Japanese romanization is available.
        
        Returns:
            True if cutlet library is available
        """
        return self.cutlet is not None
    
    def contains_japanese(self, text: str) -> bool:
        """
        Check if text contains Japanese characters.
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains Japanese characters
        """
        return bool(self.japanese_char_pattern.search(text))
    
    def romanize_text(self, text: str) -> str:
        """
        Romanize Japanese text while preserving non-Japanese content.
        
        Args:
            text: Text to romanize
            
        Returns:
            Romanized text
            
        Raises:
            JapaneseRomanizerError: If romanization fails
        """
        if not self.cutlet:
            raise JapaneseRomanizerError("cutlet library not available")
        
        if not self.contains_japanese(text):
            return text
        
        try:
            return self.cutlet.romaji(text)
        except Exception as e:
            raise JapaneseRomanizerError(f"Romanization failed: {e}") from e
    
    def romanize_lrc_file(self, lrc_path: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Romanize Japanese text in an LRC file while preserving timestamps.
        
        This method processes an LRC file, detects Japanese text, and converts
        it to romaji while preserving all timing information and metadata.
        
        Args:
            lrc_path: Path to input LRC file
            output_path: Path for output file (defaults to overwriting input)
            
        Returns:
            Tuple of (was_modified, output_path)
            
        Raises:
            JapaneseRomanizerError: If processing fails
        """
        if not self.cutlet:
            self.logger.warning("cutlet not available - skipping romanization")
            return False, lrc_path
        
        self.logger.info(f"Processing LRC file for Japanese romanization: {lrc_path}")
        
        try:
            # Read the file
            with open(lrc_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Check if any line contains Japanese
            if not any(self.contains_japanese(line) for line in lines):
                self.logger.debug("No Japanese text detected in LRC file")
                return False, lrc_path
            
            # Process each line
            modified_lines = []
            was_modified = False
            
            for line in lines:
                processed_line = self._process_lrc_line(line.rstrip('\n'))
                modified_lines.append(processed_line + '\n')
                
                if processed_line != line.rstrip('\n'):
                    was_modified = True
            
            # Write output file if modified
            if was_modified:
                output_file = output_path or lrc_path
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.writelines(modified_lines)
                
                self.logger.info(f"Romanized Japanese lyrics in: {output_file}")
                return True, output_file
            else:
                return False, lrc_path
                
        except Exception as e:
            raise JapaneseRomanizerError(f"Failed to process LRC file: {e}") from e
    
    def _process_lrc_line(self, line: str) -> str:
        """
        Process a single LRC line for romanization.
        
        This method handles the complex task of romanizing Japanese text while
        preserving LRC timing tags and metadata.
        
        Args:
            line: LRC line to process
            
        Returns:
            Processed line with romanized Japanese text
        """
        # Skip metadata lines like [ti:], [ar:], etc.
        if re.match(r'^\[[a-zA-Z]{2,}:.*\]$', line):
            return line
        
        # Split off line-level timestamp
        if ']' in line:
            timestamp_part, text_part = line.split(']', 1)
            timestamp_part += ']'
        else:
            timestamp_part, text_part = '', line
        
        # Process the text part, handling word-level timestamps
        if '<' in text_part and '>' in text_part:
            # Has word-level timestamps
            processed_text = self._romanize_with_word_timestamps(text_part)
        else:
            # Plain text or line-level only
            processed_text = self.romanize_text(text_part) if self.contains_japanese(text_part) else text_part
        
        return timestamp_part + processed_text
    
    def _romanize_with_word_timestamps(self, text: str) -> str:
        """
        Romanize text that contains word-level timestamps.
        
        Args:
            text: Text with word-level timestamps
            
        Returns:
            Romanized text with preserved timestamps
        """
        # Split by word-level timestamp tags
        parts = self.word_timestamp_pattern.split(text)
        
        romanized_parts = []
        for part in parts:
            if self.word_timestamp_pattern.match(part):
                # This is a timestamp tag - keep as is
                romanized_parts.append(part)
            else:
                # This is text content - romanize if contains Japanese
                if self.contains_japanese(part):
                    romanized_parts.append(self.romanize_text(part))
                else:
                    romanized_parts.append(part)
        
        return ''.join(romanized_parts)
    
    def get_romanization_info(self, text: str) -> dict:
        """
        Get information about Japanese content in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with analysis information
        """
        has_japanese = self.contains_japanese(text)
        
        info = {
            'has_japanese': has_japanese,
            'romanization_available': self.is_available(),
            'original_length': len(text),
        }
        
        if has_japanese and self.is_available():
            try:
                romanized = self.romanize_text(text)
                info.update({
                    'romanized_text': romanized,
                    'romanized_length': len(romanized),
                    'length_change': len(romanized) - len(text),
                })
            except Exception as e:
                info['romanization_error'] = str(e)
        
        return info
    
    def detect_japanese_content_ratio(self, text: str) -> float:
        """
        Calculate the ratio of Japanese characters to total characters.
        
        Args:
            text: Text to analyze
            
        Returns:
            Ratio of Japanese characters (0.0 to 1.0)
        """
        if not text:
            return 0.0
        
        japanese_chars = len(self.japanese_char_pattern.findall(text))
        total_chars = len([c for c in text if c.strip()])  # Exclude whitespace
        
        return japanese_chars / total_chars if total_chars > 0 else 0.0


def romanize_lrc_file_inplace(lrc_path: str, config: Optional[Config] = None) -> bool:
    """
    Convenience function to romanize an LRC file in place.
    
    Args:
        lrc_path: Path to LRC file
        config: Optional configuration
        
    Returns:
        True if file was modified
    """
    romanizer = JapaneseRomanizer(config)
    
    if not romanizer.is_available():
        return False
    
    try:
        was_modified, _ = romanizer.romanize_lrc_file(lrc_path)
        return was_modified
    except JapaneseRomanizerError:
        return False


def is_japanese_romanization_available() -> bool:
    """
    Check if Japanese romanization is available.
    
    Returns:
        True if cutlet library is available
    """
    romanizer = JapaneseRomanizer()
    return romanizer.is_available()