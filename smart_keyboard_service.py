#!/usr/bin/env python3
"""
Kannada Smart Keyboard Service (Phase 2 - Suggestion Popup Prototype)
==============================================================================

This service monitors keyboard input system-wide and shows Kannada
word suggestions instead of auto-correcting automatically.

Features:
- Shows Kannada spelling suggestions in a popup box
- Works in any app (Notepad, Word, Browser)
- Uses keyboard hooks for input capture
- You choose whether to insert a suggestion (not auto-correct)

Requirements:
    pip install pywin32 pynput
    (Tkinter is built-in with Python)

Usage:
    python smart_keyboard_service.py

Press Ctrl+Shift+K to toggle suggestion feature ON/OFF
Press Esc twice to stop the service
"""

import sys
import os
import time
import uuid
import threading
import tkinter as tk
import ctypes
from ctypes import wintypes, windll, byref, Structure, c_long, c_ulong, c_short, pointer, POINTER, sizeof, create_unicode_buffer
from win32api import GetCursorPos
import signal
import win32clipboard
import re
import win32gui
import win32con
from typing import List, Optional, Tuple, Dict

from dpi_utils import DPIScaler

try:
    from win32com.client import Dispatch  # noqa: F401
except ImportError:
    Dispatch = None  # Word COM automation is optional

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except AttributeError:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
except OSError:
    # DPI awareness already configured; ignore.
    pass


# ---------------------------------------------------------------------------
# Windows API structures for caret position and metrics
# ---------------------------------------------------------------------------
class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


class RECT(Structure):
    _fields_ = [("left", c_long), ("top", c_long), ("right", c_long), ("bottom", c_long)]


class GUITHREADINFO(Structure):
    _fields_ = [
        ("cbSize", c_ulong),
        ("flags", c_ulong),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", RECT)
    ]


def get_dpi_scale():
    """Get DPI scaling factor for proper positioning across different displays"""
    try:
        windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    try:
        hdc = windll.user32.GetDC(0)
        dpi = windll.gdi32.GetDeviceCaps(hdc, 88)
        windll.user32.ReleaseDC(0, hdc)
        scale = dpi / 96.0
        return scale
    except Exception:
        return 1.0


def get_caret_position():
    """Get the screen position of the text caret (insertion point) with DPI awareness"""
    try:
        hwnd = windll.user32.GetForegroundWindow()
        thread_id = windll.user32.GetWindowThreadProcessId(hwnd, 0)

        gui_info = GUITHREADINFO(cbSize=sizeof(GUITHREADINFO))
        result = windll.user32.GetGUIThreadInfo(thread_id, byref(gui_info))

        if not result:
            return GetCursorPos()

        caret_hwnd = gui_info.hwndCaret
        if not caret_hwnd:
            caret_hwnd = gui_info.hwndFocus

        if not caret_hwnd:
            return GetCursorPos()

        caret_rect = gui_info.rcCaret
        point = POINT(caret_rect.left, caret_rect.bottom)
        windll.user32.ClientToScreen(caret_hwnd, byref(point))
        return (point.x, point.y)
    except Exception:
        return GetCursorPos()


def measure_text_width(text: str, hwnd: Optional[int] = None) -> int:
    """Measure the pixel width of text, particularly for Kannada characters"""
    if text is None:
        return 0

    try:
        if not hwnd:
            hwnd = windll.user32.GetForegroundWindow()

        hdc = windll.user32.GetDC(hwnd)
        if not hdc:
            return len(text) * 12

        class SIZE(Structure):
            _fields_ = [("cx", c_long), ("cy", c_long)]

        size = SIZE()
        windll.gdi32.GetTextExtentPoint32W(hdc, text, len(text), byref(size))
        windll.user32.ReleaseDC(hwnd, hdc)

        scale = get_dpi_scale()
        width = int(size.cx / scale) if scale > 0 else size.cx
        return max(width, len(text) * 8)
    except Exception:
        return len(text) * 12


# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import spell checker and Kannada utilities
from enhanced_spell_checker import EnhancedSpellChecker
from kannada_wx_converter import is_kannada_text

# Import Grammarly-style overlay helpers
from grammarly_underline_system import (
    UnderlineOverlayWindow,
    CaretTracker,
    WordPositionCalculator
)

try:
    from pynput import keyboard, mouse
    from pynput.keyboard import Key, Controller
    from pynput.mouse import Button
except ImportError:
    print("❌ Error: Required packages not installed")
    print("Install: pip install pywin32 pynput")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Suggestion Popup UI (Tkinter overlay window)
# ---------------------------------------------------------------------------
class SuggestionPopup:
    """Floating popup that shows Kannada word suggestions"""

    def __init__(
        self,
        on_selection_callback=None,
        on_close_callback=None,
        *,
        caret_tracker=None,
        dpi_scaler: Optional[DPIScaler] = None,
    ):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.withdraw()
        self.suggestions = []
        self.selected = 0
        self.visible = False
        self.on_selection_callback = on_selection_callback
        self.on_close_callback = on_close_callback
        self.caret_tracker = caret_tracker
        self.dpi_scaler = dpi_scaler
        self.current_hwnd: Optional[int] = None

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Add frame for border
        frame = tk.Frame(self.root, bg='#0078D7', bd=1)
        frame.pack(fill='both', expand=True)

        self.listbox = tk.Listbox(
            frame, font=('Nirmala UI', 14),
            height=6, width=20, bg='white', fg='black',
            selectbackground='#0078D7', selectforeground='white',
            highlightthickness=0, relief='flat', cursor='hand2'
        )
        self.listbox.pack(padx=1, pady=1)
        
        # Bind mouse click event
        self.listbox.bind('<ButtonRelease-1>', self._on_click)
        self.listbox.bind('<Motion>', self._on_hover)

    def get_window_handle(self) -> Optional[int]:
        """Return the native HWND for the popup window if available."""
        try:
            return int(self.root.winfo_id())
        except Exception:
            return None

    def show(self, suggestions):
        """Show popup near the text caret (where text is being typed)"""
        if not suggestions:
            return
        self.suggestions = suggestions
        self.selected = 0
        self.listbox.delete(0, tk.END)
        for s in suggestions:
            self.listbox.insert(tk.END, s)
        self.listbox.select_set(0)
        self.listbox.activate(0)
        
        # Get caret position (where text is being typed) instead of mouse cursor
        caret_x = caret_y = None
        if self.caret_tracker:
            raw_rect = self.caret_tracker.get_caret_rect()
            scale = self.dpi_scaler.scale if self.dpi_scaler else 1.0
            rect = self.caret_tracker.get_scaled_rect(raw_rect, scale)
            if rect:
                caret_x = rect['left']
                caret_y = rect['top'] + rect['height']

        if caret_x is None or caret_y is None:
            caret_x, caret_y = get_caret_position()
        
        offset_x = self.dpi_scaler.px(10) if self.dpi_scaler else 10
        offset_y = self.dpi_scaler.px(5) if self.dpi_scaler else 5
        
        # Position popup slightly below and to the right of the caret
        self.root.geometry(f"+{caret_x + offset_x}+{caret_y + offset_y}")
        self.root.deiconify()
        self.visible = True
        self.root.lift()
        self.root.focus_force()
        try:
            self.current_hwnd = windll.user32.GetForegroundWindow()
        except Exception:
            self.current_hwnd = None

    def hide(self):
        self.root.withdraw()
        self.visible = False
        self.current_hwnd = None

    def select_next(self):
        if not self.visible or not self.suggestions:
            return
        self.selected = (self.selected + 1) % len(self.suggestions)
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(self.selected)
        self.listbox.activate(self.selected)

    def select_prev(self):
        if not self.visible or not self.suggestions:
            return
        self.selected = (self.selected - 1) % len(self.suggestions)
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(self.selected)
        self.listbox.activate(self.selected)

    def get_selected(self):
        if not self.suggestions:
            print(f"⚠️ get_selected: No suggestions available")
            return None
        if not self.visible:
            print(f"⚠️ get_selected: Popup not visible")
            return None
        if self.selected < 0 or self.selected >= len(self.suggestions):
            print(f"⚠️ get_selected: Invalid selection index {self.selected}")
            return None
        print(f"✅ get_selected: Returning '{self.suggestions[self.selected]}'")
        return self.suggestions[self.selected]
    
    def _on_click(self, event):
        """Handle mouse click on suggestion"""
        index = self.listbox.nearest(event.y)
        if 0 <= index < len(self.suggestions):
            self.selected = index
            word = self.suggestions[self.selected]
            self.hide()
            if self.on_selection_callback:
                self.on_selection_callback(word)
    
    def _on_hover(self, event):
        """Highlight suggestion on mouse hover"""
        index = self.listbox.nearest(event.y)
        if 0 <= index < len(self.suggestions):
            self.listbox.select_clear(0, tk.END)
            self.listbox.select_set(index)
            self.listbox.activate(index)
            self.selected = index
    
    def _on_window_close(self):
        """Handle window close event"""
        if self.on_close_callback:
            self.on_close_callback()


# ---------------------------------------------------------------------------
# Smart Keyboard Service
# ---------------------------------------------------------------------------
class SmartKeyboardService:
    """Background service for Kannada word suggestion"""
    def __init__(self):
        print("\n" + "="*70)
        print("🎯 Kannada Smart Keyboard Service - Suggestion Mode")
        print("="*70)
        
        self.spell_checker = EnhancedSpellChecker()
        self.keyboard_controller = Controller()
        self.dpi = DPIScaler()
        self.caret_tracker = CaretTracker()  # Now with font metrics, DPI, and UI Automation
        self.popup = SuggestionPopup(
            on_selection_callback=self.replace_word,
            on_close_callback=self.on_popup_close,
            caret_tracker=self.caret_tracker,
            dpi_scaler=self.dpi,
        )
        
        # Initialize Grammarly-style fake underline overlay with DPI + Font + UIA support
        self.underline_overlay = UnderlineOverlayWindow(self.popup.root, dpi_scaler=self.dpi)
        self.word_position_calc = WordPositionCalculator(self.caret_tracker)
        self.active_overlay_hwnd: Optional[int] = None
        
        # Underline styling + relocation controls
        self.underline_focus_ratio = 0.45  # portion of the word width to underline (centered)
        self.underline_focus_min_px = self.dpi.px(28)
        self.underline_thickness_px = max(1, self.dpi.px(1.2))
        self.underline_offset_px = self.dpi.px(2)
        self.line0_underline_offset_px = self.dpi.px(6)  # Shared tweak for first-line underlines
        self.underline_lock = threading.Lock()

        # Track all misspelled words with persistent underlines (keyed by unique underline id)
        self.misspelled_words = {}
        
        # Document-wide word tracking dictionary
        # Format: {word_index: {'word': str, 'corrected_word': str, 'suggestions': list, 
        #                       'position': int, 'has_error': bool, 'checked': bool}}
        self.document_words = {}  # Dictionary to store all words in document
        self.word_index_counter = 0  # Counter for unique word indices
        self.underline_sequence = 0  # Counter for persistent underline ids
        self.document_text_cache = ""  # Cache of last known document text
        self.document_lock = threading.Lock()  # Lock for document_words access
        
        self.caret_step_delay = 0.003
        
        self.current_word_chars = []  # Characters in the current word being typed/edited
        self.cursor_index = 0  # Position within the current word buffer
        self.enabled = True
        self.words_checked = 0
        self.last_word = ""  # Store last word for replacement
        self.last_underline_id: Optional[str] = None  # Track specific underline instance
        self.running = False  # Service running flag
        self.replacing = False  # Flag to prevent re-showing popup during replacement
        self.disable_scanning = False  # Skip key processing while programmatically inserting text
        self.just_replaced_word = False  # Track whether the last action was a replacement
        self.last_esc_time = 0  # Track last Esc press for double-tap detection
        self.last_clipboard_content = ""  # Track clipboard for paste detection
        self.clipboard_check_active = False  # Flag to enable clipboard monitoring
        self.last_replacement_time = 0  # Track when last replacement happened
        self.last_replaced_word = ""  # Track what word was just replaced
        self.shift_pressed = False  # Track if shift key is held (for selections)
        self.selection_anchor = None  # Anchor position when starting a selection
        self.selection_range = None  # Tuple[int, int] for current selection within the word
        self.last_committed_word_chars = []  # Snapshot of last word confirmed with delimiter
        self.pending_restore = False  # Indicates buffer was just restored after delimiter
        self.trailing_delimiter_count = 0  # Number of consecutive delimiters after last word
        self.last_delimiter_char = ' '  # Track the delimiter that triggered suggestion
        self.restore_allowed = False  # Allow one restore after trailing delimiters
        self.last_paste_anchor = None  # Snapshot of caret/window state before paste
        self.select_all_active = False  # Track if Ctrl+A was just pressed
        self.ctrl_held = False  # Track if Ctrl key is currently held down
        self._menu_paste_candidate: Optional[dict] = None  # Snapshot for context menu paste detection
        self.default_text_margin_px = self.dpi.px(18)
        self.default_baseline_offset_px = self.dpi.px(32)
        self.default_line_height_px = max(self.dpi.px(28), 16)
        self.paste_cooldown_until = 0.0  # Timestamp until per-key checks resume after paste
        self.layout_horizontal_padding_px = self.dpi.px(12)  # Safety padding when simulating client width
        self.layout_tab_stop_spaces = 4  # Approximate tab stop spacing (Notepad default = 8, but Kannada wider)
        self.layout_min_char_px = max(1, self.dpi.px(6))  # Guard for zero-width glyphs during layout
        self.paste_line_offsets = {
            0: self.dpi.px(-6),  # Lift first line slightly for tighter alignment
        }
        self.paste_default_line_offset_px = self.dpi.px(-18)  # Fallback shift for any additional lines
        self.paste_line_offset_increment_px = self.dpi.px(4)  # Push lower lines down a touch

        print("\n✅ Smart Keyboard Service initialized!")
        print("\n📝 Controls:")
        print("   Ctrl+Shift+K : Toggle suggestions ON/OFF")
        print("   ↑ / ↓        : Navigate suggestions")
        print("   Enter / Click: Replace word with selected suggestion")
        print("   Esc (popup)  : Hide suggestions")
        print("   Esc (twice)  : Stop the service")
        print("\n🚀 Service running... Type or paste Kannada text in any app to see suggestions!")
        print("="*70 + "\n")
        print("💡 TIP: Press Esc twice quickly to stop the service cleanly")

        # Track the active interface (Notepad, Word, etc.)
        self.current_interface = None
        self._interface_monitor = None
        self._refresh_scheduled = False
    
    def reset_current_word(self, preserve_delimiter=False, clear_marker=True):
        """Clear the tracked word buffer and reset caret index"""
        self.current_word_chars = []
        self.cursor_index = 0
        self.selection_anchor = None
        self.selection_range = None
        self.pending_restore = False
        self.restore_allowed = preserve_delimiter
        if not preserve_delimiter:
            self.trailing_delimiter_count = 0
            self.last_committed_word_chars = []
            self.last_delimiter_char = ' '

    def sync_committed_buffer(self):
        """Keep committed snapshot aligned with current buffer"""
        self.last_committed_word_chars = self.current_word_chars.copy()

    def is_word_delimiter(self, char):
        """Check if character is a word boundary"""
        if not char:
            return True
        return char in [' ', '\n', '\r', '\t', '.', ',', '!', '?', ';', ':']

    def is_kannada_char(self, char):
        """Check if character is Kannada"""
        return char and '\u0C80' <= char <= '\u0CFF'

    def _compute_focus_span(self, word_width: int) -> Tuple[int, int]:
        """Return (focus_width, offset_from_word_start) for centered underline."""
        if word_width <= 0:
            return 0, 0
        focus_width = max(1, int(word_width * self.underline_focus_ratio))
        focus_width = max(self.underline_focus_min_px, focus_width)
        focus_width = min(word_width, focus_width)
        offset = max(0, (word_width - focus_width) // 2)
        return focus_width, offset

    def _maybe_remove_underline_after_edit(self, before_snapshot: str) -> bool:
        """Remove underline if the misspelled word was completely deleted."""
        before = (before_snapshot or "").strip()
        after = ''.join(self.current_word_chars).strip()
        
        # If buffer is empty, check if we should remove the underline for the word that was there
        if not after:
            # Only remove underline if the deleted word was actually a Kannada word
            if before and any(self.is_kannada_char(c) for c in before):
                print(f"🔍 Removing underline for deleted Kannada word '{before}'")
                caret_index = self._get_caret_char_index()
                fallback_index = None
                if caret_index is not None and len(before) > 1:
                    fallback_index = max(0, caret_index + len(before) - 1)
                self.remove_persistent_underline(
                    before,
                    char_index=caret_index,
                    fallback_index=fallback_index,
                )
                return True
            # Fallback for last committed word (only if it was Kannada)
            if self.last_committed_word_chars:
                last_word = ''.join(self.last_committed_word_chars).strip()
                if last_word and any(self.is_kannada_char(c) for c in last_word):
                    print(f"🔍 Removing underline for deleted Kannada word '{last_word}' (from last_committed)")
                    caret_index = self._get_caret_char_index()
                    fallback_index = None
                    if caret_index is not None and len(last_word) > 1:
                        fallback_index = max(0, caret_index + len(last_word) - 1)
                    self.remove_persistent_underline(
                        last_word,
                        char_index=caret_index,
                        fallback_index=fallback_index,
                    )
                    return True
            return False
        
        # If buffer still has content, only remove if word was completely replaced
        if before and len(after) < len(before) * 0.5:  # Word reduced by more than half
            # Only process Kannada words
            if any(self.is_kannada_char(c) for c in before):
                # Check if current buffer is a prefix of the deleted word
                if before.startswith(after):
                    # Word was partially deleted, but might still be there - don't remove yet
                    return False
                # Word was replaced with something different - remove the old underline
                caret_index = self._get_caret_char_index()
                fallback_index = None
                if caret_index is not None and len(before) > 1:
                    fallback_index = max(0, caret_index + len(before) - 1)
                self.remove_persistent_underline(
                    before,
                    char_index=caret_index,
                    fallback_index=fallback_index,
                )
                return True
        return False

    def _resolve_absolute_position(self, info: dict) -> Tuple[Optional[int], Optional[int]]:
        """Get best-effort absolute screen coordinates for an underline."""
        start_x, start_y = (info.get('absolute_position') or (None, None))
        hwnd = info.get('hwnd')
        rel_x = info.get('relative_start_x')
        rel_y = info.get('relative_y')
        if hwnd and rel_x is not None and rel_y is not None:
            try:
                rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                rect = None
            if rect:
                start_x = rect[0] + rel_x
                start_y = rect[1] + rel_y
        return start_x, start_y

    def _remove_underlines_near_caret(self, tolerance: int = 8) -> bool:
        """Remove underline markers that intersect the current caret location."""

        if self.current_interface == "Notepad":
            return False

        try:
            caret_x, caret_y = get_caret_position()
        except Exception:
            return False

        with self.underline_lock:
            underline_items = list(self.misspelled_words.items())

        best_candidate = None
        best_distance = None
        for uid, info in underline_items:
            width = info.get('width', 0) or 0
            if width <= 0:
                continue

            word_x, word_y = info.get('absolute_position', (0, 0))
            hwnd = info.get('hwnd')
            rel_x = info.get('relative_start_x')
            rel_y = info.get('relative_y')

            rect = None
            if hwnd and rel_x is not None and rel_y is not None:
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                except Exception:
                    rect = None
                if rect:
                    word_x = rect[0] + rel_x
                    word_y = rect[1] + rel_y

            bbox = info.get('bbox') or {}
            left = bbox.get('left', word_x)
            right = bbox.get('right', word_x + width)
            top = bbox.get('top', word_y - (tolerance * 2))
            bottom = bbox.get('bottom', word_y + (tolerance * 2))

            if rect and rel_x is not None and rel_y is not None:
                left = word_x - tolerance
                right = word_x + width + tolerance
                top = word_y - (tolerance * 2)
                bottom = word_y + (tolerance * 2)

            horizontal_hit = left <= caret_x <= right
            vertical_hit = top <= caret_y <= bottom

            if horizontal_hit and vertical_hit:
                center_x = left + (width / 2.0)
                distance = abs(caret_x - center_x)
                if best_distance is None or distance < best_distance:
                    best_candidate = (uid, info.get('word'))
                    best_distance = distance

        if best_candidate:
            candidate, word = best_candidate
            if self.remove_persistent_underline(uid=candidate):
                print(f"🧽 Cleared underline id={candidate} near caret for '{word}'")
                return True

        return False

    def _clear_all_underlines_notepad(self):
        """Clear all persistent underlines when Ctrl+A + Backspace/Delete is used in Notepad."""
        print(f"🧹 Clearing all {len(self.misspelled_words)} underlines after select-all delete...")
        
        # Clear overlay canvas
        try:
            self.underline_overlay.clear_all_underlines()
        except Exception as e:
            print(f"⚠️ Error clearing overlay: {e}")
        
        # Clear tracking dictionary
        with self.underline_lock:
            self.misspelled_words.clear()
        
        # Clear document words cache
        with self.document_lock:
            self.document_words.clear()
        
        # Reset word buffer and related state
        self.current_word_chars = []
        self.cursor_index = 0
        self.last_committed_word_chars = []
        self.last_word = ""
        self.last_underline_id = None
        
        self._hide_overlay_temporarily()

        print("✅ All underlines cleared")

    def _clear_all_underlines_notepad_async(self):
        """Schedule a safe underline clear on the Tk thread when we detect empty content."""
        if not self.misspelled_words:
            return
        try:
            self.popup.root.after(0, self._clear_all_underlines_notepad)
        except Exception:
            self._clear_all_underlines_notepad()

    def _has_full_document_selection(self) -> bool:
        """Detect whether the entire document is currently selected in Notepad."""
        if self.current_interface != "Notepad":
            return False

        try:
            edit_hwnd = self._get_notepad_edit_hwnd()
            if not edit_hwnd:
                return False

            start = wintypes.DWORD()
            end = wintypes.DWORD()

            windll.user32.SendMessageW(edit_hwnd, win32con.EM_GETSEL, byref(start), byref(end))

            selection_start = int(start.value)
            selection_end = int(end.value)

            text_length = windll.user32.SendMessageW(edit_hwnd, win32con.WM_GETTEXTLENGTH, 0, 0)
            if selection_end == 0xFFFFFFFF:
                selection_end = text_length

            if selection_end < selection_start:
                selection_start, selection_end = selection_end, selection_start

            if selection_end <= selection_start:
                print(f"ℹ️ Select-all check: start={selection_start}, end={selection_end}, length={text_length} → no selection")
                return False

            if text_length <= 0:
                print(f"ℹ️ Select-all check: empty document (length={text_length})")
                return False

            # Require selection from document start and covering (nearly) entire content
            if selection_start != 0:
                print(f"ℹ️ Select-all check: selection does not start at 0 (start={selection_start})")
                return False

            if selection_end >= text_length:
                print(f"ℹ️ Select-all check: full selection detected (length={text_length})")
                return True

            # Some editors omit the final newline from the selection length; allow off-by-one in that case
            almost_full = text_length > 0 and (selection_end + 1) >= text_length
            print(
                f"ℹ️ Select-all check: nearly full={almost_full} (end={selection_end}, length={text_length})"
            )
            return almost_full
        except Exception as exc:
            print(f"⚠️ Full-selection detection failed: {exc}")
            return False

    def _should_clear_select_all(self) -> bool:
        """Return True if select-all deletion should clear overlay state."""
        if self.select_all_active:
            return True
        detected = self._has_full_document_selection()
        if detected:
            print("ℹ️ Select-all detected via foreground selection")
        return detected

    def _get_notepad_edit_hwnd(self) -> Optional[int]:
        """Return the HWND for Notepad's edit control if available."""
        try:
            foreground = windll.user32.GetForegroundWindow()
            if not foreground:
                return None

            thread_id = windll.user32.GetWindowThreadProcessId(foreground, 0)
            gui_info = GUITHREADINFO(cbSize=sizeof(GUITHREADINFO))

            if windll.user32.GetGUIThreadInfo(thread_id, byref(gui_info)):
                edit_hwnd = gui_info.hwndFocus or gui_info.hwndCaret
                if edit_hwnd:
                    return edit_hwnd

            child = win32gui.FindWindowEx(foreground, 0, "Edit", None)
            if child:
                return child
        except Exception as exc:
            print(f"⚠️ Failed to resolve Notepad edit control: {exc}")
        return None

    def _get_notepad_text_length(self) -> Optional[int]:
        """Best-effort document length for the active Notepad window."""
        if self.current_interface != "Notepad":
            return None

        edit_hwnd = self._get_notepad_edit_hwnd()
        if not edit_hwnd:
            return None

        try:
            length = windll.user32.SendMessageW(edit_hwnd, win32con.WM_GETTEXTLENGTH, 0, 0)
            return int(length)
        except Exception as exc:
            print(f"⚠️ Failed to query Notepad text length: {exc}")
            return None

    def _is_notepad_document_empty(self) -> bool:
        """Return True when the focused Notepad buffer currently has no visible content."""
        if self.current_interface != "Notepad":
            return False

        length = self._get_notepad_text_length()
        if length is not None:
            return length == 0

        try:
            text_snapshot = self.get_document_text()
        except Exception:
            text_snapshot = ""

        if not text_snapshot:
            return True

        return text_snapshot.strip() == ""

    def _get_caret_char_index(self) -> Optional[int]:
        """Return insertion-point index within the focused edit control when available."""
        candidate_hwnds: List[int] = []

        try:
            _, focus_hwnd = self._get_focus_handles()
            if focus_hwnd:
                candidate_hwnds.append(focus_hwnd)
        except Exception:
            pass

        if self.current_interface == "Notepad":
            try:
                edit_hwnd = self._get_notepad_edit_hwnd()
                if edit_hwnd and edit_hwnd not in candidate_hwnds:
                    candidate_hwnds.append(edit_hwnd)
            except Exception:
                pass

        for hwnd in candidate_hwnds:
            if not hwnd or not win32gui.IsWindow(hwnd):
                continue
            try:
                start = wintypes.DWORD()
                end = wintypes.DWORD()
                windll.user32.SendMessageW(hwnd, win32con.EM_GETSEL, byref(start), byref(end))
                caret_index = int(end.value)
                if caret_index >= 0:
                    return caret_index
            except Exception:
                continue
        return None

    def _get_line_index_from_char(
        self,
        text_hwnd: Optional[int],
        char_index: Optional[int],
    ) -> Optional[int]:
        """Return zero-based visual line index for a character when supported."""
        if not text_hwnd or char_index is None:
            return None
        try:
            line_idx = windll.user32.SendMessageW(text_hwnd, win32con.EM_LINEFROMCHAR, char_index, 0)
            if line_idx in (-1, 0xFFFFFFFF):
                return None
            return int(line_idx)
        except Exception:
            return None

    def _schedule_document_empty_check(self):
        """Run a short-delayed check to clear overlays if the document becomes empty."""
        if self.current_interface != "Notepad":
            return

        def _delayed_check():
            self._check_document_empty()

        threading.Timer(0.05, _delayed_check).start()

    def _check_document_empty(self):
        if self.current_interface != "Notepad":
            return

        length = self._get_notepad_text_length()
        if length is None:
            return

        if length == 0 and self.misspelled_words:
            print("🧹 Notepad document is empty after deletion - clearing underlines")
            self.select_all_active = False
            # Run on Tk thread to avoid cross-thread canvas calls
            try:
                self.popup.root.after(0, self._clear_all_underlines_notepad)
            except Exception:
                # Fallback to direct call if Tk loop not available
                self._clear_all_underlines_notepad()

    def _window_handles_match(self, stored_hwnd: Optional[int], target_hwnd: Optional[int]) -> bool:
        if not stored_hwnd or not target_hwnd:
            return False
        if stored_hwnd == target_hwnd:
            return True
        try:
            stored_root = win32gui.GetAncestor(stored_hwnd, win32con.GA_ROOT)
        except Exception:
            stored_root = stored_hwnd
        try:
            target_root = win32gui.GetAncestor(target_hwnd, win32con.GA_ROOT)
        except Exception:
            target_root = target_hwnd
        return stored_root == target_root

    def _find_matching_underline_hwnd(self, hwnd: Optional[int]) -> Optional[int]:
        if not hwnd:
            return None
        with self.underline_lock:
            for info in self.misspelled_words.values():
                stored_hwnd = info.get('hwnd')
                if stored_hwnd and self._window_handles_match(stored_hwnd, hwnd):
                    return stored_hwnd
        return None

    def _show_overlay_for_hwnd(self, hwnd: Optional[int]):
        if not hwnd:
            return
        try:
            self.underline_overlay.show(hwnd)
            self.active_overlay_hwnd = hwnd
        except Exception as exc:
            print(f"⚠️ Failed to show overlay for hwnd {hwnd}: {exc}")

    def _hide_overlay_temporarily(self):
        self.active_overlay_hwnd = None
        if not self.underline_overlay.visible:
            return
        try:
            self.underline_overlay.hide()
        except Exception as exc:
            print(f"⚠️ Failed to hide overlay: {exc}")

    def _handle_interface_switch(
        self,
        previous_interface: Optional[str],
        new_interface: Optional[str],
        previous_hwnd: Optional[int],
        new_hwnd: Optional[int],
    ):
        overlay_hwnd = self.active_overlay_hwnd
        overlay_matches_new = (
            self._window_handles_match(overlay_hwnd, new_hwnd)
            if overlay_hwnd and new_hwnd
            else False
        )

        popup_hwnd = None
        try:
            popup_hwnd = self.popup.get_window_handle()
        except Exception:
            popup_hwnd = None

        overlay_window_hwnd = None
        try:
            overlay_window_hwnd = self.underline_overlay.get_window_handle()
        except Exception:
            overlay_window_hwnd = None

        ignored_hwnds = {
            hwnd for hwnd in (popup_hwnd, overlay_window_hwnd) if hwnd
        }

        if overlay_hwnd and not overlay_matches_new:
            if not new_hwnd or new_hwnd not in ignored_hwnds:
                self._hide_overlay_temporarily()

        try:
            popup_owner = self.popup.current_hwnd
        except Exception:
            popup_owner = None
        if popup_owner and new_hwnd and not self._window_handles_match(popup_owner, new_hwnd):
            self.popup.hide()

        # Attempt to reattach overlay when returning to a window that still has underlines
        target_hwnd = self._find_matching_underline_hwnd(new_hwnd)

        if target_hwnd and self.active_overlay_hwnd != target_hwnd:
            self._show_overlay_for_hwnd(target_hwnd)

    def _start_interface_monitor(self):
        """Start monitoring the foreground window so we can log interface changes."""
        if self._interface_monitor and self._interface_monitor.is_alive():
            return
        self._interface_monitor = threading.Thread(
            target=self._monitor_active_window,
            daemon=True,
        )
        self._interface_monitor.start()

    def _monitor_active_window(self):
        """Detect foreground window switches and announce the active interface."""
        last_interface = None
        last_hwnd = None
        while self.running:
            try:
                hwnd = win32gui.GetForegroundWindow()
                if not hwnd:
                    time.sleep(0.5)
                    continue

                class_name = win32gui.GetClassName(hwnd)
                title = win32gui.GetWindowText(hwnd)
                interface = self._classify_interface(class_name, title)

                if interface != last_interface or hwnd != last_hwnd:
                    previous_interface = last_interface
                    previous_hwnd = last_hwnd
                    last_interface = interface
                    last_hwnd = hwnd
                    self.current_interface = interface
                    if interface:
                        print(f"🪟 Active interface detected: {interface}", flush=True)
                    self._handle_interface_switch(previous_interface, interface, previous_hwnd, hwnd)
            except Exception as exc:
                print(f"⚠️ Interface detection error: {exc}")
                time.sleep(1.5)
            else:
                time.sleep(0.5)

    def _classify_interface(self, class_name: str, title: str) -> Optional[str]:
        """Return a friendly name for the current window."""
        title_lower = (title or "").lower()
        class_lower = (class_name or "").lower()

        if "notepad" in title_lower or class_lower == "notepad":
            return "Notepad"

        if "word" in title_lower or class_lower == "opusapp":
            return "Microsoft Word"

        if title:
            return title

        return class_name

    def _get_caret_height(self, hwnd: Optional[int]) -> Optional[int]:
        """Best-effort caret height for dynamic underline placement."""
        if not hwnd:
            return None
        try:
            rect = self.caret_tracker.get_caret_rect(hwnd)
            if rect:
                height = int(round(rect.get('height', 0)))
                return max(height, 1) if height else None
        except Exception:
            return None
        return None

    def _compute_underline_offset(self, caret_height: Optional[int]) -> int:
        """Return underline offset based on caret height and DPI fallback."""
        if caret_height and caret_height > 0:
            dynamic = int(round(caret_height * 0.15))
            return max(self.underline_offset_px, dynamic)
        return self.underline_offset_px

    def _compute_underline_padding(self, caret_height: Optional[int]) -> int:
        """Return bounding box padding scaled to caret height."""
        base_padding = self.dpi.px(8)
        if caret_height and caret_height > 0:
            dynamic = int(round(caret_height * 0.4))
            return max(base_padding, dynamic)
        return base_padding

    def _resolve_underline_color(self, has_suggestions: bool) -> str:
        """Pick underline color based on active interface and suggestion availability."""
        if self.current_interface == "Microsoft Word":
            return "#0078D7" if has_suggestions else "#FF3B30"
        return "#F57C00" if has_suggestions else "#FF3B30"

    def type_delimiter_key(self, delimiter):
        """Re-type the delimiter that triggered the suggestion"""
        if not delimiter:
            return
        if delimiter == ' ':
            self.keyboard_controller.press(Key.space)
            self.keyboard_controller.release(Key.space)
        elif delimiter in ('\n', '\r'):
            self.keyboard_controller.press(Key.enter)
            self.keyboard_controller.release(Key.enter)
        elif delimiter == '\t':
            self.keyboard_controller.press(Key.tab)
            self.keyboard_controller.release(Key.tab)
        else:
            self.keyboard_controller.type(delimiter)
    
    def add_persistent_underline(
        self,
        word: str,
        suggestions: list,
        caret_x: int,
        caret_y: int,
        word_width: int,
        word_start_x: int,
        *,
        hwnd: Optional[int] = None,
        text_hwnd: Optional[int] = None,
        window_rect: Optional[Tuple[int, int, int, int]] = None,
        relative_start_x: Optional[int] = None,
        relative_y: Optional[int] = None,
        caret_height: Optional[int] = None,
        char_start: Optional[int] = None,
        char_length: Optional[int] = None,
        draw_overlay: bool = True,
    ):
        try:
            has_suggestions = len(suggestions) > 0
            color = self._resolve_underline_color(has_suggestions)
            style = "wavy"

            if draw_overlay:
                needs_show = not self.underline_overlay.visible or not self._window_handles_match(self.active_overlay_hwnd, hwnd)
                if needs_show:
                    self._show_overlay_for_hwnd(hwnd)

            height = caret_height if caret_height and caret_height > 0 else self._get_caret_height(hwnd)
            underline_offset = self._compute_underline_offset(height)
            underline_y = caret_y + underline_offset

            rect = window_rect
            if hwnd and rect is None:
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                except Exception:
                    rect = None

            rel_start = relative_start_x
            rel_y = relative_y
            if rect:
                if rel_start is None:
                    rel_start = word_start_x - rect[0]
                if rel_y is None:
                    rel_y = underline_y - rect[1]

            underline_padding = self._compute_underline_padding(height)
            bbox = {
                'left': word_start_x,
                'top': underline_y - underline_padding,
                'right': word_start_x + word_width,
                'bottom': underline_y + underline_padding,
            }

            line_index = self._get_line_index_from_char(text_hwnd, char_start)
            if line_index is None and char_start is not None and char_length:
                try:
                    alt_index = max(0, char_start + char_length - 1)
                except Exception:
                    alt_index = char_start
                if alt_index is not None:
                    line_index = self._get_line_index_from_char(text_hwnd, alt_index)
            if line_index is None:
                try:
                    if rect and height:
                        line_index = int(round((underline_y - rect[1]) / max(1, height)))
                    elif height:
                        line_index = int(round(caret_y / max(1, height)))
                except Exception:
                    line_index = None
            if line_index is not None and line_index < 0:
                line_index = 0

            with self.underline_lock:
                underline_index = self.underline_sequence
                self.underline_sequence += 1
                uid = f"{word}-{underline_index:04d}-{uuid.uuid4().hex[:6]}"

                underline_info = {
                    'id': uid,
                    'word': word,
                    'suggestions': suggestions,
                    'hwnd': hwnd,
                    'text_hwnd': text_hwnd,
                    'absolute_position': (word_start_x, underline_y),
                    'relative_start_x': rel_start,
                    'relative_y': rel_y,
                    'width': word_width,
                    'bbox': bbox,
                    'last_rect': rect,
                    'added_at': time.time(),
                    'caret_height': height,
                    'char_start': char_start,
                    'char_length': char_length if char_length is not None else len(word),
                    'line_index': line_index,
                }

                self.misspelled_words[uid] = underline_info
                total = len(self.misspelled_words)

            if draw_overlay:
                self.underline_overlay.add_underline(
                    word_id=uid,
                    word_x=word_start_x,
                    word_y=underline_y,
                    word_width=word_width,
                    color=color,
                    style=style,
                    hwnd=hwnd,
                )

            print(
                f"{'🟠' if has_suggestions else '🔴'} Added persistent underline for "
                f"'{word}' (id={uid}) - Total misspelled: {total}"
            )

            return uid

        except Exception as exc:
            print(f"⚠️ Failed to add persistent underline for '{word}': {exc}")
            return None
    
    def remove_persistent_underline(
        self,
        word: Optional[str] = None,
        uid: Optional[str] = None,
        *,
        char_index: Optional[int] = None,
        fallback_index: Optional[int] = None,
    ) -> bool:
        """Remove persistent underline entries by unique ID or by word."""

        if not word and not uid:
            return False

        removed_any = False
        removed_count = 0
        failed = []

        with self.underline_lock:
            candidates: List[str] = []
            if uid:
                if uid in self.misspelled_words:
                    candidates.append(uid)
            elif word:
                candidates = [
                    entry_id
                    for entry_id, info in self.misspelled_words.items()
                    if info.get('word') == word
                ]

            if word and len(candidates) > 1:
                caret_index = char_index
                if caret_index is None:
                    caret_index = self._get_caret_char_index()
                matched_candidate = None
                if caret_index is not None:
                    best_score = None
                    for candidate in candidates:
                        info = self.misspelled_words.get(candidate)
                        if not info:
                            continue
                        char_start = info.get('char_start')
                        char_length = info.get('char_length') or len(info.get('word') or "")
                        if char_start is None:
                            continue
                        span_length = max(char_length, 1)
                        span_start = char_start
                        span_end = char_start + span_length  # exclusive upper bound
                        if span_start <= caret_index < span_end:
                            score = 0
                        else:
                            distance = min(abs(caret_index - span_start), abs(caret_index - (span_end - 1)))
                            score = distance + 1
                        if best_score is None or score < best_score:
                            best_score = score
                            matched_candidate = candidate

                if matched_candidate is None and fallback_index is not None:
                    caret_index = fallback_index
                    best_score = None
                    for candidate in candidates:
                        info = self.misspelled_words.get(candidate)
                        if not info:
                            continue
                        char_start = info.get('char_start')
                        char_length = info.get('char_length') or len(info.get('word') or "")
                        if char_start is None:
                            continue
                        span_length = max(char_length, 1)
                        span_start = char_start
                        span_end = char_start + span_length
                        if span_start <= caret_index < span_end:
                            score = 0
                        else:
                            distance = min(abs(caret_index - span_start), abs(caret_index - (span_end - 1)))
                            score = distance + 1
                        if best_score is None or score < best_score:
                            best_score = score
                            matched_candidate = candidate

                try:
                    caret_x, caret_y = get_caret_position()
                except Exception:
                    caret_x = caret_y = None

                if matched_candidate is None and caret_x is not None and caret_y is not None:
                    for candidate in candidates:
                        info = self.misspelled_words.get(candidate)
                        if not info:
                            continue
                        width = info.get('width', 0) or 0
                        if width <= 0:
                            continue
                        word_x, word_y = info.get('absolute_position', (0, 0))
                        hwnd = info.get('hwnd')
                        rel_x = info.get('relative_start_x')
                        rel_y = info.get('relative_y')
                        rect = None
                        if hwnd and rel_x is not None and rel_y is not None:
                            try:
                                rect = win32gui.GetWindowRect(hwnd)
                            except Exception:
                                rect = None
                            if rect:
                                word_x = rect[0] + rel_x
                                word_y = rect[1] + rel_y

                        bbox = info.get('bbox') or {}
                        left = bbox.get('left', word_x)
                        right = bbox.get('right', word_x + width)
                        top = bbox.get('top', word_y - self.dpi.px(6))
                        bottom = bbox.get('bottom', word_y + self.dpi.px(6))

                        if left <= caret_x <= right and top <= caret_y <= bottom:
                            matched_candidate = candidate
                            break

                if not matched_candidate:
                    matched_candidate = candidates[-1]
                candidates = [matched_candidate] if matched_candidate else candidates[:1]

            for candidate in candidates:
                info = self.misspelled_words.pop(candidate, None)
                if not info:
                    continue
                removed_any = True
                removed_count += 1
                try:
                    self.underline_overlay.remove_underline(candidate)
                except Exception as exc:
                    failed.append((candidate, str(exc)))

        if removed_any:
            remaining = len(self.misspelled_words)
            target_desc = uid or word
            print(
                f"✅ Removed {removed_count} underline(s) for '{target_desc}' - Remaining: {remaining}"
            )
        if failed:
            for candidate, reason in failed:
                print(f"⚠️ Failed to remove overlay underline {candidate}: {reason}")

        with self.underline_lock:
            no_underlines_remaining = not self.misspelled_words
        if no_underlines_remaining:
            self._hide_overlay_temporarily()

        return removed_any

    def _shift_underlines_after(
        self,
        pivot_index: Optional[int],
        delta_chars: int,
        *,
        hwnd: Optional[int] = None,
        exclude_uid: Optional[str] = None,
    ):
        """Adjust stored character offsets when text before an underline changes."""
        if not delta_chars or pivot_index is None:
            return

        with self.underline_lock:
            for uid, info in self.misspelled_words.items():
                if uid == exclude_uid:
                    continue
                if hwnd and info.get('hwnd') not in (hwnd, None):
                    continue
                char_start = info.get('char_start')
                if char_start is None:
                    continue
                if char_start > pivot_index:
                    info['char_start'] = char_start + delta_chars

    def _schedule_refresh_if_needed(self, reason: str, delay: float = 0.08):
        """Schedule geometry refresh only when underlines exist."""
        with self.underline_lock:
            has_underlines = bool(self.misspelled_words)
        if has_underlines:
            self._schedule_underlines_refresh(delay=delay, reason=reason)

    def _schedule_underlines_refresh(self, delay: float = 0.05, *, reason: str = ""):
        """Trigger an async refresh of underline geometry after document edits."""

        with self.underline_lock:
            if self._refresh_scheduled:
                return
            self._refresh_scheduled = True

        def worker():
            if delay > 0:
                time.sleep(delay)
            try:
                self._refresh_underlines_geometry(reason=reason)
            except Exception as exc:
                print(f"⚠️ Underline refresh failed ({reason or 'unspecified'}): {exc}")
            finally:
                with self.underline_lock:
                    self._refresh_scheduled = False

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_underlines_geometry(self, *, reason: str = ""):
        """Recalculate underline screen coordinates using live document layout."""
        with self.underline_lock:
            entries = list(self.misspelled_words.items())

        if not entries:
            return

        baseline_map: Dict[int, Dict[int, int]] = {}
        for _, stored_info in entries:
            hwnd = stored_info.get('hwnd')
            if not hwnd:
                continue
            line_idx = stored_info.get('line_index')
            relative = stored_info.get('relative_y')
            if line_idx is None or relative is None:
                continue
            try:
                normalized_line = max(0, int(line_idx))
            except (TypeError, ValueError):
                continue
            try:
                relative_val = int(round(relative))
            except Exception:
                continue
            baseline_map.setdefault(hwnd, {}).setdefault(normalized_line, relative_val)

        doc_text = self.get_document_text()
        if not doc_text:
            return

        for uid, info in entries:
            word = info.get('word')
            hwnd = info.get('hwnd')
            if not word or not hwnd or not win32gui.IsWindow(hwnd):
                continue

            text_hwnd = info.get('text_hwnd') or hwnd
            if not text_hwnd or not win32gui.IsWindow(text_hwnd):
                text_hwnd = hwnd

            char_start = info.get('char_start')
            char_length = info.get('char_length') or len(word)
            if char_start is None or char_length <= 0:
                continue

            updated_char_start = char_start
            doc_len = len(doc_text)

            if (
                updated_char_start < 0
                or updated_char_start + char_length > doc_len
                or doc_text[updated_char_start:updated_char_start + char_length] != word
            ):
                search_radius = max(32, len(word) * 2)
                start_idx = max(0, updated_char_start - search_radius)
                end_idx = min(doc_len, updated_char_start + search_radius)
                new_index = doc_text.find(word, start_idx, end_idx)
                if new_index == -1:
                    new_index = doc_text.find(word)
                if new_index == -1:
                    self.remove_persistent_underline(uid=uid)
                    continue
                updated_char_start = new_index

            geometry = self._recalculate_word_geometry(
                word,
                updated_char_start,
                text_hwnd,
                hwnd,
                info,
            )
            if not geometry:
                continue

            start_x = geometry['start_x']
            caret_y = geometry['caret_y']
            word_width = max(1, geometry['width'])
            window_rect = geometry['window_rect']
            caret_height = geometry['caret_height']
            underline_offset = self._compute_underline_offset(caret_height)
            underline_y = caret_y + underline_offset
            # ----------------------------------------------------------
            # Maintain shared adjustments for the first two visual lines
            # ----------------------------------------------------------
            line_index = self._get_line_index_from_char(text_hwnd, updated_char_start)
            if line_index is None and char_length:
                try:
                    alt_index = max(0, updated_char_start + char_length - 1)
                except Exception:
                    alt_index = updated_char_start
                if alt_index is not None:
                    line_index = self._get_line_index_from_char(text_hwnd, alt_index)
            if line_index is None:
                prior_index = info.get('line_index')
                if prior_index is not None:
                    try:
                        line_index = int(prior_index)
                    except (TypeError, ValueError):
                        line_index = None
            if line_index is None and window_rect:
                try:
                    reference_height = caret_height or info.get('caret_height') or self._estimate_line_height(text_hwnd)
                    if reference_height and reference_height > 0:
                        relative_line = underline_y - window_rect[1]
                        line_index = int(round(relative_line / reference_height))
                except Exception:
                    line_index = None
            if line_index is not None and line_index < 0:
                line_index = 0

            stored_line_baseline = None
            if hwnd and line_index is not None:
                hw_lines = baseline_map.get(hwnd)
                if hw_lines:
                    stored_line_baseline = hw_lines.get(line_index)

            if stored_line_baseline is not None and window_rect:
                underline_y = window_rect[1] + stored_line_baseline
            elif line_index == 0:
                underline_y += self.line0_underline_offset_px
            underline_padding = self._compute_underline_padding(caret_height)

            relative_start = None
            relative_y = None
            if window_rect:
                relative_start = start_x - window_rect[0]
                relative_y = underline_y - window_rect[1]
                prev_relative = info.get('relative_y')
                prev_char_start = info.get('char_start')
                if (
                    relative_y is not None
                    and prev_relative is not None
                    and prev_char_start is not None
                    and updated_char_start == prev_char_start
                ):
                    tolerance = self.dpi.px(3)
                    if relative_y + tolerance < prev_relative:
                        relative_y = prev_relative
                        underline_y = window_rect[1] + relative_y
                        caret_y = underline_y - self._compute_underline_offset(caret_height)
                if relative_y is not None:
                    relative_y = max(relative_y, self.dpi.px(2))

            bbox = {
                'left': start_x,
                'top': underline_y - underline_padding,
                'right': start_x + word_width,
                'bottom': underline_y + underline_padding,
            }

            with self.underline_lock:
                stored = self.misspelled_words.get(uid)
                if not stored:
                    continue
                stored.update({
                    'absolute_position': (start_x, underline_y),
                    'relative_start_x': relative_start,
                    'relative_y': relative_y,
                    'width': word_width,
                    'bbox': bbox,
                    'caret_height': caret_height,
                    'char_start': updated_char_start,
                    'char_length': len(word),
                    'last_rect': window_rect,
                    'text_hwnd': text_hwnd,
                    'line_index': line_index,
                })

            if (
                hwnd
                and window_rect
                and line_index is not None
                and relative_y is not None
            ):
                normalized_index = None
                relative_val = None
                try:
                    normalized_index = max(0, int(line_index))
                    relative_val = int(round(relative_y))
                except Exception:
                    pass
                if normalized_index is not None and relative_val is not None:
                    baseline_map.setdefault(hwnd, {})[normalized_index] = relative_val

            color = self._resolve_underline_color(bool(info.get('suggestions')))
            self.underline_overlay.add_underline(
                word_id=uid,
                word_x=start_x,
                word_y=underline_y,
                word_width=word_width,
                color=color,
                style='wavy',
                hwnd=hwnd,
            )

    def _recalculate_word_geometry(
        self,
        word: str,
        char_start: int,
        text_hwnd: int,
        hwnd: int,
        info: dict,
    ) -> Optional[dict]:
        """Measure the onscreen geometry for a word starting at a given index."""
        if not word or not hwnd or not win32gui.IsWindow(hwnd):
            return None

        if not text_hwnd or not win32gui.IsWindow(text_hwnd):
            return None

        try:
            try:
                window_rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                window_rect = None

            spans = list(re.finditer(r'[^\s\n\r\t.,!?;:]+', word))
            if not spans:
                return None

            line_height = info.get('caret_height') or self._estimate_line_height(text_hwnd)
            geometry = {
                'hwnd': hwnd,
                'text_hwnd': text_hwnd,
                'window_rect': window_rect,
                'line_height': line_height,
                'selection_start': char_start,
            }

            layout_map = self._build_notepad_layout(word, spans, geometry)
            layout_info = layout_map.get(0)
            if not layout_info:
                return None

            caret_height = info.get('caret_height') or self._get_caret_height(hwnd)
            if caret_height is None:
                caret_height = line_height

            return {
                'start_x': layout_info['start_x'],
                'caret_y': layout_info['baseline_y'],
                'width': layout_info['width'],
                'window_rect': window_rect,
                'caret_height': caret_height,
            }

        except Exception as exc:
            print(f"⚠️ Unable to recompute geometry for '{word}': {exc}")
            return None
    
    def on_mouse_click(self, x, y, button, pressed):
        """Handle mouse clicks to detect clicks on underlined words"""
        if button == Button.right:
            if pressed:
                self._prepare_mouse_paste_candidate()
            return

        if button != Button.left:
            return

        if self.current_interface == "Microsoft Word" and Dispatch is not None:
            if pressed:
                return
            self._maybe_trigger_mouse_paste_check()
            time.sleep(0.05)
            self._handle_word_click()
            return

        if not pressed:
            self._maybe_trigger_mouse_paste_check()
            return
        
        # Small delay to let caret position update
        time.sleep(0.05)
        
        with self.underline_lock:
            underline_items = list(self.misspelled_words.items())

        # Check if click is within the underlined word area (with some tolerance)
        for uid, info in underline_items:
            word = info.get('word')
            rect = None
            word_x, word_y = info.get('absolute_position', (0, 0))
            hwnd = info.get('hwnd')
            rel_x = info.get('relative_start_x')
            rel_y = info.get('relative_y')
            if hwnd and rel_x is not None and rel_y is not None:
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                except Exception:
                    rect = None
                if rect:
                    word_x = rect[0] + rel_x
                    word_y = rect[1] + rel_y

            word_width = info.get('width', 0)
            if word_width <= 0:
                continue

            bbox = info.get('bbox') or {}
            left = bbox.get('left', word_x)
            right = bbox.get('right', word_x + word_width)
            top = bbox.get('top', word_y - 14)
            bottom = bbox.get('bottom', word_y + 18)

            if rect and rel_x is not None and rel_y is not None:
                left = word_x - 4
                right = word_x + word_width + 4
                top = word_y - 14
                bottom = word_y + 18

            if left <= x <= right and top <= y <= bottom:
                
                # User clicked on this underlined word!
                suggestions = info['suggestions']
                print(f"🖱️ Clicked on underlined word '{word}' - showing suggestions")
                
                if suggestions:
                    self.last_underline_id = uid
                    self.last_word = word
                    target_hwnd = info.get('hwnd')
                    current_hwnd = None
                    try:
                        current_hwnd = win32gui.GetForegroundWindow()
                    except Exception:
                        current_hwnd = None
                    if target_hwnd and current_hwnd and not self._window_handles_match(target_hwnd, current_hwnd):
                        print("ℹ️ Ignoring click: interface switched during click")
                        return
                    self.popup.show(suggestions)
                else:
                    print(f"⚠️ No suggestions available for '{word}'")
                break

    def _handle_word_click(self) -> None:
        """Show suggestions for the currently selected Word token."""
        try:
            word_app = Dispatch("Word.Application")
            selection = getattr(word_app, "Selection", None)
            if not selection:
                return

            word_range = selection.Words(1)
            raw_text = getattr(word_range, "Text", "") if word_range else ""
        except Exception:
            raw_text = ""

        word_text = (raw_text or "").strip().strip("\r\n\t\u0007")
        if not word_text:
            return

        normalized = re.sub(r"[.,!?;:]+$", "", word_text)
        if not normalized:
            return

        with self.underline_lock:
            items = list(self.misspelled_words.items())

        for uid, info in items:
            if info.get("word") != normalized:
                continue

            suggestions = info.get("suggestions") or []
            if not suggestions:
                continue

            self.last_underline_id = uid
            self.last_word = normalized
            self.popup.show(suggestions)
            return

        suggestions, had_error = self.get_suggestions(normalized)
        if had_error and suggestions:
            self.last_underline_id = None
            self.last_word = normalized
            self.popup.show(suggestions)
    
    def _move_caret(self, key, steps: int):
        """Move caret left/right by a given number of steps."""
        if steps <= 0:
            return
        for _ in range(steps):
            try:
                self.keyboard_controller.press(key)
                self.keyboard_controller.release(key)
            except Exception:
                break
            time.sleep(self.caret_step_delay)

    def move_caret_left(self, steps: int):
        self._move_caret(Key.left, steps)

    def move_caret_right(self, steps: int):
        self._move_caret(Key.right, steps)

    def _compute_typed_word_overlay(self, word: str, geometry: dict) -> Optional[dict]:
        """Return precise overlay geometry for a typed word using live layout data."""
        if not word:
            return None

        text_hwnd = geometry.get('text_hwnd') or geometry.get('hwnd')
        selection_start = geometry.get('selection_start')
        if not text_hwnd or selection_start is None:
            return None

        full_text = self.get_document_text()
        if not full_text:
            return None

        cursor_index = min(selection_start, len(full_text))

        # Back up past any delimiters (space, newline, etc.) to reach the word end.
        word_end = cursor_index
        while word_end > 0 and self.is_word_delimiter(full_text[word_end - 1]):
            word_end -= 1

        word_start = word_end - len(word)
        if word_start < 0 or full_text[word_start:word_end] != word:
            candidate = full_text.rfind(word, 0, word_end)
            if candidate == -1:
                return None
            word_start = candidate
            word_end = word_start + len(word)

        spans = list(re.finditer(r'[^\s\n\r\t.,!?;:]+', word))
        if not spans:
            return None

        typed_geometry = geometry.copy()
        typed_geometry['selection_start'] = word_start

        layout_map = self._build_notepad_layout(word, spans, typed_geometry)
        layout_info = layout_map.get(0)
        if not layout_info:
            return None

        word_start_x = layout_info['start_x']
        word_width = layout_info['width']
        caret_y = layout_info['baseline_y']
        caret_x = word_start_x + word_width

        return {
            'word_start_x': word_start_x,
            'word_width': word_width,
            'caret_y': caret_y,
            'caret_x': caret_x,
            'hwnd': geometry.get('hwnd'),
            'window_rect': geometry.get('window_rect'),
            'text_hwnd': geometry.get('text_hwnd'),
            'char_start': word_start,
            'char_length': len(word),
        }

    def show_no_suggestion_marker(self, word: str, has_suggestions: bool = False, suggestions: list = None):
        """Show persistent underline directly beneath the misspelled Kannada word.
        
        Args:
            word: The word to underline
            has_suggestions: True if suggestions available (orange), False for severe errors (red)
            suggestions: List of suggestions for this word
        """
        if not word or not self.enabled:
            return
        is_word_app = self.current_interface == "Microsoft Word"
        underline_id: Optional[str] = None
        try:
            geometry = self._capture_live_geometry()
            overlay_info = self._compute_typed_word_overlay(word, geometry) if geometry else None

            caret_x = None
            caret_y = None
            word_width = None
            word_start_x = None
            window_rect = None
            hwnd = None
            text_hwnd = None
            char_start = None
            char_length = len(word)

            if overlay_info:
                hwnd = overlay_info.get('hwnd')
                window_rect = overlay_info.get('window_rect')
                caret_x = overlay_info.get('caret_x')
                caret_y = overlay_info.get('caret_y')
                word_width = overlay_info.get('word_width')
                word_start_x = overlay_info.get('word_start_x')
                text_hwnd = overlay_info.get('text_hwnd')
                char_start = overlay_info.get('char_start')
                char_length = overlay_info.get('char_length') or char_length

            if not hwnd or not win32gui.IsWindow(hwnd):
                try:
                    hwnd = windll.user32.GetForegroundWindow()
                except Exception:
                    hwnd = None

            if not text_hwnd and geometry:
                text_hwnd = geometry.get('text_hwnd')

            if char_start is None and geometry:
                selection_start = geometry.get('selection_start')
                if selection_start is not None:
                    char_start = max(0, selection_start - len(word))

            caret_rect_raw = self.caret_tracker.get_caret_rect(hwnd) if self.caret_tracker else None
            caret_rect = self.caret_tracker.get_scaled_rect(caret_rect_raw, self.dpi.scale) if caret_rect_raw else None
            caret_height = None

            if caret_rect:
                caret_width = max(caret_rect['width'], 1)
                caret_height = max(caret_rect['height'], 1)
                caret_x = caret_rect['left'] + caret_width
                caret_y = caret_rect['top'] + caret_height

            if word_width is None:
                if hwnd:
                    try:
                        word_width = self.caret_tracker.measure_text_width(word, hwnd)
                    except Exception:
                        word_width = measure_text_width(word, hwnd)
                else:
                    word_width = measure_text_width(word, hwnd)

            if caret_x is None or caret_y is None:
                caret_x, caret_y = get_caret_position()
                if caret_height is None:
                    caret_height = self._get_caret_height(hwnd)

            if caret_height is None:
                caret_height = self._get_caret_height(hwnd)

            if word_start_x is None:
                word_start_x = caret_x - (word_width or 0)

            if window_rect is None and hwnd:
                try:
                    window_rect = win32gui.GetWindowRect(hwnd)
                except Exception:
                    window_rect = None

            relative_start = None
            relative_y = None
            if window_rect:
                relative_start = word_start_x - window_rect[0]
                underline_offset = self._compute_underline_offset(caret_height)
                relative_y = (caret_y + underline_offset) - window_rect[1]

            if caret_height is None:
                caret_height = self._estimate_line_height(text_hwnd or hwnd)
            
            underline_id = self.add_persistent_underline(
                word=word,
                suggestions=suggestions or [],
                caret_x=caret_x,
                caret_y=caret_y,
                word_width=word_width,
                word_start_x=word_start_x,
                hwnd=hwnd,
                text_hwnd=text_hwnd,
                window_rect=window_rect,
                relative_start_x=relative_start,
                relative_y=relative_y,
                caret_height=caret_height,
                char_start=char_start,
                char_length=char_length,
                draw_overlay=not is_word_app,
            )
        except Exception as exc:
            print(f"⚠️ Unable to underline word '{word}': {exc}")
            underline_id = None

        if is_word_app:
            com_result = self._apply_word_underline_via_com(
                word,
                has_suggestions or bool(suggestions),
                (suggestions or []),
            )
            return underline_id or com_result

        return underline_id

    def _apply_word_underline_via_com(
        self,
        word: str,
        has_suggestions: bool,
        suggestions: List[str],
    ) -> Optional[str]:
        """Drive Microsoft Word's native wavy underline via COM automation."""
        if Dispatch is None:
            print("⚠️ Word COM automation unavailable (win32com not installed)")
            return None

        try:
            word_app = Dispatch("Word.Application")
        except Exception as exc:
            print(f"⚠️ Unable to attach to Word: {exc}")
            return None

        try:
            doc = word_app.ActiveDocument
        except Exception as exc:
            print(f"⚠️ Word automation error (ActiveDocument): {exc}")
            return None

        if doc is None:
            print("⚠️ No active Word document detected")
            return None

        try:
            find_range = doc.Content.Duplicate
            find = find_range.Find
            find.ClearFormatting()
            find.Text = word
            find.MatchWholeWord = True
            find.MatchCase = False
            find.Forward = True
            find.Wrap = 0  # wdFindStop

            found = 0
            marker = "🔵" if has_suggestions else "🔴"
            underline_style = 4 if has_suggestions else 11  # wdUnderlineWavyHeavy / wdUnderlineWavy
            underline_color = 12611584 if has_suggestions else 255  # Blue / Red

            while find.Execute():
                found += 1
                range_to_format = find_range.Duplicate
                try:
                    range_to_format.MoveStartWhile(" \t\r\n", 1)
                except Exception:
                    pass
                try:
                    range_to_format.MoveEndWhile(" \t\r\n", -1)
                except Exception:
                    pass

                has_chars = range_to_format.Characters.Count > 0
                if has_chars:
                    # Apply underline directly in Word's document range (excluding whitespace)
                    range_to_format.Font.Underline = underline_style
                    range_to_format.Font.UnderlineColor = underline_color

                    # Ensure trailing whitespace after the word stays clean so squiggles don't bridge words
                    try:
                        space_range = doc.Range(range_to_format.End, min(range_to_format.End + 1, doc.Content.End))
                        if space_range and space_range.Characters.Count:
                            space_range.Font.Underline = 0
                            space_range.Font.UnderlineColor = 0
                            space_range.Font.UnderlineColorIndex = 0
                    except Exception:
                        pass

                # Collapse to end and continue searching
                find_range.Collapse(0)
                find_range.SetRange(find_range.End, doc.Content.End)
                find = find_range.Find
                find.ClearFormatting()
                find.Text = word
                find.MatchWholeWord = True
                find.MatchCase = False
                find.Forward = True
                find.Wrap = 0

            if found:
                print(f"{marker} Word underline applied for '{word}' ({found} occurrence{'s' if found != 1 else ''})")
                return f"word-com-{uuid.uuid4().hex[:6]}"

            print(f"⚠️ Word underline: '{word}' not found in active document")
            return None

        except Exception as exc:
            print(f"⚠️ Word underline failed for '{word}': {exc}")
            return None

    def _reset_word_range_underlines(self, target_range, *, label: Optional[str] = None) -> bool:
        """Remove custom underline styling from a specific Word range."""
        if target_range is None:
            return False
        try:
            if target_range.Characters.Count <= 0:
                return False
            target_range.Font.Underline = 0
            target_range.Font.UnderlineColor = 0
            target_range.Font.UnderlineColorIndex = 0
            if label:
                cleaned = (target_range.Text or "").strip()
                if cleaned:
                    print(f"🧼 Cleared Word underline for '{cleaned}' ({label})")
            return True
        except Exception as exc:
            print(f"⚠️ Failed to clear Word underline{f' ({label})' if label else ''}: {exc}")
            return False

    def _clear_word_underline_for_replacement(self, word_text: str, delimiter: str):
        """Clear underline styling from the word we just replaced in Microsoft Word."""
        if self.current_interface != "Microsoft Word" or Dispatch is None:
            return

        word_text = word_text or ""
        if not word_text.strip():
            return

        try:
            word_app = Dispatch("Word.Application")
        except Exception as exc:
            print(f"⚠️ Unable to attach to Word for underline clear: {exc}")
            return

        try:
            selection = getattr(word_app, "Selection", None)
            document = getattr(word_app, "ActiveDocument", None)
            if not selection or not document:
                return

            delimiter_len = len(delimiter or "")
            selection_anchor = selection.Start
            if delimiter_len:
                selection_anchor = max(0, selection_anchor - delimiter_len)

            search_span = max(128, len(word_text) * 6)
            search_start = max(0, selection_anchor - search_span)
            search_range = document.Range(search_start, selection_anchor)

            best_range = None
            if search_range and search_range.Start < search_range.End:
                find = search_range.Find
                find.ClearFormatting()
                find.Text = word_text
                find.MatchWholeWord = True
                find.MatchCase = False
                find.Forward = True
                find.Wrap = 0  # wdFindStop

                while find.Execute():
                    candidate = search_range.Duplicate
                    try:
                        candidate.MoveStartWhile(" \t\r\n", 1)
                    except Exception:
                        pass
                    try:
                        candidate.MoveEndWhile(" \t\r\n", -1)
                    except Exception:
                        pass

                    if candidate.Characters.Count > 0:
                        best_range = candidate.Duplicate

                    # Narrow the search window to continue looking forward
                    new_start = candidate.End
                    if new_start >= selection_anchor:
                        break
                    search_range.SetRange(new_start, selection_anchor)
                    find = search_range.Find
                    find.ClearFormatting()
                    find.Text = word_text
                    find.MatchWholeWord = True
                    find.MatchCase = False
                    find.Forward = True
                    find.Wrap = 0

            if best_range is None:
                fallback_start = max(0, selection_anchor - len(word_text))
                best_range = document.Range(fallback_start, selection_anchor)

            cleared = False
            if best_range and best_range.Start < best_range.End:
                cleared = self._reset_word_range_underlines(best_range, label="post-replacement")

            if delimiter_len:
                try:
                    gap_range = document.Range(selection_anchor, min(selection_anchor + delimiter_len, document.Content.End))
                    if gap_range and gap_range.Characters.Count:
                        self._reset_word_range_underlines(gap_range, label="delimiter cleanup")
                except Exception:
                    pass

            if not cleared:
                try:
                    WD_CHARACTER = 1
                    WD_WORD = 2
                    fallback_selection = selection.Range.Duplicate
                    if delimiter_len:
                        fallback_selection.MoveStart(Unit=WD_CHARACTER, Count=-delimiter_len)
                        fallback_selection.MoveEnd(Unit=WD_CHARACTER, Count=-delimiter_len)
                    fallback_selection.MoveStart(Unit=WD_WORD, Count=-1)
                    try:
                        fallback_selection.MoveStartWhile(" \t\r\n", 1)
                    except Exception:
                        pass
                    try:
                        fallback_selection.MoveEndWhile(" \t\r\n", -1)
                    except Exception:
                        pass
                    if fallback_selection.Characters.Count > 0:
                        cleared = self._reset_word_range_underlines(fallback_selection, label="prev-word fallback")
                except Exception as fallback_exc:
                    print(f"⚠️ Word underline selection fallback failed: {fallback_exc}")

            if not cleared:
                print(f"⚠️ Word underline cleanup fallback triggered for '{word_text}'")

        except Exception as exc:
            print(f"⚠️ Word underline cleanup error: {exc}")

    def _cleanup_word_whitespace_after_space(self):
        """Ensure a newly inserted space near a misspelled Word keeps underlines separate."""
        if self.current_interface != "Microsoft Word" or Dispatch is None:
            return

        try:
            word_app = Dispatch("Word.Application")
            selection = getattr(word_app, "Selection", None)
            document = getattr(word_app, "ActiveDocument", None)
            if not selection or not document:
                return

            caret_pos = selection.Start
            if caret_pos > 0:
                whitespace_range = document.Range(max(0, caret_pos - 1), caret_pos)
                if whitespace_range and whitespace_range.Characters.Count:
                    value = whitespace_range.Text
                    if value and value in (" ", "\t"):
                        whitespace_range.Font.Underline = 0
                        whitespace_range.Font.UnderlineColor = 0
                        whitespace_range.Font.UnderlineColorIndex = 0

            word_obj = selection.Words(1) if selection else None
            if not word_obj:
                return

            word_range = word_obj.Duplicate
            original_style = word_range.Font.Underline
            if not original_style:
                return

            original_color = word_range.Font.UnderlineColor
            original_color_index = word_range.Font.UnderlineColorIndex

            trimmed = word_range.Duplicate
            try:
                trimmed.MoveStartWhile(" \t\r\n", 1)
            except Exception:
                pass
            try:
                trimmed.MoveEndWhile(" \t\r\n", -1)
            except Exception:
                pass

            if trimmed.Characters.Count <= 0:
                return

            try:
                word_range.Font.Underline = 0
                word_range.Font.UnderlineColor = 0
                word_range.Font.UnderlineColorIndex = 0
            except Exception:
                pass

            try:
                trimmed.Font.Underline = original_style
                trimmed.Font.UnderlineColor = original_color
                trimmed.Font.UnderlineColorIndex = original_color_index
            except Exception:
                pass
        except Exception as exc:
            print(f"⚠️ Word whitespace cleanup failed: {exc}")
    
    def get_clipboard_text(self):
        """Get text from clipboard safely"""
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    return data
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            pass
        return None
    
    def _get_focus_handles(self) -> Tuple[Optional[int], Optional[int]]:
        """Return (foreground_hwnd, focus_hwnd) using GUI thread info"""
        try:
            foreground = windll.user32.GetForegroundWindow()
            if not foreground:
                return None, None
            thread_id = windll.user32.GetWindowThreadProcessId(foreground, 0)
            gui_info = GUITHREADINFO(cbSize=sizeof(GUITHREADINFO))
            if windll.user32.GetGUIThreadInfo(thread_id, byref(gui_info)):
                focus = gui_info.hwndFocus or gui_info.hwndCaret or foreground
                return foreground, focus
        except Exception as exc:
            print(f"⚠️ Focus handle lookup failed: {exc}")
        return None, None

    def _get_text_via_win32(self, hwnd: Optional[int]) -> Optional[str]:
        """Try to read text from standard edit controls without emitting keystrokes."""
        if not hwnd:
            return None
        try:
            length = win32gui.SendMessage(hwnd, win32con.WM_GETTEXTLENGTH, 0, 0)
            if length <= 0 or length > 500000:
                return None
            buffer = create_unicode_buffer(length + 1)
            win32gui.SendMessage(hwnd, win32con.WM_GETTEXT, length + 1, buffer)
            return buffer.value
        except Exception:
            return None

    def extract_words_from_text(self, text):
        """Extract words from pasted text"""
        if not text:
            return []
        # Split by delimiters while preserving Kannada words
        words = re.findall(r'[^\s\n\r\t.,!?;:]+', text)
        return [w for w in words if any(self.is_kannada_char(c) for c in w)]
    
    def get_document_text(self) -> str:
        """Get all text from the active document without injecting 'Ctrl+A/C' keystrokes."""
        try:
            foreground, focus_hwnd = self._get_focus_handles()
            
            # First try UI Automation (works for Notepad, Word, browsers that expose TextPattern)
            if foreground:
                text = self.caret_tracker.get_text_via_ui_automation(foreground)
                if text:
                    return text
            
            # Fallback to Win32 WM_GETTEXT for standard edit controls
            text = self._get_text_via_win32(focus_hwnd or foreground)
            if text:
                return text
            
            print("⚠️ Unable to capture document text without keystrokes; skipping full scan.")
            return ""
        except Exception as exc:
            print(f"⚠️ Error getting document text: {exc}")
            return ""
    
    def check_all_words_from_start_to_end(self):
        """Check all words in document from start to end and update dictionary"""
        try:
            # Get full document text
            full_text = self.get_document_text()
            if not full_text:
                return
            
            # Update cache
            self.document_text_cache = full_text
            
            # Extract all words with their positions
            word_matches = list(re.finditer(r'[^\s\n\r\t.,!?;:]+', full_text))
            kannada_words = []
            
            for match in word_matches:
                word = match.group(0)
                position = match.start()
                # Only process Kannada words
                if any(self.is_kannada_char(c) for c in word) and len(word) >= 2:
                    kannada_words.append((word, position))
            
            print(f"📝 Checking {len(kannada_words)} words from start to end...")
            
            # Clear old document_words and rebuild
            with self.document_lock:
                self.document_words.clear()
                self.word_index_counter = 0
                
                for word, position in kannada_words:
                    word_index = self.word_index_counter
                    self.word_index_counter += 1
                    
                    # Check spelling
                    suggestions, had_error = self.get_suggestions(word)
                    
                    # Store in dictionary
                    self.document_words[word_index] = {
                        'word': word,
                        'corrected_word': word,  # Initially same as word
                        'suggestions': suggestions,
                        'position': position,
                        'has_error': had_error,
                        'checked': True
                    }
                    
                    # Add underline if error
                    if had_error:
                        # Note: We'll need to get caret position for this word
                        # For now, we'll add it to misspelled_words for tracking
                        # The underline will be added when we process each word individually
                        pass
            
            print(f"✅ Document dictionary updated: {len(self.document_words)} words tracked")
            print(f"   Errors found: {sum(1 for w in self.document_words.values() if w['has_error'])}")
            
        except Exception as exc:
            print(f"❌ Error checking all words: {exc}")
            import traceback
            traceback.print_exc()
    
    def update_document_word(self, old_word: str, new_word: str):
        """Update a word in the document dictionary when replaced"""
        with self.document_lock:
            for word_index, word_data in self.document_words.items():
                if word_data['word'] == old_word or word_data['corrected_word'] == old_word:
                    word_data['corrected_word'] = new_word
                    word_data['has_error'] = False
                    # Re-check the new word
                    suggestions, had_error = self.get_suggestions(new_word)
                    word_data['suggestions'] = suggestions
                    word_data['has_error'] = had_error
                    print(f"📝 Updated document word {word_index}: '{old_word}' → '{new_word}'")
                    break

    def _capture_live_geometry(self) -> Optional[dict]:
        """Collect the latest caret + window geometry snapshot."""
        try:
            anchor_x, anchor_y = get_caret_position()
        except Exception:
            anchor_x = None
            anchor_y = None

        try:
            hwnd = windll.user32.GetForegroundWindow()
        except Exception:
            hwnd = None

        text_hwnd = None
        selection_start = None
        caret_rect = None
        if hwnd:
            try:
                thread_id = windll.user32.GetWindowThreadProcessId(hwnd, 0)
                gui_info = GUITHREADINFO(cbSize=sizeof(GUITHREADINFO))
                if windll.user32.GetGUIThreadInfo(thread_id, byref(gui_info)):
                    text_hwnd = gui_info.hwndCaret or gui_info.hwndFocus or hwnd
                    caret_rect = gui_info.rcCaret
                    if text_hwnd:
                        start_index = wintypes.DWORD()
                        end_index = wintypes.DWORD()
                        try:
                            windll.user32.SendMessageW(
                                text_hwnd,
                                win32con.EM_GETSEL,
                                byref(start_index),
                                byref(end_index)
                            )
                            selection_start = start_index.value
                        except Exception:
                            selection_start = None
            except Exception:
                text_hwnd = None

        window_rect = None
        if hwnd:
            try:
                window_rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                window_rect = None

        relative_x = None
        relative_y = None
        if window_rect and anchor_x is not None and anchor_y is not None:
            relative_x = anchor_x - window_rect[0]
            relative_y = anchor_y - window_rect[1]

        line_height = self._estimate_line_height(text_hwnd or hwnd)

        snapshot = {
            'absolute_x': anchor_x,
            'absolute_y': anchor_y,
            'relative_x': relative_x,
            'relative_y': relative_y,
            'hwnd': hwnd,
            'text_hwnd': text_hwnd,
            'window_rect': window_rect,
            'line_height': line_height,
            'caret_rect': caret_rect,
            'selection_start': selection_start,
            'timestamp': time.time(),
        }

        return snapshot

    def capture_paste_anchor(self):
        """Snapshot caret and window geometry just before a paste."""
        snapshot = self._capture_live_geometry()
        if snapshot:
            self.last_paste_anchor = snapshot

    def _prepare_mouse_paste_candidate(self):
        """Capture document state ahead of a potential context-menu paste."""
        try:
            geometry = self._capture_live_geometry()
            if geometry:
                self.last_paste_anchor = geometry

            before_text = ""
            if self.current_interface == "Microsoft Word":
                before_text = self._get_word_document_text() or ""
            if not before_text:
                before_text = self.get_document_text() or ""
            caret_index = self._get_caret_char_index()

            self._menu_paste_candidate = {
                'timestamp': time.time(),
                'before_text': before_text,
                'caret_index': caret_index,
                'geometry': geometry,
            }
            print("🖱️ Context menu snapshot captured for paste candidate")
        except Exception as exc:
            print(f"⚠️ Unable to prepare mouse paste snapshot: {exc}")
            self._menu_paste_candidate = None

    def _maybe_trigger_mouse_paste_check(self):
        """Schedule a paste scan when a context-menu selection just finished."""
        candidate = self._menu_paste_candidate
        if not candidate:
            return

        if time.time() - candidate.get('timestamp', 0) > 5.0:
            self._menu_paste_candidate = None
            return

        self._menu_paste_candidate = None

        def run_evaluation():
            self._evaluate_mouse_paste_candidate(candidate)

        timer = threading.Timer(0.25, run_evaluation)
        timer.daemon = True
        timer.start()

    def _evaluate_mouse_paste_candidate(self, candidate: dict):
        """Compare document text before/after to confirm a mouse-driven paste."""
        if not candidate:
            return

        if not self.enabled or self.replacing:
            return

        if time.time() - candidate.get('timestamp', 0) > 5.0:
            return

        before_text = candidate.get('before_text') or ""
        after_text = ""
        if self.current_interface == "Microsoft Word":
            try:
                after_text = self._get_word_document_text() or ""
            except Exception as exc:
                print(f"⚠️ Unable to capture Word document text: {exc}")
        if not after_text:
            try:
                after_text = self.get_document_text() or ""
            except Exception as exc:
                print(f"⚠️ Unable to capture document text for paste confirmation: {exc}")
                return

        if after_text == before_text:
            return

        inserted, removed = self._extract_inserted_segment(before_text, after_text)

        clipboard_text = self.get_clipboard_text() or ""
        if not inserted.strip():
            if self.current_interface == "Microsoft Word" and clipboard_text.strip():
                inserted = clipboard_text
            if not inserted.strip():
                return

        if self.current_interface == "Microsoft Word" and clipboard_text.strip():
            text_to_process = clipboard_text
        else:
            text_to_process = inserted

        words = self.extract_words_from_text(text_to_process)
        if not words:
            return

        geometry = candidate.get('geometry')
        if geometry:
            self.last_paste_anchor = geometry
        elif not self.last_paste_anchor:
            self.capture_paste_anchor()

        if clipboard_text:
            self.last_clipboard_content = clipboard_text
        else:
            self.last_clipboard_content = text_to_process

        print("📋 Detected mouse paste - processing underlines")
        self._start_paste_cooldown(0.8)
        self.process_pasted_text_for_underlines(text_to_process)

    def _extract_inserted_segment(self, before: str, after: str) -> Tuple[str, str]:
        """Return inserted and removed substrings between two document snapshots."""
        before = before or ""
        after = after or ""

        if before == after:
            return "", ""

        len_before = len(before)
        len_after = len(after)
        prefix_len = 0
        max_prefix = min(len_before, len_after)
        while prefix_len < max_prefix and before[prefix_len] == after[prefix_len]:
            prefix_len += 1

        suffix_len = 0
        remaining_before = len_before - prefix_len
        remaining_after = len_after - prefix_len
        max_suffix = min(remaining_before, remaining_after)
        while (
            suffix_len < max_suffix
            and before[len_before - 1 - suffix_len] == after[len_after - 1 - suffix_len]
        ):
            suffix_len += 1

        start_after = prefix_len
        end_after = len_after - suffix_len if suffix_len <= len_after - prefix_len else len_after
        start_before = prefix_len
        end_before = len_before - suffix_len if suffix_len <= len_before - prefix_len else len_before

        inserted = after[start_after:end_after]
        removed = before[start_before:end_before]
        return inserted, removed

    def _get_word_document_text(self) -> Optional[str]:
        """Return full document text from Word via COM when available."""
        if Dispatch is None or self.current_interface != "Microsoft Word":
            return None
        try:
            word_app = Dispatch("Word.Application")
            doc = getattr(word_app, "ActiveDocument", None)
            if not doc:
                return None
            content = getattr(doc, "Content", None)
            if not content:
                return None
            text = getattr(content, "Text", None)
            if text is None:
                return None
            return str(text)
        except Exception as exc:
            print(f"⚠️ Unable to read Word document text: {exc}")
            return None

    def _estimate_line_height(self, hwnd: Optional[int]) -> int:
        """Best-effort line height (pixels) for the target window."""
        line_height = self.default_line_height_px
        if not hwnd:
            return line_height
        try:
            metrics = self.caret_tracker.get_font_metrics(hwnd)
            scale = self.caret_tracker.get_dpi_scale_factor(hwnd)
            if metrics:
                line_height = metrics.tmHeight + metrics.tmExternalLeading
            if scale and scale > 0:
                line_height = int(line_height * scale)
        except Exception:
            pass
        return max(16, line_height)

    def _start_paste_cooldown(self, duration: float = 0.3):
        """Pause keystroke-based processing for a short, Grammarly-style cooldown."""
        self.paste_cooldown_until = max(self.paste_cooldown_until, time.time() + max(0.0, duration))

    def _in_paste_cooldown(self) -> bool:
        """Return True while paste processing is still settling."""
        return time.time() < self.paste_cooldown_until

    def _resolve_paste_anchor_geometry(self) -> Optional[dict]:
        """Build a geometry snapshot for paste underline placement."""
        anchor = (self.last_paste_anchor or {}).copy()
        hwnd = anchor.get('hwnd')
        if not hwnd:
            try:
                hwnd = windll.user32.GetForegroundWindow()
            except Exception:
                hwnd = None

        window_rect = anchor.get('window_rect')
        if not window_rect and hwnd:
            try:
                window_rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                window_rect = None

        base_x = anchor.get('absolute_x')
        rel_x = anchor.get('relative_x')
        if base_x is None and window_rect and rel_x is not None:
            base_x = window_rect[0] + rel_x
        if base_x is None and window_rect:
            base_x = window_rect[0] + self.default_text_margin_px

        base_y = anchor.get('absolute_y')
        rel_y = anchor.get('relative_y')
        if base_y is None and window_rect and rel_y is not None:
            base_y = window_rect[1] + rel_y
        if base_y is None and window_rect:
            base_y = window_rect[1] + self.default_baseline_offset_px

        if base_x is None or base_y is None:
            try:
                fallback_x, fallback_y = get_caret_position()
                base_x = base_x if base_x is not None else fallback_x
                base_y = base_y if base_y is not None else fallback_y
            except Exception:
                pass

        if base_x is None or base_y is None:
            return None

        line_height = anchor.get('line_height') or self._estimate_line_height(hwnd)

        return {
            'hwnd': hwnd,
            'text_hwnd': anchor.get('text_hwnd'),
            'window_rect': window_rect,
            'base_x': base_x,
            'base_y': base_y,
            'line_height': line_height,
            'selection_start': anchor.get('selection_start'),
            'caret_rect': anchor.get('caret_rect')
        }

    def _build_notepad_layout(
        self,
        full_text: str,
        spans: List[re.Match],
        geometry: dict
    ) -> Dict[int, dict]:
        """Return per-word geometry using the edit control's own layout data."""
        if not full_text or not spans or not geometry:
            return {}

        text_hwnd = geometry.get('text_hwnd') or geometry.get('hwnd')
        selection_start = geometry.get('selection_start')
        if not text_hwnd or selection_start is None:
            return {}

        layout: Dict[int, dict] = {}
        origin_x = 0
        origin_y = 0
        ascent = None
        line_height = geometry.get('line_height', self.default_line_height_px)
        last_line_y: Optional[int] = None
        current_line = -1

        try:
            origin_x, origin_y = win32gui.ClientToScreen(text_hwnd, (0, 0))
        except Exception:
            origin_x = origin_y = 0

        hdc = None
        old_font = None
        try:
            hdc = win32gui.GetDC(text_hwnd)
            if not hdc:
                return {}

            hfont = win32gui.SendMessage(text_hwnd, win32con.WM_GETFONT, 0, 0)
            if hfont:
                try:
                    old_font = win32gui.SelectObject(hdc, hfont)
                except Exception:
                    old_font = None

            try:
                metrics = win32gui.GetTextMetrics(hdc)
                ascent = metrics.get('tmAscent')
                tm_height = metrics.get('tmHeight')
                tm_external = metrics.get('tmExternalLeading', 0)
                if tm_height:
                    line_height = max(line_height, tm_height + tm_external)
            except Exception:
                ascent = None

            for span_idx, match in enumerate(spans):
                word = match.group(0)
                if not word:
                    continue

                char_start = selection_start + match.start()
                char_end = char_start + len(word)

                start_pos = windll.user32.SendMessageW(text_hwnd, win32con.EM_POSFROMCHAR, char_start, 0)
                if start_pos in (-1, 0xFFFFFFFF):
                    continue
                start_x = c_short(start_pos & 0xFFFF).value
                start_y = c_short((start_pos >> 16) & 0xFFFF).value

                end_pos = windll.user32.SendMessageW(text_hwnd, win32con.EM_POSFROMCHAR, char_end, 0)
                if end_pos in (-1, 0xFFFFFFFF):
                    end_x = start_x + measure_text_width(word, text_hwnd)
                    end_y = start_y
                else:
                    end_x = c_short(end_pos & 0xFFFF).value
                    end_y = c_short((end_pos >> 16) & 0xFFFF).value

                screen_start_x = origin_x + start_x
                screen_start_y = origin_y + start_y
                screen_end_x = origin_x + end_x
                screen_end_y = origin_y + end_y

                if screen_end_y != screen_start_y:
                    word_width = measure_text_width(word, text_hwnd)
                else:
                    word_width = max(self.layout_min_char_px, screen_end_x - screen_start_x)

                if word_width <= 0:
                    word_width = measure_text_width(word, text_hwnd)

                if ascent is not None:
                    baseline_offset = ascent
                else:
                    baseline_offset = line_height

                if line_height > 0:
                    if last_line_y is None:
                        current_line = 0
                        last_line_y = start_y
                    else:
                        threshold = max(1, int(line_height * 0.6))
                        if abs(start_y - last_line_y) > threshold:
                            current_line += 1
                            last_line_y = start_y
                        else:
                            # Track the smallest Y so wrapped lines stay anchored.
                            if start_y < last_line_y:
                                last_line_y = start_y
                    line_number = max(current_line, 0)
                else:
                    line_number = 0

                base_line_offset = self.paste_line_offsets.get(
                    line_number,
                    self.paste_default_line_offset_px,
                )

                if line_height and self.default_line_height_px:
                    line_scale = max(0.2, min(2.5, line_height / float(self.default_line_height_px)))
                    line_offset = int(round(base_line_offset * line_scale))
                else:
                    line_offset = base_line_offset

                if line_number > 0 and self.paste_line_offset_increment_px:
                    increment = self.paste_line_offset_increment_px
                    if line_height and self.default_line_height_px:
                        increment = int(round(increment * line_scale))
                    line_offset += increment

                baseline_y = screen_start_y + baseline_offset + line_offset

                layout[span_idx] = {
                    'start_x': screen_start_x,
                    'baseline_y': baseline_y,
                    'width': word_width,
                    'line_number': line_number,
                }
        finally:
            if hdc:
                if old_font:
                    try:
                        win32gui.SelectObject(hdc, old_font)
                    except Exception:
                        pass
                try:
                    win32gui.ReleaseDC(text_hwnd, hdc)
                except Exception:
                    pass

        return layout

    def process_pasted_text_for_underlines(self, full_text: str):
        """One-shot paste pass that measures every word from the window edge.

        Correct Paste Handling Logic:
        "When a paste event is detected, disable the normal keystroke-based
        spell-checking and instead run a single full-sentence pass. Then
        re-enable normal keystroke checking after a short delay."
        """
        if not full_text:
            return

        if self.current_interface == "Notepad" and self._is_notepad_document_empty():
            print("ℹ️ Notepad document cleared before paste processing; skipping underline pass.")
            self._clear_all_underlines_notepad_async()
            return

        # Keep extending the cooldown while this batch runs to avoid keystroke overlap.
        self._start_paste_cooldown(0.8)

        spans = list(re.finditer(r'[^\s\n\r\t.,!?;:]+', full_text))
        if not spans:
            return

        geometry_snapshot = self._resolve_paste_anchor_geometry()

        def worker():
            try:
                self.replacing = True
                self.popup.hide()

                if self.current_interface == "Notepad" and self._is_notepad_document_empty():
                    print("ℹ️ Notepad document cleared during paste processing; aborting underline generation.")
                    self._clear_all_underlines_notepad_async()
                    return

                if self.current_interface == "Microsoft Word":
                    for match in spans:
                        word = match.group(0)
                        if len(word) < 2 or not any(self.is_kannada_char(c) for c in word):
                            continue

                        suggestions, had_error = self.get_suggestions(word)
                        if not had_error:
                            continue

                        underline_id = self.show_no_suggestion_marker(
                            word,
                            has_suggestions=bool(suggestions),
                            suggestions=suggestions,
                        )
                    return

                geometry = geometry_snapshot or self._resolve_paste_anchor_geometry()
                if not geometry:
                    print("⚠️ Unable to resolve paste geometry; skipping underline placement.")
                    return

                target_hwnd = geometry['hwnd']
                window_rect = geometry['window_rect']
                line_height = geometry['line_height']
                text_hwnd = geometry.get('text_hwnd')
                selection_start = geometry.get('selection_start')
                layout_map = self._build_notepad_layout(full_text, spans, geometry)
                if not layout_map:
                    print("⚠️ Unable to rebuild Notepad layout; skipping paste underlines.")
                    return
                caret_height = self._get_caret_height(target_hwnd)
                if caret_height is None:
                    caret_height = line_height
                underline_offset = self._compute_underline_offset(caret_height)

                for idx, match in enumerate(spans):
                    if self.current_interface == "Notepad" and self._is_notepad_document_empty():
                        print("ℹ️ Notepad document cleared mid-paste; stopping underline placement loop.")
                        self._clear_all_underlines_notepad_async()
                        return

                    layout_info = layout_map.get(idx)
                    if not layout_info:
                        continue
                    word_width = layout_info['width']
                    caret_y = layout_info['baseline_y']
                    word_start_x = layout_info['start_x']
                    word = match.group(0)
                    word_len = len(word)
                    is_kannada_word = word_len >= 2 and any(self.is_kannada_char(c) for c in word)

                    if not is_kannada_word:
                        continue

                    suggestions, had_error = self.get_suggestions(word)
                    if not had_error:
                        continue

                    caret_x = word_start_x + word_width

                    relative_start = None
                    relative_y = None
                    if window_rect:
                        relative_start = word_start_x - window_rect[0]
                        relative_y = (caret_y + underline_offset) - window_rect[1]

                    char_start = None
                    if selection_start is not None:
                        char_start = selection_start + match.start()

                    underline_id = self.add_persistent_underline(
                        word=word,
                        suggestions=suggestions,
                        caret_x=caret_x,
                        caret_y=caret_y,
                        word_width=word_width,
                        word_start_x=word_start_x,
                        hwnd=target_hwnd,
                        text_hwnd=text_hwnd,
                        window_rect=window_rect,
                        relative_start_x=relative_start,
                        relative_y=relative_y,
                        caret_height=caret_height,
                        char_start=char_start,
                        char_length=len(word),
                    )

            except Exception as exc:
                print(f"❌ Error processing pasted words for underlines: {exc}")
                import traceback
                traceback.print_exc()
            finally:
                self.replacing = False
                self.last_paste_anchor = None
                self.select_all_active = False
                self.ctrl_held = False

        threading.Thread(target=worker, daemon=True).start()
    
    def check_pasted_text(self):
        """Entry point invoked after Ctrl+V settles; runs the one-shot paste pass."""
        try:
            clipboard_text = self.get_clipboard_text()
            print(f"🔍 Clipboard content: {repr(clipboard_text)}")
            
            if not clipboard_text:
                print("⚠️ No clipboard text found")
                return
                
            # Always update clipboard content
            self.last_clipboard_content = clipboard_text
            
            # Extract Kannada words from pasted text
            words = self.extract_words_from_text(clipboard_text)
            print(f"🔍 Extracted Kannada words: {words}")
            
            if words and self.enabled and not self.replacing:
                self.process_pasted_text_for_underlines(clipboard_text)
            else:
                print(f"⚠️ No Kannada words found or service disabled")
        except Exception as e:
            print(f"❌ Error checking pasted text: {e}")
            import traceback
            traceback.print_exc()
    
    def get_suggestions(self, word) -> Tuple[List[str], bool]:
        """Return suggestion list for a word along with an error flag"""
        if not word or len(word) < 2:
            return [], False
        if not any(self.is_kannada_char(c) for c in word):
            return [], False
        was_kannada = is_kannada_text(word)
        try:
            errors = self.spell_checker.check_text(word)
            if errors:
                error = errors[0]
                suggestions = error.get('suggestions', [])
                if was_kannada:
                    from kannada_wx_converter import wx_to_kannada
                    suggestions = [wx_to_kannada(s) for s in suggestions]
                return suggestions[:5], True
        except Exception:
            return [], False
        return [], False
    
    def replace_word(self, chosen_word):
        """Replace the misspelled word with chosen suggestion"""
        print(f"✅ Replacing with: '{chosen_word}'")
        pivot_info = None
        with self.underline_lock:
            if self.last_underline_id and self.last_underline_id in self.misspelled_words:
                pivot_info = self.misspelled_words[self.last_underline_id].copy()

        pivot_index = None
        pivot_hwnd = None
        previous_length = len(self.last_word or "")
        if pivot_info:
            pivot_index = pivot_info.get('char_start')
            pivot_hwnd = pivot_info.get('hwnd')
            previous_length = pivot_info.get('char_length') or previous_length

        self.replacing = True
        self.disable_scanning = True
        self.select_all_active = False
        self.ctrl_held = False
        try:
            self.last_replaced_word = chosen_word
            self.last_replacement_time = time.time()
            self.popup.hide()
            time.sleep(0.05)

            delimiter = self.last_delimiter_char or ' '

            # Remove the delimiter (space) that triggered the suggestion
            self.keyboard_controller.press(Key.backspace)
            self.keyboard_controller.release(Key.backspace)
            time.sleep(0.01)

            # Select the previous word using Ctrl+Shift+Left
            self.keyboard_controller.press(Key.ctrl)
            self.keyboard_controller.press(Key.shift)
            self.keyboard_controller.press(Key.left)
            self.keyboard_controller.release(Key.left)
            self.keyboard_controller.release(Key.shift)
            self.keyboard_controller.release(Key.ctrl)
            time.sleep(0.01)

            # Delete the selected word
            self.keyboard_controller.press(Key.delete)
            self.keyboard_controller.release(Key.delete)
            time.sleep(0.02)

            # Type the chosen word
            self.keyboard_controller.type(chosen_word)
            time.sleep(0.01)

            # Re-type the original delimiter so spacing stays consistent
            self.type_delimiter_key(delimiter)
            self.last_delimiter_char = delimiter
            self.trailing_delimiter_count = 1

            if self.current_interface == "Microsoft Word":
                self._clear_word_underline_for_replacement(chosen_word, delimiter)

            # Wait longer before resetting flag to ensure space is fully processed
            time.sleep(0.15)

            print("✅ Replacement complete")

            delta_chars = len(chosen_word) - previous_length
            if delta_chars and pivot_index is not None:
                self._shift_underlines_after(
                    pivot_index,
                    delta_chars,
                    hwnd=pivot_hwnd,
                    exclude_uid=self.last_underline_id,
                )

            # Update document dictionary with the replacement
            self.update_document_word(self.last_word, chosen_word)

            # Remove the persistent underline for the OLD misspelled word
            removed = False
            if self.last_underline_id:
                removed = self.remove_persistent_underline(uid=self.last_underline_id)
            if not removed and self.last_word:
                caret_index = self._get_caret_char_index()
                fallback_index = None
                if caret_index is not None and len(self.last_word) > 1:
                    fallback_index = max(0, caret_index + len(self.last_word) - 1)
                self.remove_persistent_underline(
                    self.last_word,
                    char_index=caret_index,
                    fallback_index=fallback_index,
                )
            self.last_underline_id = None

            # Clear buffers to prevent reprocessing the replaced word
            self.current_word_chars = []
            self.cursor_index = 0
            self.last_committed_word_chars = []
            self.pending_restore = False
            self.restore_allowed = False
            self.selection_anchor = None
            self.selection_range = None
            self.just_replaced_word = True

            with self.underline_lock:
                need_refresh = bool(self.misspelled_words)
            if need_refresh:
                self._schedule_underlines_refresh(reason="post-replacement")

            # Re-check all words from start to end in background
            threading.Thread(
                target=self.check_all_words_from_start_to_end,
                daemon=True
            ).start()

        except Exception as e:
            print(f"⚠️ Replacement failed: {e}")
            self.just_replaced_word = False
            self.last_underline_id = None
        finally:
            self.disable_scanning = False
            self.replacing = False

    def on_press(self, key):
        """Handle key press events"""
        try:
            # Debug: print every key press
            print(f"🔑 Key pressed: {key}, ctrl_held={getattr(self, 'ctrl_held', False)}, select_all_active={getattr(self, 'select_all_active', False)}")
            
            # Skip processing if we're in the middle of replacing
            if self.replacing:
                return

            if self.disable_scanning:
                return

            if self.just_replaced_word and key not in (Key.backspace, Key.esc):
                self.just_replaced_word = False

            in_paste_cooldown = self._in_paste_cooldown()

            # Track Shift key for selection handling
            if key in (Key.shift, Key.shift_r):
                self.shift_pressed = True
                if self.selection_anchor is None:
                    self.selection_anchor = self.cursor_index
                return
            
            # Detect Ctrl+V paste operation and Ctrl+A select-all
            if key == Key.ctrl_l or key == Key.ctrl_r:
                self.clipboard_check_active = True
                self.ctrl_held = True
                print(f"🎛️ Ctrl pressed - ctrl_held set to True")
            
            # Check for 'A' or 'V' key while Ctrl is held
            if self.ctrl_held:
                # Check if 'v' key is pressed (either as char or vk code)
                is_v_key = False
                is_a_key = False
                
                # Try multiple ways to detect the key
                key_char = None
                key_vk = None
                if hasattr(key, 'char') and key.char:
                    key_char = key.char.lower()
                if hasattr(key, 'vk'):
                    key_vk = key.vk
                
                # Also check the key name for KeyCode objects
                key_name = None
                try:
                    key_name = str(key).lower()
                except:
                    pass
                
                print(f"🔍 Checking key while Ctrl held: char={key_char}, vk={key_vk}, name={key_name}")
                
                if key_char == 'v' or key_vk == 86 or (key_name and 'v' in key_name):
                    is_v_key = True
                if key_char == 'a' or key_vk == 65 or key_char == '\x01' or (key_name and "'a'" in key_name):
                    is_a_key = True
                
                if is_v_key:
                    self._start_paste_cooldown(0.8)
                    in_paste_cooldown = True
                    self.capture_paste_anchor()
                    # Ctrl+V detected - schedule clipboard check after paste completes
                    print("📋 Paste detected - checking clipboard...")
                    threading.Timer(0.3, self.check_pasted_text).start()
                
                if is_a_key:
                    # Ctrl+A detected - mark select-all active
                    self.select_all_active = True
                    print(f"📋 Ctrl+A detected - select all active (interface: {self.current_interface})")
            
            if key in (Key.backspace, Key.esc) and self.just_replaced_word:
                self.just_replaced_word = False
                self.pending_restore = False
                self.restore_allowed = False
                return

            # Handle Esc key - hide popup or exit if pressed twice quickly
            if key == Key.esc:
                # record time of this Esc press
                current_time = time.time()
                # if second Esc within threshold -> stop service
                if current_time - self.last_esc_time < 1.0:
                    print("\n🛑 Esc pressed twice - Stopping service...")
                    self.running = False
                    try:
                        self.popup.hide()
                    except Exception:
                        pass
                    try:
                        self.popup.root.quit()
                    except Exception:
                        pass
                    self.last_esc_time = 0
                    return

                # otherwise, set last_esc_time and hide popup if visible
                self.last_esc_time = current_time
                if self.popup.visible:
                    try:
                        self.popup.hide()
                    except Exception:
                        pass
                return
            
            # Navigation controls for popup (only handles list navigation/selection)
            if self.popup.visible:
                if key == Key.down:
                    self.popup.select_next()
                    return
                elif key == Key.up:
                    self.popup.select_prev()
                    return
                elif key == Key.enter:
                    print("🔍 Enter pressed - popup visible")
                    chosen = self.popup.get_selected()
                    print(f"🔍 Selected suggestion: {chosen}")
                    if chosen:
                        self.popup.hide()
                        self.replace_word(chosen)
                    else:
                        print("⚠️ No suggestion selected")
                    return

            # Buffer-aware editing controls (apply whether popup is visible or not)
            if key == Key.backspace:
                triggered_via_ctrl = self.select_all_active
                if self._should_clear_select_all():
                    reason = "Ctrl+A" if triggered_via_ctrl else "Selection"
                    print(f"🧹 {reason} + Backspace detected - clearing all underlines (interface: {self.current_interface})")
                    self._clear_all_underlines_notepad()
                    self.select_all_active = False
                    self.reset_current_word()
                    if self.popup.visible:
                        self.popup.hide()
                    return
                self._schedule_document_empty_check()
                buffer_before_edit = ''.join(self.current_word_chars)
                if self.trailing_delimiter_count > 0:
                    self.trailing_delimiter_count = max(0, self.trailing_delimiter_count - 1)
                    self.pending_restore = False
                    print(f"⬅️ Removed trailing delimiter (remaining: {self.trailing_delimiter_count})")
                    if (self.trailing_delimiter_count == 0 and not self.current_word_chars
                            and self.last_committed_word_chars and self.restore_allowed):
                        self.current_word_chars = self.last_committed_word_chars.copy()
                        self.cursor_index = len(self.current_word_chars)
                        self.pending_restore = True
                        self.restore_allowed = False
                        # Update buffer_before_edit to reflect the restored word
                        buffer_before_edit = ''.join(self.current_word_chars)
                        print(f"🔄 Restored last word buffer '{buffer_before_edit}' before backspace")
                    return
                removal_checked = False
                if self.pending_restore:
                    # When deleting a restored word, use the current buffer as the word being deleted
                    buffer_before_edit = ''.join(self.current_word_chars)
                    # We restored the buffer on previous event; now perform actual deletion
                    self.pending_restore = False
                    self.restore_allowed = False
                    if self.selection_range:
                        start, end = self.selection_range
                        removed = ''.join(self.current_word_chars[start:end])
                        del self.current_word_chars[start:end]
                        self.cursor_index = start
                        print(f"⌫ Backspace cleared selection '{removed}' → Buffer: {''.join(self.current_word_chars)} (cursor @ {self.cursor_index})")
                        self.selection_range = None
                        self.selection_anchor = None
                        self.sync_committed_buffer()
                    elif self.cursor_index > 0:
                        removed_char = self.current_word_chars.pop(self.cursor_index - 1)
                        self.cursor_index -= 1
                        print(f"⌫ Backspace removed '{removed_char}' → Buffer: {''.join(self.current_word_chars)} (cursor @ {self.cursor_index})")
                        self.sync_committed_buffer()
                    else:
                        self.reset_current_word()
                    removal_checked = True
                elif self.selection_range:
                    self.restore_allowed = False
                    start, end = self.selection_range
                    removed = ''.join(self.current_word_chars[start:end])
                    del self.current_word_chars[start:end]
                    self.cursor_index = start
                    print(f"⌫ Backspace cleared selection '{removed}' → Buffer: {''.join(self.current_word_chars)} (cursor @ {self.cursor_index})")
                    self.selection_range = None
                    self.selection_anchor = None
                    self.sync_committed_buffer()
                    removal_checked = True
                elif self.cursor_index > 0:
                    self.restore_allowed = False
                    removed_char = self.current_word_chars.pop(self.cursor_index - 1)
                    self.cursor_index -= 1
                    print(f"⌫ Backspace removed '{removed_char}' → Buffer: {''.join(self.current_word_chars)} (cursor @ {self.cursor_index})")
                    self.sync_committed_buffer()
                    removal_checked = True
                elif not self.current_word_chars and self.last_committed_word_chars and self.restore_allowed:
                    # Restore the last committed word so edits after clicking still have context
                    self.current_word_chars = self.last_committed_word_chars.copy()
                    self.cursor_index = len(self.current_word_chars)
                    self.pending_restore = True
                    self.restore_allowed = False
                    print(f"🔄 Restored last word buffer '{''.join(self.current_word_chars)}' before backspace")
                    return
                else:
                    self.reset_current_word()
                    removal_checked = True
                if removal_checked:
                    removed = self._maybe_remove_underline_after_edit(buffer_before_edit)
                    if removed:
                        return
                    if self.current_interface != "Notepad":
                        if not removed and not self.current_word_chars and not buffer_before_edit.strip():
                            self._remove_underlines_near_caret()
                    self._schedule_refresh_if_needed("backspace-edit")
                    if self.popup.visible:
                        self.popup.hide()
                    return

            if key == Key.delete:
                triggered_via_ctrl = self.select_all_active
                if self._should_clear_select_all():
                    reason = "Ctrl+A" if triggered_via_ctrl else "Selection"
                    print(f"🧹 {reason} + Delete detected - clearing all underlines (interface: {self.current_interface})")
                    self._clear_all_underlines_notepad()
                    self.select_all_active = False
                    self.reset_current_word()
                    if self.popup.visible:
                        self.popup.hide()
                    return
                self._schedule_document_empty_check()
                buffer_before_edit = ''.join(self.current_word_chars)
                self.pending_restore = False
                removal_checked = False
                if self.selection_range:
                    self.restore_allowed = False
                    start, end = self.selection_range
                    removed = ''.join(self.current_word_chars[start:end])
                    del self.current_word_chars[start:end]
                    self.cursor_index = start
                    print(f"⌦ Delete cleared selection '{removed}' → Buffer: {''.join(self.current_word_chars)} (cursor @ {self.cursor_index})")
                    self.selection_range = None
                    self.selection_anchor = None
                    removal_checked = True
                elif self.cursor_index < len(self.current_word_chars):
                    self.restore_allowed = False
                    removed_char = self.current_word_chars.pop(self.cursor_index)
                    print(f"⌦ Delete removed '{removed_char}' → Buffer: {''.join(self.current_word_chars)} (cursor @ {self.cursor_index})")
                    removal_checked = True
                elif self.trailing_delimiter_count > 0:
                    self.trailing_delimiter_count = max(0, self.trailing_delimiter_count - 1)
                    print(f"⌦ Consumed trailing delimiter with Delete (remaining: {self.trailing_delimiter_count})")
                else:
                    # Nothing to delete in buffer; ensure we don't leave stale underline when buffer already empty
                    removal_checked = True
                if removal_checked:
                    removed = self._maybe_remove_underline_after_edit(buffer_before_edit)
                    if removed:
                        return
                    if self.current_interface != "Notepad":
                        if not removed and not self.current_word_chars and not buffer_before_edit.strip():
                            self._remove_underlines_near_caret()
                    self._schedule_refresh_if_needed("delete-edit")
                    if self.popup.visible:
                        self.popup.hide()
                    return

            if key == Key.left:
                self.pending_restore = False
                self.restore_allowed = False
                prev_index = self.cursor_index
                if self.cursor_index > 0:
                    self.cursor_index -= 1
                if self.shift_pressed:
                    if self.selection_anchor is None:
                        self.selection_anchor = prev_index
                    start = min(self.cursor_index, self.selection_anchor)
                    end = max(self.cursor_index, self.selection_anchor)
                    self.selection_range = (start, end)
                    print(f"◀️ Selection range {self.selection_range}")
                else:
                    self.selection_anchor = None
                    self.selection_range = None
                    print(f"◀️ Cursor moved left → index {self.cursor_index}")
                return

            if key == Key.right:
                self.pending_restore = False
                self.restore_allowed = False
                prev_index = self.cursor_index
                if self.cursor_index < len(self.current_word_chars):
                    self.cursor_index += 1
                if self.shift_pressed:
                    if self.selection_anchor is None:
                        self.selection_anchor = prev_index
                    start = min(self.cursor_index, self.selection_anchor)
                    end = max(self.cursor_index, self.selection_anchor)
                    self.selection_range = (start, end)
                    print(f"▶️ Selection range {self.selection_range}")
                else:
                    self.selection_anchor = None
                    self.selection_range = None
                    print(f"▶️ Cursor moved right → index {self.cursor_index}")
                return

            if key in [Key.up, Key.down, Key.home, Key.end, Key.page_up, Key.page_down]:
                self.pending_restore = False
                self.reset_current_word()
                if self.popup.visible:
                    self.popup.hide()
                return

            # Handle normal characters
            char = None
            if hasattr(key, 'char'):
                char = key.char
            elif key == Key.space:
                char = ' '
            elif key == Key.enter:
                # Don't treat Enter as delimiter if popup is visible (it's for selection)
                if not self.popup.visible:
                    char = '\n'
            elif key == Key.tab:
                char = '\t'

            # Reset select-all flag when typing any character (user cancelled select-all by typing)
            if char and self.select_all_active:
                self.select_all_active = False

            if char and self.is_word_delimiter(char):
                self.pending_restore = False
                self.last_delimiter_char = char
                self.trailing_delimiter_count += 1
                # ✅ ALWAYS check and hide popup, even if word is empty
                word = ''.join(self.current_word_chars) if self.current_word_chars else ""
                if self.current_word_chars:
                    self.last_committed_word_chars = self.current_word_chars.copy()

                if self.current_word_chars and self.enabled and not self.replacing:
                    print(f"🔍 Buffer at delimiter: {self.current_word_chars} (cursor @ {self.cursor_index}) → Word: '{word}'")

                    if in_paste_cooldown:
                        print("⏸️ Skipping keystroke-based check during paste cooldown")
                        self.popup.hide()
                    else:
                        # Check if this is the word we just replaced (within 0.5 seconds)
                        time_since_replacement = time.time() - self.last_replacement_time
                        if word == self.last_replaced_word and time_since_replacement < 0.5:
                            print(f"⏭️ Skipping check - just replaced this word")
                            self.popup.hide()
                            self.last_replaced_word = ""  # Clear it
                        else:
                            self.last_word = word  # Store the word for replacement
                            self.words_checked += 1
                            suggestions, had_error = self.get_suggestions(word)
                            if had_error:
                                has_suggestions = len(suggestions) > 0
                                # Add persistent underline that stays until word is corrected
                                underline_id = self.show_no_suggestion_marker(
                                    word,
                                    has_suggestions=has_suggestions,
                                    suggestions=suggestions
                                )
                                if suggestions:
                                    if underline_id:
                                        self.last_underline_id = underline_id
                                    self.popup.hide()
                                else:
                                    if underline_id:
                                        # reset so unrelated words don't reuse the id
                                        self.last_underline_id = underline_id
                                    self.popup.hide()
                            else:
                                # Word is correct - remove any existing underline for this word
                                caret_index = self._get_caret_char_index()
                                fallback_index = None
                                if caret_index is not None and len(word) > 1:
                                    fallback_index = max(0, caret_index - 1)
                                self.remove_persistent_underline(
                                    word,
                                    char_index=caret_index,
                                    fallback_index=fallback_index,
                                )
                                self.popup.hide()
                else:
                    # ✅ Hide popup if no word was typed (multiple spaces, etc.)
                    self.popup.hide()
                # Always clear buffer after delimiter
                self.reset_current_word(preserve_delimiter=True, clear_marker=False)
                if char == ' ' and self.current_interface == "Microsoft Word":
                    try:
                        self.popup.root.after(60, self._cleanup_word_whitespace_after_space)
                    except Exception:
                        threading.Thread(target=self._cleanup_word_whitespace_after_space, daemon=True).start()
            elif char:
                self.pending_restore = False
                self.restore_allowed = False
                # ✅ Hide popup while actively typing a new word
                if self.popup.visible:
                    self.popup.hide()
                if self.selection_range:
                    start, end = self.selection_range
                    removed = ''.join(self.current_word_chars[start:end])
                    del self.current_word_chars[start:end]
                    self.cursor_index = start
                    print(f"✏️ Replacing selection '{removed}' before inserting '{char}'")
                    self.selection_range = None
                    self.selection_anchor = None
                self.current_word_chars.insert(self.cursor_index, char)
                self.cursor_index += 1
                self.trailing_delimiter_count = 0
                if len(self.current_word_chars) > 50:
                    # Keep last 50 chars and adjust cursor index accordingly
                    overflow = len(self.current_word_chars) - 50
                    if overflow > 0:
                        self.current_word_chars = self.current_word_chars[overflow:]
                        self.cursor_index = max(0, self.cursor_index - overflow)
                else:
                    # Clear selection state after normal typing
                    self.selection_anchor = None
                    self.selection_range = None
                print(f"⌨️ Typed '{char}' → Buffer: {''.join(self.current_word_chars)} (cursor @ {self.cursor_index})")
                self._schedule_refresh_if_needed("typing-insert")
        except Exception:
            pass
    
    def on_release(self, key):
        """Handle key release events"""
        # Reset clipboard check flag and ctrl_held when Ctrl is released
        if key == Key.ctrl_l or key == Key.ctrl_r:
            self.clipboard_check_active = False
            self.ctrl_held = False
        if key in (Key.shift, Key.shift_r):
            self.shift_pressed = False
            # Keep selection range (text remains highlighted) but clear anchor
            self.selection_anchor = None
    
    def toggle_enabled(self):
        """Toggle suggestion mode"""
        self.enabled = not self.enabled
        status = "ENABLED ✅" if self.enabled else "DISABLED ⛔"
        print(f"\n🔄 Suggestion mode {status}")
        if not self.enabled:
            self.popup.hide()
    
    def on_popup_close(self):
        """Handle popup window close"""
        self.running = False
        print("\n🛑 Exiting service...")
    
    def run(self):
        """Start the keyboard monitoring service"""
        self.running = True
        self._start_interface_monitor()
        
        def on_activate_toggle():
            self.toggle_enabled()
        
        from pynput import keyboard as kb
        
        # Setup hotkeys
        toggle_hotkey = kb.HotKey(
            kb.HotKey.parse('<ctrl>+<shift>+k'),
            on_activate_toggle
        )
        
        def for_canonical(f):
            return lambda k: f(listener.canonical(k))
        
        def on_key_press(key):
            for_canonical(toggle_hotkey.press)(key)
            if self.running:
                self.on_press(key)
        
        def on_key_release(key):
            for_canonical(toggle_hotkey.release)(key)
            if self.running:
                self.on_release(key)
        
        listener = kb.Listener(on_press=on_key_press, on_release=on_key_release)
        listener.start()
        
        # Start mouse listener to detect clicks on underlined words
        mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
        mouse_listener.start()
        print("🖱️ Mouse click detection enabled - click on underlined words to see suggestions")
        
        # Add periodic check to keep UI responsive
        def check_running():
            if self.running:
                self.popup.root.after(100, check_running)
            else:
                listener.stop()
                mouse_listener.stop()
                # Destroy Grammarly-style overlay
                try:
                    self.underline_overlay.destroy()
                except Exception:
                    pass
                self.active_overlay_hwnd = None
                self.popup.root.destroy()
        
        self.popup.root.after(100, check_running)
        
        try:
            self.popup.root.mainloop()  # keep Tkinter UI active
        except Exception as e:
            print(f"\n⚠️ Service stopped: {e}")
        finally:
            self.running = False
            # Clean up all persistent underlines
            self.cleanup_all_underlines()
            if listener.running:
                listener.stop()
            if mouse_listener.running:
                mouse_listener.stop()
            print("\n✅ Service stopped successfully\n")
    
    def cleanup_all_underlines(self):
        """Remove all persistent underlines when service stops"""
        print(f"\n🧹 Cleaning up {len(self.misspelled_words)} persistent underlines...")
        
        # Clear Grammarly-style overlay
        try:
            self.underline_overlay.clear_all_underlines()
        except Exception as e:
            print(f"⚠️ Error clearing overlay: {e}")
        self.active_overlay_hwnd = None
        
        with self.underline_lock:
            self.misspelled_words.clear()
        print("✅ All underlines cleaned up")


def main():
    """Main entry point"""
    service = None
    
    # Ignore Ctrl+C (SIGINT) so only double Esc can stop the service
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except Exception:
        pass
    
    try:
        print("\n🎯 Starting Kannada Smart Keyboard Service...")
        print("   Loading NLP models...\n")
        service = SmartKeyboardService()
        service.run()
    except Exception as e:
        import traceback
        print(f"❌ Fatal Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
