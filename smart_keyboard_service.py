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
from ctypes import wintypes, windll, byref, Structure, c_long, c_ulong, pointer, POINTER, sizeof
from win32api import GetCursorPos
import signal
import win32clipboard
import re
import win32gui
import win32con
from typing import List, Optional, Tuple

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import spell checker
from enhanced_spell_checker import EnhancedSpellChecker
from kannada_wx_converter import is_kannada_text

try:
    from pynput import keyboard
    from pynput.keyboard import Key, Controller
except ImportError:
    print("❌ Error: Required packages not installed")
    print("Install: pip install pywin32 pynput")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Windows API structures for caret position
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
        # Set DPI awareness
        windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except:
        try:
            windll.user32.SetProcessDPIAware()
        except:
            pass
    
    try:
        hdc = windll.user32.GetDC(0)
        dpi = windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        windll.user32.ReleaseDC(0, hdc)
        scale = dpi / 96.0  # 96 is default DPI
        return scale
    except:
        return 1.0

def get_caret_position():
    """Get the screen position of the text caret (insertion point) with DPI awareness"""
    try:
        # Get the foreground window and thread
        hwnd = windll.user32.GetForegroundWindow()
        thread_id = windll.user32.GetWindowThreadProcessId(hwnd, 0)
        
        # Get GUI thread info for the foreground window's thread
        gui_info = GUITHREADINFO(cbSize=sizeof(GUITHREADINFO))
        result = windll.user32.GetGUIThreadInfo(thread_id, byref(gui_info))
        
        if not result:
            return GetCursorPos()
        
        # Get caret window and rectangle
        caret_hwnd = gui_info.hwndCaret
        if not caret_hwnd:
            caret_hwnd = gui_info.hwndFocus
            
        if not caret_hwnd:
            return GetCursorPos()
        
        # Convert caret rect to screen coordinates
        caret_rect = gui_info.rcCaret
        point = POINT(caret_rect.left, caret_rect.bottom)
        windll.user32.ClientToScreen(caret_hwnd, byref(point))
        
        return (point.x, point.y)
    except Exception as e:
        # Fallback to mouse cursor position
        cursor_pos = GetCursorPos()
        return cursor_pos

def measure_text_width(text, hwnd=None):
    """Measure the pixel width of text, particularly for Kannada characters"""
    try:
        if not hwnd:
            hwnd = windll.user32.GetForegroundWindow()
        
        hdc = windll.user32.GetDC(hwnd)
        if not hdc:
            # Fallback to character count estimation
            return len(text) * 12
        
        # Create SIZE structure for text measurement
        class SIZE(Structure):
            _fields_ = [("cx", c_long), ("cy", c_long)]
        
        size = SIZE()
        windll.gdi32.GetTextExtentPoint32W(hdc, text, len(text), byref(size))
        windll.user32.ReleaseDC(hwnd, hdc)
        
        # Apply DPI scaling
        scale = get_dpi_scale()
        width = int(size.cx / scale) if scale > 0 else size.cx
        
        return max(width, len(text) * 8)  # Minimum width estimation
    except:
        # Fallback: estimate based on character count
        # Kannada characters are typically wider
        return len(text) * 12


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


class UnderlineMarker:
    """Overlay window that draws an underline below a target word."""

    def __init__(
        self,
        master: tk.Tk,
        *,
        char_px: int = 12,
        min_width: int = 10,
        duration_ms: Optional[int] = 2200,
        line_color: str = "#FF3B30"
    ) -> None:
        self.master = master
        self.char_px = max(8, char_px)
        self.min_width = max(8, min_width)
        self.duration_ms = duration_ms
        self._hide_job: Optional[str] = None
        self.visible = False
        self._bg_color = "#00FF00"
        self._line_color = line_color

        self.window = tk.Toplevel(master)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        try:
            self.window.wm_attributes("-transparentcolor", self._bg_color)
        except tk.TclError:
            try:
                self.window.attributes("-alpha", 0.85)
            except tk.TclError:
                pass
        self.window.withdraw()

        self.canvas = tk.Canvas(self.window, height=4, width=self.min_width, bg=self._bg_color, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

    def show(
        self,
        caret_x: int,
        caret_y: int,
        word_length: int,
        delimiter_extra: int = 0,
        *,
        line_color: Optional[str] = None,
        duration_ms: Optional[int] = None,
        absolute_start_x: Optional[int] = None,
        pixel_width: Optional[int] = None,
    ) -> None:
        if word_length <= 0:
            return

        total_chars = max(1, word_length + max(0, delimiter_extra))
        if pixel_width is not None:
            width = max(self.min_width, int(pixel_width))
        else:
            width = max(self.min_width, total_chars * self.char_px)
        start_x = max(0, int(absolute_start_x) if absolute_start_x is not None else int(caret_x - width))
        underline_y = 2
        color = line_color or self._line_color
        
        # Use passed duration_ms if explicitly provided, otherwise use default behavior
        # If duration_ms is explicitly None, underline persists forever (no auto-hide)
        if duration_ms is not None:
            effective_duration = duration_ms
        else:
            # No duration_ms passed, don't auto-hide (persistent underline)
            effective_duration = None

        self.canvas.config(width=width + 4, height=4)
        self.canvas.delete("underline")
        self.canvas.create_line(
            2,
            underline_y,
            width + 2,
            underline_y,
            fill=color,
            width=2,
            capstyle=tk.ROUND,
            tags="underline",
        )

        try:
            self.window.geometry(f"+{int(start_x)}+{int(caret_y + 4)}")
        except tk.TclError:
            return

        self.window.deiconify()
        self.window.lift()
        self.visible = True

        # Cancel any existing auto-hide job
        if self._hide_job is not None:
            try:
                self.window.after_cancel(self._hide_job)
            except tk.TclError:
                pass
            self._hide_job = None
        
        # Only set auto-hide timer if duration is explicitly provided and not None
        if effective_duration is not None and effective_duration > 0:
            self._hide_job = self.window.after(effective_duration, self.hide)
            print(f"⏱️ Underline will auto-hide after {effective_duration}ms")
        else:
            print(f"🔒 Underline is PERSISTENT (no auto-hide) - will stay until manually hidden")

    def hide(self) -> None:
        """Hide the underline marker"""
        if self._hide_job is not None:
            try:
                self.window.after_cancel(self._hide_job)
            except tk.TclError:
                pass
            self._hide_job = None

        if self.visible:
            try:
                self.window.withdraw()
            except tk.TclError:
                pass
            self.visible = False
    
    def keep_visible(self) -> None:
        """Ensure underline stays on top and visible (for persistent underlines)"""
        if self.visible:
            try:
                self.window.lift()
                self.window.attributes("-topmost", True)
            except tk.TclError:
                pass

    def destroy(self) -> None:
        self.hide()
        try:
            self.window.destroy()
        except tk.TclError:
            pass


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
        self.no_suggestion_marker = UnderlineMarker(self.popup.root)
        self.paste_markers: List[UnderlineMarker] = []
        
        # NEW: Track all misspelled words with persistent underlines
        self.misspelled_words = {}  # {word: {'marker': UnderlineMarker, 'suggestions': [], 'position': (x, y)}}
        self.active_misspelled_word = None  # Currently selected misspelled word for correction
        
        self.caret_step_delay = 0.003
        self.marker_active_word: str = ""
        self.marker_target_hwnd: Optional[int] = None
        self.marker_lock = threading.Lock()
        
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
        # NOTE: We don't clear markers anymore - misspelled words keep their underlines!
        # Only hide the temporary suggestion marker
        if clear_marker and not preserve_delimiter:
            self.hide_no_suggestion_marker()
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
    
    def add_persistent_underline(self, word: str, suggestions: list, caret_x: int, caret_y: int, word_width: int, word_start_x: int):
        """Add a persistent underline for a misspelled word that stays until corrected"""
        # Don't add duplicate underlines for the same word
        if word in self.misspelled_words:
            return
        
        try:
            # Create a new marker for this misspelled word
            marker = UnderlineMarker(self.popup.root)
            has_suggestions = len(suggestions) > 0
            line_color = "#F57C00" if has_suggestions else "#FF3B30"  # Orange or Red
            
            # Show persistent underline (duration_ms=None means no auto-hide)
            marker.show(
                caret_x=caret_x,
                caret_y=caret_y,
                word_length=len(word),
                delimiter_extra=0,
                line_color=line_color,
                duration_ms=None,  # Persistent!
                absolute_start_x=word_start_x,
                pixel_width=word_width
            )
            
            # Store the marker and word info
            self.misspelled_words[word] = {
                'marker': marker,
                'suggestions': suggestions,
                'position': (word_start_x, caret_y),
                'width': word_width
            }
            
            print(f"{'🟠' if has_suggestions else '🔴'} Added persistent underline for '{word}' - Total misspelled: {len(self.misspelled_words)}")
            
        except Exception as exc:
            print(f"⚠️ Failed to add persistent underline for '{word}': {exc}")
    
    def remove_persistent_underline(self, word: str):
        """Remove the persistent underline for a corrected word"""
        if word in self.misspelled_words:
            try:
                self.misspelled_words[word]['marker'].destroy()
                del self.misspelled_words[word]
                print(f"✅ Removed underline for corrected word '{word}' - Remaining: {len(self.misspelled_words)}")
            except Exception as exc:
                print(f"⚠️ Failed to remove underline for '{word}': {exc}")
    
    def hide_no_suggestion_marker(self):
        """Hide temporary suggestion overlay (not the persistent ones)"""
        try:
            self.no_suggestion_marker.hide()
        except Exception:
            pass
        self.marker_active_word = ""

    def clear_paste_underlines(self):
        """Remove all underline overlays created during paste processing."""

        def _clear():
            with self.marker_lock:
                while self.paste_markers:
                    marker = self.paste_markers.pop()
                    try:
                        marker.destroy()
                    except Exception:
                        pass
                self.marker_target_hwnd = None

        if threading.current_thread() is threading.main_thread():
            _clear()
        else:
            try:
                self.popup.root.after(0, _clear)
            except Exception:
                pass

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

    def add_paste_marker(
        self,
        caret_x: int,
        caret_y: int,
        word_length: int,
        *,
        color: str,
        absolute_start_x: Optional[int] = None,
        pixel_width: Optional[int] = None,
    ):
        """Create a persistent underline marker for pasted text."""
        marker = UnderlineMarker(
            self.popup.root,
            duration_ms=None,
            line_color=color,
        )
        try:
            marker.show(
                caret_x,
                caret_y,
                word_length,
                line_color=color,
                duration_ms=None,
                absolute_start_x=absolute_start_x,
                pixel_width=pixel_width,
            )
            self.paste_markers.append(marker)
        except Exception:
            marker.destroy()

    def start_marker_visibility_watch(self, hwnd: Optional[int]):
        if not hwnd:
            return

        def watcher(target_hwnd: int):
            while True:
                with self.marker_lock:
                    has_markers = bool(self.paste_markers) and self.marker_target_hwnd == target_hwnd
                if not has_markers:
                    break
                try:
                    if not win32gui.IsWindow(target_hwnd):
                        self.clear_paste_underlines()
                        break
                    if win32gui.IsIconic(target_hwnd):
                        self.clear_paste_underlines()
                        break
                    if win32gui.GetForegroundWindow() != target_hwnd:
                        self.clear_paste_underlines()
                        break
                except Exception:
                    self.clear_paste_underlines()
                    break
                time.sleep(0.4)

        threading.Thread(target=watcher, args=(hwnd,), daemon=True).start()

    def show_no_suggestion_marker(self, word: str, has_suggestions: bool = False, persist: bool = True, suggestions: list = None):
        """Show persistent underline directly beneath the misspelled Kannada word.
        
        Args:
            word: The word to underline
            has_suggestions: True if suggestions available (orange), False for severe errors (red)
            persist: If True, underline stays until word is corrected/replaced
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
            
            # Calculate word start position (caret is at end, move back by word width)
            word_start_x = caret_x - word_width
            
            if persist:
                # Add to persistent underlines - this will stay visible!
                self.add_persistent_underline(
                    word=word,
                    suggestions=suggestions or [],
                    caret_x=caret_x,
                    caret_y=caret_y,
                    word_width=word_width,
                    word_start_x=word_start_x
                )
            else:
                # Show temporary underline (old behavior)
                line_color = "#F57C00" if has_suggestions else "#FF3B30"
                duration = 2200
                
                self.no_suggestion_marker.show(
                    caret_x=caret_x,
                    caret_y=caret_y,
                    word_length=len(word),
                    delimiter_extra=0,
                    line_color=line_color,
                    duration_ms=duration,
                    absolute_start_x=word_start_x,
                    pixel_width=word_width
                )
                self.marker_active_word = word
            
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
    
    def extract_words_from_text(self, text):
        """Extract words from pasted text"""
        if not text:
            return []
        # Split by delimiters while preserving Kannada words
        words = re.findall(r'[^\s\n\r\t.,!?;:]+', text)
        return [w for w in words if any(self.is_kannada_char(c) for c in w)]

    def process_pasted_text_for_underlines(self, full_text: str):
        """Iterate through pasted text and underline every non-correct Kannada word."""
        if not full_text:
            return

        spans = list(re.finditer(r'[^\s\n\r\t.,!?;:]+', full_text))
        if not spans:
            return

        def worker():
            try:
                self.replacing = True
                self.popup.hide()
                self.clear_paste_underlines()

                total_chars = len(full_text)
                # Move caret back to the start of the pasted content
                self.move_caret_left(total_chars)
                time.sleep(0.06)

                target_hwnd = windll.user32.GetForegroundWindow()
                with self.marker_lock:
                    self.marker_target_hwnd = target_hwnd
                monitor_started = False

                for idx, match in enumerate(spans):
                    word = match.group(0)
                    word_len = len(word)

                    # Advance caret to the end of the current word
                    self.move_caret_right(word_len)
                    time.sleep(0.02)

                    if any(self.is_kannada_char(c) for c in word) and word_len >= 2:
                        suggestions, had_error = self.get_suggestions(word)
                        if had_error:
                            marker_color = "#FF3B30" if suggestions else "#FFA500"
                            start_x = None
                            start_y = None

                            # Walk caret back to measure start boundary
                            self.move_caret_left(word_len)
                            time.sleep(0.02)
                            try:
                                start_x, start_y = get_caret_position()
                            except Exception:
                                start_x = None
                                start_y = None

                            # Return caret to end of the word
                            self.move_caret_right(word_len)
                            time.sleep(0.02)
                            try:
                                end_x, end_y = get_caret_position()
                            except Exception:
                                end_x, end_y = (0, 0)

                            pixel_width = None
                            absolute_start = None
                            caret_y = end_y

                            if (
                                start_x is not None
                                and start_y is not None
                                and abs(end_y - start_y) < 30
                            ):
                                width_px = end_x - start_x
                                if width_px >= 4:
                                    pixel_width = width_px
                                    absolute_start = start_x

                            self.add_paste_marker(
                                end_x,
                                caret_y,
                                word_len,
                                color=marker_color,
                                absolute_start_x=absolute_start,
                                pixel_width=pixel_width,
                            )
                            if not monitor_started:
                                monitor_started = True
                                self.start_marker_visibility_watch(target_hwnd)

                    # Skip delimiters between this word and the next
                    next_start = spans[idx + 1].start() if idx + 1 < len(spans) else len(full_text)
                    delimiter_count = max(0, next_start - match.end())
                    if delimiter_count:
                        self.move_caret_right(delimiter_count)
                        time.sleep(0.015)

            except Exception as exc:
                print(f"❌ Error processing pasted words for underlines: {exc}")
                import traceback
                traceback.print_exc()
            finally:
                self.replacing = False

        threading.Thread(target=worker, daemon=True).start()
    
    def check_pasted_text(self):
        """Check if text was pasted and show suggestions for last word"""
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
                # Check the last word pasted
                last_pasted_word = words[-1]
                self.last_word = last_pasted_word
                print(f"🔍 Checking last pasted word: '{last_pasted_word}'")
                suggestions, had_error = self.get_suggestions(last_pasted_word)
                print(f"🔍 Suggestions found: {suggestions}")
                
                if had_error:
                    has_suggestions = len(suggestions) > 0
                    self.show_no_suggestion_marker(
                        last_pasted_word, 
                        has_suggestions=has_suggestions, 
                        persist=True,
                        suggestions=suggestions
                    )
                else:
                    self.remove_persistent_underline(last_pasted_word)
                    self.hide_no_suggestion_marker()

                if suggestions:
                    print(f"✅ Showing suggestions for pasted word: '{last_pasted_word}'")
                    self.popup.show(suggestions)
                else:
                    print(f"ℹ️ No suggestions for: '{last_pasted_word}'")
                    self.popup.hide()
                    if not had_error:
                        self.hide_no_suggestion_marker()
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
            
            # Remove the persistent underline for the OLD misspelled word
            self.remove_persistent_underline(self.last_word)
            
            # Hide the temporary marker and reset
            self.hide_no_suggestion_marker()
            self.reset_current_word(preserve_delimiter=True, clear_marker=False)
            
        except Exception as e:
            print(f"⚠️ Replacement failed: {e}")
            self.replacing = False

    def on_press(self, key):
        """Handle key press events"""
        try:
            # Skip processing if we're in the middle of replacing
            if self.replacing:
                return

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
                        print(f"🔄 Restored last word buffer '{''.join(self.current_word_chars)}' before backspace")
                    return
                if self.pending_restore:
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
                elif self.cursor_index > 0:
                    self.restore_allowed = False
                    removed_char = self.current_word_chars.pop(self.cursor_index - 1)
                    self.cursor_index -= 1
                    print(f"⌫ Backspace removed '{removed_char}' → Buffer: {''.join(self.current_word_chars)} (cursor @ {self.cursor_index})")
                    self.sync_committed_buffer()
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
                if self.popup.visible:
                    self.popup.hide()
                return

            if key == Key.delete:
                self.pending_restore = False
                if self.selection_range:
                    self.restore_allowed = False
                    start, end = self.selection_range
                    removed = ''.join(self.current_word_chars[start:end])
                    del self.current_word_chars[start:end]
                    self.cursor_index = start
                    print(f"⌦ Delete cleared selection '{removed}' → Buffer: {''.join(self.current_word_chars)} (cursor @ {self.cursor_index})")
                    self.selection_range = None
                    self.selection_anchor = None
                elif self.cursor_index < len(self.current_word_chars):
                    self.restore_allowed = False
                    removed_char = self.current_word_chars.pop(self.cursor_index)
                    print(f"⌦ Delete removed '{removed_char}' → Buffer: {''.join(self.current_word_chars)} (cursor @ {self.cursor_index})")
                elif self.trailing_delimiter_count > 0:
                    self.trailing_delimiter_count = max(0, self.trailing_delimiter_count - 1)
                    print(f"⌦ Consumed trailing delimiter with Delete (remaining: {self.trailing_delimiter_count})")
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
                if self.current_word_chars and self.enabled and not self.replacing:
                    word = ''.join(self.current_word_chars)
                    self.last_committed_word_chars = self.current_word_chars.copy()
                    print(f"🔍 Buffer at delimiter: {self.current_word_chars} (cursor @ {self.cursor_index}) → Word: '{word}'")
                    
                    # Check if this is the word we just replaced (within 0.5 seconds)
                    time_since_replacement = time.time() - self.last_replacement_time
                    if word == self.last_replaced_word and time_since_replacement < 0.5:
                        print(f"⏭️ Skipping check - just replaced this word")
                        self.popup.hide()
                        self.hide_no_suggestion_marker()
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
                                persist=True,
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
                            self.hide_no_suggestion_marker()
                else:
                    # ✅ Hide popup if no word was typed (multiple spaces, etc.)
                    self.popup.hide()
                    self.hide_no_suggestion_marker()
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
            self.hide_no_suggestion_marker()
            self.clear_paste_underlines()
    
    def on_popup_close(self):
        """Handle popup window close"""
        self.running = False
        self.clear_paste_underlines()
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
        
        # Add periodic check to keep UI responsive
        def check_running():
            if self.running:
                self.popup.root.after(100, check_running)
            else:
                listener.stop()
                try:
                    self.no_suggestion_marker.destroy()
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
            print("\n✅ Service stopped successfully\n")
    
    def cleanup_all_underlines(self):
        """Remove all persistent underlines when service stops"""
        print(f"\n🧹 Cleaning up {len(self.misspelled_words)} persistent underlines...")
        for word in list(self.misspelled_words.keys()):
            self.remove_persistent_underline(word)
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
