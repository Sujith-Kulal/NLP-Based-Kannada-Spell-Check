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
import threading
import tkinter as tk
from ctypes import wintypes, windll, byref, Structure, c_long, c_ulong, c_short, pointer, POINTER, sizeof, create_unicode_buffer
from win32api import GetCursorPos
import signal
import win32clipboard
import re
import win32gui
import win32con
from typing import List, Optional, Tuple, Dict


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
    def __init__(self, on_selection_callback=None, on_close_callback=None):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.withdraw()
        self.suggestions = []
        self.selected = 0
        self.visible = False
        self.on_selection_callback = on_selection_callback
        self.on_close_callback = on_close_callback

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
        x, y = get_caret_position()
        
        # Position popup slightly below and to the right of the caret
        self.root.geometry(f"+{x+10}+{y+5}")
        self.root.deiconify()
        self.visible = True
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        self.root.withdraw()
        self.visible = False

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
        self.popup = SuggestionPopup(
            on_selection_callback=self.replace_word,
            on_close_callback=self.on_popup_close
        )
        
        # Initialize Grammarly-style fake underline overlay with DPI + Font + UIA support
        self.underline_overlay = UnderlineOverlayWindow(self.popup.root)
        self.caret_tracker = CaretTracker()  # Now with font metrics, DPI, and UI Automation
        self.word_position_calc = WordPositionCalculator(self.caret_tracker)
        
        # Underline styling + relocation controls
        self.underline_focus_ratio = 0.45  # portion of the word width to underline (centered)
        self.underline_focus_min_px = 28
        self.underline_lock = threading.Lock()

        # Track all misspelled words with persistent underlines
        self.misspelled_words = {}
        
        # Document-wide word tracking dictionary
        # Format: {word_index: {'word': str, 'corrected_word': str, 'suggestions': list, 
        #                       'position': int, 'has_error': bool, 'checked': bool}}
        self.document_words = {}  # Dictionary to store all words in document
        self.word_index_counter = 0  # Counter for unique word indices
        self.document_text_cache = ""  # Cache of last known document text
        self.document_lock = threading.Lock()  # Lock for document_words access
        
        self.caret_step_delay = 0.003
        
        self.current_word_chars = []  # Characters in the current word being typed/edited
        self.cursor_index = 0  # Position within the current word buffer
        self.enabled = True
        self.words_checked = 0
        self.last_word = ""  # Store last word for replacement
        self.running = False  # Service running flag
        self.replacing = False  # Flag to prevent re-showing popup during replacement
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
        self.default_text_margin_px = 18
        self.default_baseline_offset_px = 32
        self.default_line_height_px = 28
        self.paste_cooldown_until = 0.0  # Timestamp until per-key checks resume after paste
        self.layout_horizontal_padding_px = 12  # Safety padding when simulating client width
        self.layout_tab_stop_spaces = 4  # Approximate tab stop spacing (Notepad default = 8, but Kannada wider)
        self.layout_min_char_px = 6  # Guard for zero-width glyphs during layout

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
                self.remove_persistent_underline(before)
                return True
            # Fallback for last committed word (only if it was Kannada)
            if self.last_committed_word_chars:
                last_word = ''.join(self.last_committed_word_chars).strip()
                if last_word and any(self.is_kannada_char(c) for c in last_word):
                    print(f"🔍 Removing underline for deleted Kannada word '{last_word}' (from last_committed)")
                    self.remove_persistent_underline(last_word)
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
                self.remove_persistent_underline(before)
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
        """Heuristic: remove the underline closest to the caret, if any."""
        try:
            caret_x, caret_y = get_caret_position()
        except Exception:
            return False

        best_word = None
        best_distance = None

        with self.underline_lock:
            items = list(self.misspelled_words.items())

        for word, info in items:
            start_x, start_y = self._resolve_absolute_position(info)
            width = info.get('width', 0)
            if start_x is None or start_y is None or width <= 0:
                continue
            inside_span = start_x <= caret_x <= start_x + width
            near_span = (
                start_x - tolerance <= caret_x <= start_x + width + tolerance
                and start_y - tolerance <= caret_y <= start_y + 20 + tolerance
            )
            if not inside_span and not near_span:
                continue

            if inside_span:
                distance = 0
            else:
                distance = min(abs(caret_x - start_x), abs(caret_x - (start_x + width)))

            if best_word is None or distance < best_distance:
                best_word = word
                best_distance = distance

        if best_word:
            self.remove_persistent_underline(best_word)
            return True
        return False

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
        window_rect: Optional[Tuple[int, int, int, int]] = None,
        relative_start_x: Optional[int] = None,
        relative_y: Optional[int] = None,
    ):
        """
        Add a persistent Grammarly-style fake underline for a misspelled word.
        This creates a transparent overlay window with red wavy line beneath the word.
        """
        with self.underline_lock:
            if word in self.misspelled_words:
                return

        try:
            # Determine underline color and style
            has_suggestions = len(suggestions) > 0
            color = "#F57C00" if has_suggestions else "#FF3B30"  # Orange or Red
            style = "wavy"  # Wavy underline for spelling errors (like Grammarly)
            
            # Show overlay if not already visible
            if not self.underline_overlay.visible:
                self.underline_overlay.show(hwnd)
            
            # Add fake underline to the transparent overlay
            self.underline_overlay.add_underline(
                word_id=word,
                word_x=word_start_x,
                word_y=caret_y + 2,  # Position slightly below text
                word_width=word_width,
                color=color,
                style=style,
                hwnd=hwnd
            )
            
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
                    rel_y = caret_y - rect[1]

            info = {
                'suggestions': suggestions,
                'relative_start_x': rel_start,
                'relative_y': rel_y,
                'hwnd': hwnd,
                'last_rect': rect,
                'absolute_position': (word_start_x, caret_y),
                'width': word_width
            }

            # Store the marker and word info
            with self.underline_lock:
                self.misspelled_words[word] = info
                total = len(self.misspelled_words)

            print(f"{'🟠' if has_suggestions else '🔴'} Added persistent underline for '{word}' - Total misspelled: {total}")

        except Exception as exc:
            print(f"⚠️ Failed to add persistent underline for '{word}': {exc}")
    
    def remove_persistent_underline(self, word: str):
        """Remove the persistent fake underline for a corrected word."""
        # Remove from Grammarly-style overlay
        try:
            self.underline_overlay.remove_underline(word)
        except Exception as e:
            print(f"⚠️ Error removing overlay underline: {e}")
        
        with self.underline_lock:
            removed = self.misspelled_words.pop(word, None)
            remaining = len(self.misspelled_words)
        if removed is not None:
            print(f"✅ Removed underline for corrected word '{word}' - Remaining: {remaining}")
    
    def on_mouse_click(self, x, y, button, pressed):
        """Handle mouse clicks to detect clicks on underlined words"""
        if not pressed or button != Button.left:
            return
        
        # Small delay to let caret position update
        time.sleep(0.05)
        
        with self.underline_lock:
            underline_items = list(self.misspelled_words.items())

        # Check if click is near any underlined word
        for word, info in underline_items:
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

            word_width = info['width']
            
            # Check if click is within the underlined word area (with some tolerance)
            tolerance = 10
            if (word_x - tolerance <= x <= word_x + word_width + tolerance and
                word_y - tolerance <= y <= word_y + 20 + tolerance):
                
                # User clicked on this underlined word!
                suggestions = info['suggestions']
                print(f"🖱️ Clicked on underlined word '{word}' - showing suggestions")
                
                if suggestions:
                    self.last_word = word
                    self.popup.show(suggestions)
                else:
                    print(f"⚠️ No suggestions available for '{word}'")
                break
    
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

    def show_no_suggestion_marker(self, word: str, has_suggestions: bool = False, suggestions: list = None):
        """Show persistent underline directly beneath the misspelled Kannada word.
        
        Args:
            word: The word to underline
            has_suggestions: True if suggestions available (orange), False for severe errors (red)
            suggestions: List of suggestions for this word
        """
        if not word or not self.enabled:
            return

        try:
            # Get current caret position (end of word)
            caret_x, caret_y = get_caret_position()
            
            # Measure the actual pixel width of the Kannada word
            hwnd = windll.user32.GetForegroundWindow()
            word_width = measure_text_width(word, hwnd)

            window_rect = None
            try:
                window_rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                window_rect = None
            
            # Calculate word start position (caret is at end, move back by word width)
            word_start_x = caret_x - word_width

            focus_width, focus_offset = self._compute_focus_span(word_width)
            display_start_x = word_start_x + focus_offset
            relative_start = None
            relative_y = None
            if window_rect:
                relative_start = display_start_x - window_rect[0]
                relative_y = caret_y - window_rect[1]
            
            # Always use persistent overlays now
            self.add_persistent_underline(
                word=word,
                suggestions=suggestions or [],
                caret_x=caret_x,
                caret_y=caret_y,
                word_width=focus_width,
                word_start_x=display_start_x,
                hwnd=hwnd,
                window_rect=window_rect,
                relative_start_x=relative_start,
                relative_y=relative_y
            )
            
        except Exception as exc:
            print(f"⚠️ Unable to underline word '{word}': {exc}")
    
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

    def capture_paste_anchor(self):
        """Snapshot caret and window geometry just before a paste."""
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

        self.last_paste_anchor = {
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
                    baseline_y = screen_start_y + ascent
                else:
                    baseline_y = screen_start_y + line_height

                layout[span_idx] = {
                    'start_x': screen_start_x,
                    'baseline_y': baseline_y,
                    'width': word_width
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
                geometry = geometry_snapshot or self._resolve_paste_anchor_geometry()
                if not geometry:
                    print("⚠️ Unable to resolve paste geometry; skipping underline placement.")
                    return

                target_hwnd = geometry['hwnd']
                window_rect = geometry['window_rect']
                line_height = geometry['line_height']
                layout_map = self._build_notepad_layout(full_text, spans, geometry)
                if not layout_map:
                    print("⚠️ Unable to rebuild Notepad layout; skipping paste underlines.")
                    return
                last_popup_data: Optional[Tuple[str, List[str]]] = None

                for idx, match in enumerate(spans):
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
                        relative_y = caret_y - window_rect[1]

                    self.add_persistent_underline(
                        word=word,
                        suggestions=suggestions,
                        caret_x=caret_x,
                        caret_y=caret_y,
                        word_width=word_width,
                        word_start_x=word_start_x,
                        hwnd=target_hwnd,
                        window_rect=window_rect,
                        relative_start_x=relative_start,
                        relative_y=relative_y,
                    )

                    if suggestions:
                        last_popup_data = (word, suggestions)

                if last_popup_data:
                    word, suggestions = last_popup_data

                    def _show_last_popup():
                        self.last_word = word
                        self.popup.show(suggestions)

                    try:
                        self.popup.root.after(0, _show_last_popup)
                    except Exception:
                        pass

            except Exception as exc:
                print(f"❌ Error processing pasted words for underlines: {exc}")
                import traceback
                traceback.print_exc()
            finally:
                self.replacing = False
                self.last_paste_anchor = None

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
        try:
            print(f"✅ Replacing with: '{chosen_word}'")
            self.replacing = True  # Set flag to prevent re-triggering
            self.last_replaced_word = chosen_word  # Remember what we just replaced
            self.last_replacement_time = time.time()  # Remember when
            self.popup.hide()  # Ensure popup is hidden
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
            self.last_committed_word_chars = list(chosen_word)
            
            # Re-type the original delimiter so spacing stays consistent
            self.type_delimiter_key(delimiter)
            self.last_delimiter_char = delimiter
            self.trailing_delimiter_count = 1
            
            # Wait longer before resetting flag to ensure space is fully processed
            time.sleep(0.15)
            
            self.replacing = False  # Reset flag after replacement complete
            print("✅ Replacement complete")
            
            # Update document dictionary with the replacement
            self.update_document_word(self.last_word, chosen_word)
            
            # Remove the persistent underline for the OLD misspelled word
            self.remove_persistent_underline(self.last_word)
            
            self.reset_current_word(preserve_delimiter=True, clear_marker=False)
            
            # Re-check all words from start to end in background
            threading.Thread(
                target=self.check_all_words_from_start_to_end,
                daemon=True
            ).start()
            
        except Exception as e:
            print(f"⚠️ Replacement failed: {e}")
            self.replacing = False

    def on_press(self, key):
        """Handle key press events"""
        try:
            # Skip processing if we're in the middle of replacing
            if self.replacing:
                return

            in_paste_cooldown = self._in_paste_cooldown()

            # Track Shift key for selection handling
            if key in (Key.shift, Key.shift_r):
                self.shift_pressed = True
                if self.selection_anchor is None:
                    self.selection_anchor = self.cursor_index
                return
            
            # Detect Ctrl+V paste operation
            if key == Key.ctrl_l or key == Key.ctrl_r:
                self.clipboard_check_active = True
            elif self.clipboard_check_active:
                # Check if 'v' key is pressed (either as char or vk code)
                is_v_key = False
                if hasattr(key, 'char') and key.char and key.char.lower() == 'v':
                    is_v_key = True
                elif hasattr(key, 'vk') and key.vk == 86:  # VK code for 'V'
                    is_v_key = True
                
                if is_v_key:
                    self._start_paste_cooldown(0.8)
                    in_paste_cooldown = True
                    self.capture_paste_anchor()
                    # Ctrl+V detected - schedule clipboard check after paste completes
                    print("📋 Paste detected - checking clipboard...")
                    threading.Timer(0.3, self.check_pasted_text).start()
                
                self.clipboard_check_active = False
            
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
                    # Only use caret-based removal as last resort when we truly don't know which word was deleted
                    # (i.e., when buffer_before_edit is empty/unknown)
                    if not removed and not self.current_word_chars and not buffer_before_edit.strip():
                        self._remove_underlines_near_caret()
                if self.popup.visible:
                    self.popup.hide()
                return

            if key == Key.delete:
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
                    # Only use caret-based removal as last resort when we truly don't know which word was deleted
                    # (i.e., when buffer_before_edit is empty/unknown)
                    if not removed and not self.current_word_chars and not buffer_before_edit.strip():
                        self._remove_underlines_near_caret()
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
                                self.show_no_suggestion_marker(
                                    word,
                                    has_suggestions=has_suggestions,
                                    suggestions=suggestions
                                )
                                if suggestions:
                                    self.popup.show(suggestions)
                                else:
                                    self.popup.hide()
                            else:
                                # Word is correct - remove any existing underline for this word
                                self.remove_persistent_underline(word)
                                self.popup.hide()
                else:
                    # ✅ Hide popup if no word was typed (multiple spaces, etc.)
                    self.popup.hide()
                # Always clear buffer after delimiter
                self.reset_current_word(preserve_delimiter=True, clear_marker=False)
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
        except Exception:
            pass
    
    def on_release(self, key):
        """Handle key release events"""
        # Reset clipboard check flag when Ctrl is released
        if key == Key.ctrl_l or key == Key.ctrl_r:
            self.clipboard_check_active = False
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
                self.popup.root.destroy()
        
        self.popup.root.after(100, check_running)
        
        try:
            self.popup.root.mainloop()  # keep Tkinter UI active
        except Exception as e:
            print(f"\n⚠️ Service stopped: {e}")
        finally:
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
