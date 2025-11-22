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
import signal
import re
from typing import Dict, Optional, List, Sequence, Tuple
from ctypes import (
    wintypes,
    windll,
    byref,
    Structure,
    c_long,
    c_ulong,
    pointer,
    POINTER,
    sizeof,
    create_unicode_buffer,
)
from win32api import GetCursorPos
import win32clipboard
import win32gui
import win32con
from PyQt5.QtCore import QObject, QPoint, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import spell checker
from enhanced_spell_checker import EnhancedSpellChecker
from kannada_wx_converter import is_kannada_text
from qt_overlay import QtOverlay
from qt_suggestion_popup import QtSuggestionPopup

try:
    from pynput import keyboard
    from pynput.keyboard import Key, Controller
except ImportError:
    print("❌ Error: Required packages not installed")
    print("Install: pip install pywin32 pynput")
    sys.exit(1)

try:
    import uiautomation as auto  # type: ignore[import]
except ImportError:
    auto = None

if auto:
    TEXT_RANGE_START = getattr(auto, "TextPatternRangeEndpoint_Start", 0)
    TEXT_RANGE_END = getattr(auto, "TextPatternRangeEndpoint_End", 1)
    TEXT_UNIT_CHARACTER = getattr(auto, "TextUnit_Character", 0)
else:
    TEXT_RANGE_START = 0
    TEXT_RANGE_END = 1
    TEXT_UNIT_CHARACTER = 0


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

def get_caret_position():
    """Get the screen position of the text caret (insertion point)"""
    try:
        # Get the foreground window and thread
        hwnd = windll.user32.GetForegroundWindow()
        thread_id = windll.user32.GetWindowThreadProcessId(hwnd, 0)
        
        # Get GUI thread info for the foreground window's thread
        gui_info = GUITHREADINFO(cbSize=sizeof(GUITHREADINFO))
        result = windll.user32.GetGUIThreadInfo(thread_id, byref(gui_info))
        
        if not result:
            print("⚠️ GetGUIThreadInfo failed, using cursor position")
            return GetCursorPos()
        
        # Get caret window and rectangle
        caret_hwnd = gui_info.hwndCaret
        if not caret_hwnd:
            print("⚠️ No caret window found, using cursor position")
            return GetCursorPos()
        
        # Get focused window if caret window is 0
        if not caret_hwnd:
            caret_hwnd = gui_info.hwndFocus
            
        if not caret_hwnd:
            print("⚠️ No focus window found, using cursor position")
            return GetCursorPos()
        
        # Convert caret rect to screen coordinates
        caret_rect = gui_info.rcCaret
        point = POINT(caret_rect.left, caret_rect.bottom)
        windll.user32.ClientToScreen(caret_hwnd, byref(point))
        
        print(f"✅ Caret position: ({point.x}, {point.y})")
        return (point.x, point.y)
    except Exception as e:
        print(f"❌ Error getting caret position: {e}")
        # Fallback to mouse cursor position
        cursor_pos = GetCursorPos()
        print(f"⚠️ Using cursor position: {cursor_pos}")
        return cursor_pos


# ---------------------------------------------------------------------------
# Smart Keyboard Service
# ---------------------------------------------------------------------------
class SmartKeyboardService(QObject):
    """Background service for Kannada word suggestion"""

    show_popup_requested = pyqtSignal(list, tuple)
    hide_popup_requested = pyqtSignal()
    popup_nav_requested = pyqtSignal(int)
    popup_commit_requested = pyqtSignal()
    overlay_refresh_requested = pyqtSignal(object, str, object)
    overlay_clear_requested = pyqtSignal()

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        print("\n" + "="*70)
        print("🎯 Kannada Smart Keyboard Service - Suggestion Mode")
        print("="*70)
        
        self.spell_checker = EnhancedSpellChecker()
        self.keyboard_controller = Controller()
        self.popup = QtSuggestionPopup()
        self.overlay = QtOverlay()
        self.popup_visible = False
        self._overlay_lock = threading.RLock()

        self.show_popup_requested.connect(self._handle_show_popup)
        self.hide_popup_requested.connect(self._handle_hide_popup)
        self.popup_nav_requested.connect(self._handle_popup_nav)
        self.popup_commit_requested.connect(self._handle_popup_commit)
        self.overlay_refresh_requested.connect(self._handle_overlay_refresh)
        self.overlay_clear_requested.connect(self.overlay.clear)
        self.popup.suggestion_chosen.connect(self._handle_popup_selection)
        self.popup.popup_closed.connect(self._handle_popup_closed)
        
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
        self.overlay_targets: Dict[str, Dict[str, object]] = {}
        self.word_occurrences: Dict[str, List[str]] = {}
        self.current_word_target_id: Optional[str] = None
        self.active_popup_target_id: Optional[str] = None
        self.focused_target_id: Optional[str] = None
        self.word_id_counter = 0
        self.last_window_handle: Optional[int] = None
        self.last_document_text = ''
        self.listener = None
        self._watchdog = QTimer(self)
        self._watchdog.setInterval(200)
        self._watchdog.timeout.connect(self._watch_service_health)
        self._caret_poll_timer = QTimer(self)
        self._caret_poll_timer.setInterval(250)
        self._caret_poll_timer.timeout.connect(self._poll_caret_position)

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

    # ------------------------------------------------------------------
    # UI helpers (executed on the Qt main thread via signals)
    # ------------------------------------------------------------------
    def _handle_show_popup(self, suggestions, caret_pos):
        if not suggestions:
            self._handle_hide_popup()
            return
        x, y = caret_pos
        point = QPoint(int(x + 10), int(y + 5))
        self.popup.show_suggestions(suggestions, point)
        self.popup_visible = True

    def _handle_hide_popup(self):
        self.popup.hide_popup()
        self.popup_visible = False
        self.active_popup_target_id = None

    def _handle_popup_nav(self, delta: int):
        if self.popup_visible:
            self.popup.navigate(delta)

    def _handle_popup_commit(self):
        if not self.popup_visible:
            return
        choice = self.popup.current_text()
        if choice:
            self._handle_hide_popup()
            self.replace_word(choice)

    def _handle_popup_selection(self, word: str):
        if word:
            self._handle_hide_popup()
            self.replace_word(word)

    def _handle_popup_closed(self):
        self.popup_visible = False

    def _request_popup_show(self, suggestions, target_id: Optional[str] = None):
        self.active_popup_target_id = target_id
        caret_pos = get_caret_position()
        self.show_popup_requested.emit(suggestions, caret_pos)

    def _request_popup_hide(self):
        self.hide_popup_requested.emit()

    def _request_popup_navigation(self, delta: int):
        self.popup_nav_requested.emit(delta)

    def _request_popup_commit(self):
        self.popup_commit_requested.emit()

    def _handle_overlay_refresh(self, hwnd, text, targets):
        if not hwnd or not text or not targets:
            self.overlay.clear()
            return
        self.overlay.update_underlines(hwnd, text, targets)

    # ------------------------------------------------------------------
    # Overlay + document helpers
    # ------------------------------------------------------------------
    def _find_available_char_index(self, text: str, word: str) -> Optional[int]:
        if not word or not text:
            return None
        with self._overlay_lock:
            existing_positions = {
                value.get('char_index')
                for value in self.overlay_targets.values()
                if value.get('word') == word and value.get('char_index') is not None
            }
        matches = list(re.finditer(re.escape(word), text))
        for match in matches:
            if match.start() not in existing_positions:
                return match.start()
        return matches[-1].start() if matches else None

    def _register_misspelling(
        self,
        word: str,
        suggestions: Sequence[str],
        document_state: Optional[Tuple[int, str]] = None,
    ) -> Optional[str]:
        state = document_state or self._capture_document_state()
        hwnd, text = state
        if not hwnd or not text:
            return None
        char_index = self._find_available_char_index(text, word)
        self.word_id_counter += 1
        word_id = f"{word}_{self.word_id_counter}"
        entry = {
            'id': word_id,
            'word': word,
            'char_index': char_index,
            'color': 'orange' if suggestions else 'red',
            'suggestions': list(suggestions),
            'length': len(word),
        }
        with self._overlay_lock:
            self.overlay_targets[word_id] = entry
            self.word_occurrences.setdefault(word, []).append(word_id)
            self.current_word_target_id = word_id
        self._refresh_overlay(hwnd, text)
        return word_id

    def _remove_misspelling(
        self,
        word: Optional[str] = None,
        *,
        word_id: Optional[str] = None,
        char_index: Optional[int] = None,
        remove_all: bool = False,
    ) -> bool:
        targets_to_remove: List[str] = []
        if not word_id and not word:
            return False

        with self._overlay_lock:
            if word_id:
                targets_to_remove.append(word_id)
                target_word = self.overlay_targets.get(word_id, {}).get('word')
                if target_word:
                    bucket = self.word_occurrences.get(target_word)
                    if bucket and word_id in bucket:
                        bucket.remove(word_id)
                        if not bucket:
                            self.word_occurrences.pop(target_word, None)
            elif word:
                bucket = self.word_occurrences.get(word, [])
                if not bucket:
                    return False
                if remove_all:
                    targets_to_remove.extend(bucket)
                    self.word_occurrences.pop(word, None)
                else:
                    chosen_id = None
                    if char_index is not None:
                        for candidate in bucket:
                            entry = self.overlay_targets.get(candidate)
                            if entry and entry.get('char_index') == char_index:
                                chosen_id = candidate
                                break
                    if not chosen_id:
                        chosen_id = bucket[-1]
                    bucket.remove(chosen_id)
                    if not bucket:
                        self.word_occurrences.pop(word, None)
                    targets_to_remove.append(chosen_id)

        removed_any = False
        with self._overlay_lock:
            for target_id in targets_to_remove:
                if self.overlay_targets.pop(target_id, None) is not None:
                    removed_any = True
                    if self.current_word_target_id == target_id:
                        self.current_word_target_id = None
                    if self.active_popup_target_id == target_id:
                        self.active_popup_target_id = None
                    if self.focused_target_id == target_id:
                        self.focused_target_id = None
        if removed_any:
            self._refresh_overlay()
        return removed_any

    def _clear_current_word_highlight(self):
        if self.current_word_target_id:
            target_id = self.current_word_target_id
            self._remove_misspelling(word_id=target_id)
            if self.focused_target_id == target_id:
                self.focused_target_id = None
            self.current_word_target_id = None

    def _get_caret_text_index(self) -> Optional[int]:
        if auto is None:
            return None
        try:
            element = auto.GetFocusedControl()
            if not element:
                return None
            pattern = element.GetPattern(auto.PatternId.TextPattern)
            if not pattern:
                return None
            selections = pattern.GetSelection()
            if not selections:
                return None
            caret_range = selections[0].Clone()
            temp_range = caret_range.Clone()
            temp_range.MoveEndpointByRange(
                TEXT_RANGE_START,
                pattern.DocumentRange,
                TEXT_RANGE_START,
            )
            prefix = temp_range.GetText(-1) or ''
            return len(prefix)
        except Exception:
            return None

    def _locate_target_by_index(self, caret_index: int) -> Optional[Dict[str, object]]:
        if caret_index is None:
            return None
        with self._overlay_lock:
            targets = list(self.overlay_targets.values())
        for target in targets:
            start = target.get('char_index')
            if start is None:
                continue
            length = target.get('length') or len(target.get('word', ''))
            if length is None:
                continue
            if start <= caret_index <= start + length:
                return target
        return None

    def _select_target_range(self, target_id: Optional[str]) -> bool:
        if auto is None or not target_id:
            return False
        with self._overlay_lock:
            target = self.overlay_targets.get(target_id)
        if not target:
            return False
        start = target.get('char_index')
        length = target.get('length') or len(target.get('word') or '')
        if start is None or length <= 0:
            return False
        try:
            element = auto.GetFocusedControl()
            if not element:
                return False
            pattern = element.GetPattern(auto.PatternId.TextPattern)
            if not pattern:
                return False
            document_range = pattern.DocumentRange
            selection_range = document_range.Clone()
            selection_range.MoveEndpointByRange(TEXT_RANGE_START, document_range, TEXT_RANGE_START)
            selection_range.MoveEndpointByRange(TEXT_RANGE_END, document_range, TEXT_RANGE_START)
            selection_range.MoveEndpointByUnit(TEXT_RANGE_START, TEXT_UNIT_CHARACTER, start)
            selection_range.MoveEndpointByUnit(TEXT_RANGE_END, TEXT_UNIT_CHARACTER, start + length)
            selection_range.Select()
            return True
        except Exception:
            return False

    def _select_word_via_hotkeys(self):
        self.keyboard_controller.press(Key.ctrl)
        self.keyboard_controller.press(Key.shift)
        self.keyboard_controller.press(Key.left)
        self.keyboard_controller.release(Key.left)
        self.keyboard_controller.press(Key.right)
        self.keyboard_controller.release(Key.right)
        self.keyboard_controller.release(Key.shift)
        self.keyboard_controller.release(Key.ctrl)
        time.sleep(0.01)

    def _poll_caret_position(self):
        if not self.running or not self.enabled:
            if self.popup_visible and not self.current_word_chars:
                self._request_popup_hide()
            return
        with self._overlay_lock:
            has_targets = bool(self.overlay_targets)
        if not has_targets:
            if self.focused_target_id:
                self.focused_target_id = None
            if self.popup_visible and not self.current_word_chars:
                self._request_popup_hide()
            return
        if self.current_word_chars:
            return
        caret_index = self._get_caret_text_index()
        if caret_index is None:
            return
        target = self._locate_target_by_index(caret_index)
        if not target:
            if self.focused_target_id:
                self.focused_target_id = None
                self.current_word_target_id = None
                if self.popup_visible:
                    self._request_popup_hide()
            return
        if target['id'] == self.focused_target_id:
            return
        self.focused_target_id = target['id']
        self.current_word_target_id = target['id']
        self.last_word = target.get('word', '') or ''
        suggestions = target.get('suggestions', [])
        if suggestions:
            self._request_popup_show(suggestions, target['id'])
        else:
            self._request_popup_hide()

    def _refresh_overlay(self, hwnd: Optional[int] = None, text: Optional[str] = None):
        with self._overlay_lock:
            if not self.overlay_targets:
                self.word_occurrences.clear()
                should_clear = True
                targets: List[Dict[str, object]] = []
            else:
                should_clear = False
                targets = list(self.overlay_targets.values())
        if should_clear:
            self.overlay_clear_requested.emit()
            return
        hwnd = hwnd or self.last_window_handle
        text = text if text is not None else self.last_document_text
        if not hwnd or text is None:
            self.overlay_clear_requested.emit()
            return
        self.overlay_refresh_requested.emit(hwnd, text, targets)

    def _capture_document_state(self):
        hwnd = self._get_focus_window_handle() or win32gui.GetForegroundWindow()
        text = self._get_text_via_uia(hwnd)
        if not text:
            text = self._get_text_via_win32(hwnd)
        self.last_window_handle = hwnd
        self.last_document_text = text or ''
        return hwnd, self.last_document_text

    def _get_focus_window_handle(self) -> Optional[int]:
        try:
            foreground = windll.user32.GetForegroundWindow()
            thread_id = windll.user32.GetWindowThreadProcessId(foreground, 0)
            gui_info = GUITHREADINFO(cbSize=sizeof(GUITHREADINFO))
            result = windll.user32.GetGUIThreadInfo(thread_id, byref(gui_info))
            if not result:
                return foreground
            if gui_info.hwndFocus:
                return gui_info.hwndFocus
            if gui_info.hwndCaret:
                return gui_info.hwndCaret
            return foreground
        except Exception:
            return None

    def _get_text_via_uia(self, expected_hwnd: Optional[int] = None) -> str:
        if auto is None:
            return ''
        try:
            element = auto.GetFocusedControl()
            if not element:
                return ''
            if not self._element_matches_hwnd(element, expected_hwnd):
                return ''
            pattern = element.GetPattern(auto.PatternId.TextPattern)
            if not pattern:
                return ''
            document_range = getattr(pattern, 'DocumentRange', None)
            if document_range:
                text = document_range.GetText(-1)
                return text or ''
        except Exception:
            return ''
        return ''

    def _element_matches_hwnd(self, element, expected_hwnd: Optional[int]) -> bool:
        if not expected_hwnd or not element:
            return True
        try:
            handle = getattr(element, 'NativeWindowHandle', None)
            if handle and handle != expected_hwnd:
                return False
        except Exception:
            pass
        return True

    def _get_text_via_win32(self, hwnd: Optional[int]) -> str:
        if not hwnd:
            return ''
        handles_to_try = []
        current = hwnd
        visited = set()
        while current and current not in visited:
            handles_to_try.append(current)
            visited.add(current)
            current = win32gui.GetParent(current)
        for handle in handles_to_try:
            try:
                length = win32gui.SendMessage(handle, win32con.WM_GETTEXTLENGTH, 0, 0)
                if length <= 0 or length > 1_000_000:
                    continue
                buffer = create_unicode_buffer(length + 1)
                win32gui.SendMessage(handle, win32con.WM_GETTEXT, length + 1, buffer)
                if buffer.value:
                    return buffer.value
            except Exception:
                continue
        return ''

    def _watch_service_health(self):
        if self.running:
            return
        self._watchdog.stop()
        self._caret_poll_timer.stop()
        if self.listener and self.listener.running:
            self.listener.stop()
        self.overlay_clear_requested.emit()
        self._request_popup_hide()
        self.app.quit()
    
    def reset_current_word(self, preserve_delimiter=False):
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
                print(f"🔍 Scanning pasted words ({len(words)})")
                doc_state = self._capture_document_state()
                hwnd, captured_text = doc_state
                if not hwnd or not captured_text:
                    print("⚠️ Unable to capture document text for paste scan")
                    return
                any_tracked = False
                for pasted_word in words:
                    has_error, suggestions = self.check_word_spelling(pasted_word)
                    if has_error:
                        print(f"   ⚠️ '{pasted_word}' flagged")
                        self._register_misspelling(pasted_word, suggestions, document_state=doc_state)
                        any_tracked = True
                if not any_tracked:
                    print("ℹ️ No spelling issues detected in pasted text")
                self.current_word_target_id = None
                self._request_popup_hide()
            else:
                print(f"⚠️ No Kannada words found or service disabled")
        except Exception as e:
            print(f"❌ Error checking pasted text: {e}")
            import traceback
            traceback.print_exc()
    
    def check_word_spelling(self, word):
        """Return (has_error, suggestions) for a given word"""
        if not word or len(word) < 2:
            return False, []
        if not any(self.is_kannada_char(c) for c in word):
            return False, []
        was_kannada = is_kannada_text(word)
        try:
            errors = self.spell_checker.check_text(word)
            if errors:
                error = errors[0]
                suggestions = error.get('suggestions', [])
                if was_kannada:
                    from kannada_wx_converter import wx_to_kannada
                    suggestions = [wx_to_kannada(s) for s in suggestions]
                return True, suggestions[:5]
        except Exception:
            pass
        return False, []
    
    def replace_word(self, chosen_word):
        """Replace the misspelled word with chosen suggestion"""
        try:
            print(f"✅ Replacing with: '{chosen_word}'")
            self.replacing = True  # Set flag to prevent re-triggering
            self.last_replaced_word = chosen_word  # Remember what we just replaced
            self.last_replacement_time = time.time()  # Remember when
            self._request_popup_hide()  # Ensure popup is hidden
            time.sleep(0.05)

            delimiter = self.last_delimiter_char or ' '
            target_id = self.active_popup_target_id or self.current_word_target_id
            remove_delimiter = self.trailing_delimiter_count > 0 and bool(self.last_delimiter_char)
            
            # Remove the delimiter (space) that triggered the suggestion, if applicable
            if remove_delimiter:
                self.keyboard_controller.press(Key.backspace)
                self.keyboard_controller.release(Key.backspace)
                time.sleep(0.01)
            
            # Select the target word via UIA if possible, otherwise fall back to hotkeys
            selected = self._select_target_range(target_id)
            if not selected:
                self._select_word_via_hotkeys()
            
            # Delete the selected word
            self.keyboard_controller.press(Key.delete)
            self.keyboard_controller.release(Key.delete)
            time.sleep(0.02)
            
            # Type the chosen word
            self.keyboard_controller.type(chosen_word)
            time.sleep(0.01)
            self.last_committed_word_chars = list(chosen_word)
            
            # Re-type the original delimiter so spacing stays consistent
            if remove_delimiter:
                self.type_delimiter_key(delimiter)
                self.last_delimiter_char = delimiter
                self.trailing_delimiter_count = 1
            else:
                self.trailing_delimiter_count = 0
            
            # Wait longer before resetting flag to ensure space is fully processed
            time.sleep(0.15)
            
            self.replacing = False  # Reset flag after replacement complete
            print("✅ Replacement complete")
            if self.last_word:
                if target_id:
                    self._remove_misspelling(word_id=target_id)
                else:
                    self._remove_misspelling(self.last_word)
                self.current_word_target_id = None
            self.reset_current_word(preserve_delimiter=True)
            
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
                    self._request_popup_hide()
                    self.last_esc_time = 0
                    return

                # otherwise, set last_esc_time and hide popup if visible
                self.last_esc_time = current_time
                if self.popup_visible:
                    self._request_popup_hide()
                return
            
            # Navigation controls for popup (only handles list navigation/selection)
            if self.popup_visible:
                if key == Key.down:
                    self._request_popup_navigation(1)
                    return
                elif key == Key.up:
                    self._request_popup_navigation(-1)
                    return
                elif key == Key.enter:
                    print("🔍 Enter pressed - popup visible")
                    self._request_popup_commit()
                    return

            # Buffer-aware editing controls (apply whether popup is visible or not)
            if key == Key.backspace:
                self._clear_current_word_highlight()
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
                if self.popup_visible:
                    self._request_popup_hide()
                return

            if key == Key.delete:
                self._clear_current_word_highlight()
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
                if self.popup_visible:
                    self._request_popup_hide()
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
                if self.popup_visible:
                    self._request_popup_hide()
                return

            # Handle normal characters
            char = None
            if hasattr(key, 'char'):
                char = key.char
            elif key == Key.space:
                char = ' '
            elif key == Key.enter:
                # Don't treat Enter as delimiter if popup is visible (it's for selection)
                if not self.popup_visible:
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
                        self._request_popup_hide()
                        self.last_replaced_word = ""  # Clear it
                    else:
                        self.last_word = word  # Store the word for replacement
                        has_error, suggestions = self.check_word_spelling(word)
                        if has_error:
                            self.words_checked += 1
                            target_id = self._register_misspelling(word, suggestions)
                            if suggestions:
                                self._request_popup_show(suggestions, target_id)
                            else:
                                self._request_popup_hide()
                        else:
                            self._remove_misspelling(word)
                            self._request_popup_hide()
                else:
                    # ✅ Hide popup if no word was typed (multiple spaces, etc.)
                    self._request_popup_hide()
                # Always clear buffer after delimiter
                self.reset_current_word(preserve_delimiter=True)
            elif char:
                self.pending_restore = False
                self.restore_allowed = False
                self.focused_target_id = None
                # ✅ Hide popup while actively typing a new word
                if self.popup_visible:
                    self._request_popup_hide()
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
            self._request_popup_hide()
    
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
        self.listener = listener
        listener.start()
        self._watchdog.start()
        self._caret_poll_timer.start()

        try:
            self.app.exec_()
        except Exception as e:
            print(f"\n⚠️ Service stopped: {e}")
        finally:
            self.running = False
            self._watchdog.stop()
            self._caret_poll_timer.stop()
            if self.listener:
                self.listener.stop()
                self.listener.join()
            self.overlay_clear_requested.emit()
            self._request_popup_hide()
            print("\n✅ Service stopped successfully\n")


def main():
    """Main entry point"""
    service = None
    app = None
    
    # Ignore Ctrl+C (SIGINT) so only double Esc can stop the service
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except Exception:
        pass
    
    try:
        print("\n🎯 Starting Kannada Smart Keyboard Service...")
        print("   Loading NLP models...\n")
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        service = SmartKeyboardService(app)
        service.run()
    except Exception as e:
        import traceback
        print(f"❌ Fatal Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
