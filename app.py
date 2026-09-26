"""
SRT Subtitle Translator with Strict Line Splitting
A PyQt6 desktop application for translating Serbian SRT files to English
with enforced character-count-based line splitting rules.

Supports OpenRouter API provider.
"""

import sys
import json
import os
import re
import requests
import argparse
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


# Handle PyQt6 imports with error handling for frozen environment
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QTextEdit, QFileDialog, QStatusBar,
        QMessageBox, QDialog, QFormLayout, QLineEdit, QComboBox,
        QFrame, QSplitter, QTabWidget, QCheckBox, QScrollArea,
        QSizePolicy, QMenu, QGroupBox, QTableWidget, QTableWidgetItem,
        QStyledItemDelegate, QAbstractItemView, QHeaderView, QProgressBar
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRect, QTimer
    from PyQt6.QtGui import QFont, QFontMetrics, QTextCursor, QTextFormat, QTextCharFormat, QColor, QPainter, QPen, QIcon, QPixmap, QTextOption, QAction
    PYQT6_AVAILABLE = True
except ImportError as e:
    PYQT6_AVAILABLE = False
    IMPORT_ERROR = str(e)
    
    # Create dummy classes for type checking if imports fail
    # Create dummy classes that accept arguments like real PyQt6 classes
    class pyqtSignal:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
        def connect(self, slot):
            pass
        def emit(self, *args):
            pass
    
    class QApplication:
        def __init__(self, *args):
            pass
        def exec(self):
            return 0
        @staticmethod
        def instance():
            return None
    
    class QMainWindow: pass
    class QWidget: pass
    class QVBoxLayout: pass
    class QHBoxLayout: pass
    class QPushButton: pass
    class QTextEdit: pass
    class QLabel: pass
    class QFileDialog: pass
    class QMessageBox:
        @staticmethod
        def critical(parent, title, text):
            print(f"ERROR: {title} - {text}")
    
    class QDialog: pass
    class QLineEdit: pass
    class QSplitter: pass
    class QStatusBar: pass
    class QComboBox: pass
    class QGroupBox: pass
    class QTableWidget: pass
    class QTableWidgetItem: pass
    class QStyledItemDelegate: pass
    class QAbstractItemView: pass
    class QFormLayout: pass
    class QTabWidget: pass
    class QScrollBar: pass
    class QFrame: pass
    class QGridLayout: pass
    class Qt: pass
    class QThread:
        def __init__(self):
            pass
        def start(self):
            pass
        def connect(self, signal, slot):
            pass
    
    class QRect: pass
    class QTimer:
        def __init__(self):
            self.timeout = pyqtSignal()
        def setSingleShot(self, single):
            pass
        def start(self, ms=None):
            pass
        def stop(self):
            pass
    
    class QFont: pass
    class QFontMetrics: pass
    class QTextCursor: pass
    class QTextFormat: pass
    class QTextCharFormat: pass
    class QColor: pass
    class QPainter: pass
    class QPen: pass
    class QIcon: pass
    class QPixmap: pass
    class QTextOption: pass


# ============================================================================
# Custom Widgets
# ============================================================================

class APIKeyWidget(QWidget):
    """Custom widget for API key input with show/hide toggle."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the API key widget UI."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # API key input field - QTextEdit for multi-line with custom wrapping
        self.api_key_input = QTextEdit()
        self.api_key_input.setPlaceholderText("Enter API key...")
        self.api_key_input.setFixedHeight(80)  # Fixed height: does not resize when toggling visibility
        self.api_key_input.setAcceptRichText(False)  # Plain text only
        
        # Custom text option to prevent hyphenation
        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        text_option.setFlags(QTextOption.Flag.IncludeTrailingSpaces)
        self.api_key_input.document().setDefaultTextOption(text_option)
        
        # Store original text for hyphen replacement
        self._original_text = ""
        
        # Set initial visible state (default is visible)
        self._actual_key = ""  # Store actual key
        self.api_key_input.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                min-height: 80px;
                color: #000000;
            }
            QTextEdit:hover {
                border-color: #80bdff;
            }
            QTextEdit:focus {
                border-color: #007bff;
                outline: none;
            }
        """)
        
        # Show/Hide toggle button
        self.toggle_button = QPushButton("Show")
        self.toggle_button.setFixedSize(60, 30)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)  # Start in hidden state
        self.toggle_button.toggled.connect(self.toggle_visibility)
        self.toggle_button.setToolTip("Show/Hide API Key")
        
        # Add to layout
        layout.addWidget(self.api_key_input)
        layout.addWidget(self.toggle_button)
        
        self.setLayout(layout)
    
    def toggle_visibility(self, checked: bool):
        """Toggle API key visibility."""
        if checked:
            # Show the API key
            self.api_key_input.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    padding: 8px 12px;
                    font-size: 14px;
                    min-height: 80px;
                    color: #000000;
                }
                QTextEdit:hover {
                    border-color: #80bdff;
                }
                QTextEdit:focus {
                    border-color: #007bff;
                    outline: none;
                }
            """)
            self.toggle_button.setText("Hide")
            # Restore actual key if we have it stored
            if hasattr(self, '_actual_key') and self._actual_key:
                # Replace regular hyphens with non-breaking hyphens to prevent wrapping
                display_text = self._actual_key.replace('-', '\u2011')  # Use non-breaking hyphen
                self.api_key_input.setText(display_text)
        else:
            # Hide the API key by replacing with asterisks
            # Store the actual key first
            current_text = self.api_key_input.toPlainText()
            if current_text and not current_text.startswith('•'):
                self._actual_key = current_text  # Store real key before hiding
            
            if hasattr(self, '_actual_key') and self._actual_key:
                hidden_text = "•" * len(self._actual_key)
                self.api_key_input.setText(hidden_text)
            self.toggle_button.setText("Show")
            
            # Apply hidden styling
            self.api_key_input.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    padding: 8px 12px;
                    font-size: 14px;
                    min-height: 80px;
                    color: #6c757d;
                }
                QTextEdit:hover {
                    border-color: #80bdff;
                }
                QTextEdit:focus {
                    border-color: #007bff;
                    outline: none;
                }
            """)
    
    def show_key(self):
        """Helper method to restore actual key when showing."""
        # Store the actual key when hidden
        if not hasattr(self, '_actual_key'):
            self._actual_key = self.api_key_input.toPlainText()
        return self._actual_key
    
    def hide_key(self):
        """Helper method to hide the actual key."""
        if hasattr(self, '_actual_key'):
            return self._actual_key
        return self.api_key_input.toPlainText()
    
    def text(self) -> str:
        """Get the API key text."""
        if hasattr(self, '_actual_key'):
            return self._actual_key.strip()
        # Convert non-breaking hyphens back to regular hyphens
        current_text = self.api_key_input.toPlainText()
        return current_text.replace('\u2011', '-').strip()
    
    def setText(self, text: str):
        """Set the API key text."""
        self._actual_key = text
        self._original_text = text
        # Check if currently hidden or visible using checked state
        if not self.toggle_button.isChecked():
            # Currently hidden, keep it hidden
            hidden_text = "•" * len(text)
            self.api_key_input.setText(hidden_text)
        else:
            # Currently visible, show the actual text with non-breaking hyphens
            # Replace regular hyphens with non-breaking hyphens to prevent wrapping
            display_text = text.replace('-', '\u2011')  # Use non-breaking hyphen
            self.api_key_input.setText(display_text)
    
    def setPlaceholderText(self, text: str):
        """Set placeholder text."""
        self.api_key_input.setPlaceholderText(text)
    
    def setEchoMode(self, mode):
        """Set echo mode (for compatibility)."""
        # QTextEdit doesn't have echo mode, but we keep this for compatibility
        pass





# ============================================================================
# Data Models
# ============================================================================

@dataclass
class SrtBlock:
    """Represents a single SRT subtitle block."""
    index: int
    timestamp: str
    original_text_lines: List[str]
    translated_text: str = ""
    was_shortened: bool = False
    
    # New fields for characters-per-second calculations
    start_time_ms: int = 0
    end_time_ms: int = 0
    duration_ms: int = 0
    characters_per_second: float = 0.0
    timestamp_extended: bool = False
    extension_reason: str = ""
    was_retranslated: bool = False


# ============================================================================
# SRT Parser
# ============================================================================

class SrtParser:
    """Handles parsing and rebuilding of SRT files."""
    
    @staticmethod
    def parse_timestamp_to_ms(timestamp: str) -> tuple[int, int]:
        """
        Convert SRT timestamp to milliseconds.
        
        Args:
            timestamp: SRT timestamp format "00:01:44,120 --> 00:01:48,210"
            
        Returns:
            (start_time_ms, end_time_ms)
        """
        try:
            start_part, end_part = timestamp.split(' --> ')
            start_ms = SrtParser.time_to_ms(start_part.strip())
            end_ms = SrtParser.time_to_ms(end_part.strip())
            return start_ms, end_ms
        except Exception as e:
            raise ValueError(f"Invalid timestamp format: {timestamp}. Error: {e}")
    
    @staticmethod
    def time_to_ms(time_str: str) -> int:
        """
        Convert time string "00:01:44,120" to milliseconds.
        
        Args:
            time_str: Time string in SRT format
            
        Returns:
            Milliseconds as integer
        """
        # Split time and milliseconds
        if ',' in time_str:
            time_part, ms_part = time_str.split(',')
            ms = int(ms_part.ljust(3, '0')[:3])  # Ensure 3 digits
        else:
            time_part = time_str
            ms = 0
        
        # Split hours, minutes, seconds
        parts = time_part.split(':')
        if len(parts) != 3:
            raise ValueError(f"Invalid time format: {time_str}")
        
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        
        total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + ms
        return total_ms
    
    @staticmethod
    def ms_to_srt_time(ms: int) -> str:
        """
        Convert milliseconds to SRT time format.
        
        Args:
            ms: Milliseconds as integer
            
        Returns:
            SRT time string "00:01:44,120"
        """
        total_seconds = ms // 1000
        remaining_ms = ms % 1000
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{remaining_ms:03d}"
    
    @staticmethod
    def calculate_characters_per_second(block: SrtBlock) -> float:
        """
        Calculate characters per second for a subtitle block.
        
        Args:
            block: SrtBlock object with timing info
            
        Returns:
            Characters per second as float
        """
        if block.duration_ms <= 0:
            return 0.0
        
        # Count total characters in translated text (excluding newlines)
        text = block.translated_text.replace('\n', '').strip()
        char_count = len(text)
        
        # Calculate CPS
        cps = (char_count / block.duration_ms) * 1000
        return round(cps, 2)
    
    @staticmethod
    def parse(srt_content: str) -> List[SrtBlock]:
        """
        Parse SRT content into a list of SrtBlock objects.
        
        Args:
            srt_content: Raw SRT file content
            
        Returns:
            List of SrtBlock objects
            
        Raises:
            ValueError: If SRT format is invalid
        """
        blocks = []
        lines = srt_content.strip().split('\n')
        
        i = 0
        while i < len(lines):
            # Skip empty lines
            if not lines[i].strip():
                i += 1
                continue
            
            # Read block index
            try:
                index = int(lines[i].strip())
            except (ValueError, IndexError):
                raise ValueError(f"Invalid block number at line {i + 1}: '{lines[i]}'")
            
            i += 1
            if i >= len(lines):
                raise ValueError(f"Incomplete block {index}: missing timestamp")
            
            # Read timestamp
            timestamp = lines[i].strip()
            if '-->' not in timestamp:
                raise ValueError(f"Invalid timestamp at line {i + 1}: '{timestamp}'")
            
            i += 1
            
            # Read text lines until blank line or end
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].rstrip())
                i += 1
            
            if not text_lines:
                raise ValueError(f"Block {index} has no text content")
            
            # Parse timing information
            start_ms, end_ms = SrtParser.parse_timestamp_to_ms(timestamp)
            duration_ms = end_ms - start_ms
            
            blocks.append(SrtBlock(
                index=index,
                timestamp=timestamp,
                original_text_lines=text_lines,
                start_time_ms=start_ms,
                end_time_ms=end_ms,
                duration_ms=duration_ms
            ))
            
            i += 1
        
        return blocks
    
    @staticmethod
    def rebuild(blocks: List[SrtBlock]) -> str:
        """
        Rebuild SRT content from blocks with translated text.
        
        Args:
            blocks: List of SrtBlock objects with translated_text filled
            
        Returns:
            Complete SRT file content as string
        """
        output_lines = []
        
        for i, block in enumerate(blocks):
            output_lines.append(str(block.index))
            output_lines.append(block.timestamp)
            
            # Use translated_text if available, otherwise use original_text_lines
            if block.translated_text and block.translated_text.strip():
                text_to_use = block.translated_text
            else:
                text_to_use = '\n'.join(block.original_text_lines)
            
            # Split text by newlines and add each line separately
            text_lines = text_to_use.split('\n')
            for line in text_lines:
                output_lines.append(line)
            
            output_lines.append('')  # Blank line separator
        
        return '\n'.join(output_lines)
    
    @staticmethod
    def calculate_cps_for_all_blocks(blocks: List[SrtBlock]) -> None:
        """
        Calculate characters per second for all blocks.
        Populates the characters_per_second field for each block.
        
        Args:
            blocks: List of SrtBlock objects (will be modified in place)
        """
        for block in blocks:
            block.characters_per_second = SrtParser.calculate_characters_per_second(block)
    
    @staticmethod
    def find_blocks_reducing_cps_adjustment(blocks: List[SrtBlock]) -> List[int]:
        """
        Find blocks that need CPS adjustment (>19.0 c/s).
        
        Args:
            blocks: List of SrtBlock objects with CPS calculated
            
        Returns:
            List of block indices that need adjustment
        """
        high_cps_indices = []
        for i, block in enumerate(blocks):
            if block.characters_per_second > 19.0:
                high_cps_indices.append(i)
        return high_cps_indices
    
    @staticmethod
    def can_extend_timestamp(current_block: SrtBlock, next_block: Optional[SrtBlock]) -> tuple[bool, int]:
        """
        Check if current block's end time can be extended to achieve better CPS.
        
        Args:
            current_block: Current SRT block
            next_block: Next SRT block (can be None if last block)
            
        Returns:
            (can_extend, new_end_time_ms)
        """
        if not next_block:
            # Last block, can extend reasonably (up to 10 seconds max)
            max_extend = 10000  # 10 seconds in ms
            new_end = current_block.end_time_ms + max_extend
            return True, new_end
        
        # Calculate available extension time
        available_ms = next_block.start_time_ms - current_block.end_time_ms
        
        # If no gap or negative gap, cannot extend
        if available_ms <= 0:
            return False, current_block.end_time_ms
        
        # Calculate target duration for acceptable CPS (target ~18 CPS)
        text_length = len(current_block.translated_text.replace('\n', '').strip())
        target_duration_ms = int((text_length / 18.0) * 1000)  # Target ~18 CPS
        needed_duration_ms = target_duration_ms - current_block.duration_ms
        
        # Can we extend enough to achieve target CPS?
        if needed_duration_ms <= available_ms and needed_duration_ms > 0:
            new_end_time = current_block.end_time_ms + needed_duration_ms
            # Ensure we don't go below 10 CPS (too slow) or above 19 CPS
            new_duration = new_end_time - current_block.start_time_ms
            new_cps = (text_length / new_duration) * 1000
            if 10.0 <= new_cps <= 19.0:
                return True, new_end_time
        
        return False, current_block.end_time_ms
    
    @staticmethod
    def extend_timestamp(block: SrtBlock, new_end_time_ms: int, reason: str) -> None:
        """
        Extend a block's end time and update related fields.
        
        Args:
            block: SRT block to modify
            new_end_time_ms: New end time in milliseconds
            reason: Reason for extension (for debugging)
        """
        block.end_time_ms = new_end_time_ms
        block.duration_ms = new_end_time_ms - block.start_time_ms
        block.timestamp_extended = True
        block.extension_reason = reason
        block.characters_per_second = SrtParser.calculate_characters_per_second(block)
        
        # Update timestamp string
        start_time_str = SrtParser.ms_to_srt_time(block.start_time_ms)
        end_time_str = SrtParser.ms_to_srt_time(block.end_time_ms)
        block.timestamp = f"{start_time_str} --> {end_time_str}"

    @staticmethod
    def adjust_single_block_cps(block: SrtBlock, blocks: List['SrtBlock'], block_idx: int) -> bool:
        """
        Adjust a single block's CPS by extending timing only.
        
        For manual retranslation: ONLY extend timing (END then START).
        NEVER shorten text - high CPS is acceptable if timing can't be extended.
        
        Args:
            block: The SRT block to adjust
            blocks: Full list of blocks (to find prev/next)
            block_idx: Index of block in the list
            
        Returns:
            True if timing was extended, False otherwise
        """
        text_length = len(block.translated_text.replace('\n', '').strip())
        if text_length == 0:
            return False
        
        CPS_THRESHOLD = 19.0
        current_cps = block.characters_per_second
        
        # Check if CPS is already acceptable
        if current_cps <= CPS_THRESHOLD:
            return False
        
        # Calculate minimum duration needed for 19 CPS
        min_duration_ms = int((text_length / CPS_THRESHOLD) * 1000)
        current_duration_ms = block.duration_ms
        extra_time_needed = min_duration_ms - current_duration_ms
        
        if extra_time_needed <= 0:
            return False
        
        # Find previous and next blocks
        prev_block = blocks[block_idx - 1] if block_idx > 0 else None
        next_block = blocks[block_idx + 1] if block_idx + 1 < len(blocks) else None
        
        # Try extending END time first
        max_extra_end = 0
        if next_block:
            # Can't overlap with next block's start
            max_extra_end = max(0, next_block.start_time_ms - block.end_time_ms - 1)
        else:
            # Last block, allow up to 10 seconds extension
            max_extra_end = 10000
        
        # Try extending START time (moving earlier)
        max_extra_start = 0
        if prev_block:
            # Can't overlap with previous block's end
            max_extra_start = max(0, block.start_time_ms - prev_block.end_time_ms - 1)
        else:
            # First block, allow up to 10 seconds extension
            max_extra_start = 10000
        
        total_possible_extension = max_extra_end + max_extra_start
        
        # Only extend timing, no text shortening
        if total_possible_extension <= 0:
            return False
        
        # Extend END first
        end_extension = min(extra_time_needed, max_extra_end)
        if end_extension > 0:
            block.end_time_ms += end_extension
            extra_time_needed -= end_extension
        
        # If more needed, extend START (move earlier)
        if extra_time_needed > 0:
            start_extension = min(extra_time_needed, max_extra_start)
            block.start_time_ms -= start_extension
        
        block.duration_ms = block.end_time_ms - block.start_time_ms
        block.timestamp_extended = True

        # Update timestamp string
        start_time_str = SrtParser.ms_to_srt_time(block.start_time_ms)
        end_time_str = SrtParser.ms_to_srt_time(block.end_time_ms)
        block.timestamp = f"{start_time_str} --> {end_time_str}"

        # Recalculate CPS
        block.characters_per_second = SrtParser.calculate_characters_per_second(block)

        block.extension_reason = f"Extended timing for CPS ({current_cps:.1f} → {block.characters_per_second:.1f})"

        return True


# ============================================================================
# Line Splitting Algorithm
# ============================================================================

class LineSplitter:
    """Implements the strict character-count-based line splitting algorithm."""
    
    CHARACTER_THRESHOLD = 45
    
    @staticmethod
    def split_text(text: str) -> str:
        """
        Split text according to strict rules:
        - If < 45 chars: 1 line
        - If >= 45 chars: 2 lines, split on space with most balanced lengths
        
        Args:
            text: English text to split
            
        Returns:
            Text with appropriate line breaks
        """
        # Clean up the text
        cleaned = text.replace('\n', ' ')
        cleaned = ' '.join(cleaned.split())  # Collapse multiple spaces
        cleaned = cleaned.strip()
        
        total_len = len(cleaned)
        
        # Rule 1: Less than 45 characters -> one line
        if total_len < LineSplitter.CHARACTER_THRESHOLD:
            return cleaned
        
        # Rule 2: 45 or more characters -> two lines
        # Find all space positions
        space_indices = [i for i, char in enumerate(cleaned) if char == ' ']
        
        # Edge case: No spaces (single long word)
        if not space_indices:
            return cleaned
        
        # Find the split position that minimizes length difference
        best_split = None
        min_diff = float('inf')
        
        for space_idx in space_indices:
            left = cleaned[:space_idx]
            right = cleaned[space_idx + 1:]
            
            len_left = len(left)
            len_right = len(right)
            diff = abs(len_left - len_right)
            
            # Choose split with smallest difference
            # If tie, prefer left-biased (len_left <= len_right)
            if diff < min_diff or (diff == min_diff and len_left <= len_right):
                min_diff = diff
                best_split = space_idx
        
        if best_split is not None:
            line1 = cleaned[:best_split]
            line2 = cleaned[best_split + 1:]
            return f"{line1}\n{line2}"
        
        # Fallback (should not reach here if space_indices is not empty)
        return cleaned


# ============================================================================
# OpenRouter Translator
# ============================================================================

class Translator:
    """Handles translation using OpenRouter API."""
    
    def __init__(self, provider: str, api_key: str, model: str, 
                 referer: Optional[str] = None, app_title: Optional[str] = None,
                 is_manual: bool = False):
        """
        Initialize translator with API credentials.
        
        Args:
            provider: "openrouter"
            api_key: API key for the selected provider
            model: Model name to use for translation
            referer: HTTP Referer for OpenRouter (optional)
            app_title: App title for OpenRouter X-Title header (optional)
            is_manual: If True, use manual/simplified prompts for single block retranslation
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model
        self.referer = referer
        self.app_title = app_title
        self.is_manual = is_manual

        # Load prompts from config
        self.reload_prompts()
    
    def reload_prompts(self):
        """Reload prompts from shared config (MainWindow.current_config) - MUST exist."""
        # Use the shared config from MainWindow to avoid reloading from disk
        if MainWindow.current_config is not None:
            self.config = MainWindow.current_config
        else:
            # Fallback: load from disk if shared config is None (first load)
            self.config = load_config()
        
        self.prompts = self.config['prompts']  # MUST exist, no fallback
        print(f"DEBUG: Reloaded {len(self.prompts)} prompt keys from shared config")
    
    def get_translator_prompt(self) -> str:
        """Get batch translation prompt."""
        return self.prompts.get('translator', '')
    
    def get_shorten_cps_prompt(self, original_text: str, current_chars: int, target_chars: int, 
                               duration_ms: int, target_cps: float, shorten_instruction: str) -> str:
        """Get the CPS shortening prompt."""
        template = self.prompts.get('shorten_cps', '')
        
        if not template:
            return ""
        
        duration_s = duration_ms / 1000.0
        try:
            return template.format(
                original_text=original_text,
                current_chars=current_chars,
                target_chars=target_chars,
                duration_ms=duration_ms,
                duration_s=duration_s,
                target_cps=target_cps,
                shorten_instruction=shorten_instruction
            )
        except KeyError:
            return template
    
    def get_shorten_long_prompt(self) -> str:
        """Get the long text shortening prompt."""
        return self.prompts.get('shorten_long', '')
    
    def get_translator_manual_prompt(self) -> str:
        """Get manual (right-click) translation prompt."""
        return self.prompts.get('translator_manual', '')
    
    
    def translate_blocks(self, block_texts: List[str]) -> List[str]:
        """
        Translate a list of Serbian text blocks to English.
        
        Args:
            block_texts: List of Serbian text strings (one per subtitle block)
            
        Returns:
            List of English translations (same order)
            
        Raises:
            Exception: If API call fails
        """
        translations, _, _ = self.translate_blocks_with_debug(block_texts)
        return translations
    
    def translate_blocks_with_debug(self, block_texts: List[str]) -> tuple[List[str], str, str]:
        """
        Translate with debug information.
        
        Returns:
            (translations, raw_response, cleanup_info)
        """
        return self._translate_with_openrouter_debug(block_texts)
    
    def _cleanup_block_markers(self, text: str, block_index: int) -> tuple[str, str]:
        """
        Enhanced cleanup to remove BLOCK_ markers from anywhere in text.
        
        Args:
            text: Text to clean
            block_index: Index of the current block (for pattern matching)
            
        Returns:
            (cleaned_text, cleanup_info)
        """
        original_text = text
        cleanup_info = ""
        
        # First, try to remove prefix patterns (original logic)
        expected_patterns = [
            f"BLOCK_{block_index}:",  # Structured format
            f"[#{block_index}]",      # Old format fallback
            f"{block_index}.",        # Old format fallback
            f"{block_index})",        # Old format fallback
        ]

        removed = ""
        # Check prefixes
        for pattern in expected_patterns:
            # Check with space
            if text.startswith(pattern + " "):
                removed = pattern + " "
                text = text[len(removed):]
                break
            # Check without space (rare but possible)
            elif text.startswith(pattern):
                removed = pattern
                text = text[len(removed):]
                break
        
        if removed:
            cleanup_info += f"{block_index}. REMOVED PREFIX '{removed}' → '{text}'\n"
        
        # Second, remove any BLOCK_N: patterns that appear anywhere in the text
        # This handles cases where the model includes markers in the middle of content
        import re
        block_pattern = r'BLOCK_\d+:'
        matches = re.findall(block_pattern, text)
        
        if matches:
            for match in matches:
                text = text.replace(match, "").strip()
                # Remove double spaces that might result from replacement
                text = re.sub(r'\s+', ' ', text)
            
            cleanup_info += f"{block_index}. REMOVED INTERNAL MARKERS {matches} → '{text}'\n"
        
        # If no markers were found or removed
        if not removed and not matches:
            cleanup_info += f"{block_index}. KEPT AS-IS → '{text}'\n"
        
        return text, cleanup_info

    def _parse_block_response(self, response_text: str, num_blocks: int) -> List[str]:
        """Parse AI response using structured BLOCK_N: markers for reliable parsing."""
        results = [""] * num_blocks

        for i in range(1, num_blocks + 1):
            marker = f"BLOCK_{i}:"
            next_marker = f"BLOCK_{i+1}:" if i < num_blocks else None

            start_pos = response_text.find(marker)
            if start_pos == -1:
                continue

            start_pos += len(marker)

            if next_marker:
                end_pos = response_text.find(next_marker)
                if end_pos == -1:
                    end_pos = len(response_text)
            else:
                end_pos = len(response_text)

            content = response_text[start_pos:end_pos].strip()
            results[i-1] = content

        return results

    def _translate_with_openrouter_debug(self, block_texts: List[str]) -> tuple[List[str], str, str]:
        """Translate using OpenRouter API with debug info."""
        # Try translation with retry logic for missing entries
        return self._translate_with_openrouter_with_retry_debug(block_texts, max_retries=2)
    
    def shorten_long_translations(self, translations: List[str]) -> tuple[List[str], List[int]]:
        """
        Check and shorten translations with enhanced two-line constraints:
        - Max 90 characters total (only valid as 45+45 exactly)
        - Target 75-80 characters
        - If split into two lines, each line must be ≤45 characters
        
        Args:
            translations: List of translated text strings
            
        Returns:
            (shortened_translations, shortened_indices)
        """
        MAX_CHARS = 90
        TARGET_CHARS = 77  # Target 75-80 range
        
        shortened_translations = translations.copy()
        long_blocks = []
        long_indices = []
        
        # Identify translations that need shortening
        for i, trans in enumerate(translations):
            # Check both character count and line constraints
            is_valid, details = self.validate_line_constraints(trans)
            if not is_valid or len(trans) > MAX_CHARS:
                long_blocks.append(trans)
                long_indices.append(i)
        
        # Re-translate problematic blocks if any
        if long_blocks:
            for i, trans in enumerate(long_blocks):
                block_idx = long_indices[i] + 1
                print(f"{block_idx}: '{trans}' - Long shorten Input")
            
            shortened_versions = self._translate_with_shortening_prompt(long_blocks)
            
            for i, shortened in enumerate(shortened_versions):
                block_idx = long_indices[i] + 1
                print(f"{block_idx}: '{shortened}' - Long shorten Output")
            
            # Replace problematic translations with shortened versions
            for idx, shortened in zip(long_indices, shortened_versions):
                shortened_translations[idx] = shortened
        
        return shortened_translations, long_indices
    
    def validate_line_constraints(self, text: str) -> tuple[bool, str]:
        """
        Validate that text conforms to line length constraints.
        
        Args:
            text: Text to validate
            
        Returns:
            (is_valid, details) - boolean validity and description of any violations
        """
        # Clean text same way as LineSplitter does
        cleaned = text.replace('\n', ' ')
        cleaned = ' '.join(cleaned.split())  # Collapse multiple spaces
        cleaned = cleaned.strip()
        
        total_len = len(cleaned)
        
        # Rule 1: If < 45 chars, single line is fine
        if total_len < LineSplitter.CHARACTER_THRESHOLD:
            return True, f"Single line: {total_len} chars ✓"
        
        # Rule 2: If ≥ 45 chars, simulate split and check each line
        if total_len > 90:  # MAX_CHARS for validation
            return False, f"Total {total_len} chars exceeds max 90"
        
        # Simulate the split
        split_result = LineSplitter.split_text(cleaned)
        split_lines = split_result.split('\n')
        
        # Check each line length
        for i, line in enumerate(split_lines, 1):
            line_len = len(line.strip())
            if line_len > LineSplitter.CHARACTER_THRESHOLD:
                return False, f"Line {i}: {line_len} chars > {LineSplitter.CHARACTER_THRESHOLD} limit"
        
        return True, f"Split into {len(split_lines)} lines: {', '.join(str(len(l.strip())) for l in split_lines)} chars each ✓"
    
    def shorten_high_cps_blocks(self, blocks: List[SrtBlock], high_cps_indices: List[int], allow_timestamp_extension: bool = True) -> tuple[List[str], List[int]]:
        """
        Shorten blocks with high characters-per-second using smart CPS-based logic.
        
        First tries to extend timestamps, then shortens text if extension not possible.
        Uses batching for text shortening to reduce API calls.
        
        Args:
            blocks: List of SrtBlock objects with timing and CPS calculated
            high_cps_indices: List of indices for blocks with >19.5 CPS
            allow_timestamp_extension: If False, skip timestamp extension and only shorten text
            
        Returns:
            (shortened_texts, shortened_indices)
        """
        shortened_texts = []
        shortened_indices = []
        
        # Collect blocks that need text shortening (cannot extend timestamp)
        blocks_to_shorten = []
        blocks_to_shorten_indices = []
        
        for i, block_idx in enumerate(high_cps_indices):
            block = blocks[block_idx]
            original_text = block.translated_text
            
            # Try timestamp extension first
            next_block = blocks[block_idx + 1] if block_idx + 1 < len(blocks) else None
            can_extend, new_end_time = SrtParser.can_extend_timestamp(block, next_block)
            
            if can_extend and allow_timestamp_extension:
                # Extend timestamp to achieve better CPS
                SrtParser.extend_timestamp(block, new_end_time, f"Extended to achieve target CPS ({block.characters_per_second:.1f} → ...)")
                shortened_texts.append(original_text)
            else:
                # Cannot extend (or not allowed), need to shorten text - collect for batch processing
                target_chars = int(18.0 * (block.duration_ms / 1000))
                target_chars = max(10, min(target_chars, 85))
                blocks_to_shorten.append({
                    'block_idx': block_idx,
                    'text': original_text,
                    'target_chars': target_chars,
                    'duration_ms': block.duration_ms
                })
                blocks_to_shorten_indices.append(block_idx)
                shortened_texts.append(None)  # Placeholder
        
        # Batch shorten all texts at once if any need shortening
        if blocks_to_shorten:
            for item in blocks_to_shorten:
                block_num = blocks[item['block_idx']].index
                print(f"{block_num}: '{item['text']}' - CPS shorten Input")
            
            shortened_results = self._shorten_for_cps_batch(blocks_to_shorten)
            
            # Update blocks with shortened text
            for result in shortened_results:
                block_idx = result['block_idx']
                block_num = blocks[block_idx].index
                new_text = result['shortened_text']
                print(f"{block_num}: '{new_text}' - CPS shorten Output")
                blocks[block_idx].translated_text = new_text
                blocks[block_idx].was_shortened = True
                
                # Find and update the placeholder
                placeholder_idx = blocks_to_shorten_indices.index(block_idx)
                shortened_texts[placeholder_idx] = new_text
                shortened_indices.append(block_idx)
        
        return shortened_texts, shortened_indices
    
    def _shorten_for_cps_batch(self, blocks_to_shorten: List[dict]) -> List[dict]:
        """
        Batch shorten multiple blocks for CPS compliance in a single API call.
        
        Args:
            blocks_to_shorten: List of dicts with 'block_idx', 'text', 'target_chars', 'duration_ms'
            
        Returns:
            List of dicts with 'block_idx' and 'shortened_text'
        """
        if not blocks_to_shorten:
            return []
        
        # Build user message with all texts
        user_message = "Shorten these cooking subtitles to meet CPS requirements:\n\n"
        for i, item in enumerate(blocks_to_shorten, 1):
            user_message += f"BLOCK_{i}: Shorten to {item['target_chars']} chars - {item['text']}\n"
        
        # Use same API logic
        if self.provider == "openrouter":
            return self._shorten_batch_openrouter(user_message, blocks_to_shorten)
        else:
            # Fallback to individual processing
            results = []
            for item in blocks_to_shorten:
                shortened = self._shorten_for_cps(item['text'], item['target_chars'], item['duration_ms'])
                results.append({'block_idx': item['block_idx'], 'shortened_text': shortened})
            return results
    
    def _shorten_batch_openrouter(self, user_message: str, blocks_to_shorten: List[dict]) -> List[dict]:
        """Batch shorten texts using OpenRouter API."""
        system_message = (
            "You are shortening English subtitle text to achieve acceptable characters-per-second rate. "
            "Shorten each text to the specified character count while preserving meaning."
        )
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if self.referer:
            headers["HTTP-Referer"] = self.referer
        
        if self.app_title:
            headers["X-Title"] = self.app_title
        
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.3
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=120
        )
        
        response.raise_for_status()
        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"].strip()
        
        # Parse results - expect BLOCK_N: format
        results = []
        for i, item in enumerate(blocks_to_shorten, 1):
            marker = f"BLOCK_{i}:"
            start_pos = content.find(marker)
            if start_pos == -1:
                # Fallback to original if parsing fails
                shortened = item['text'][:item['target_chars']]
            else:
                start_pos += len(marker)
                end_pos = content.find("BLOCK_", start_pos)
                if end_pos == -1:
                    end_pos = len(content)
                shortened = content[start_pos:end_pos].strip()
            
            # Clean and validate
            # Remove markdown ** markers
            shortened = shortened.replace("**", "")
            
            # Remove any (XX) patterns at end that might be AI metadata
            shortened = re.sub(r'\s*\(\d+\)\s*$', '', shortened)
            
            shortened = ' '.join(shortened.split())
            
            # Don't truncate here - trust the API response
            # If it's too long, let it be and it will be handled later
            
            results.append({'block_idx': item['block_idx'], 'shortened_text': shortened})
        
        return results
    
    def _shorten_for_cps(self, original_text: str, target_chars: int, duration_ms: int) -> str:
        """
        Shorten text to achieve target characters per second.
        
        Args:
            original_text: Original translated text
            target_chars: Target character count for acceptable CPS
            duration_ms: Block duration in milliseconds
            
        Returns:
            Shortened text
        """
        # Use helper method to get appropriate prompt based on manual mode
        system_message = self.get_shorten_cps_prompt(
            original_text=original_text,
            current_chars=len(original_text),
            target_chars=target_chars,
            duration_ms=duration_ms,
            target_cps=(target_chars/duration_ms)*1000 if duration_ms else 0.0,
            shorten_instruction=f"1. Shorten text to exactly {target_chars} characters (±2 chars acceptable)"
        )
        
        if not system_message:
            # Fallback if no manual prompt
            system_message = f"Shorten this text to {target_chars} characters while keeping meaning."
        
        print(f"DEBUG: Using CPS shorten prompt: {system_message[:100]}...")
        
        user_message = f"Shorten this cooking subtitle to {target_chars} characters:\n\n{original_text}"
        
        # Use same API logic as other methods
        if self.provider == "openrouter":
            return self._shorten_for_cps_openrouter(system_message, user_message)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _shorten_for_cps_openrouter(self, system_message: str, user_message: str) -> str:
        """Shorten text for CPS using OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if self.referer:
            headers["HTTP-Referer"] = self.referer
        
        if self.app_title:
            headers["X-Title"] = self.app_title
        
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.3
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=60
        )
        
        response.raise_for_status()
        response_data = response.json()
        shortened_text = response_data["choices"][0]["message"]["content"].strip()
        
        # Clean and validate result
        shortened_text = shortened_text.strip()
        
        # Remove markdown ** markers
        shortened_text = shortened_text.replace("**", "")
        
        # Remove any leading/trailing quotes
        shortened_text = shortened_text.strip('"\'- ')
        
        shortened_text = ' '.join(shortened_text.split())  # Collapse multiple spaces
        
        # Clean up "(XX chars)" artifacts from AI output
        shortened_text = re.sub(r'\s*\(\d+\s*(?:chars?|characters?)\)\s*', '', shortened_text)
        
        return shortened_text
    
    def _translate_with_shortening_prompt(self, long_texts: List[str]) -> List[str]:
        """
        Re-translate long texts with shortening instructions.
        
        Args:
            long_texts: List of texts that need shortening
            
        Returns:
            List of shortened translations
        """
        # Get prompt from config - NO FALLBACKS, MUST EXIST
        base_prompt = self.prompts['shorten_long']
        print(f"DEBUG: Using shorten_long: {base_prompt[:100]}...")
        
        # Format the prompt with additional instructions
        additional_instructions = (
            "CRITICAL LINE LENGTH RULES:\n"
            "1. Shorten text to 75-80 characters (absolute max: 90)\n"
            "2. If text is < 45 chars: single line is fine\n"
            "3. If text is ≥ 45 chars: it will be split into two lines\n"
            "4. CRITICAL: Each line must be ≤ 45 characters after splitting\n"
            "5. Maximum 90 chars only achievable as perfect 45+45 split\n"
            "6. Examples: GOOD: 44 chars, 45+40 split, 40+38 split. BAD: 50 chars, 55+35 split"
        )
        
        user_message = base_prompt.format(additional_instructions=additional_instructions) + "\n\n" + "Shorten these translations to 75-80 characters (max 90):\n\n"
        for i, text in enumerate(long_texts, 1):
            user_message += f"BLOCK_{i}: {text}\n"
        
        # Use same API logic as main translation
        num_texts = len(long_texts)
        if self.provider == "openrouter":
            return self._shorten_with_openrouter(user_message, num_texts)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _shorten_with_openrouter(self, user_message: str, num_texts: int) -> List[str]:
        """Shorten texts using OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if self.referer:
            headers["HTTP-Referer"] = self.referer
        
        if self.app_title:
            headers["X-Title"] = self.app_title
        
        body = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.3
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=60
        )
        
        response.raise_for_status()
        response_data = response.json()
        shortened_text = response_data["choices"][0]["message"]["content"].strip()

        # Parse using structured markers for reliability
        shortened_texts = self._parse_block_response(shortened_text, num_texts)

        # If structured parsing failed, fall back to line-based parsing
        if len(shortened_texts) != num_texts or all(t == "" for t in shortened_texts):
            print("DEBUG: Structured shortening parsing failed, falling back to line-based parsing")
            shortened_texts = shortened_text.split('\n')
            shortened_texts = [t.strip() for t in shortened_texts if t.strip()]

        # Validate response count
        if len(shortened_texts) != num_texts:
            print(f"DEBUG: Shortening response count mismatch - expected {num_texts}, got {len(shortened_texts)}")
            print(f"DEBUG: Raw shortening response: {shortened_text}")

        # Clean up shortened texts using enhanced cleanup
        cleaned_shortened = []
        for i, text in enumerate(shortened_texts[:num_texts], 1):
            text = text.strip()
            if text:
                # Use enhanced cleanup to remove BLOCK_ markers from anywhere
                text, _ = self._cleanup_block_markers(text, i)
            cleaned_shortened.append(text)
        
        return cleaned_shortened

    def _translate_with_openrouter_with_retry_debug(self, block_texts: List[str], max_retries: int = 2) -> tuple[List[str], str, str]:
        """Translate using OpenRouter API with retry logic and debug info."""
        
        for attempt in range(max_retries + 1):
            # Get translator prompt - use manual prompt if is_manual is True
            if self.is_manual:
                translator_prompt = self.get_translator_manual_prompt()
                print(f"DEBUG: Using MANUAL translator prompt for OpenRouter: {translator_prompt[:100]}...")
            else:
                translator_prompt = self.get_translator_prompt()
                print(f"DEBUG: Using translator prompt for OpenRouter: {translator_prompt[:100]}...")
            
            # Format input using structured markers for reliable parsing
            text_blocks = ""
            for i, text in enumerate(block_texts, 1):
                text_blocks += f"BLOCK_{i}: {text}\n"
            
            # Combine prompt + text as single user message
            user_message = translator_prompt.format(text=text_blocks)
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            if self.referer:
                headers["HTTP-Referer"] = self.referer
            
            if self.app_title:
                headers["X-Title"] = self.app_title
            
            # Prepare request body - single message only
            body = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.3
            }
            
            # Call OpenRouter API
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=body,
                timeout=120
            )
            
            # Check for errors
            if response.status_code != 200:
                raise Exception(
                    f"OpenRouter API error (status {response.status_code}): {response.text}"
                )
            
            # Parse response
            response_data = response.json()
            translated_text = response_data["choices"][0]["message"]["content"].strip()
            raw_response = translated_text  # Save for debug

            # Parse using structured markers for reliability
            translations = self._parse_block_response(translated_text, len(block_texts))

            # If structured parsing failed, fall back to line-based parsing
            if len(translations) != len(block_texts) or all(t == "" for t in translations):
                print("DEBUG: Structured parsing failed, falling back to line-based parsing")
                translations = translated_text.split('\n')
                translations = [t.strip() for t in translations if t.strip()]

            # Validate response count
            if len(translations) != len(block_texts):
                print(f"DEBUG: Response count mismatch - expected {len(block_texts)}, got {len(translations)}")
                print(f"DEBUG: Raw response: {raw_response}")

            # Clean up translations
            cleaned_translations = []
            cleanup_info = ""
            for i, trans in enumerate(translations[:len(block_texts)], 1):
                original_trans = trans
                trans = trans.strip()

                if trans:
                    # Use enhanced cleanup to remove BLOCK_ markers from anywhere
                    trans, cleanup_details = self._cleanup_block_markers(trans, i)
                    cleanup_info += cleanup_details
                
                # Only add non-empty translations to the list checked for length
                if trans:
                    cleaned_translations.append(trans)
            
            # Check if we have the right number
            if len(cleaned_translations) == len(block_texts):
                return cleaned_translations, raw_response, cleanup_info
            
            # If not, and we have retries left, try again
            if attempt < max_retries:
                print(f"Warning: Got {len(cleaned_translations)} translations, expected {len(block_texts)}. Retrying (attempt {attempt + 1}/{max_retries})...")
                continue
            else:
                # Last attempt failed, raise error
                raise ValueError(
                    f"Translation mismatch after {max_retries + 1} attempts: expected {len(block_texts)} translations, "
                    f"got {len(cleaned_translations)}"
                )


# ============================================================================
# Translation Worker Thread
# ============================================================================

class TranslationWorker(QThread):
    """Worker thread for performing translation without blocking UI."""
    
    finished = pyqtSignal(str, list, list, list, object)  # Emits translated SRT content, shortened_long_indices, shortened_cps_indices, time_extended_indices, and blocks
    error = pyqtSignal(str)  # Emits error message
    progress = pyqtSignal(str)  # Emits progress updates
    debug_input = pyqtSignal(str)  # Emits input sent to API
    debug_raw_response = pyqtSignal(str)  # Emits raw API response
    debug_cleaned = pyqtSignal(str)  # Emits cleaned translations
    
    def __init__(self, srt_content: str, provider: str, api_key: str, model: str,
                 referer: Optional[str] = None, app_title: Optional[str] = None):
        super().__init__()
        self.srt_content = srt_content
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.referer = referer
        self.app_title = app_title
    
    def run(self):
        """Execute translation process."""
        try:
            # DEBUG: Print what worker received

            
            # Parse SRT
            self.progress.emit("Parsing SRT file...")
            blocks = SrtParser.parse(self.srt_content)
            
            # Prepare texts for translation
            self.progress.emit(f"Preparing {len(blocks)} blocks for translation...")
            block_texts = []
            for block in blocks:
                # Join lines with spaces to preserve context
                text = ' '.join(block.original_text_lines)
                block_texts.append(text)
            
            # Emit debug: input blocks
            debug_input_text = "=== INPUT TO API ===\n"
            for i, text in enumerate(block_texts, 1):
                debug_input_text += f"{i}. {text}\n"
            self.debug_input.emit(debug_input_text)
            
            # Translate (single call)
            self.progress.emit(f"Translating with OpenRouter...")
            translator = Translator(
                provider=self.provider,
                api_key=self.api_key,
                model=self.model,
                referer=self.referer,
                app_title=self.app_title
            )

            translations, raw_response, cleaned_info = translator.translate_blocks_with_debug(block_texts)

            self.debug_raw_response.emit(f"=== RAW API RESPONSE ===\n{raw_response}")
            self.debug_cleaned.emit(f"=== AFTER CLEANUP ===\n{cleaned_info}")
            
            # Check for long translations and shorten if needed
            self.progress.emit("Checking for long translations...")
            translations, shortened_indices = translator.shorten_long_translations(translations)
            
            # Emit debug: shortening info
            if shortened_indices:
                shortening_info = f"=== SHORTENED TRANSLATIONS ===\n"
                shortening_info += f"Blocks shortened: {shortened_indices}\n"
                for idx in shortened_indices:
                    shortening_info += f"Block {idx + 1}: {len(translations[idx])} chars\n"
                self.debug_cleaned.emit(shortening_info)
            
            # Apply translated text to blocks first (needed for CPS calculation)
            for i, (block, translated_text) in enumerate(zip(blocks, translations)):
                # Mark if this block was shortened
                block.was_shortened = i in shortened_indices
                block.translated_text = translated_text
            
            # Calculate characters per second for all blocks
            self.progress.emit("Calculating characters per second...")
            SrtParser.calculate_cps_for_all_blocks(blocks)
            
            # Find blocks with high CPS that need adjustment
            self.progress.emit("Finding blocks with high CPS (>19.5 c/s)...")
            high_cps_indices = SrtParser.find_blocks_reducing_cps_adjustment(blocks)
            
            # Emit debug: CPS information
            cps_debug = "=== CHARACTERS PER SECOND ANALYSIS ===\n"
            for i, block in enumerate(blocks):
                status = "HIGH" if block.characters_per_second > 19.5 else "OK"
                cps_debug += f"Block {block.index}: {block.characters_per_second:.1f} c/s ({len(block.translated_text)} chars, {block.duration_ms}ms) - {status}\n"
            
            if high_cps_indices:
                cps_debug += f"\nBlocks needing adjustment: {[blocks[i].index for i in high_cps_indices]}\n"
            else:
                cps_debug += "\nAll blocks have acceptable CPS!\n"
            
            self.debug_cleaned.emit(cps_debug)
            
            # Apply CPS adjustments (timestamp extension or text shortening)
            cps_shortened_indices = []  # Track which blocks were shortened specifically for CPS
            if high_cps_indices:
                self.progress.emit(f"Adjusting {len(high_cps_indices)} high CPS blocks...")
                translator = Translator(
                    provider=self.provider,
                    api_key=self.api_key,
                    model=self.model,
                    referer=self.referer,
                    app_title=self.app_title
                )

                cps_shortened_texts, cps_shortened_indices = translator.shorten_high_cps_blocks(blocks, high_cps_indices)
                
                # Update translations with CPS-adjusted text
                for i, block_idx in enumerate(cps_shortened_indices):
                    translations[block_idx] = blocks[block_idx].translated_text
                    # Recalculate CPS after text shortening
                    blocks[block_idx].characters_per_second = SrtParser.calculate_characters_per_second(blocks[block_idx])
                    # Add to overall shortened indices if not already there
                    if block_idx not in shortened_indices:
                        shortened_indices.append(block_idx)
                
                # Emit debug: CPS adjustment results
                cps_result_debug = "=== CPS ADJUSTMENT RESULTS ===\n"
                for block_idx in high_cps_indices:
                    block = blocks[block_idx]
                    if block.timestamp_extended:
                        cps_result_debug += f"Block {block.index}: EXTENDED timestamp to {block.characters_per_second:.1f} c/s - {block.extension_reason}\n"
                    elif block_idx in cps_shortened_indices:
                        cps_result_debug += f"Block {block.index}: SHORTENED text to {len(block.translated_text)} chars ({block.characters_per_second:.1f} c/s)\n"
                    else:
                        cps_result_debug += f"Block {block.index}: No adjustment applied\n"
                
                self.debug_cleaned.emit(cps_result_debug)
            
            # Apply line splitting and update blocks
            self.progress.emit("Applying line splitting rules...")
            for i, (block, translated_text) in enumerate(zip(blocks, translations)):
                # Handle single line in original becoming double line in translation
                split_translated = LineSplitter.split_text(translated_text)
                
                # Always apply line splitting - the 45-character rule should be enforced
                # regardless of original Serbian text length
                block.translated_text = split_translated
                # Recalculate CPS after line splitting
                block.characters_per_second = SrtParser.calculate_characters_per_second(block)
            
            # ENFORCE: Check each block after line splitting - if any line > 45, shorten
            self.progress.emit("Final check: enforcing line length rules...")
            blocks_needing_reshorten = []
            for i, block in enumerate(blocks):
                lines = block.translated_text.split('\n')
                for line_idx, line in enumerate(lines):
                    if len(line) > 45:
                        print(f"[DEBUG] Block {block.index} line {line_idx+1} has {len(line)} chars > 45 - marking for reshorten")
                        blocks_needing_reshorten.append(i)
                        break
            
            # If any blocks need reshortening, do it
            if blocks_needing_reshorten:
                print(f"[DEBUG] Reshortening {len(blocks_needing_reshorten)} blocks: {blocks_needing_reshorten}")
                translator = Translator(
                    provider=self.provider,
                    api_key=self.api_key,
                    model=self.model,
                    referer=self.referer,
                    app_title=self.app_title
                )
                
                # Get texts that need reshortening
                texts_to_reshorten = [blocks[i].translated_text for i in blocks_needing_reshorten]
                
                # Reshorten
                reshortened = translator._translate_with_shortening_prompt(texts_to_reshorten)
                
                # Apply back
                for idx, new_text in zip(blocks_needing_reshorten, reshortened):
                    old_text = blocks[idx].translated_text
                    blocks[idx].translated_text = new_text
                    blocks[idx].was_shortened = True
                    print(f"[DEBUG] Block {blocks[idx].index} reshortened: {len(old_text)} -> {len(new_text)} chars")
                
                # Re-apply line splitting after reshortening
                for idx in blocks_needing_reshorten:
                    block = blocks[idx]
                    split = LineSplitter.split_text(block.translated_text)
                    block.translated_text = split
                    block.characters_per_second = SrtParser.calculate_characters_per_second(block)
            
            # FINAL ENFORCEMENT: Ensure ALL blocks are <= 19 CPS
            self.progress.emit("Final check: enforcing CPS <= 19...")
            blocks_over_19 = []
            for i, block in enumerate(blocks):
                if block.characters_per_second > 19.0:
                    blocks_over_19.append(i)
                    print(f"[DEBUG] Block {block.index} has {block.characters_per_second:.1f} CPS > 19 - forcing extend")
            
            if blocks_over_19:
                # Force extend timestamps as much as possible for remaining high CPS blocks
                for block_idx in blocks_over_19:
                    block = blocks[block_idx]
                    next_block = blocks[block_idx + 1] if block_idx + 1 < len(blocks) else None
                    prev_block = blocks[block_idx - 1] if block_idx > 0 else None
                    
                    # Calculate how much time needed for exactly 19 CPS
                    text_len = len(block.translated_text.replace('\n', '').strip())
                    min_duration = int((text_len / 19.0) * 1000)
                    needed = min_duration - block.duration_ms
                    
                    # Step 1: Extend END time
                    if needed > 0:
                        if next_block:
                            max_extend = next_block.start_time_ms - block.end_time_ms - 1
                            extend = min(needed, max_extend)
                            if extend > 0:
                                block.end_time_ms += extend
                                block.duration_ms = block.end_time_ms - block.start_time_ms
                                block.characters_per_second = SrtParser.calculate_characters_per_second(block)
                                print(f"[DEBUG] Block {block.index} END extended by {extend}ms, CPS: {block.characters_per_second:.1f}")
                                needed = min_duration - block.duration_ms
                        elif not next_block:
                            extend = min(needed, 10000)
                            block.end_time_ms += extend
                            block.duration_ms = block.end_time_ms - block.start_time_ms
                            block.characters_per_second = SrtParser.calculate_characters_per_second(block)
                            print(f"[DEBUG] Block {block.index} END extended by {extend}ms (last), CPS: {block.characters_per_second:.1f}")
                            needed = min_duration - block.duration_ms
                    
                    # Step 2: Try extending START time (last resort - move earlier)
                    if needed > 0 and prev_block:
                        max_start_extend = block.start_time_ms - prev_block.end_time_ms - 1
                        extend = min(needed, max_start_extend)
                        if extend > 0:
                            block.start_time_ms -= extend
                            block.duration_ms = block.end_time_ms - block.start_time_ms
                            block.characters_per_second = SrtParser.calculate_characters_per_second(block)
                            print(f"[DEBUG] Block {block.index} START extended by {extend}ms, CPS: {block.characters_per_second:.1f}")
            
            # Rebuild SRT
            self.progress.emit("Rebuilding SRT file...")
            output_srt = SrtParser.rebuild(blocks)
            
            # Enhanced validation: Check all line length constraints
            debug_validation = "=== ENHANCED LINE LENGTH VALIDATION ===\n"
            output_lines = output_srt.split('\n')
            block_num = 0
            current_block_lines = []
            violations_found = False
            validation_details = []
            
            for line in output_lines:
                stripped_line = line.strip()
                
                if stripped_line.isdigit():
                    # New block - check previous block
                    if current_block_lines:
                        block_text_lines = current_block_lines
                        total_chars = sum(len(text) for text in block_text_lines)
                        
                        # Validate each line in the block
                        block_violations = []
                        for line_idx, text in enumerate(block_text_lines):
                            if len(text) > 45:
                                block_violations.append(f"Line {line_idx + 1}: {len(text)} chars")
                        
                        if block_violations:
                            violations_found = True
                            violations_str = ", ".join(block_violations)
                            validation_details.append(f"❌ Block {block_num}: {violations_str}")
                        else:
                            validation_details.append(f"✅ Block {block_num}: {len(block_text_lines)} line(s), {total_chars} total chars")
                    
                    current_block_lines = []
                    block_num = int(stripped_line)
                elif '-->' in stripped_line or not stripped_line:
                    continue
                else:
                    current_block_lines.append(stripped_line)
            
            # Check last block
            if current_block_lines:
                block_text_lines = current_block_lines
                total_chars = sum(len(text) for text in block_text_lines)
                
                # Validate each line in the block
                block_violations = []
                for line_idx, text in enumerate(block_text_lines):
                    if len(text) > 45:
                        block_violations.append(f"Line {line_idx + 1}: {len(text)} chars")
                
                if block_violations:
                    violations_found = True
                    violations_str = ", ".join(block_violations)
                    validation_details.append(f"❌ Block {block_num}: {violations_str}")
                else:
                    validation_details.append(f"✅ Block {block_num}: {len(block_text_lines)} line(s), {total_chars} total chars")
            
            # Compile validation report
            debug_validation += "\n".join(validation_details)
            
            if violations_found:
                debug_validation += "\n\n❌ LINE LENGTH VIOLATIONS FOUND!\n"
                debug_validation += "Blocks with lines > 45 characters need re-shortening.\n"
            else:
                debug_validation += "\n\n✅ ALL BLOCKS VALID!\n"
                debug_validation += "All lines respect the 45-character limit.\n"
            
            self.debug_cleaned.emit(debug_validation)
            
            # Compute separate indices for different modification types
            shortened_long_indices = shortened_indices  # From shorten_long_translations (>90/line constraints)
            shortened_cps_indices = cps_shortened_indices  # From CPS fallback shortening
            time_extended_indices = [i for i, block in enumerate(blocks) if block.timestamp_extended]
            
            self.progress.emit("Translation complete!")
            self.finished.emit(output_srt, shortened_long_indices, shortened_cps_indices, time_extended_indices, blocks)
            
        except Exception as e:
            self.error.emit(str(e))


# ============================================================================
# Secrets (API keys) — stored OUTSIDE config.json and never committed
# ============================================================================

SECRETS_FILENAME = "secrets.json"
SECRET_KEY_NAMES = ("openrouter_api_key",)

SECRETS_TEMPLATE = {
    "_readme": (
        "SRT Translator API keys. Paste your key between the quotes. "
        "This file is created automatically on first run, stays on this machine, "
        "and is never part of the repository."
    ),
    "openrouter_api_key": "",
}


def get_secrets_file_path() -> str:
    """Path to secrets.json (next to the executable, or next to app.py)."""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, SECRETS_FILENAME)


def ensure_secrets_file() -> str:
    """Create secrets.json with placeholders if missing; return its path."""
    path = get_secrets_file_path()
    if not os.path.exists(path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(SECRETS_TEMPLATE, f, indent=2)
            print(f"Created secrets file: {path}")
        except Exception as e:
            print(f"WARNING: could not create secrets file {path}: {e}")
    return path


def load_secrets() -> dict:
    """Read API keys from secrets.json (creating the file if needed)."""
    path = ensure_secrets_file()
    keys = {name: "" for name in SECRET_KEY_NAMES}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for name in SECRET_KEY_NAMES:
            value = data.get(name)
            if isinstance(value, str):
                keys[name] = value
    except Exception as e:
        print(f"WARNING: could not read secrets file {path}: {e}")
    return keys


def save_secrets(keys: dict) -> None:
    """Write API keys to secrets.json, preserving the readme field."""
    path = ensure_secrets_file()
    data = {}
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
    data.setdefault("_readme", SECRETS_TEMPLATE["_readme"])
    for name in SECRET_KEY_NAMES:
        if name in keys:
            data[name] = keys.get(name, "")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def strip_secrets(config: dict) -> dict:
    """Remove API keys from a config dict so they are never written to config.json."""
    for name in SECRET_KEY_NAMES:
        config.pop(name, None)
    return config


def _open_path(path: str) -> None:
    """Open a file or folder in the OS default application (best effort)."""
    try:
        if hasattr(os, 'startfile'):
            os.startfile(path)  # Windows
        else:
            import subprocess
            opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
            subprocess.Popen([opener, path])
    except Exception as e:
        print(f"WARNING: could not open {path}: {e}")


def notify_missing_api_key(parent=None) -> None:
    """Tell the user where the API keys file is and offer to open it."""
    path = ensure_secrets_file()
    if load_secrets().get("openrouter_api_key"):
        return

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle("API key required")
    box.setText("SRT Translator stores your API key in a separate file.")
    box.setInformativeText(
        "The file is created automatically, stays on this machine, and is never "
        "uploaded:\n\n"
        f"{path}\n\n"
        "Paste your OpenRouter key into it, or enter it in Settings → API Keys."
    )
    open_file_btn = box.addButton("Open secrets file", QMessageBox.ButtonRole.ActionRole)
    open_folder_btn = box.addButton("Open folder", QMessageBox.ButtonRole.ActionRole)
    box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
    box.exec()

    clicked = box.clickedButton()
    if clicked == open_file_btn:
        _open_path(path)
    elif clicked == open_folder_btn:
        _open_path(os.path.dirname(path))


# ============================================================================
# Settings Dialog
# ============================================================================

def load_config() -> dict:
    """Load configuration from config.json - FAIL if invalid."""
    config_file = SettingsDialog.get_config_file_path()
    
    print(f"DEBUG: Loading config from: {config_file}")
    
    # Check if config file exists
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    try:
        with open(config_file, 'r') as f:
            loaded_config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file {config_file}: {e}")
    except Exception as e:
        raise Exception(f"Error reading config file {config_file}: {e}")
    
    # Validate that prompts section exists
    if "prompts" not in loaded_config:
        raise KeyError("Missing 'prompts' section in config.json")
    
    prompts = loaded_config["prompts"]
    
    # Validate required prompt keys (only standard prompts - manual prompts are optional, fall back to standard if missing)
    required_keys = ["translator", "shorten_cps", "shorten_long", "translator_manual"]
    missing_keys = [key for key in required_keys if key not in prompts or not prompts[key].strip()]
    
    if missing_keys:
        raise KeyError(f"Missing or empty required prompt keys in config.json: {missing_keys}")
    
    print(f"DEBUG: Successfully loaded config with {len(prompts)} prompt keys")

    # API keys live in a separate, never-committed secrets.json. Move any keys
    # still found in config.json over, then merge the secrets into the config
    # dict so the rest of the app keeps using settings['openrouter_api_key'].
    legacy_keys = {name: loaded_config.pop(name) for name in SECRET_KEY_NAMES if loaded_config.get(name)}
    secrets = load_secrets()
    if legacy_keys:
        for name, value in legacy_keys.items():
            if value and not secrets.get(name):
                secrets[name] = value
        save_secrets(secrets)
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(loaded_config, f, indent=2)
            print("DEBUG: Moved API keys from config.json to secrets.json")
        except Exception as e:
            print(f"WARNING: could not rewrite config.json without keys: {e}")
    loaded_config.update(secrets)

    # Update shared config in MainWindow class for immediate use
    MainWindow.current_config = loaded_config
    
    return loaded_config


class SettingsDialog(QDialog):
    """Dialog for configuring OpenRouter API settings."""
    CONFIG_FILE = "config.json"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.center_settings_title())
        self.setModal(True)
        self.resize(500, 400)
        
        # Setup UI
        self.setup_ui()
        
        # Load settings
        self.load_settings()
        
        # Ensure proper size
        self.adjustSize()
        
        # Load window geometry after UI is ready
        self.load_window_geometry()
    
    def setup_ui(self):
        """Create settings dialog UI with tabs for Prompts and API Keys."""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        # Allow reordering tabs by drag and drop, and remember the order
        self.tab_widget.tabBar().setMovable(True)
        self.tab_widget.tabBar().tabMoved.connect(self.save_tab_order)

        # Create tabs
        self.create_models_tab()
        self.create_prompts_tab()
        self.create_api_keys_tab()
        self.restore_tab_order()
        
        # Modern buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        save_btn = QPushButton("💾 Save")
        cancel_btn = QPushButton("❌ Cancel")
        
        # Modern button styling
        button_style = """
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """
        
        cancel_style = """
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """
        
        save_btn.setStyleSheet(button_style)
        cancel_btn.setStyleSheet(cancel_style)
        
        save_btn.clicked.connect(self.save_settings)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        # Add to layout
        layout.addWidget(self.tab_widget)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def create_prompts_tab(self):
        """Create the Prompts tab with nested sub-tabs for each prompt."""
        prompts_tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create nested tab widget for prompts
        self.prompts_tabs = QTabWidget()
        
        # Common styling for text edits
        text_edit_style = """
            QTextEdit {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: 'Consolas', 'Monaco', monospace;
                line-height: 1.4;
                min-height: 200px;
            }
            QTextEdit:hover {
                border-color: #80bdff;
            }
            QTextEdit:focus {
                border-color: #007bff;
                outline: none;
            }
        """
        
        # Description label styling
        desc_style = """
            QLabel {
                color: #6c757d;
                font-size: 12px;
                margin-bottom: 15px;
                font-style: italic;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 4px;
                border: 1px solid #e9ecef;
            }
        """
        
        # Tab 1: Translator System
        sys_tab = QWidget()
        sys_layout = QVBoxLayout()
        sys_layout.setSpacing(15)
        sys_layout.setContentsMargins(20, 20, 20, 20)
        
        sys_desc = QLabel("Main instructions for the AI translator - defines tone, style, rules, and formatting for Serbian to English translation")
        sys_desc.setStyleSheet(desc_style)
        sys_desc.setWordWrap(True)
        sys_layout.addWidget(sys_desc)
        
        self.translator_system_edit = QTextEdit()
        self.translator_system_edit.setStyleSheet(text_edit_style)
        sys_layout.addWidget(self.translator_system_edit)
        
        sys_tab.setLayout(sys_layout)
        self.prompts_tabs.addTab(sys_tab, "Translator")
        
        # Tab 2: CPS Shortening System Template
        cps_tab = QWidget()
        cps_layout = QVBoxLayout()
        cps_layout.setSpacing(15)
        cps_layout.setContentsMargins(20, 20, 20, 20)
        
        cps_desc = QLabel("Template for shortening text to achieve acceptable characters-per-second rate. Variables: {original_text}, {current_chars}, {target_chars}, {duration_ms}, {duration_s}, {target_cps}, {shorten_instruction}")
        cps_desc.setStyleSheet(desc_style)
        cps_desc.setWordWrap(True)
        cps_layout.addWidget(cps_desc)
        
        self.shorten_cps_system_edit = QTextEdit()
        self.shorten_cps_system_edit.setStyleSheet(text_edit_style)
        cps_layout.addWidget(self.shorten_cps_system_edit)
        
        cps_tab.setLayout(cps_layout)
        self.prompts_tabs.addTab(cps_tab, "CPS Shortening")
        
        # Tab 3: Long Text Shortening System
        long_tab = QWidget()
        long_layout = QVBoxLayout()
        long_layout.setSpacing(15)
        long_layout.setContentsMargins(20, 20, 20, 20)
        
        long_desc = QLabel("Instructions for shortening overly long translations. Variable: {additional_instructions}")
        long_desc.setStyleSheet(desc_style)
        long_desc.setWordWrap(True)
        long_layout.addWidget(long_desc)
        
        self.shorten_long_system_edit = QTextEdit()
        self.shorten_long_system_edit.setStyleSheet(text_edit_style)
        long_layout.addWidget(self.shorten_long_system_edit)
        
        long_tab.setLayout(long_layout)
        self.prompts_tabs.addTab(long_tab, "Long Shortening")
        
        # Tab 4: Manual Translation (for single block retranslation - right-click)
        manual_tab = QWidget()
        manual_layout = QVBoxLayout()
        manual_layout.setSpacing(15)
        manual_layout.setContentsMargins(20, 20, 20, 20)
        
        manual_desc = QLabel("Prompt for manual single-block retranslation (right-click). This is used when you right-click on a block and select 'Retranslate this block'. Use {text} as placeholder.")
        manual_desc.setStyleSheet(desc_style)
        manual_desc.setWordWrap(True)
        manual_layout.addWidget(manual_desc)
        
        self.translator_manual_edit = QTextEdit()
        self.translator_manual_edit.setStyleSheet(text_edit_style)
        manual_layout.addWidget(self.translator_manual_edit)
        
        manual_tab.setLayout(manual_layout)
        self.prompts_tabs.addTab(manual_tab, "Manual Translation")
        
        layout.addWidget(self.prompts_tabs)
        prompts_tab.setLayout(layout)
        
        self.tab_widget.addTab(prompts_tab, "📝 Prompts")
    
    def create_api_keys_tab(self):
        """Create the API Keys tab with OpenRouter API key only."""
        api_tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Modern group box styling
        group_style = """
            QGroupBox {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: 600;
                color: #495057;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                background-color: white;
            }
        """
        
        # OpenRouter Settings Group
        openrouter_group = QGroupBox("🌐 OpenRouter Settings")
        openrouter_group.setStyleSheet(group_style)
        openrouter_layout = QFormLayout()
        openrouter_layout.setSpacing(10)
        openrouter_layout.setContentsMargins(15, 20, 15, 15)
        
        self.openrouter_api_key_widget = APIKeyWidget()
        self.openrouter_api_key_widget.api_key_input.setPlaceholderText("sk-or-...")
        self.openrouter_api_key_widget.api_key_input.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                min-height: 80px;
                max-height: 80px;
                color: #000000;
            }
            QTextEdit:hover {
                border-color: #80bdff;
            }
            QTextEdit:focus {
                border-color: #007bff;
                outline: none;
            }
        """)
        
        openrouter_layout.addRow("API Key:", self.openrouter_api_key_widget)
        openrouter_group.setLayout(openrouter_layout)
        
        layout.addWidget(openrouter_group)
        layout.addStretch()
        
        api_tab.setLayout(layout)
        self.tab_widget.addTab(api_tab, "🔑 API Keys")

    def create_models_tab(self):
        """Create the Models tab for managing OpenRouter models."""
        models_tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        desc_style = """
            QLabel {
                color: #6c757d;
                font-size: 12px;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 4px;
                border: 1px solid #e9ecef;
            }
        """
        
        desc = QLabel("Enter one model ID per line. Empty lines and trailing commas or periods will be ignored.")
        desc.setStyleSheet(desc_style)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        self.models_text = QTextEdit()
        self.models_text.setPlaceholderText("google/gemini-2.0-flash-001\ngoogle/gemini-2.5-flash\ngpt-4o-mini")
        self.models_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QTextEdit:hover {
                border-color: #80bdff;
            }
            QTextEdit:focus {
                border-color: #007bff;
                outline: none;
            }
        """)
        layout.addWidget(self.models_text)
        
        models_tab.setLayout(layout)
        self.tab_widget.addTab(models_tab, "🤖 Models")
    def load_settings(self):
        """Load settings from config file."""
        try:
            config = load_config()
            print(f"DEBUG: Successfully loaded config for settings dialog")
        except Exception as e:
            print(f"CRITICAL ERROR: Cannot load config for settings: {e}")
            QMessageBox.critical(self, "Configuration Error", 
                             f"Failed to load config.json:\n\n{e}\n\n"
                             "The application requires a valid config.json file to function.")
            return
        
        # Load OpenRouter settings
        self.openrouter_api_key_widget.setText(config.get('openrouter_api_key', ''))
        
        # Load prompts - 4 fields only
        prompts = config['prompts']
        self.translator_system_edit.setPlainText(prompts.get('translator', ''))
        self.shorten_cps_system_edit.setPlainText(prompts.get('shorten_cps', ''))
        self.shorten_long_system_edit.setPlainText(prompts.get('shorten_long', ''))
        self.translator_manual_edit.setPlainText(prompts.get('translator_manual', ''))
        
        # Load OpenRouter models
        models = config.get('openrouter_models', [])
        self.models_text.setPlainText('\n'.join(models))
        

    

    
    def save_settings(self):
        """Save settings to config file."""
        # Save window geometry first
        self.save_window_geometry()

        # Get config file path using centralized method
        config_file = SettingsDialog.get_config_file_path()

        # Load existing config to preserve cache
        try:
            config = load_config()
            print(f"DEBUG: Successfully loaded existing config for saving")
        except Exception as e:
            print(f"WARNING: Could not load existing config, creating new: {e}")
            # Start with empty config if we can't load existing
            config = {}
        
        # Update API keys - stored in secrets.json, never in config.json
        save_secrets({
            'openrouter_api_key': self.openrouter_api_key_widget.text().strip()
        })
        strip_secrets(config)
        
        # Update prompts - 4 fields only
        config['prompts'] = {
            'translator': self.translator_system_edit.toPlainText(),
            'shorten_cps': self.shorten_cps_system_edit.toPlainText(),
            'shorten_long': self.shorten_long_system_edit.toPlainText(),
            'translator_manual': self.translator_manual_edit.toPlainText()
        }
        
        # Update OpenRouter models - parse text, ignore empty lines and trailing commas/periods
        models = []
        for line in self.models_text.toPlainText().split('\n'):
            model = line.strip()
            if model:
                model = model.rstrip(',.').strip()
                if model:
                    models.append(model)
        config['openrouter_models'] = models
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
    

    
    def resizeEvent(self, event):
        """Handle dialog resize to ensure proper title display."""
        super().resizeEvent(event)
        # Ensure title is properly updated on resize
        padded_title = self.center_settings_title()
        self.setWindowTitle(padded_title)
    
    def center_settings_title(self) -> str:
        """Add padding to make settings title appear centered."""
        title = "Settings"
        target_width = 60  # Approximate characters for centering
        if len(title) < target_width:
            padding = (target_width - len(title)) // 2
            return " " * padding + title + " " * padding
        return title
    
    def load_window_geometry(self):
        """Load and restore Settings dialog geometry."""
        settings = self.get_settings()
        if settings:
            geometry = settings.get('settings_geometry', {})
            if geometry and geometry.get('geometry'):
                try:
                    self.restoreGeometry(bytes.fromhex(geometry.get('geometry', '')))
                except:
                    pass  # Use default geometry if restoration fails
    
    def save_window_geometry(self):
        """Save current window geometry for Settings dialog only."""
        settings = self.get_settings() or {}
        strip_secrets(settings)
        settings['settings_geometry'] = {
            'geometry': self.saveGeometry().toHex().data().decode()
        }
        
        try:
            with open(SettingsDialog.get_config_file_path(), 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass
    
    def closeEvent(self, event):
        """Handle close event to save window geometry."""
        self.save_window_geometry()
        super().closeEvent(event)
    
    def reject(self):
        """Handle reject (cancel) to save window geometry."""
        self.save_window_geometry()
        super().reject()
    
    def accept(self):
        """Handle accept (save) to save window geometry."""
        self.save_window_geometry()
        super().accept()
    
    @staticmethod
    def get_config_file_path() -> str:
        """Get the correct config file path (exe directory when frozen, script directory otherwise)."""
        if getattr(sys, 'frozen', False):
            # For PyInstaller, config.json should be in exe directory
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(exe_dir, "config.json")
    
    @staticmethod
    def get_settings() -> Optional[dict]:
        """Get current settings, with API keys merged from secrets.json."""
        config_file = SettingsDialog.get_config_file_path()

        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception:
                config = {}
        strip_secrets(config)
        config.update(load_secrets())
        return config

    TAB_ORDER_KEY = "settings_tab_order"

    def save_tab_order(self, *args):
        """Persist the current tab order to config.json (fired when a tab is dragged)."""
        if getattr(self, '_restoring_tab_order', False):
            return
        order = [self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]
        config_file = SettingsDialog.get_config_file_path()
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception:
                config = {}
        strip_secrets(config)
        config[SettingsDialog.TAB_ORDER_KEY] = order
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"WARNING: could not save tab order: {e}")

    def restore_tab_order(self):
        """Apply the saved tab order (if any)."""
        config_file = SettingsDialog.get_config_file_path()
        saved = None
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f).get(SettingsDialog.TAB_ORDER_KEY)
            except Exception:
                saved = None
        if not isinstance(saved, list):
            return

        bar = self.tab_widget.tabBar()
        self._restoring_tab_order = True
        try:
            for target_index, label in enumerate(saved):
                for i in range(bar.count()):
                    if self.tab_widget.tabText(i) == label:
                        if i != target_index:
                            bar.moveTab(i, target_index)
                        break
        finally:
            self._restoring_tab_order = False


# ============================================================================
# Drag and Drop Text Edit
# ============================================================================

class SynchronizedTextEdit(QTextEdit):
    """QTextEdit with synchronized scrolling and modern block highlighting."""
    
    block_selected = pyqtSignal(int)  # Emits block index when selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.synchronized_widget = None
        self.block_positions = []  # Store start/end positions of each block
        self.current_block = -1
        self.highlighted_block = -1
        self.is_output_panel = False  # Track if this is output panel
        self.block_number_map = {}  # Map block number → block info
        self.shortened_blocks = set()  # Track which blocks were shortened (legacy)
        self.extended_blocks = set()  # Track which blocks were extended (legacy)
        self.shortened_blocks_long = set()  # Track blocks shortened for >90/line constraints
        self.shortened_blocks_cps = set()  # Track blocks shortened for CPS fallback
        self.time_extended_blocks = set()  # Track blocks with timestamp extension
        self.retranslated_blocks = set()  # Track blocks that were retranslated
        self.manual_blocks = set()  # Track blocks manually retranslated via right-click
        self.padding_offsets = {}  # Track visual padding for each block
        self.is_aligning = False  # Flag to prevent infinite alignment loops
        self.is_scrolling = False  # Flag to prevent recursive scrolling
        self.alignment_applied = False  # Flag to prevent re-alignment of already aligned content
        
        # Remove blue focus line
        self.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Enable mouse tracking for better interaction
        self.setMouseTracking(True)
        
        # Connect text change signal to update block positions and trigger alignment
        self.textChanged.connect(self.on_text_changed)
        
        # Set up timer for visual alignment updates
        self.alignment_timer = QTimer()
        self.alignment_timer.timeout.connect(self.update_visual_alignment)
        self.alignment_timer.setSingleShot(True)
        
        # Add timer for delayed alignment update
        self.delayed_alignment_timer = QTimer()
        self.delayed_alignment_timer.timeout.connect(self.delayed_alignment_update)
        self.delayed_alignment_timer.setSingleShot(True)
    
    def calculate_proportional_scroll(self, source_value: int, source_max: int, target_max: int) -> int:
        """Calculate proportional scroll position for target widget based on source widget."""
        if source_max <= 0:
            return 0
        
        # Calculate ratio of source scroll position (0.0 to 1.0)
        ratio = source_value / source_max
        
        # Apply ratio to target max value
        target_value = int(ratio * target_max)
        
        # Ensure within bounds
        return max(0, min(target_value, target_max))
    
    def set_synchronized_partner(self, partner):
        """Set the partner widget for synchronized scrolling."""
        self.synchronized_widget = partner
    
    def set_output_panel(self, is_output: bool):
        """Mark this as output panel to handle selection differently."""
        self.is_output_panel = is_output
    
    def set_shortened_blocks(self, shortened_indices: List[int]):
        """Mark which blocks were shortened for highlighting."""
        self.shortened_blocks = set(shortened_indices)
        self.update()  # Trigger repaint
    
    def set_extended_blocks(self, extended_indices: List[int]):
        """Mark which blocks were extended for highlighting."""
        self.extended_blocks = set(extended_indices)
        self.update()  # Trigger repaint
    
    def set_shortened_blocks_long(self, shortened_long_indices: List[int]):
        """Mark which blocks were shortened for >90/line constraints."""
        self.shortened_blocks_long = set(shortened_long_indices)
        self.update()  # Trigger repaint
    
    def set_shortened_blocks_cps(self, shortened_cps_indices: List[int]):
        """Mark which blocks were shortened for CPS fallback."""
        self.shortened_blocks_cps = set(shortened_cps_indices)
        self.update()  # Trigger repaint
    
    def set_time_extended_blocks(self, time_extended_indices: List[int]):
        """Mark which blocks had timestamp extension."""
        self.time_extended_blocks = set(time_extended_indices)
        self.update()  # Trigger repaint
    
    def set_retranslated_blocks(self, retranslated_indices: List[int]):
        """Mark which blocks were retranslated."""
        self.retranslated_blocks = set(retranslated_indices)
        self.update()  # Trigger repaint
    
    def set_manual_blocks(self, manual_indices: List[int]):
        """Mark which blocks were manually retranslated via right-click."""
        self.manual_blocks = set(manual_indices)
        self.update()  # Trigger repaint
    
    def wheelEvent(self, event):
        """Handle mouse wheel for synchronized scrolling."""
        # Always handle wheel event for scrolling
        super().wheelEvent(event)
        
        # Synchronize with partner
        if self.synchronized_widget and not self.is_scrolling:
            self.is_scrolling = True
            self.synchronized_widget.is_scrolling = True
            
            # Get the scroll delta and apply to partner
            delta = event.angleDelta().y()
            if delta != 0:
                # Calculate new scroll position for partner using proportional synchronization
                my_scrollbar = self.verticalScrollBar()
                partner_scrollbar = self.synchronized_widget.verticalScrollBar()
                
                if my_scrollbar and partner_scrollbar:
                    # Get current scroll values and max values
                    my_current = my_scrollbar.value()
                    my_max = my_scrollbar.maximum()
                    partner_max = partner_scrollbar.maximum()
                    
                    # Calculate new position for self first
                    new_my_value = my_current - delta // 8
                    new_my_value = max(0, min(new_my_value, my_max))
                    
                    # Calculate proportional position for partner
                    new_partner_value = self.calculate_proportional_scroll(new_my_value, my_max, partner_max)
                    
                    # Apply synchronized scroll
                    my_scrollbar.setValue(new_my_value)
                    partner_scrollbar.setValue(new_partner_value)
            
            # Clear flag after synchronization
            self.is_scrolling = False
            self.synchronized_widget.is_scrolling = False
    
    def scrollContentsBy(self, dx, dy):
        """Override scroll to synchronize with partner."""
        super().scrollContentsBy(dx, dy)
        if self.synchronized_widget and not self.is_scrolling:
            self.is_scrolling = True
            self.synchronized_widget.is_scrolling = True
            
            # Synchronize partner's scroll position using proportional synchronization
            try:
                my_scrollbar = self.verticalScrollBar()
                partner_scrollbar = self.synchronized_widget.verticalScrollBar()
                
                if my_scrollbar and partner_scrollbar:
                    # Get current scroll values and max values
                    my_current = my_scrollbar.value()
                    my_max = my_scrollbar.maximum()
                    partner_max = partner_scrollbar.maximum()
                    
                    # Calculate proportional position for partner
                    partner_value = self.calculate_proportional_scroll(my_current, my_max, partner_max)
                    
                    # Apply synchronized scroll
                    partner_scrollbar.setValue(partner_value)
            except:
                # Handle case where scrollbar doesn't exist yet
                pass
            
            # Clear flag after synchronization
            self.is_scrolling = False
            self.synchronized_widget.is_scrolling = False
    
    def update_block_positions(self):
        """Update the positions of SRT blocks in the text."""
        self.block_positions = []
        content = self.toPlainText()
        lines = content.split('\n')
        
        i = 0
        block_start = 0
        current_block_index = 0
        
        # Clear block number map
        self.block_number_map = {}
        
        while i < len(lines):
            # Skip empty lines
            if not lines[i].strip():
                i += 1
                continue
            
            # Check if this line is a block number
            try:
                block_num = int(lines[i].strip())
                i += 1
                
                # Skip timestamp
                if i < len(lines) and '-->' in lines[i]:
                    i += 1
                    
                    # Find all text lines until blank line
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i])
                        i += 1
                    
                    # Include all empty lines until next block number
                    # These empty lines are part of the current block
                    empty_start = i
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    
                    # Block ends at current position (before next block number)
                    # i is now at the next block number, so block_end = i
                    # This ensures the next block number is NOT included in current block
                    block_end = i
                    
                    block_info = {
                        'index': current_block_index,  # Use actual array index
                        'start': block_start,  # Always start at block number
                        'end': block_end,      # End at next block number or end of file
                        'block_num': block_num,
                        'text_lines': len(text_lines)
                    }
                    
                    self.block_positions.append(block_info)
                    self.block_number_map[block_num] = block_info  # Map block number → block info
                    
                    current_block_index += 1
                    block_start = i  # Next block starts here
                    
            except (ValueError, IndexError):
                i += 1
                block_start = i
    
    def mousePressEvent(self, event):
        """Handle mouse press for block selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Get cursor position
            cursor = self.cursorForPosition(event.pos())
            line_num = cursor.blockNumber()
            
            # Find which block this line belongs to
            for idx, block_info in enumerate(self.block_positions):
                # Use corrected block boundaries (start to end)
                if block_info['start'] <= line_num < block_info['end']:
                    # Get block number for synchronization
                    block_number = block_info['block_num']
                    

                    

                    self.highlighted_block = block_info['index']
                    self.block_selected.emit(block_info['index'])
                    
                    # Notify partner to highlight SAME BLOCK NUMBER
                    if self.synchronized_widget:

                        # Find block with same number in partner
                        partner_block = self.synchronized_widget.block_number_map.get(block_number)
                        if partner_block:
                            self.synchronized_widget.highlighted_block = partner_block['index']
                            self.synchronized_widget.update()
                        else:
                            pass  # Partner block not found
                    
                    # Update visual
                    self.update()
                    break
        
        super().mousePressEvent(event)
    
    def paintEvent(self, event):
        """Override paint to draw modern block highlighting and modification type indicators."""
        super().paintEvent(event)
        
        painter = QPainter(self.viewport())
        
        # Helper function to get block rectangle
        def get_block_rect(block_idx):
            if 0 <= block_idx < len(self.block_positions):
                block_info = self.block_positions[block_idx]
                
                # Calculate block rectangle
                start_cursor = QTextCursor(self.document())
                start_cursor.movePosition(QTextCursor.MoveOperation.Start)
                for _ in range(block_info['start']):
                    start_cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
                
                end_cursor = QTextCursor(self.document())
                end_cursor.movePosition(QTextCursor.MoveOperation.Start)
                for _ in range(block_info['end'] - 1):  # Stop before next block number
                    end_cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
                
                # Get visual rectangles
                start_rect = self.cursorRect(start_cursor)
                end_rect = self.cursorRect(end_cursor)
                
                return QRect(
                    0,
                    start_rect.top(),
                    self.viewport().width(),
                    end_rect.bottom() - start_rect.top()
                ), start_rect.top()
            return None, 0
        
        # Draw background overlays and labels with priority logic
        # Priority: MANUAL > TIME-extended > RETRANSLATED > CPS-shortened > SHORTENED(long)
        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)
        fm = QFontMetrics(font)
        
        for block_idx in range(len(self.block_positions)):
            block_rect, top_y = get_block_rect(block_idx)
            if not block_rect:
                continue
            
            # Single-decision logic with priority - avoid duplicate labels
            if block_idx in self.manual_blocks:
                # LIGHT YELLOW overlay for manual retranslated blocks (topmost priority)
                painter.fillRect(block_rect, QColor(255, 255, 150, 50))  # Light yellow with transparency
                # Draw "MANUAL" label
                painter.setPen(QPen(QColor(0, 0, 0), 2))  # Black text
                text_width = fm.horizontalAdvance("MANUAL")
                text_x = self.viewport().width() - text_width - 10
                text_y = top_y + 15
                painter.drawText(text_x, text_y, "MANUAL")
            elif block_idx in self.time_extended_blocks:
                # LIGHT GREEN overlay for time extended blocks
                painter.fillRect(block_rect, QColor(150, 255, 150, 30))  # Light green with transparency
                # Draw "TIME EXTENDED" label
                painter.setPen(QPen(QColor(0, 0, 0), 2))  # Black text
                text_width = fm.horizontalAdvance("TIME EXTENDED")
                text_x = self.viewport().width() - text_width - 10
                text_y = top_y + 15
                painter.drawText(text_x, text_y, "TIME EXTENDED")
            elif block_idx in self.retranslated_blocks:
                # LIGHT RED overlay for retranslated blocks (same as CPS-shortened styling)
                painter.fillRect(block_rect, QColor(255, 150, 150, 30))  # Light red with transparency
                # Draw "RETRANSLATED" label
                painter.setPen(QPen(QColor(0, 0, 0), 2))  # Black text
                text_width = fm.horizontalAdvance("RETRANSLATED")
                text_x = self.viewport().width() - text_width - 10
                text_y = top_y + 15
                painter.drawText(text_x, text_y, "RETRANSLATED")
            elif block_idx in self.shortened_blocks_cps:
                # LIGHT RED overlay for CPS shortened blocks
                painter.fillRect(block_rect, QColor(255, 150, 150, 30))  # Light red with transparency
                # Draw "RETRANSLATED" label
                painter.setPen(QPen(QColor(0, 0, 0), 2))  # Black text
                text_width = fm.horizontalAdvance("RETRANSLATED")
                text_x = self.viewport().width() - text_width - 10
                text_y = top_y + 15
                painter.drawText(text_x, text_y, "RETRANSLATED")
            elif block_idx in self.shortened_blocks_long:
                # DARK BLUE overlay for >90/line constraint shortened blocks
                painter.fillRect(block_rect, QColor(0, 50, 150, 25))  # Dark blue with transparency
                # Draw "RETRANSLATED" label
                painter.setPen(QPen(QColor(0, 0, 0), 2))  # Black text
                text_width = fm.horizontalAdvance("RETRANSLATED")
                text_x = self.viewport().width() - text_width - 10
                text_y = top_y + 15
                painter.drawText(text_x, text_y, "RETRANSLATED")
        
        # Draw highlighted block (if any)
        if self.highlighted_block >= 0 and self.highlighted_block < len(self.block_positions):
            block_info = self.block_positions[self.highlighted_block]
            
            # Calculate block rectangle
            start_cursor = QTextCursor(self.document())
            start_cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(block_info['start']):
                start_cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
            
            end_cursor = QTextCursor(self.document())
            end_cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(block_info['end'] - 1):  # Stop before next block number
                end_cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
            
            # Get visual rectangles
            start_rect = self.cursorRect(start_cursor)
            end_rect = self.cursorRect(end_cursor)
            
            # Draw highlight rectangle
            highlight_rect = QRect(
                0,
                start_rect.top(),
                self.viewport().width(),
                end_rect.bottom() - start_rect.top()
            )
            
            # Check if this block has a colored overlay
            colored = (self.highlighted_block in self.manual_blocks or 
                      self.highlighted_block in self.shortened_blocks_cps or
                      self.highlighted_block in self.time_extended_blocks or
                      self.highlighted_block in self.shortened_blocks_long or
                      self.highlighted_block in self.retranslated_blocks)
            
            if colored:
                # For colored blocks, draw ONLY outline (no fill) to avoid color mixing
                painter.setPen(QPen(QColor(64, 64, 64), 2))  # Dark gray pen
                painter.setBrush(Qt.BrushStyle.NoBrush)  # No fill
                painter.drawRect(highlight_rect)
            else:
                # For non-colored blocks, keep existing blue fill behavior
                painter.fillRect(highlight_rect, QColor(52, 152, 219, 30))  # Light blue with transparency
                pen = QPen(QColor(52, 152, 219, 100), 1)
                painter.setPen(pen)
                painter.drawRect(highlight_rect)
    
    def apply_content_alignment(self):
        """Apply content alignment by inserting empty lines to match partner widget."""
        if not self.synchronized_widget:
            return
        
        # Check if alignment has already been applied to prevent infinite loops
        if self.alignment_applied and self.synchronized_widget.alignment_applied:
            return
        
        # Get current content as lines
        lines = self.toPlainText().split('\n')
        
        # Calculate needed padding for each block
        padding_insertions = []  # List of (line_index, num_lines) to insert
        
        for my_block in self.block_positions:
            my_block_num = my_block['block_num']
            
            # Find corresponding block in partner by block number
            partner_block = self.synchronized_widget.block_number_map.get(my_block_num)
            
            if partner_block:
                my_lines = my_block['text_lines']
                partner_lines = partner_block['text_lines']
                
                # If this block needs padding, calculate where to insert empty lines
                if my_lines < partner_lines:
                    padding_needed = partner_lines - my_lines
                    
                    # Find separator line position (empty line after this block)
                    # The separator should be at block['end'] - 1
                    separator_line_idx = my_block['end'] - 1
                    
                    # Make sure we're at an empty line (the separator)
                    while separator_line_idx >= 0 and separator_line_idx < len(lines) and lines[separator_line_idx].strip():
                        separator_line_idx -= 1
                    
                    # Insert empty lines AFTER the separator line (before next block starts)
                    if separator_line_idx >= 0 and separator_line_idx < len(lines):
                        padding_insertions.append((separator_line_idx + 1, padding_needed))
        
        # Apply all insertions (in reverse order to maintain indices)
        if padding_insertions:
            # Sort by line index in descending order to maintain correct positions
            padding_insertions.sort(key=lambda x: x[0], reverse=True)
            
            for insert_line_idx, num_lines in padding_insertions:
                for i in range(num_lines):
                    lines.insert(insert_line_idx, '')
            
            # Update content with inserted empty lines
            new_content = '\n'.join(lines)
            
            # Only update if content actually changed
            if new_content != self.toPlainText():
                # Store cursor position and scroll position BEFORE content change
                cursor = self.textCursor()
                position = cursor.position()
                scroll_position = self.verticalScrollBar().value()
                
                # Update content
                self.setPlainText(new_content)
                
                # Restore cursor position if possible
                try:
                    cursor.setPosition(min(position, self.document().characterCount() - 1))
                    self.setTextCursor(cursor)
                except:
                    pass
                
                # Restore scroll position to prevent "return to beginning" behavior
                try:
                    self.verticalScrollBar().setValue(scroll_position)
                except:
                    pass
                
                # Update block positions after content change
                self.update_block_positions()
    
    def update_visual_alignment(self):
        """Update visual alignment by inserting empty lines to match partner widget."""
        if not self.synchronized_widget or self.is_aligning:
            return
        
        # Store scroll positions for both widgets BEFORE alignment
        my_scroll_pos = self.verticalScrollBar().value()
        partner_scroll_pos = self.synchronized_widget.verticalScrollBar().value()
        
        # Set flag to prevent infinite loops
        self.is_aligning = True
        self.synchronized_widget.is_aligning = True
        
        try:
            # Get block positions for both widgets
            self.update_block_positions()
            self.synchronized_widget.update_block_positions()
            
            # Apply content alignment by inserting empty lines
            self.apply_content_alignment()
            self.synchronized_widget.apply_content_alignment()
            
            # Restore scroll positions for both widgets AFTER alignment
            try:
                self.verticalScrollBar().setValue(my_scroll_pos)
                self.synchronized_widget.verticalScrollBar().setValue(partner_scroll_pos)
            except:
                pass
        finally:
            # Clear flag after alignment is complete
            self.is_aligning = False
            self.synchronized_widget.is_aligning = False
            
            # Mark alignment as applied to prevent re-alignment
            self.alignment_applied = True
            self.synchronized_widget.alignment_applied = True
    
    def calculate_visual_offsets(self):
        """Calculate visual padding offsets for each block based on partner widget."""
        if not self.synchronized_widget:
            return
        
        self.padding_offsets = {}  # block_index -> extra_lines_needed
        
        # Compare blocks by block number, not array index
        for my_block in self.block_positions:
            my_block_num = my_block['block_num']
            
            # Find corresponding block in partner by block number
            partner_block = self.synchronized_widget.block_number_map.get(my_block_num)
            
            if partner_block:
                my_lines = my_block['text_lines']
                partner_lines = partner_block['text_lines']
                
                # Calculate how many extra lines this block needs visually
                # If this block has fewer lines than partner, it needs padding
                if my_lines < partner_lines:
                    self.padding_offsets[my_block['index']] = partner_lines - my_lines
                else:
                    self.padding_offsets[my_block['index']] = 0
    

    
    def on_text_changed(self):
        """Handle text change events."""
        # Update block positions immediately
        self.update_block_positions()
        
        # Only trigger alignment if it hasn't been applied yet
        if not self.alignment_applied and self.synchronized_widget and not self.is_aligning:
            # Start delayed alignment update to avoid excessive calls during typing
            # Use longer delay to avoid conflicts with scroll synchronization
            self.delayed_alignment_timer.start(500)  # 500ms delay to avoid scroll conflicts
    
    def delayed_alignment_update(self):
        """Delayed alignment update to handle text changes."""
        if (self.synchronized_widget and not self.is_aligning and 
            not self.alignment_applied and not self.synchronized_widget.alignment_applied):
            self.update_visual_alignment()
    



class DragDropTextEdit(SynchronizedTextEdit):
    """QTextEdit with drag-and-drop support for SRT files."""
    
    file_dropped = pyqtSignal(str)  # Emits file path when file is dropped
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, e):
        """Handle drag enter event."""
        print(f"dragEnterEvent called: {e.mimeData().hasUrls()}")
        if e.mimeData().hasUrls():
            # Check if any of the URLs is a file
            urls = e.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile().lower()
                    print(f"Found file: {file_path}")
                    if file_path.endswith('.srt'):
                        print("Accepting drag")
                        e.accept()
                        return
        print("Ignoring drag")
        e.ignore()
    
    def dragMoveEvent(self, e):
        """Handle drag move event."""
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()
    
    def dropEvent(self, e):
        """Handle drop event."""
        print(f"dropEvent called: {e.mimeData().hasUrls()}")
        if e.mimeData().hasUrls():
            urls = e.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    print(f"Dropping file: {file_path}")
                    if file_path.lower().endswith('.srt'):
                        try:
                            with open(file_path, 'r', encoding='utf-8-sig') as f:
                                content = f.read()

                            # Normalize line endings and strip
                            content = content.replace("\r\n", "\n").replace("\r", "\n")
                            content = content.strip()
                            
                            # Normalize SRT endings to ensure exactly one empty line at end
                            parent = self.parent()
                            while parent and not isinstance(parent, MainWindow):
                                parent = parent.parent()
                            
                            if parent and hasattr(parent, 'normalize_srt_endings'):
                                content = parent.normalize_srt_endings(content)
                            
                            # Store original unprocessed content in parent
                            if parent and hasattr(parent, 'original_srt_content'):
                                parent.original_srt_content = content
                            
                            self.setPlainText(content)
                            self.file_dropped.emit(file_path)
                            

                            
                            e.accept()
                            print("File dropped successfully")
                            return
                        except Exception as ex:
                            print(f"Error loading dropped file: {ex}")
                            continue
            e.ignore()
        else:
            e.ignore()


# ============================================================================
# Single Block Retranslation Worker
# ============================================================================

class SingleBlockRetranslationWorker(QThread):
    """Worker thread for retranslating a single SRT block."""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(object, object, object, object)  # block, shortened_long, shortened_cps, time_extended
    
    def __init__(self, original_block: SrtBlock, provider: str, api_key: str, model: str, all_blocks: List[SrtBlock], referer: str = None, app_title: str = None):
        super().__init__()
        self.original_block = original_block
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.all_blocks = all_blocks
        self.referer = referer
        self.app_title = app_title
    
    def run(self):
        """Execute single block retranslation with full pipeline."""
        try:
            self.progress.emit(f"Translating block {self.original_block.index}...")
            
            # Rebuild original text for translation
            original_text = ' '.join(self.original_block.original_text_lines)
            
            # Create translator with manual mode enabled
            translator = Translator(
                provider=self.provider,
                api_key=self.api_key,
                model=self.model,
                referer=self.referer,
                app_title=self.app_title,
                is_manual=True
            )
            
            # Step a: Translate the single block using existing translation method
            translations = translator.translate_blocks([original_text])
            translated_text = translations[0] if translations else original_text
            
            # Step b: Enforce hard limit for manual retranslation (max 90, target 77-80)
            current_len = len(translated_text.replace('\n', ''))
            if current_len > 80:
                # Shorten to target range first
                target_chars = 77 if current_len > 90 else 80
                target_chars = max(10, min(target_chars, 85))
                translated_text = translator._shorten_for_cps(translated_text, target_chars, self.original_block.duration_ms)
            
            # Apply hard limit 90 if still too long
            current_len = len(translated_text.replace('\n', ''))
            if current_len > 90:
                # Force hard limit using shortening helper
                translated_text = translator._shorten_for_cps(translated_text, 90, self.original_block.duration_ms)
            
            # Step c: Apply standard long text shortening if still needed
            shortened_long = False
            shortened_long_indices = []
            
            # Validate line constraints and shorten if needed
            is_valid, details = translator.validate_line_constraints(translated_text)
            if not is_valid or len(translated_text) > 90:
                shortened_texts, shortened_indices = translator.shorten_long_translations([translated_text])
                if shortened_indices:
                    translated_text = shortened_texts[0]
                    shortened_long = True
                    shortened_long_indices = [0]  # Index 0 for this single block
            
            # Step c: Create updated block and apply translation
            updated_block = SrtBlock(
                index=self.original_block.index,
                timestamp=self.original_block.timestamp,
                original_text_lines=self.original_block.original_text_lines,
                translated_text=translated_text,
                start_time_ms=self.original_block.start_time_ms,
                end_time_ms=self.original_block.end_time_ms,
                duration_ms=self.original_block.duration_ms
            )
            
            # Step d: Recalculate CPS
            updated_block.characters_per_second = SrtParser.calculate_characters_per_second(updated_block)
            
            # Step e: Apply CPS adjustment if needed (>19.5 CPS)
            shortened_cps = False
            time_extended = False
            
            if updated_block.characters_per_second > 19.5:
                self.progress.emit(f"Adjusting high CPS ({updated_block.characters_per_second:.1f})...")
                
                # Try time extension first
                next_block = None
                for i, block in enumerate(self.all_blocks):
                    if block.index > updated_block.index:
                        next_block = block
                        break
                
                can_extend, new_end_time = SrtParser.can_extend_timestamp(updated_block, next_block)
                if can_extend:
                    SrtParser.extend_timestamp(updated_block, new_end_time, "Extended to achieve target CPS")
                    time_extended = True
                else:
                    # Apply CPS shortening (same logic as full pipeline)
                    target_chars = int(15.5 * (updated_block.duration_ms / 1000))
                    target_chars = max(10, min(target_chars, 85))
                    shortened_text = translator._shorten_for_cps(original_text, target_chars, updated_block.duration_ms)
                    updated_block.translated_text = shortened_text
                    updated_block.characters_per_second = SrtParser.calculate_characters_per_second(updated_block)
                    shortened_cps = True
                    updated_block.was_shortened = True
            
            # Step f: Apply line splitting
            updated_block.translated_text = LineSplitter.split_text(updated_block.translated_text)
            
            # Step g: Recalculate CPS after line splitting
            updated_block.characters_per_second = SrtParser.calculate_characters_per_second(updated_block)
            
            # Step h: Enforce hard limit again after line splitting
            final_len = len(updated_block.translated_text.replace('\n', ''))
            if final_len > 90:
                updated_block.translated_text = translator._shorten_for_cps(updated_block.translated_text, 90, self.original_block.duration_ms)
                updated_block.characters_per_second = SrtParser.calculate_characters_per_second(updated_block)
            
            # Step h: Mark as retranslated
            updated_block.was_retranslated = True
            
            self.progress.emit(f"Block {self.original_block.index} retranslation complete!")
            self.finished.emit(updated_block, shortened_long, shortened_cps, time_extended)
            
        except Exception as e:
            self.progress.emit(f"Error retranslating block: {e}")
            self.finished.emit(None, None, None, None)

# ============================================================================
# Custom Delegate (QTextEdit editor for multi-line cells)
# ============================================================================

class _MultiLineDelegate(QStyledItemDelegate):
    """Uses QTextEdit so multi-line text stays multi-line during editing."""
    def createEditor(self, parent, option, index):
        editor = QTextEdit(parent)
        editor.setFrameStyle(0)
        editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        return editor

    def setEditorData(self, editor, index):
        text = index.data()
        editor.setPlainText(text)
        # Place cursor at end — do NOT select all
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)

    def setModelData(self, editor, model, index):
        text = editor.toPlainText()
        model.setData(index, text)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
    
    def paint(self, painter, option, index):
        from PyQt6.QtWidgets import QStyleOptionViewItem, QStyle
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QBrush
        
        # Check if cell has custom background by inspecting the brush
        bg_data = index.data(Qt.ItemDataRole.BackgroundRole)
        
        # Determine if this is a custom background or default
        # Default backgrounds have NoBrush style, custom ones have a solid/filled pattern
        has_custom_bg = False
        if bg_data is not None and isinstance(bg_data, QBrush):
            has_custom_bg = bg_data.style() != Qt.BrushStyle.NoBrush
        
        # Create a clean option without hover state for cells without custom background
        clean_option = option
        if not has_custom_bg:
            if hasattr(option, 'state') and option.state & QStyle.StateFlag.State_MouseOver:
                clean_state = option.state & ~QStyle.StateFlag.State_MouseOver
                clean_option = QStyleOptionViewItem(option)
                clean_option.state = clean_state
        
        super(_MultiLineDelegate, self).paint(painter, clean_option, index)

# ============================================================================
# Main Window
# ============================================================================

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        import time
        t0 = time.time()
        super().__init__()
        t1 = time.time()
        print(f"[DEBUG STARTUP] super().__init__: {t1-t0:.3f}s")
        
        self.setWindowTitle(self.center_title_text("SRT Subtitle Translator"))
        self.resize(1200, 700)
        # Create a transparent icon to remove default
        transparent_pixmap = QPixmap(1, 1)
        transparent_pixmap.fill(Qt.GlobalColor.transparent)
        self.setWindowIcon(QIcon(transparent_pixmap))
        # Try to center title using window flags
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowTitleHint)
        
        self.worker = None
        self.single_block_worker = None  # Track single block retranslation worker
        self.last_loaded_file = None  # Track last loaded file for save dialog
        self.base_window_title = "SRT Subtitle Translator"  # Store base title
        self.line_splitting_enabled = False  # Track line splitting toggle state
        self.original_srt_content = ""  # Buffer to preserve original unprocessed content
        self.blocks_with_cps = None  # Store blocks with CPS data for status bar enhancement
        self.original_blocks = None  # Store original parsed blocks for retranslation
        MainWindow.current_config = None  # Shared config to avoid reloading from disk
        self.always_on_top = True  # Default always on top
        self.setup_ui()
        
        import time
        t_before_geo = time.time()
        self.load_window_geometry()
        t_after_geo = time.time()
        print(f"[DEBUG STARTUP] load_window_geometry: {t_after_geo - t_before_geo:.3f}s")
        
        # Apply custom window flags for better title display
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowStaysOnTopHint)
        
        # Enable drag and drop on main window
        self.setAcceptDrops(True)
        
        t_end = time.time()
        print(f"[DEBUG STARTUP] __init__ total: {t_end - t_before_geo:.3f}s")
    
    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        print("[DEBUG DRAG] dragEnterEvent")
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.srt'):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drop event."""
        print("[DEBUG DRAG] dropEvent")
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    print(f"[DEBUG DRAG] Dropped file: {file_path}")
                    if file_path.lower().endswith('.srt'):
                        self.load_srt_file(file_path)
                        event.acceptProposedAction()
                        return
        event.ignore()
    
    def setup_ui(self):
        """Create main window UI."""
        import time
        t0 = time.time()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Top control panel with modern design
        control_panel = QFrame()
        control_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        control_panel.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin: 5px;
                padding: 10px;
            }
        """)
        
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)
        
        # Button row with modern styling
        button_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("📁 Load SRT")
        self.save_input_btn = QPushButton("💾 Save Original")
        self.save_btn = QPushButton("💾 Save Translated")
        self.save_btn.setFixedWidth(160)  # Fixed width to accommodate both "Save Translated" and "Save Line Split"
        self.settings_btn = QPushButton("⚙️ Settings")
        self.line_splitting_toggle = QPushButton("✂️ Line Split: OFF")
        self.restart_btn = QPushButton("🔄 Restart")
        
        # Modern button styling
        button_style = """
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
        """
        
        # Restart button styling (different color to distinguish)
        restart_style = """
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
        """
        
        # Line splitting toggle button styling (OFF state - gray)
        toggle_off_style = """
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
        """
        
        # Line splitting toggle button styling (ON state - green)
        toggle_on_style = """
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
        """
        
        self.load_btn.setStyleSheet(button_style)
        self.save_input_btn.setStyleSheet(button_style)
        self.save_btn.setStyleSheet(button_style)
        self.settings_btn.setStyleSheet(button_style)
        self.line_splitting_toggle.setStyleSheet(toggle_off_style)
        self.restart_btn.setStyleSheet(restart_style)
        
        self.load_btn.clicked.connect(self.load_srt)
        self.save_input_btn.clicked.connect(self.save_original_srt)
        self.save_btn.clicked.connect(self.save_srt)
        self.settings_btn.clicked.connect(self.open_settings)
        self.line_splitting_toggle.clicked.connect(self.toggle_line_splitting)
        self.restart_btn.clicked.connect(self.restart_application)
        
        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.save_input_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.settings_btn)
        button_layout.addWidget(self.line_splitting_toggle)
        button_layout.addStretch()
        button_layout.addWidget(self.restart_btn)
        
        control_layout.addLayout(button_layout)
        
        # Provider and model selection with better alignment
        provider_layout = QHBoxLayout()
        provider_layout.setSpacing(10)
        
        # OpenRouter model selection (hardcoded as default provider)
        self.openrouter_model_label = QLabel("OpenRouter Model:")
        self.openrouter_model_label.setStyleSheet("font-weight: 600; color: #495057;")
        self.openrouter_model_label.setMinimumWidth(120)
        
        self.openrouter_model_combo = QComboBox()
        self.openrouter_model_combo.setEditable(False)
        self.openrouter_model_combo.setMinimumWidth(200)
        
        # Modern combobox styling
        combo_style = """
            QComboBox {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #80bdff;
            }
            QComboBox:focus {
                border-color: #007bff;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #6c757d;
                margin-right: 5px;
            }
            QComboBox:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
        """
        
        self.openrouter_model_combo.setStyleSheet(combo_style)
        
        # Load fixed models list
        self.load_fixed_openrouter_models()
        
        # Add to horizontal layout - all widgets flow naturally
        provider_layout.addWidget(self.openrouter_model_label)
        provider_layout.addWidget(self.openrouter_model_combo)
        
        # Always on top checkbox
        self.always_on_top_checkbox = QCheckBox("Always on top")
        self.always_on_top_checkbox.setChecked(True)  # Default to on
        self.always_on_top_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: 600;
                color: #495057;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #ced4da;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #007bff;
                border-color: #007bff;
            }
            QCheckBox::indicator:checked:after {
                color: white;
                font-size: 12px;
            }
        """)
        self.always_on_top_checkbox.stateChanged.connect(self.on_always_on_top_changed)
        provider_layout.addWidget(self.always_on_top_checkbox)
        
        # Add stretch to push balance elements to the right
        provider_layout.addStretch()
        
        # Add credit balance label for OpenRouter
        self.credit_balance_label = QLabel("Balance: $0.00")
        self.credit_balance_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-weight: 600;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: right;
                min-width: 120px;
            }
        """)
        
        # Add refresh button for credit balance
        self.refresh_balance_button = QPushButton("💰")
        self.refresh_balance_button.setToolTip("Refresh credit balance")
        self.refresh_balance_button.setFixedSize(30, 30)
        self.refresh_balance_button.clicked.connect(self.fetch_credit_balance)
        self.refresh_balance_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117a8b;
            }
        """)
        
        provider_layout.addWidget(self.credit_balance_label)
        provider_layout.addWidget(self.refresh_balance_button)
        
        control_layout.addLayout(provider_layout)
        
        main_layout.addWidget(control_panel)
        
        # Set default model to first in fixed list
        self.openrouter_model_combo.setCurrentIndex(0)
        
        # Fetch credit balance on startup
        self.fetch_credit_balance()
        
        # Tab widget for Translation and Debug
        self.tab_widget = QTabWidget()
        
        # === TRANSLATION TAB ===
        translation_tab = QWidget()
        translation_layout = QVBoxLayout()
        translation_layout.setContentsMargins(6, 6, 6, 6)
        translation_layout.setSpacing(4)
        translation_tab.setLayout(translation_layout)

        # ── Hidden input widget (stores content, handles drag-drop) ─────
        self.input_text = DragDropTextEdit()
        self.input_text.setVisible(False)
        self.input_text.file_dropped.connect(self.handle_file_dropped)
        self.input_text.set_output_panel(False)
        self.input_text.textChanged.connect(self.on_input_text_changed)

        # ── Subtitle table (main view, fills all space) ────────────────
        self.output_label = QLabel("Subtitles")
        self.output_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        translation_layout.addWidget(self.output_label)

        self.subtitle_table = QTableWidget()
        self.setup_subtitle_table()
        translation_layout.addWidget(self.subtitle_table, 1)   # stretch=1 → fills space

        # Connect table row selection to status bar
        self.subtitle_table.selectionModel().selectionChanged.connect(self.on_row_selected)

        # Storage for current blocks list
        self.blocks = []

        # Hidden QTextEdit that still receives rebuilt SRT for save operations
        self.output_text = QTextEdit()
        self.output_text.setVisible(False)

        # Context menu on subtitle table (right-click → retranslate)
        self.subtitle_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.subtitle_table.customContextMenuRequested.connect(self.show_table_context_menu)

        # Track rows that were manually retranslated (for row highlighting)
        self._retranslated_rows = set()

        # Translate button — deliberately prominent so it is easy to find
        self.translate_btn = QPushButton("▶  Translate")
        self.translate_btn.setMinimumHeight(48)
        self.translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.translate_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 17px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1765cc; }
            QPushButton:pressed { background-color: #1253a8; }
            QPushButton:disabled { background-color: #a9c7f0; color: #f0f4fb; }
        """)
        self.translate_btn.clicked.connect(self.start_translation)

        translate_row = QHBoxLayout()
        translate_row.setContentsMargins(16, 6, 16, 10)
        translate_row.addWidget(self.translate_btn)
        main_layout.addLayout(translate_row)
        main_layout.addWidget(translation_tab)

        # Status bar with progress bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Progress bar in status bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { border: 1px solid #ccc; border-radius: 3px; text-align: center; } QProgressBar::chunk { background-color: #4CAF50; }")
        
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.showMessage("Ready")
    
    # ----------------------------------------------------------------
    # Table helpers
    # ----------------------------------------------------------------

    @staticmethod
    def _normalize_lines(text: str, max_lines: int = 2) -> List[str]:
        """Split text by newline and return exactly *max_lines* items."""
        if not text:
            return [""] * max_lines
        parts = text.split("\n")
        result = [p.strip() for p in parts[:max_lines]]
        while len(result) < max_lines:
            result.append("")
        return result

    def log_debug(self, message: str):
        """Log message to console."""
        print(f"[DEBUG] {message}")

    def setup_subtitle_table(self):
        """Configure the QTableWidget for 7-column subtitle display."""
        COLUMNS = ["#", "Start", "End", "", "ORIGINAL", "TRANSLATION", "CPS"]
        self.subtitle_table.setColumnCount(len(COLUMNS))
        self.subtitle_table.setHorizontalHeaderLabels(COLUMNS)

        # Selection
        self.subtitle_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.subtitle_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.subtitle_table.setAlternatingRowColors(True)
        self.subtitle_table.verticalHeader().setVisible(False)

        # Double-click to edit (single click selects, right click opens menu)
        self.subtitle_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
        )
 
        # Custom delegate: don't select-all when editor opens
        # Multi-line QTextEdit delegate for text columns only
        _ml = _MultiLineDelegate(self.subtitle_table)
        self.subtitle_table.setItemDelegateForColumn(4, _ml)  # ORIGINAL
        self.subtitle_table.setItemDelegateForColumn(5, _ml)  # TRANSLATION

        # Word wrap inside cells (no truncation)
        self.subtitle_table.setWordWrap(True)
        self.subtitle_table.setTextElideMode(Qt.TextElideMode.ElideNone)

        # Column sizing: #, Start, End, spacer, CPS → content;  Original, Translation → stretch
        header = self.subtitle_table.horizontalHeader()
        header.setStretchLastSection(False)
        from PyQt6.QtWidgets import QHeaderView as _QHV
        for col in [0, 1, 2, 3, 6]:  # #, Start, End, spacer, CPS
            header.setSectionResizeMode(col, _QHV.ResizeMode.ResizeToContents)
        for col in [4, 5]:  # ORIGINAL, TRANSLATION
            header.setSectionResizeMode(col, _QHV.ResizeMode.Stretch)

        # Generous minimum column widths
        self.subtitle_table.setColumnWidth(0, 40)   # #
        self.subtitle_table.setColumnWidth(3, 15)  # spacer

        # Visual style - NO custom background so cell colors work
        self.subtitle_table.setAlternatingRowColors(False)
        self.subtitle_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
                selection-background-color: #cce5ff;
                selection-color: #000;
            }
            QTableWidget::item:selected {
                background-color: #cce5ff;
                color: #000;
            }

            QHeaderView::section {
                background-color: #f1f3f5;
                padding: 6px 8px;
                border: 1px solid #dee2e6;
                font-weight: 600;
                font-size: 12px;
            }
            /* Add extra space after End column (index 2) */
            QHeaderView::section:2 {
                padding-right: 20px;
            }
            QTableWidget::item:column(2) {
                padding-right: 15px;
            }
        """)
        
        # Disable hover tracking entirely
        self.subtitle_table.setMouseTracking(False)
        self.subtitle_table.viewport().setMouseTracking(False)

        # Smooth scrolling
        self.subtitle_table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.subtitle_table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)

        # Fixed row height for 2 lines - use reliable pixel value
        # 54px is enough for 2 lines of 13px font with padding
        self.subtitle_table.verticalHeader().setDefaultSectionSize(54)
        # Disable automatic size calculation to prevent expensive recalculations
        self.subtitle_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        # Guard so on_item_changed doesn't fire during populate/update
        self._table_loading = False

        # Connect signals
        self.subtitle_table.itemChanged.connect(self.on_item_changed)

    def populate_table(self, blocks: List[SrtBlock]):
        """Fill the subtitle table from a list of SrtBlock objects (6 columns)."""
        self._table_loading = True
        self._retranslated_rows.clear()

        # Calculate CPS for all blocks before populating
        SrtParser.calculate_cps_for_all_blocks(blocks)

        # Don't disable updates - needed for colors to show
        self.subtitle_table.setRowCount(len(blocks))

        for row, block in enumerate(blocks):
            try:
                start_ts, end_ts = block.timestamp.split(" --> ")
            except ValueError:
                start_ts = block.timestamp
                end_ts = ""

            orig_text = "\n".join(block.original_text_lines)
            trans_text = block.translated_text if block.translated_text else ""

            # Column order: #, Start, End, (spacer), Original, Translation, CPS
            cells = [
                str(block.index),
                start_ts.strip(),
                end_ts.strip(),
                "",  # spacer
                orig_text,
                trans_text,
                f"{block.characters_per_second:.1f}",
            ]

            # CPS highlighting and modified block highlighting
            cps = block.characters_per_second
            was_shortened = getattr(block, 'was_shortened', False)
            timestamp_extended = getattr(block, 'timestamp_extended', False)
            is_modified = was_shortened or timestamp_extended

            for col, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if col < 3 or col == 6:  # #, Start, End, CPS → centered, non-editable
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                    )
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                elif col == 3:  # spacer → minimal width
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                else:  # Original, Translation → left, editable
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    )
                
                # Apply highlighting - modified blocks get row highlighting
                if is_modified:
                    if was_shortened and timestamp_extended:
                        item.setData(Qt.ItemDataRole.BackgroundRole, QColor(235, 235, 245))
                    elif was_shortened:
                        item.setData(Qt.ItemDataRole.BackgroundRole, QColor(235, 245, 250))
                    elif timestamp_extended:
                        item.setData(Qt.ItemDataRole.BackgroundRole, QColor(235, 250, 235))
                
                # CPS highlighting - ONLY for CPS column (col 6)
                if col == 6 and cps >= 19:
                    # Pastel red for high CPS
                    item.setData(Qt.ItemDataRole.BackgroundRole, QColor(255, 220, 220))
                
                self.subtitle_table.setItem(row, col, item)

        # Fixed row height already set in setup_subtitle_table()
        self.subtitle_table.setWordWrap(True)

        self.subtitle_table.viewport().update()  # Force visual update
        self._validate_table(blocks)
        self._table_loading = False

    def update_table_row(self, row: int, block: SrtBlock):
        """Update a single row in the table without refreshing the rest."""
        if row < 0 or row >= self.subtitle_table.rowCount():
            print(f"[DEBUG] ERROR: update_table_row row={row} out of range")
            return

        self._table_loading = True
        print(f"[DEBUG] Updating single row {row} (block {block.index})")

        try:
            start_ts, end_ts = block.timestamp.split(" --> ")
        except ValueError:
            start_ts = block.timestamp
            end_ts = ""

        orig_text = "\n".join(block.original_text_lines)
        trans_text = block.translated_text if block.translated_text else ""

        # Column order: #, Start, End, (spacer), Original, Translation, CPS
        cells = [
            str(block.index),
            start_ts.strip(),
            end_ts.strip(),
            "",  # spacer
            orig_text,
            trans_text,
            f"{block.characters_per_second:.1f}",
        ]

        # CPS highlighting and modified block highlighting
        cps = block.characters_per_second
        is_modified = getattr(block, 'was_shortened', False) or getattr(block, 'timestamp_extended', False)

        for col, value in enumerate(cells):
            item = QTableWidgetItem(value)
            if col < 3 or col == 6:  # #, Start, End, CPS → centered, non-editable
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            else:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
            
            # Apply highlighting - modified blocks get blue, CPS >= 19 gets red (only on CPS column)
            if col == 4 or col == 5:  # Original, Translation
                if is_modified:
                    item.setBackground(QColor(173, 216, 230))  # Light blue for modified
            elif col == 6 and cps >= 19:  # CPS column
                item.setBackground(QColor(255, 220, 220))  # Pastel red for high CPS
            
            self.subtitle_table.setItem(row, col, item)

        # Highlight retranslated rows with a warm tint (overrides CPS if both apply)
        self._retranslated_rows.add(row)
        self._apply_row_highlight(row)

        # Fixed row height already set in setup_subtitle_table()
        self._table_loading = False
        print(f"[DEBUG] Row {row} updated successfully")

    def _apply_row_highlight(self, row: int):
        """Apply a tinted background to a retranslated row, but preserve CPS red if CPS >= 19."""
        _HIGHLIGHT = QColor(255, 249, 196)  # warm yellow
        cps = 0
        if row < len(self.blocks):
            cps = self.blocks[row].characters_per_second
        
        for col in range(self.subtitle_table.columnCount()):
            # Skip CPS column - preserve its red highlighting if CPS >= 19
            if col == 6 and cps >= 19:
                continue
            item = self.subtitle_table.item(row, col)
            if item:
                item.setBackground(_HIGHLIGHT)

    def on_item_changed(self, item: QTableWidgetItem):
        """Sync edited cell back into the underlying SrtBlock."""
        if getattr(self, '_table_loading', False):
            return
        if not self.blocks:
            return

        row = item.row()
        col = item.column()
        if row >= len(self.blocks):
            return

        text = item.text()
        block = self.blocks[row]

        # Columns: 0=#, 1=Start, 2=End, 3=spacer, 4=ORIGINAL, 5=TRANSLATION, 6=CPS
        if col == 4:  # ORIGINAL
            block.original_text_lines = text.split("\n")
            print(f"[DEBUG] Edited original block {block.index}: {block.original_text_lines}")
        elif col == 5:  # TRANSLATION
            block.translated_text = text
            print(f"[DEBUG] Edited translation block {block.index}")

    def handle_item_click(self, item: QTableWidgetItem):
        """No-op — editing triggered by DoubleClicked."""
        pass

    def on_row_selected(self):
        """Update status bar when a table row is selected."""
        indexes = self.subtitle_table.selectionModel().selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        if not hasattr(self, 'blocks') or row >= len(self.blocks):
            return

        block = self.blocks[row]
        chars = len(block.translated_text.replace("\n", "")) if block.translated_text else 0
        cps = block.characters_per_second

        if cps > 0:
            status = f"Block {block.index} | {chars} chars | {cps:.1f} c/s"
        else:
            status = f"Block {block.index} | {chars} chars"

        self.status_bar.showMessage(status)
        print(f"[DEBUG] Row selected: index={row} block={block.index}")

    def _toggle_input_section(self):
        """No-op — input panel removed."""
        pass

    def _validate_table(self, blocks: List[SrtBlock]):
        """Self-check: verify table integrity after population."""
        errors = []

        if self.subtitle_table.columnCount() != 7:
            errors.append(
                f"Column count is {self.subtitle_table.columnCount()}, expected 7"
            )

        if self.subtitle_table.rowCount() != len(blocks):
            errors.append(
                f"Row count {self.subtitle_table.rowCount()} != blocks {len(blocks)}"
            )

        for row in range(self.subtitle_table.rowCount()):
            for col in range(self.subtitle_table.columnCount()):
                item = self.subtitle_table.item(row, col)
                if item is None:
                    errors.append(f"NULL cell at row={row} col={col}")

        if errors:
            for err in errors:
                print(f"[DEBUG] VALIDATION ERROR: {err}")
        else:
            print(f"[DEBUG] Validation OK: {self.subtitle_table.rowCount()} rows x "
                  f"{self.subtitle_table.columnCount()} cols")

    def show_table_context_menu(self, pos):
        """Right-click context menu on the subtitle table."""
        row = self.subtitle_table.rowAt(pos.y())
        if row < 0:
            return

        print(f"[DEBUG] Right-click on table row {row}")
        self.subtitle_table.selectRow(row)

        menu = QMenu(self)
        action = QAction("Retranslate this block", self)
        action.triggered.connect(lambda: self.retranslate_table_row(row))

        if (
            hasattr(self, "single_block_worker")
            and self.single_block_worker
            and self.single_block_worker.isRunning()
        ):
            action.setEnabled(False)

        menu.addAction(action)
        menu.exec(self.subtitle_table.viewport().mapToGlobal(pos))

    def retranslate_table_row(self, row: int):
        """Start retranslation for the block at *row* in the table."""
        if not self.original_blocks or row >= len(self.original_blocks):
            print(f"[DEBUG] ERROR: invalid row {row} for retranslation")
            return

        self.current_selected_block_index = row
        print(f"[DEBUG] Retranslate requested for row {row}")

        # Reuse existing retranslation logic
        self.retranslate_selected_block()

    def load_fixed_openrouter_models(self):
        """Load OpenRouter models list from config/settings only."""
        settings = SettingsDialog.get_settings()
        models = []
        
        if settings and 'openrouter_models' in settings:
            models = settings['openrouter_models']
        
        self.openrouter_model_combo.clear()
        if models:
            self.openrouter_model_combo.addItems(models)
            self.openrouter_model_combo.setCurrentIndex(0)
    
    def fetch_credit_balance(self):
        """Fetch OpenRouter credit balance."""
        settings = SettingsDialog.get_settings()
        api_key = settings.get('openrouter_api_key', '') if settings else ''
        
        # Clean API key - remove non-breaking hyphens and other problematic characters
        if api_key:
            # Replace non-breaking hyphen with regular hyphen
            api_key = api_key.replace('\u2011', '-').replace('\u2012', '-').replace('\u2013', '-').replace('\u2014', '-')
            # Remove any other non-ASCII characters except for the key itself
            api_key = ''.join(char for char in api_key if ord(char) < 128 or char in 'sk-or-')
        
        if not api_key:
            self.credit_balance_label.setText("Balance: No API key")
            self.credit_balance_label.setStyleSheet("""
                QLabel {
                    color: #dc3545;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    text-align: right;
                    min-width: 120px;
                }
            """)
            return
        
        try:
            # Clean API key - replace non-breaking hyphens with regular hyphens
            clean_api_key = api_key.replace('\u2011', '-').replace('\u2012', '-').replace('\u2013', '-').replace('\u2014', '-')
            
            # Fetch credit balance from OpenRouter API
            response = requests.get(
                "https://openrouter.ai/api/v1/credits",
                headers={
                    "Authorization": f"Bearer {clean_api_key}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            response.raise_for_status()
            balance_data = response.json()
            
            # Extract balance information from correct structure
            # Response format: {"data": {"total_credits": 100.5, "total_usage": 25.75}}
            data = balance_data.get('data', {})
            total_credits = data.get('total_credits', 0)
            total_usage = data.get('total_usage', 0)
            
            # Calculate remaining balance
            try:
                remaining_balance = total_credits - total_usage
                
                if isinstance(remaining_balance, (int, float)):
                    balance_str = f"Balance: ${remaining_balance:.2f}"
                    color = "#28a745" if remaining_balance > 1 else "#ffc107" if remaining_balance > 0.1 else "#dc3545"
                else:
                    balance_str = "Balance: Unknown"
                    color = "#6c757d"
            except Exception as e:
                print(f"Balance calculation error: {e}")
                balance_str = "Balance: Error"
                color = "#dc3545"
            
            self.credit_balance_label.setText(balance_str)
            self.credit_balance_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-weight: 600;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    text-align: right;
                    min-width: 120px;
                }}
            """)
            
        except requests.exceptions.RequestException as e:
            print(f"Balance request error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                if status_code == 401:
                    self.credit_balance_label.setText("Balance: Invalid API Key")
                elif status_code == 403:
                    self.credit_balance_label.setText("Balance: Forbidden")
                else:
                    self.credit_balance_label.setText(f"Balance: HTTP {status_code}")
            else:
                self.credit_balance_label.setText("Balance: Network Error")
            self.credit_balance_label.setStyleSheet("""
                QLabel {
                    color: #dc3545;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    text-align: right;
                    min-width: 120px;
                }
            """)
        except Exception as e:
            print(f"Balance general error: {e}")
            self.credit_balance_label.setText("Balance: Error")
            self.credit_balance_label.setStyleSheet("""
                QLabel {
                    color: #dc3545;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    text-align: right;
                    min-width: 120px;
                }
            """)
    
    def on_provider_changed(self, provider: str):
        """Handle provider selection change."""
        if provider == "OpenRouter":
            self.openrouter_model_label.show()
            self.openrouter_model_combo.show()
            self.credit_balance_label.show()
            self.refresh_balance_button.show()
            self.fetch_credit_balance()
        else:
            self.openrouter_model_label.hide()
            self.openrouter_model_combo.hide()
            self.credit_balance_label.hide()
            self.refresh_balance_button.hide()
    
    def on_always_on_top_changed(self, state):
        """Handle always on top checkbox change."""
        try:
            import ctypes
            from PyQt6.QtWidgets import QApplication
            
            SWP_NOMOVE = 0x0001
            SWP_NOSIZE = 0x0001
            GWL_EXSTYLE = -20
            WS_EX_TOPMOST = 0x00000008
            
            SetWindowLongW = ctypes.windll.user32.SetWindowLongW
            GetWindowLongW = ctypes.windll.user32.GetWindowLongW
            SetWindowPos = ctypes.windll.user32.SetWindowPos
            
            hwnd = int(self.winId())
            
            is_checked = bool(int(state))
            
            if is_checked:
                current_style = GetWindowLongW(hwnd, GWL_EXSTYLE)
                new_style = current_style | WS_EX_TOPMOST
                SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
                SetWindowPos(hwnd, -1, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
            else:
                current_style = GetWindowLongW(hwnd, GWL_EXSTYLE)
                new_style = current_style & ~WS_EX_TOPMOST
                SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
                SetWindowPos(hwnd, -2, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
            
            # Force Qt to refresh window state
            QApplication.processEvents()
            
            # Update Qt window flags to match
            if is_checked:
                self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            else:
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
            
            self.show()
            self.raise_()
            self.activateWindow()
            
        except Exception as e:
            print(f"Error: {e}")
        
        self.always_on_top = bool(int(state))
    
    def handle_file_dropped(self, file_path: str):
        """Handle file dropped onto input text area."""
        self.last_loaded_file = file_path
        self.update_window_title(file_path)
        self.status_bar.showMessage(f"Loaded: {os.path.basename(file_path)}")
    
    def on_input_text_changed(self):
        """Handle manual text changes in input area."""
        # Update original content when user manually changes the input
        # This ensures that subsequent operations work on the latest content
        current_content = self.input_text.toPlainText()
        if current_content.strip():  # Only update if there's actual content
            self.original_srt_content = current_content
    
    def load_srt(self):
        """Load SRT file from disk."""
        from datetime import datetime
        now_str = datetime.now().strftime("%H:%M:%S") + f".{int(datetime.now().microsecond/1000):03d}"
        print(f"[DEBUG {now_str}] Load button clicked")
        
        now_str = datetime.now().strftime("%H:%M:%S") + f".{int(datetime.now().microsecond/1000):03d}"
        print(f"[DEBUG {now_str}] About to show file dialog...")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open SRT File",
            r"d:\_ZA MONTAŽU",
            "SRT Files (*.srt);;All Files (*)"
        )

        if file_path:
            import time
            from datetime import datetime
            try:
                t0 = time.time()
                now_str = datetime.now().strftime("%H:%M:%S") + f".{int(datetime.now().microsecond/1000):03d}"
                print(f"[DEBUG {now_str}] Starting file read")
                
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                t1 = time.time()
                now_str = datetime.now().strftime("%H:%M:%S") + f".{int(datetime.now().microsecond/1000):03d}"
                print(f"[DEBUG {now_str}] LOAD TIME - File read: {t1-t0:.3f}s")

                # Normalize line endings and strip whitespace
                content = content.replace("\r\n", "\n").replace("\r", "\n")
                content = content.strip()

                print(f"[DEBUG] RAW CONTENT START: {repr(content[:80])}")

                # Normalize SRT endings to ensure exactly one empty line at end
                content = self.normalize_srt_endings(content)
                t2 = time.time()
                print(f"[DEBUG] LOAD TIME - Normalize: {t2-t1:.3f}s")

                # Store original unprocessed content (single source of truth)
                self.original_srt_content = content

                self.input_text.setPlainText(content)
                t3 = time.time()
                print(f"[DEBUG] LOAD TIME - Set text: {t3-t2:.3f}s")
                
                self.last_loaded_file = file_path  # Store for save dialog
                self.update_window_title(file_path)

                # Parse blocks and populate table immediately
                try:
                    t4 = time.time()
                    self.blocks = SrtParser().parse(content)
                    t5 = time.time()
                    print(f"[DEBUG] LOAD TIME - Parse: {t5-t4:.3f}s")
                    
                    self.populate_table(self.blocks)
                    t6 = time.time()
                    print(f"[DEBUG] LOAD TIME - Populate table: {t6-t5:.3f}s")
                    print(f"[DEBUG] LOAD TIME - TOTAL: {t6-t0:.3f}s")
                    print(f"[DEBUG] Parsed {len(self.blocks)} blocks, table populated")
                except Exception as parse_err:
                    print(f"[DEBUG] Parsing failed: {parse_err}")
                    raise

                self.status_bar.showMessage(f"Loaded: {os.path.basename(file_path)}")

                # Save window geometry after successful load
                self.save_window_geometry()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")
    
    def load_srt_file(self, file_path: str):
        """Load SRT file from given path (for file association)."""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", f"The file {file_path} was not found.")
            return
        
        if not file_path.lower().endswith('.srt'):
            QMessageBox.warning(self, "Invalid File", f"The file {file_path} is not an SRT file.")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()

            # Normalize line endings and strip whitespace
            content = content.replace("\r\n", "\n").replace("\r", "\n")
            content = content.strip()

            print(f"[DEBUG] RAW CONTENT START: {repr(content[:80])}")

            # Normalize SRT endings to ensure exactly one empty line at end
            content = self.normalize_srt_endings(content)

            # Store original unprocessed content (single source of truth)
            self.original_srt_content = content

            self.input_text.setPlainText(content)
            self.last_loaded_file = file_path  # Store for save dialog
            self.update_window_title(file_path)

            # Parse blocks and populate table immediately
            try:
                self.blocks = SrtParser().parse(content)
                self.populate_table(self.blocks)
                print(f"[DEBUG] Parsed {len(self.blocks)} blocks, table populated")
            except Exception as parse_err:
                print(f"[DEBUG] Parsing failed: {parse_err}")
                raise

            self.status_bar.showMessage(f"Loaded: {os.path.basename(file_path)}")

            # Save window geometry after successful load
            self.save_window_geometry()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")
    
    def normalize_srt_endings(self, content: str) -> str:
        """Normalize SRT content to ensure exactly one empty line at the end."""
        import re
        # Replace double empty lines (3 or more consecutive newlines) with single empty line
        cleaned = re.sub(r'\n{3,}', '\n\n', content)
        
        # Ensure exactly one empty line at the end
        # Remove all trailing empty lines, then add exactly one
        cleaned = re.sub(r'\n+$', '', cleaned)  # Remove all trailing newlines
        cleaned += '\n'  # Add exactly one empty line at the end
        
        return cleaned
    
    def _sync_table_to_blocks(self):
        """Sync all table cell edits to the underlying blocks."""
        if not self.blocks:
            return
        
        # Commit any active editor
        current_item = self.subtitle_table.currentItem()
        if current_item:
            self.subtitle_table.closePersistentEditor(current_item)
        
        # Sync all rows
        for row in range(len(self.blocks)):
            orig_item = self.subtitle_table.item(row, 4)  # ORIGINAL
            trans_item = self.subtitle_table.item(row, 5)  # TRANSLATION
            
            block = self.blocks[row]
            
            if orig_item:
                edited_text = orig_item.text().strip()
                if edited_text:
                    block.original_text_lines = edited_text.split("\n")
            if trans_item:
                edited_trans = trans_item.text().strip()
                if edited_trans:
                    block.translated_text = edited_trans

    def save_original_srt(self):
        """Save original SRT content to disk with any table edits."""
        if not self.blocks:
            QMessageBox.warning(self, "Warning", "No content to save.")
            return
        
        if not self.last_loaded_file:
            QMessageBox.warning(self, "Warning", "No original file to overwrite.")
            return
        
        # Sync all table edits to blocks first
        self._sync_table_to_blocks()
        
        # Rebuild from blocks - use original_text_lines instead of translated_text
        output_lines = []
        for block in self.blocks:
            output_lines.append(str(block.index))
            output_lines.append(block.timestamp)
            
            # Use original_text_lines (includes any user edits)
            text_to_use = '\n'.join(block.original_text_lines)
            text_lines = text_to_use.split('\n')
            for line in text_lines:
                output_lines.append(line)
            output_lines.append('')  # Blank line separator
        
        content = '\n'.join(output_lines)
        
        try:
            # Normalize content for saving
            cleaned_content = self.normalize_srt_endings(content)
            with open(self.last_loaded_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            self.status_bar.showMessage(f"Saved: {os.path.basename(self.last_loaded_file)}")
            self.save_window_geometry()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")

    def save_srt(self):
        """Save translated SRT to disk."""
        if not self.blocks:
            QMessageBox.warning(self, "Warning", "No content to save.")
            return

        # Sync table edits to blocks first
        self._sync_table_to_blocks()
        
        # Rebuild from current block data (includes any table edits)
        content = SrtParser.rebuild(self.blocks)
        
        # Generate suggested filename based on mode
        suggested_name = ""
        if self.last_loaded_file:
            # Get original filename
            base_path = os.path.dirname(self.last_loaded_file)
            base_name = os.path.basename(self.last_loaded_file)
            
            if self.line_splitting_enabled:
                # Line splitting mode - use original filename (no .en suffix)
                suggested_name = base_name
            else:
                # Translation mode - insert .en before .srt extension
                if base_name.endswith('.srt'):
                    suggested_name = base_name[:-4] + '.en.srt'
                else:
                    suggested_name = base_name + '.en.srt'
            
            suggested_path = os.path.join(base_path, suggested_name)
        else:
            # No original file loaded
            if self.line_splitting_enabled:
                suggested_path = "line_split.srt"
            else:
                suggested_path = "translated.en.srt"
        
        # Set dialog title based on mode
        if self.line_splitting_enabled:
            dialog_title = "Save Line Split SRT"
            # Update save button text for line splitting mode (preserve icon)
            self.save_btn.setText("💾 Save Line Split")
        else:
            dialog_title = "Save Translated SRT"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            dialog_title,
            suggested_path,  # Pre-populate with suggested name
            "SRT Files (*.srt);;All Files (*)"
        )
        
        if file_path:
            try:
                # Normalize content for saving - ensure exactly one empty line at end
                cleaned_content = self.normalize_srt_endings(content)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                self.status_bar.showMessage(f"Saved: {os.path.basename(file_path)}")
                # Save window geometry after successful save
                self.save_window_geometry()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")
    
    def open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Reload prompts so they are immediately available for next translation
            # This uses the shared config which was updated by SettingsDialog.save_settings()
            translator = Translator(
                provider="openrouter",
                api_key="",
                model="",
                referer="",
                app_title=""
            )
            translator.reload_prompts()
            
            # Reload OpenRouter models in the main UI dropdown
            self.load_fixed_openrouter_models()
            
            # Save main window geometry after settings dialog closes
            self.save_window_geometry()
    
    def toggle_line_splitting(self):
        """Toggle line splitting mode on/off."""
        self.line_splitting_enabled = not self.line_splitting_enabled
        
        if self.line_splitting_enabled:
            # Turn ON - green styling and update button text
            self.line_splitting_toggle.setText("✂️ Line Split: ON")
            self.line_splitting_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: 600;
                    min-width: 140px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:pressed {
                    background-color: #1e7e34;
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                    color: #adb5bd;
                }
            """)
            self.translate_btn.setText("▶  Line Splitting")
            self.save_btn.setText("💾 Save Line Split")
            self.output_label.setText("Subtitles (Any Language, line split)")
        else:
            # Turn OFF - gray styling and update button text
            self.line_splitting_toggle.setText("✂️ Line Split: OFF")
            self.line_splitting_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: 600;
                    min-width: 140px;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
                QPushButton:pressed {
                    background-color: #545b62;
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                    color: #adb5bd;
                }
            """)
            self.translate_btn.setText("▶  Translate")
            self.save_btn.setText("💾 Save Translated")
            self.output_label.setText("Subtitles")
    
    def start_translation(self):
        """Start translation process."""
        # Reset progress bar from any previous run
        self._reset_progress_bar()
        
        # For translation, always reload from original source - don't rebuild from blocks
        # This ensures we get clean original text for translation
        if self.last_loaded_file and os.path.exists(self.last_loaded_file):
            print(f"DEBUG: RELOADING SRT file: {self.last_loaded_file}")
            self.load_srt_file(self.last_loaded_file)
            srt_content = self.original_srt_content.strip() if self.original_srt_content else ""
            self.status_bar.showMessage(f"RELOADED SRT file: {os.path.basename(self.last_loaded_file)}", 5000)
        else:
            print(f"DEBUG: Using stored content")
            srt_content = self.original_srt_content.strip() if self.original_srt_content else ""
        

        
        if not srt_content:
            QMessageBox.warning(self, "Warning", "Please load or paste SRT content first.")
            return
        
        # Check if line splitting mode is enabled
        if self.line_splitting_enabled:
            self.start_line_splitting(srt_content)
            return
        
        # Get settings
        settings = SettingsDialog.get_settings()
        
        # Hardcode provider to openrouter
        provider = "openrouter"

        # Validate OpenRouter API key
        api_key = settings.get('openrouter_api_key', '') if settings else ''
        if not api_key:
            QMessageBox.warning(
                self,
                "API Key Required",
                "Please set your OpenRouter API key in Settings before translating."
            )
            return
        # Clean API key - replace non-breaking hyphens with regular hyphens
        api_key = api_key.replace('\u2011', '-').replace('\u2012', '-').replace('\u2013', '-').replace('\u2014', '-')
        model = self.openrouter_model_combo.currentText()
        if not model:
            QMessageBox.warning(
                self,
                "No Models Available",
                "No OpenRouter models available. Please refresh models in Settings."
            )
            return
        referer = settings.get('openrouter_referer', '') if settings else None
        app_title = settings.get('openrouter_app_title', '') if settings else None

        # Store on self so retranslate can reuse them
        self.provider = provider
        self.api_key = api_key
        self.model = model

        # Disable controls during processing
        self.set_controls_enabled(False)
        self.output_text.clear()
        

        
        # Start worker thread
        self.worker = TranslationWorker(
            srt_content=srt_content,
            provider=provider,
            api_key=api_key,
            model=model,
            referer=referer,
            app_title=app_title
        )
        self.worker.progress.connect(self.update_status)
        self.worker.progress.connect(self._update_translation_progress)
        self.worker.finished.connect(self.translation_finished)
        self.worker.error.connect(self.translation_error)

        # Console debug output
        self.worker.debug_input.connect(self.log_debug)
        self.worker.debug_raw_response.connect(self.log_debug)
        self.worker.debug_cleaned.connect(self.log_debug)

        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.worker.start()
    
    def start_line_splitting(self, srt_content: str):
        """Apply line splitting to Serbian SRT content without translation."""
        # Reset progress bar from any previous run
        self._reset_progress_bar()
        
        # Always create parser for rebuild later
        parser = SrtParser()
        
        # Use blocks directly if available - for line splitting we need original text
        if hasattr(self, 'blocks') and self.blocks and len(self.blocks) > 0:
            blocks = self.blocks
            print(f"DEBUG: Line splitting using {len(blocks)} existing blocks")
        else:
            # Parse from content if no blocks
            blocks = parser.parse(srt_content)
            print(f"DEBUG: Line splitting parsed {len(blocks)} blocks from content")

        # Disable controls during processing
        self.set_controls_enabled(False)
        self.output_text.clear()

        self.update_status("Applying line splitting rules...")
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        try:
            # Apply line splitting to each block
            line_splitter = LineSplitter()
            processed_blocks = []
            
            # Ensure blocks have timing data
            for block in blocks:
                if not block.duration_ms or block.duration_ms == 0:
                    block.start_time_ms, block.end_time_ms = SrtParser.parse_timestamp_to_ms(block.timestamp)
                    block.duration_ms = block.end_time_ms - block.start_time_ms
            
            for i, block in enumerate(blocks):
                self.update_status(f"Processing block {i+1}/{len(blocks)}...")
                # Update progress bar with animation
                percent = int(((i + 1) / len(blocks)) * 100)
                self._animate_progress(percent)
                
                # Apply line splitting to the original text
                original_text = ' '.join(block.original_text_lines)
                split_text = line_splitter.split_text(original_text)
                
                # Calculate CPS
                cps = SrtParser.calculate_characters_per_second(block)
                
                # Create new block with split text as translated text
                processed_block = SrtBlock(
                    index=block.index,
                    timestamp=block.timestamp,
                    original_text_lines=block.original_text_lines,
                    translated_text=split_text,
                    start_time_ms=block.start_time_ms,
                    end_time_ms=block.end_time_ms,
                    duration_ms=block.duration_ms,
                    characters_per_second=cps
                )
                processed_blocks.append(processed_block)
            
            # Store original blocks for retranslation
            self.original_blocks = blocks.copy()
            
            # Rebuild SRT content
            output_srt = parser.rebuild(processed_blocks)

            # Set output content
            self.output_text.setPlainText(output_srt)

            # Populate the table with processed blocks
            self.blocks = processed_blocks
            self.populate_table(processed_blocks)
            
            self.update_status(f"Line splitting complete! Processed {len(processed_blocks)} blocks.")
            # Animate to 100% and keep visible
            self._animate_progress(100)
            
        except Exception as e:
            print(f"[ERROR] Line splitting failed: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to apply line splitting:\n{e}")
            self.update_status("Line splitting failed")
            # Hide on error
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)
        finally:
            # Re-enable controls
            self.set_controls_enabled(True)
    
    def set_controls_enabled(self, enabled: bool):
        """Enable or disable UI controls during translation."""
        self.load_btn.setEnabled(enabled)
        self.save_input_btn.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)
        self.settings_btn.setEnabled(enabled)
        self.line_splitting_toggle.setEnabled(enabled)
        self.openrouter_model_combo.setEnabled(enabled)
        self.translate_btn.setEnabled(enabled)
    
    def update_status(self, message: str):
        """Update status bar with progress message."""
        self.status_bar.showMessage(message)
    
    def _update_translation_progress(self, message: str):
        """Update progress bar based on translation progress messages."""
        # Define translation stages with their progress percentages
        stages = [
            ("Parsing SRT file", 0),
            ("Preparing", 5),
            ("Translating with OpenRouter", 10),
            ("Checking for long translations", 40),
            ("Calculating characters per second", 50),
            ("Finding blocks with high CPS", 55),
            ("Adjusting", 60),
            ("Applying line splitting rules", 70),
            ("Final check", 80),
            ("Rebuilding SRT file", 90),
            ("complete", 100),
            ("Translation complete", 100),
        ]
        
        message_lower = message.lower()
        target_percent = 0
        
        # Check for specific stage matches
        for stage_name, base_percent in stages:
            if stage_name.lower() in message_lower:
                target_percent = base_percent
                break
        else:
            # Parse block progress if present
            import re
            match = re.search(r'block (\d+) of (\d+)', message)
            if match:
                current = int(match.group(1))
                total = int(match.group(2))
                if total > 0:
                    target_percent = 10 + int((current / total) * 30)
        
        # Animate progress bar smoothly to target
        if target_percent > 0:
            self._animate_progress(target_percent)
        elif "complete" in message_lower:
            # Fallback: if complete in message, go to 100%
            self._animate_progress(100)
    
    def _animate_progress(self, target_percent: int):
        """Animate progress bar smoothly to target percentage."""
        current = self.progress_bar.value()
        if current >= target_percent:
            return
        
        # Simple animation: increment by 1% every 10ms
        def step_progress():
            nonlocal current
            if current < target_percent:
                current = min(current + 1, target_percent)
                self.progress_bar.setValue(current)
                if current < target_percent:
                    QTimer.singleShot(10, step_progress)
        
        step_progress()
    
    def _reset_progress_bar(self):
        """Reset progress bar to hidden state."""
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
    
    def translation_finished(self, output_srt: str, shortened_long_indices: List[int] = None, shortened_cps_indices: List[int] = None, time_extended_indices: List[int] = None, blocks = None):
        """Handle successful translation completion."""
        # Store blocks for all access paths
        self.blocks = blocks
        self.blocks_with_cps = blocks
        
        # Store original blocks with full timing data (deep copy to preserve timing)
        import copy
        if not hasattr(self, 'original_blocks') or not self.original_blocks:
            self.original_blocks = copy.deepcopy(blocks)

        # Keep raw SRT in hidden output_text for save operations
        self.output_text.setPlainText(output_srt)

        # Populate the subtitle table
        if blocks:
            self.populate_table(blocks)

        self.set_controls_enabled(True)
        self.status_bar.showMessage("Translation complete!")
        # Animate to 100% and keep visible
        self._animate_progress(100)
        # Save window geometry after translation completes
        self.save_window_geometry()
    
    def translation_error(self, error_message: str):
        """Handle translation error."""
        self.set_controls_enabled(True)
        self.status_bar.showMessage("Translation failed")
        # Hide progress bar
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        QMessageBox.critical(
            self,
            "Translation Error",
            f"An error occurred during translation:\n\n{error_message}"
        )
    
    def show_context_menu(self, pos):
        """Show context menu for retranslation on both panels."""
        sender = self.sender()
        menu = QMenu(self)
        action = QAction("Retranslate this block", self)
        action.triggered.connect(self.retranslate_selected_block)
        
        # Disable if worker is already running
        if hasattr(self, 'single_block_worker') and self.single_block_worker and self.single_block_worker.isRunning():
            action.setEnabled(False)
        
        menu.addAction(action)
        if sender is not None:
            menu.exec(sender.mapToGlobal(pos))
    
    def retranslate_selected_block(self):
        """Retranslate the currently selected block using EDITED text."""
        if not hasattr(self, 'current_selected_block_index'):
            QMessageBox.information(self, "No Selection", "Please select a block to retranslate.")
            return

        row = self.current_selected_block_index

        if not self.blocks or row < 0 or row >= len(self.blocks):
            QMessageBox.information(self, "Invalid Selection", "Invalid block selection.")
            return

        # Commit any in-progress editor so on_item_changed fires
        current_item = self.subtitle_table.currentItem()
        if current_item:
            self.subtitle_table.closePersistentEditor(current_item)
        self.subtitle_table.clearFocus()

        # Sync table cell content to block BEFORE retranslation
        # Columns: 0=#, 1=Start, 2=End, 3=spacer, 4=ORIGINAL, 5=TRANSLATION, 6=CPS
        orig_item = self.subtitle_table.item(row, 4)
        trans_item = self.subtitle_table.item(row, 5)
        
        # Read edited block from self.blocks
        block = self.blocks[row]
        
        # Update block with user's edited text from table
        if orig_item:
            edited_text = orig_item.text().strip()
            if edited_text:
                block.original_text_lines = edited_text.split("\n")
        if trans_item:
            edited_trans = trans_item.text().strip()
            if edited_trans:
                block.translated_text = edited_trans

        # Get current settings
        settings = SettingsDialog.get_settings()
        api_key = settings.get('openrouter_api_key', '') if settings else ''
        api_key = api_key.replace('\u2011', '-').replace('\u2012', '-').replace('\u2013', '-').replace('\u2014', '-')
        referer = settings.get('openrouter_referer', '') if settings else None
        app_title = settings.get('openrouter_app_title', '') if settings else None

        self.status_bar.showMessage(f"Retranslating block {block.index}...")
        QApplication.processEvents()

        try:
            translator = Translator(
                provider=self.provider,
                api_key=self.api_key,
                model=self.model,
                referer=referer,
                app_title=app_title,
                is_manual=True
            )

            # Step 1: Get current block data (NOT original file)
            text = " ".join(block.original_text_lines)
            print(f"[DEBUG RETRANSLATE] Input: {text}")

            # Step 2: Translate
            raw = translator.translate_blocks([text])[0]
            print(f"[DEBUG RETRANSLATE] Raw output: {raw}")

            # Step 3: Clean AI output (MANDATORY)
            cleaned = raw.strip()

            # Remove common AI prefixes
            cleaned = re.sub(r"^(Okay.*?:|Here.*?:|Sure.*?:)", "", cleaned, flags=re.IGNORECASE)

            # Remove markdown artifacts
            cleaned = cleaned.replace("**", "")

            # Normalize whitespace
            cleaned = ' '.join(cleaned.split())
            
            print(f"[DEBUG RETRANSLATE] Cleaned: {cleaned}")

            # Step 5: Apply same post-processing as full pipeline
            translations = [cleaned]

            # Apply shorten_long_translations
            translations, _ = translator.shorten_long_translations(translations)
            cleaned = translations[0]

            block.translated_text = cleaned

            # RESET adjustment flags - new translation may not need adjustment
            block.was_shortened = False
            block.timestamp_extended = False
            if hasattr(block, 'extension_reason'):
                block.extension_reason = None

            # DEBUG: Print duration info before CPS calc
            print(f"[DEBUG RETRANS] Block {block.index}: text_len={len(cleaned)}, duration_ms={block.duration_ms}, start={block.start_time_ms}, end={block.end_time_ms}")

            # Calculate CPS
            SrtParser.calculate_cps_for_all_blocks([block])

            # For single block retranslation: ONLY extend timing - never shorten text
            # Pass full blocks list to find prev/next for timing constraints
            timing_extended = SrtParser.adjust_single_block_cps(block, self.blocks, row)
            
            if timing_extended:
                # Recalculate CPS after adjustment
                SrtParser.calculate_cps_for_all_blocks([block])
                print(f"[DEBUG RETRANS] Block {block.index}: timing extended, new_cps={block.characters_per_second:.1f}, duration={block.duration_ms}ms")

            # Step 6: Apply line splitting (MANDATORY)
            block.translated_text = LineSplitter.split_text(block.translated_text)

            # Step 7: Update table
            self.update_table_row(row, block)

            # Update hidden output for save
            self.output_text.setPlainText(SrtParser.rebuild(self.blocks))

            char_count = len(block.translated_text.replace('\n', ''))
            cps = block.characters_per_second
            self.status_bar.showMessage(f"Block {block.index} retranslated | {char_count} chars | {cps:.1f} c/s")

        except Exception as e:
            QMessageBox.warning(self, "Retranslate Failed", str(e))
            self.status_bar.showMessage("Retranslate failed")
    
    def single_block_retranslation_finished(self, updated_block, shortened_long, shortened_cps, time_extended):
        """Handle single block retranslation completion."""
        if not updated_block:
            QMessageBox.warning(self, "Error", "Block retranslation failed.")
            return
        
        # Find the correct list position for this block (use 0-based index)
        try:
            idx = next(i for i, b in enumerate(self.blocks_with_cps) if b.index == updated_block.index)
        except StopIteration:
            QMessageBox.warning(self, "Error", f"Block {updated_block.index} not found in blocks list.")
            return
        
        print(f"[DEBUG] Retranslation finished for block {updated_block.index} (row {idx})")
        
        # Update the block at the correct position (list length never changes)
        self.blocks_with_cps[idx] = updated_block
        
        # Rebuild full SRT output and store in hidden output_text for save
        output_srt = SrtParser.rebuild(self.blocks_with_cps)
        self.output_text.setPlainText(output_srt)
        
        # Update ONLY the affected row in the table
        self.update_table_row(idx, updated_block)
        
        # Update status bar for the updated block
        char_count = len(updated_block.translated_text.replace('\n', ''))
        cps = updated_block.characters_per_second
        
        if time_extended:
            mod_type = "TIME EXTENDED"
        else:
            mod_type = "RETRANSLATED"
        
        self.status_bar.showMessage(f"Block {updated_block.index} selected | {char_count} chars | {cps:.1f} c/s | {mod_type}")
        
        # Clean up worker
        self.single_block_worker = None

    def update_window_title(self, file_path: str):
        """Update window title to include current SRT filename with full path."""
        if file_path:
            title = f"{self.base_window_title} - {file_path}"
        else:
            title = self.base_window_title
        
        # Try to center title by adding padding spaces
        # This is a workaround since Windows doesn't allow title centering via Qt
        padded_title = self.center_title_text(title)
        self.setWindowTitle(padded_title)
    
    def center_title_text(self, title: str) -> str:
        """Add padding to make title appear centered."""
        # Estimate title width and add padding (rough approximation)
        target_width = 80  # Approximate characters for centering
        if len(title) < target_width:
            padding = (target_width - len(title)) // 2
            return " " * padding + title + " " * padding
        return title
    
    def resizeEvent(self, event):
        """Handle window resize to ensure proper title display."""
        super().resizeEvent(event)
        # Ensure title is properly updated on resize
        if self.last_loaded_file:
            self.update_window_title(self.last_loaded_file)
    

    
    def on_block_selected(self, block_index: int):
        """Handle block selection in either panel."""
        # Store current selected block index for context menu
        self.current_selected_block_index = block_index
        
        # Get character count for selected block
        char_count = self.get_block_char_count(block_index)
        
        # Enhanced status bar with CPS and modification type
        if self.blocks_with_cps and block_index < len(self.blocks_with_cps):
            block = self.blocks_with_cps[block_index]
            cps = block.characters_per_second
            
            # Determine modification type based on block attributes
            if block.timestamp_extended:
                mod_type = "TIME EXTENDED"
            elif getattr(block, 'was_retranslated', False):
                mod_type = "RETRANSLATED"
            elif getattr(block, 'was_shortened', False):
                mod_type = "SHORTENED"
            else:
                mod_type = None
            
            # Enhanced status bar message without milliseconds
            if mod_type:
                if char_count > 0:
                    self.status_bar.showMessage(f"Block {block_index + 1} selected | {char_count} chars | {cps:.1f} c/s | {mod_type}")
                else:
                    self.status_bar.showMessage(f"Block {block_index + 1} selected | {cps:.1f} c/s | {mod_type}")
            else:
                if char_count > 0:
                    self.status_bar.showMessage(f"Block {block_index + 1} selected | {char_count} chars | {cps:.1f} c/s")
                else:
                    self.status_bar.showMessage(f"Block {block_index + 1} selected | {cps:.1f} c/s")
        else:
            # Fallback to original behavior if blocks_with_cps not available
            if char_count > 0:
                self.status_bar.showMessage(f"Block {block_index + 1} selected | {char_count} chars")
            else:
                self.status_bar.showMessage(f"Block {block_index + 1} selected")
    
    def get_block_char_count(self, block_index: int) -> int:
        """Get character count of selected block's text content."""
        # Check input panel (output is now a table, not a text widget with block_positions)
        widget = self.input_text
        if (block_index >= 0 and 
            block_index < len(widget.block_positions)):
            
            block_info = widget.block_positions[block_index]
            lines = widget.toPlainText().split('\n')
            
            # Extract text lines for this block
            start_line = block_info['start']
            end_line = block_info['end']
            
            if start_line < len(lines):
                block_lines = lines[start_line:end_line]
                
                # Count only text content (skip numbers and timestamps)
                char_count = 0
                for line in block_lines:
                    line = line.strip()
                    if line and not line.isdigit() and '-->' not in line:
                        char_count += len(line)
                
                if char_count > 0:
                    return char_count
        
        return 0
    
    def load_window_geometry(self):
        """Load and restore window geometry."""
        settings = SettingsDialog.get_settings()
        if settings:
            geometry = settings.get('main_window_geometry', {})
            if geometry:
                try:
                    self.restoreGeometry(bytes.fromhex(geometry.get('geometry', '')))
                    self.restoreState(bytes.fromhex(geometry.get('state', '')))
                except:
                    pass  # Use default geometry if restoration fails
    
    def save_window_geometry(self):
        """Save current window geometry."""
        settings = SettingsDialog.get_settings() or {}
        strip_secrets(settings)
        settings['main_window_geometry'] = {
            'geometry': self.saveGeometry().toHex().data().decode(),
            'state': self.saveState().toHex().data().decode()
        }

        # Use centralized config path method
        config_file = SettingsDialog.get_config_file_path()

        try:
            with open(config_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass
    
    def closeEvent(self, event):
        """Handle close event to save window geometry."""
        self.save_window_geometry()
        super().closeEvent(event)
    
    def restart_application(self):
        """Restart the application using exact same approach as restart_app.py."""
        # Save window geometry before restarting
        self.save_window_geometry()
        
        # Store current state to restore after restart
        file_to_reload = self.last_loaded_file
        openrouter_model = self.openrouter_model_combo.currentText()
        line_splitting_state = self.line_splitting_enabled
        always_on_top_state = self.always_on_top_checkbox.isChecked()
        
        # Destroy current window
        self.destroy()
        
        # Create new instance - same as restart_app.py approach
        self.__init__()
        
        # Restore state
        self.openrouter_model_combo.setCurrentText(openrouter_model)
        
        # Restore line splitting state
        if line_splitting_state:
            self.line_splitting_enabled = False  # Force toggle
            self.toggle_line_splitting()
        
        # Restore always on top state
        self.always_on_top_checkbox.setChecked(always_on_top_state)
        
        # Reload file if there was one
        if file_to_reload and os.path.exists(file_to_reload):
            self.load_srt_file(file_to_reload)
        
        # Show new window
        self.show()
    






# ============================================================================
# Main Entry Point
# ============================================================================



def verify_dependencies():
    """Verify all required dependencies are available."""
    errors = []
    
    # Check PyQt6
    if not PYQT6_AVAILABLE:
        errors.append(f"PyQt6 import error: {IMPORT_ERROR}")
    
    # No external library checks needed
    
    # Check requests
    try:
        import requests
    except ImportError:
        errors.append("The requests library is not installed.")
    
    if errors:
        # Create error message
        error_msg = "Missing required dependencies:\n\n"
        for i, error in enumerate(errors, 1):
            error_msg += f"{i}. {error}\n"
        
        error_msg += "\nTo install missing dependencies:\n"
        error_msg += "pip install PyQt6 requests\n\n"
        error_msg += "If you're running the executable, this indicates a packaging error."
        
        # Try to show error dialog, fallback to console
        try:
            if PYQT6_AVAILABLE:
                QMessageBox.critical(None, "Missing Dependencies", error_msg)
        except:
            pass
        
        print("=" * 60)
        print("DEPENDENCY ERROR")
        print("=" * 60)
        print(error_msg)
        print("=" * 60)
        
        return False
    
    return True


def main():
    """Application entry point."""
    # Verify dependencies first
    if not verify_dependencies():
        sys.exit(1)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SRT Subtitle Translator')
    parser.add_argument('file', nargs='?', help='SRT file to open')
    
    # Filter out PyQt arguments before parsing
    qt_args = []
    script_args = []
    for arg in sys.argv:
        if arg.startswith('-'):
            # Check if it's a Qt argument
            if any(arg.startswith(qt_prefix) for qt_prefix in ['-platform', '-style', '-geometry']):
                qt_args.append(arg)
                if qt_args.index(arg) + 1 < len(sys.argv):
                    qt_args.append(sys.argv[qt_args.index(arg) + 1])
            else:
                script_args.append(arg)
        else:
            script_args.append(arg)
    
    # Parse only non-Qt arguments
    args = parser.parse_args([arg for arg in script_args if arg not in sys.argv[:1]])
    
    # Reconstruct sys.argv with only Qt arguments for QApplication
    sys.argv = [sys.argv[0]] + qt_args
    
    import time
    from datetime import datetime
    t0 = time.time()
    now_str = datetime.now().strftime("%H:%M:%S") + f".{int(datetime.now().microsecond/1000):03d}"
    print(f"[DEBUG {now_str}] Creating QApplication")
    
    app = QApplication(sys.argv)
    t1 = time.time()
    now_str = datetime.now().strftime("%H:%M:%S") + f".{int(datetime.now().microsecond/1000):03d}"
    print(f"[DEBUG {now_str}] QApplication created: {t1-t0:.3f}s")
    
    t2 = time.time()
    now_str = datetime.now().strftime("%H:%M:%S") + f".{int(datetime.now().microsecond/1000):03d}"
    print(f"[DEBUG {now_str}] Creating MainWindow")
    
    window = MainWindow()
    t3 = time.time()
    now_str = datetime.now().strftime("%H:%M:%S") + f".{int(datetime.now().microsecond/1000):03d}"
    print(f"[DEBUG {now_str}] MainWindow created: {t3-t2:.3f}s")
    
    # Load file if provided
    if args.file:
        window.load_srt_file(args.file)
    
    window.show()

    # Make sure the API keys file exists and, if it is still empty, tell the
    # user exactly where it is (it is created automatically, never uploaded).
    notify_missing_api_key(window)

    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()