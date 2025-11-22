#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-Time Kannada Spell Checker with Transparent Overlay and Wavy Underlines
============================================================================

Architecture:
→ Keyboard hook captures typed characters
→ Current Kannada word is built in the buffer
→ Detect delimiter (space/enter/punctuation)
→ On word completion → send word to Kannada Spell Checker
→ Spell Checker returns: {correct / incorrect, suggestions}

IF WORD IS CORRECT:
    → Remove underline (if any)
    → Clear popup

IF WORD IS INCORRECT:
    → Compute caret position via Win32 GUIThreadInfo
    → Try UIA TextPattern for accurate bounding rectangles
    → If UIA fails → compute coordinates using caret start/end difference
    → If caret method fails → fallback to font-measure width
    → Compute underline start_x, underline_y, underline_width
    → Create/Update transparent overlay window on top of editor
    → Draw red/orange wavy underline for the word on Tkinter canvas
    → Store underline info in misspelled_words dictionary

→ Show suggestion popup near caret position
→ User can press arrows / click / press Enter to select suggestion
→ Replace incorrect word with chosen suggestion using keyboard simulation
→ Remove underline for corrected word
→ Update internal document_words dictionary
→ Reset current word buffer

→ (On scrolling/moving window) overlay auto-syncs with target HWND
→ (On paste event) parse entire pasted text, scan all Kannada words
→ For each wrong word → repeat underline + popup logic
→ Underlines stay persistent until corrected

Supports: Notepad, Microsoft Word

Requirements:
    pip install pywin32 pynput comtypes uiautomation

Usage:
    python realtime_spell_checker.py

Press Ctrl+Shift+S to toggle spell checking ON/OFF
Press Esc twice to stop the service
"""

import sys
import os
import time
import math
import threading
import tkinter as tk
from collections import defaultdict
from ctypes import wintypes, windll, byref, Structure, c_long, c_ulong, sizeof, POINTER, pointer
import win32gui
import win32con
import win32api
import win32clipboard

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import spell checker and converter
from enhanced_spell_checker import EnhancedSpellChecker
from kannada_wx_converter import is_kannada_text, wx_to_kannada

try:
    from pynput import keyboard
    from pynput.keyboard import Key, Controller
except ImportError:
    print("❌ Error: Required packages not installed")
    print("Install: pip install pywin32 pynput comtypes uiautomation")
    sys.exit(1)

# Try to import UIA for advanced caret detection
try:
    import comtypes.client
    import uiautomation as auto
    HAS_UIA = True
except ImportError:
    HAS_UIA = False
    print("⚠️  Warning: UIA not available (install comtypes and uiautomation for better accuracy)")


# ===========================================================================
# Windows API Structures for Caret Position
# ===========================================================================

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


# ===========================================================================
# Caret Position Detection with Fallback Strategy
# ===========================================================================

def get_caret_position_win32():
    """
    Method 1: Get caret position using Win32 GUIThreadInfo
    Returns: (x, y, width, height) or None
    """
    try:
        hwnd = windll.user32.GetForegroundWindow()
        thread_id = windll.user32.GetWindowThreadProcessId(hwnd, 0)
        
        gui_info = GUITHREADINFO(cbSize=sizeof(GUITHREADINFO))
        result = windll.user32.GetGUIThreadInfo(thread_id, byref(gui_info))
        
        if not result:
            return None
        
        caret_hwnd = gui_info.hwndCaret
        if not caret_hwnd:
            caret_hwnd = gui_info.hwndFocus
        
        if not caret_hwnd:
            return None
        
        caret_rect = gui_info.rcCaret
        
        # Convert to screen coordinates
        point_start = POINT(caret_rect.left, caret_rect.top)
        point_end = POINT(caret_rect.right, caret_rect.bottom)
        
        windll.user32.ClientToScreen(caret_hwnd, byref(point_start))
        windll.user32.ClientToScreen(caret_hwnd, byref(point_end))
        
        width = point_end.x - point_start.x
        height = point_end.y - point_start.y
        
        return (point_start.x, point_end.y, max(width, 2), height)
    except Exception as e:
        return None


def get_caret_position_uia():
    """
    Method 2: Get caret position using UIA TextPattern
    More accurate for Word and other complex editors
    Returns: (x, y, width, height) or None
    """
    if not HAS_UIA:
        return None
    
    try:
        # Get focused element
        focused = auto.GetFocusedControl()
        if not focused:
            return None
        
        # Try to get TextPattern
        text_pattern = focused.GetPattern(auto.PatternId.TextPattern)
        if not text_pattern:
            return None
        
        # Get selection (caret is a zero-width selection)
        selections = text_pattern.GetSelection()
        if not selections or len(selections) == 0:
            return None
        
        selection = selections[0]
        
        # Get bounding rectangles
        rects = selection.GetBoundingRectangles()
        if not rects or len(rects) < 4:
            return None
        
        # Extract first rectangle (x, y, width, height)
        x, y, width, height = rects[0:4]
        
        return (int(x), int(y + height), max(int(width), 2), int(height))
    except Exception:
        return None


def get_caret_position():
    """
    Get caret position with fallback strategy:
    1. Try UIA TextPattern (best for Word)
    2. Try Win32 GUIThreadInfo (good for Notepad)
    3. Fallback to cursor position
    Returns: (x, y, width, height)
    """
    # Try UIA first (best accuracy)
    result = get_caret_position_uia()
    if result:
        return result
    
    # Try Win32 API
    result = get_caret_position_win32()
    if result:
        return result
    
    # Fallback to cursor position
    cursor_pos = win32api.GetCursorPos()
    return (cursor_pos[0], cursor_pos[1], 2, 16)


def get_active_window_info():
    """Get active window handle and position"""
    try:
        hwnd = windll.user32.GetForegroundWindow()
        rect = RECT()
        windll.user32.GetWindowRect(hwnd, byref(rect))
        return {
            'hwnd': hwnd,
            'x': rect.left,
            'y': rect.top,
            'width': rect.right - rect.left,
            'height': rect.bottom - rect.top
        }
    except Exception:
        return None


# ===========================================================================
# Transparent Overlay Window with Wavy Underlines
# ===========================================================================

class TransparentOverlay:
    """
    Transparent overlay window that draws wavy underlines
    Stays on top of target application (Notepad/Word)
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide initially
        
        # Make window transparent and click-through
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', 'white')
        self.root.attributes('-alpha', 0.95)
        
        # Create canvas for drawing
        self.canvas = tk.Canvas(
            self.root,
            bg='white',
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill='both', expand=True)
        
        # Store underline objects
        self.underlines = {}  # {word_id: {canvas_items, x, y, width, word, suggestions}}
        
        self.visible = False
        self.target_hwnd = None
        
        # Start update loop
        self.update_position()
    
    def show(self):
        """Show overlay window"""
        if not self.visible:
            self.root.deiconify()
            self.visible = True
    
    def hide(self):
        """Hide overlay window"""
        if self.visible:
            self.root.withdraw()
            self.visible = False
    
    def update_position(self):
        """
        Update overlay position to match target window
        Called periodically to handle scrolling and window movement
        """
        try:
            if self.target_hwnd and self.visible:
                window_info = get_active_window_info()
                if window_info and window_info['hwnd'] == self.target_hwnd:
                    # Position overlay to cover the target window
                    self.root.geometry(
                        f"{window_info['width']}x{window_info['height']}"
                        f"+{window_info['x']}+{window_info['y']}"
                    )
        except Exception:
            pass
        
        # Schedule next update
        self.root.after(100, self.update_position)
    
    def draw_wavy_underline(self, word_id, x, y, width, color='red', suggestions=None):
        """
        Draw wavy underline at specified position
        
        Args:
            word_id: Unique identifier for this word
            x, y: Position (x = start, y = baseline)
            width: Width of underline
            color: 'red' (no suggestions) or 'orange' (has suggestions)
            suggestions: List of suggestion words
        """
        # Remove old underline if exists
        if word_id in self.underlines:
            self.remove_underline(word_id)
        
        # Choose color
        if suggestions and len(suggestions) > 0:
            line_color = '#FF8C00'  # Orange
        else:
            line_color = '#FF0000'  # Red
        
        # Generate wavy line points
        wave_height = 2
        wave_length = 4
        points = []
        
        for i in range(0, int(width) + wave_length, wave_length):
            # Create sine wave
            wave_y = y + wave_height * math.sin(i * math.pi / wave_length)
            points.extend([x + i, wave_y])
        
        # Draw the wavy line
        if len(points) >= 4:
            canvas_items = []
            
            # Draw smooth wavy line
            line_id = self.canvas.create_line(
                *points,
                fill=line_color,
                width=2,
                smooth=True
            )
            canvas_items.append(line_id)
            
            # Store underline info
            self.underlines[word_id] = {
                'items': canvas_items,
                'x': x,
                'y': y,
                'width': width,
                'suggestions': suggestions,
                'color': color
            }
            
            self.show()
    
    def remove_underline(self, word_id):
        """Remove underline for a specific word"""
        if word_id in self.underlines:
            underline = self.underlines[word_id]
            for item in underline['items']:
                try:
                    self.canvas.delete(item)
                except Exception:
                    pass
            del self.underlines[word_id]
            
            # Hide overlay if no more underlines
            if not self.underlines:
                self.hide()
    
    def clear_all(self):
        """Clear all underlines"""
        word_ids = list(self.underlines.keys())
        for word_id in word_ids:
            self.remove_underline(word_id)
        self.hide()


# ===========================================================================
# Suggestion Popup
# ===========================================================================

class SuggestionPopup:
    """Floating popup showing spelling suggestions"""
    
    def __init__(self, on_selection_callback=None, on_close_callback=None):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        # Frame for border
        frame = tk.Frame(self.root, bg='#0078D7', bd=1)
        frame.pack(fill='both', expand=True)
        
        # Listbox for<br>
        self.listbox = tk.Listbox(
            frame,
            font=('Nirmala UI', 14),
            height=6,
            width=25,
            bg='white',
            fg='black',
            selectbackground='#0078D7',
            selectforeground='white',
            highlightthickness=0,
            relief='flat',
            cursor='hand2'
        )
        self.listbox.pack(padx=1, pady=1)
        
        # Bind events
        self.listbox.bind('<ButtonRelease-1>', self._on_click)
        self.listbox.bind('<Motion>', self._on_hover)
        
        self.suggestions = []
        self.selected = 0
        self.visible = False
        self.on_selection_callback = on_selection_callback
        self.on_close_callback = on_close_callback
        self.current_word = None
    
    def show(self, suggestions, word, x, y):
        """Show popup near caret position"""
        if not suggestions:
            return
        
        self.suggestions = suggestions
        self.current_word = word
        self.selected = 0
        
        # Populate listbox
        self.listbox.delete(0, tk.END)
        for s in suggestions:
            self.listbox.insert(tk.END, s)
        
        self.listbox.select_set(0)
        self.listbox.activate(0)
        
        # Position popup near caret (slightly offset)
        self.root.geometry(f"+{x + 10}+{y + 5}")
        self.root.deiconify()
        self.visible = True
        self.root.lift()
    
    def hide(self):
        """Hide popup"""
        self.root.withdraw()
        self.visible = False
        self.current_word = None
    
    def select_next(self):
        """Select next suggestion"""
        if not self.visible or not self.suggestions:
            return
        self.selected = (self.selected + 1) % len(self.suggestions)
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(self.selected)
        self.listbox.activate(self.selected)
    
    def select_prev(self):
        """Select previous suggestion"""
        if not self.visible or not self.suggestions:
            return
        self.selected = (self.selected - 1) % len(self.suggestions)
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(self.selected)
        self.listbox.activate(self.selected)
    
    def get_selected(self):
        """Get currently selected suggestion"""
        if not self.suggestions or not self.visible:
            return None
        if 0 <= self.selected < len(self.suggestions):
            return self.suggestions[self.selected]
        return None
    
    def _on_click(self, event):
        """Handle mouse click"""
        index = self.listbox.nearest(event.y)
        if 0 <= index < len(self.suggestions):
            self.selected = index
            word = self.suggestions[self.selected]
            self.hide()
            if self.on_selection_callback:
                self.on_selection_callback(word, self.current_word)
    
    def _on_hover(self, event):
        """Handle mouse hover"""
        index = self.listbox.nearest(event.y)
        if 0 <= index < len(self.suggestions):
            self.listbox.select_clear(0, tk.END)
            self.listbox.select_set(index)
            self.listbox.activate(index)
            self.selected = index


# ===========================================================================
# Real-Time Spell Checker Service
# ===========================================================================

class RealtimeSpellChecker:
    """
    Main service that orchestrates:
    - Keyboard input capture
    - Word buffer management
    - Spell checking
    - Overlay underlines
    - Suggestion popup
    - Word replacement
    """
    
    def __init__(self):
        print("\n" + "="*80)
        print("🎯 Real-Time Kannada Spell Checker with Transparent Overlay")
        print("="*80)
        print("\nInitializing components...")
        
        # Initialize spell checker
        self.spell_checker = EnhancedSpellChecker()
        
        # Initialize UI components
        self.overlay = TransparentOverlay()
        self.popup = SuggestionPopup(
            on_selection_callback=self.replace_word,
            on_close_callback=self.on_popup_close
        )
        
        # Initialize keyboard controller
        self.keyboard_controller = Controller()
        
        # Word buffer management
        self.current_word_chars = []
        self.cursor_index = 0
        
        # Document state
        self.document_words = {}  # {word_id: {'word': str, 'position': int, 'correct': bool}}
        self.misspelled_words = {}  # {word_id: {'word': str, 'x': int, 'y': int, 'width': int, 'suggestions': list}}
        self.word_counter = 0
        
        # Service state
        self.enabled = True
        self.running = False
        self.replacing = False
        self.last_esc_time = 0
        
        # Clipboard monitoring for paste
        self.clipboard_check_active = False
        self.last_clipboard_content = ""
        
        # Tracking
        self.words_checked = 0
        self.errors_found = 0
        
        # Position tracking
        self.last_caret_pos = None
        self.caret_word_id = None
        
        print("\n✅ All components initialized!")
        print("\n📝 Controls:")
        print("   Ctrl+Shift+S : Toggle spell checking ON/OFF")
        print("   ↑ / ↓        : Navigate suggestions in popup")
        print("   Enter / Click: Replace word with selected suggestion")
        print("   Esc (popup)  : Hide suggestion popup")
        print("   Esc (twice)  : Stop the service")
        print("\n🚀 Supported Applications:")
        print("   ✅ Notepad")
        print("   ✅ Microsoft Word")
        print("\n🎨 Visual Indicators:")
        print("   🔴 Red wavy underline : Severely misspelled (no suggestions)")
        print("   🟠 Orange wavy underline : Misspelled (suggestions available)")
        print("\n💡 Type or paste Kannada text to see real-time spell checking!")
        print("="*80 + "\n")
    
    def is_word_delimiter(self, char):
        """Check if character is a word boundary"""
        if not char:
            return True
        return char in [' ', '\n', '\r', '\t', '.', ',', '!', '?', ';', ':', ')', ']', '}', '"', "'"]
    
    def is_kannada_char(self, char):
        """Check if character is Kannada"""
        return char and '\u0C80' <= char <= '\u0CFF'
    
    def get_suggestions(self, word):
        """Get spelling suggestions for a word"""
        if not word or len(word) < 2:
            return []
        if not any(self.is_kannada_char(c) for c in word):
            return []
        
        try:
            was_kannada = is_kannada_text(word)
            errors = self.spell_checker.check_text(word)
            
            if errors:
                error = errors[0]
                suggestions = error.get('suggestions', [])
                
                # Convert back to Kannada if input was Kannada
                if was_kannada and suggestions:
                    suggestions = [wx_to_kannada(s) for s in suggestions]
                
                return suggestions[:5]
        except Exception as e:
            print(f"⚠️ Error checking word: {e}")
        
        return []
    
    def compute_word_position(self, word):
        """
        Compute screen position for word underline
        Uses caret position and estimates width
        Returns: (x, y, width)
        """
        try:
            # Get caret position
            x, y, caret_width, caret_height = get_caret_position()
            
            # Estimate word width based on character count
            # Assuming average character width of 10 pixels (adjustable)
            avg_char_width = 10
            word_width = len(word) * avg_char_width
            
            # Position underline at caret, extending backward for the word
            underline_x = x - word_width
            underline_y = y + 2  # Slightly below baseline
            
            return (underline_x, underline_y, word_width)
        except Exception as e:
            print(f"⚠️ Error computing position: {e}")
            return None
    
    def check_word_spelling(self, word):
        """
        Check if word is spelled correctly
        Returns: (is_correct, suggestions)
        """
        if not word or len(word) < 2:
            return (True, [])
        
        if not any(self.is_kannada_char(c) for c in word):
            return (True, [])
        
        suggestions = self.get_suggestions(word)
        is_correct = len(suggestions) == 0
        
        return (is_correct, suggestions)
    
    def add_underline(self, word, suggestions):
        """Add wavy underline for misspelled word"""
        try:
            # Compute position
            position = self.compute_word_position(word)
            if not position:
                return
            
            x, y, width = position
            
            # Generate unique word ID
            word_id = f"word_{self.word_counter}"
            self.word_counter += 1
            
            # Store in misspelled words
            self.misspelled_words[word_id] = {
                'word': word,
                'x': x,
                'y': y,
                'width': width,
                'suggestions': suggestions
            }
            
            # Set target window for overlay
            window_info = get_active_window_info()
            if window_info:
                self.overlay.target_hwnd = window_info['hwnd']
            
            # Draw underline
            color = 'orange' if suggestions else 'red'
            self.overlay.draw_wavy_underline(word_id, x, y, width, color, suggestions)
            
            self.caret_word_id = word_id
            
            print(f"📍 Added underline for '{word}' at ({x}, {y})")
        except Exception as e:
            print(f"⚠️ Error adding underline: {e}")
    
    def remove_underline(self, word_id):
        """Remove underline for a corrected word"""
        if word_id in self.misspelled_words:
            self.overlay.remove_underline(word_id)
            del self.misspelled_words[word_id]
    
    def show_suggestions(self, word, suggestions):
        """Show suggestion popup near caret"""
        if not suggestions:
            return
        
        try:
            # Get caret position
            x, y, _, _ = get_caret_position()
            
            # Show popup
            self.popup.show(suggestions, word, x, y)
            
            print(f"💡 Showing {len(suggestions)} suggestions for '{word}'")
        except Exception as e:
            print(f"⚠️ Error showing suggestions: {e}")
    
    def replace_word(self, chosen_word, original_word):
        """Replace misspelled word with chosen suggestion"""
        try:
            print(f"✏️ Replacing '{original_word}' with '{chosen_word}'")
            
            self.replacing = True
            self.popup.hide()
            time.sleep(0.05)
            
            # Select the word using Ctrl+Shift+Left
            self.keyboard_controller.press(Key.ctrl)
            self.keyboard_controller.press(Key.shift)
            self.keyboard_controller.press(Key.left)
            self.keyboard_controller.release(Key.left)
            self.keyboard_controller.release(Key.shift)
            self.keyboard_controller.release(Key.ctrl)
            time.sleep(0.02)
            
            # Type the chosen word (replaces selection)
            self.keyboard_controller.type(chosen_word)
            time.sleep(0.02)
            
            # Remove underline
            if self.caret_word_id:
                self.remove_underline(self.caret_word_id)
                self.caret_word_id = None
            
            # Clear buffer
            self.current_word_chars = []
            self.cursor_index = 0
            
            time.sleep(0.1)
            self.replacing = False
            
            print(f"✅ Replacement complete")
        except Exception as e:
            print(f"⚠️ Replacement failed: {e}")
            self.replacing = False
    
    def process_word_completion(self, word):
        """Process a completed word (after delimiter is typed)"""
        if self.replacing or not self.enabled:
            return
        
        if not word or len(word) < 2:
            return
        
        if not any(self.is_kannada_char(c) for c in word):
            return
        
        print(f"\n🔍 Checking word: '{word}'")
        self.words_checked += 1
        
        # Check spelling
        is_correct, suggestions = self.check_word_spelling(word)
        
        if is_correct:
            print(f"✅ Correct: '{word}'")
            # Remove underline if exists
            if self.caret_word_id:
                self.remove_underline(self.caret_word_id)
                self.caret_word_id = None
            self.popup.hide()
        else:
            print(f"❌ Incorrect: '{word}' - Found {len(suggestions)} suggestions")
            self.errors_found += 1
            
            # Add underline
            self.add_underline(word, suggestions)
            
            # Show suggestions popup
            if suggestions:
                self.show_suggestions(word, suggestions)
    
    def process_pasted_text(self, text):
        """Process pasted text - check all Kannada words"""
        if not text or self.replacing or not self.enabled:
            return
        
        print(f"\n📋 Processing pasted text: {len(text)} characters")
        
        # Extract Kannada words
        import re
        words = re.findall(r'[^\s\n\r\t.,!?;:]+', text)
        kannada_words = [w for w in words if any(self.is_kannada_char(c) for c in w)]
        
        print(f"📝 Found {len(kannada_words)} Kannada words")
        
        # Check each word (only show popup for last word)
        for i, word in enumerate(kannada_words):
            if len(word) < 2:
                continue
            
            is_correct, suggestions = self.check_word_spelling(word)
            
            if not is_correct:
                print(f"❌ Word {i+1}/{len(kannada_words)}: '{word}' - {len(suggestions)} suggestions")
                self.errors_found += 1
                
                # Only show popup for last incorrect word
                if i == len(kannada_words) - 1 and suggestions:
                    # Add underline
                    self.add_underline(word, suggestions)
                    # Show popup
                    self.show_suggestions(word, suggestions)
            else:
                print(f"✅ Word {i+1}/{len(kannada_words)}: '{word}'")
            
            self.words_checked += 1
    
    def on_key_press(self, key):
        """Handle key press events"""
        try:
            # Skip if replacing
            if self.replacing:
                return
            
            # Detect Ctrl+V paste
            if key == Key.ctrl_l or key == Key.ctrl_r:
                self.clipboard_check_active = True
            elif self.clipboard_check_active:
                is_v_key = False
                if hasattr(key, 'char') and key.char and key.char.lower() == 'v':
                    is_v_key = True
                elif hasattr(key, 'vk') and key.vk == 86:
                    is_v_key = True
                
                if is_v_key:
                    print("📋 Paste detected")
                    # Schedule clipboard check after paste completes
                    threading.Timer(0.3, self._check_pasted_text).start()
                
                self.clipboard_check_active = False
            
            # Handle Esc key
            if key == Key.esc:
                current_time = time.time()
                
                # Double Esc to stop service
                if current_time - self.last_esc_time < 1.0:
                    print("\n🛑 Esc pressed twice - Stopping service...")
                    self.running = False
                    try:
                        self.popup.hide()
                        self.overlay.hide()
                    except Exception:
                        pass
                    return
                
                self.last_esc_time = current_time
                
                # Hide popup if visible
                if self.popup.visible:
                    self.popup.hide()
                    return
            
            # Navigation in popup
            if self.popup.visible:
                if key == Key.down:
                    self.popup.select_next()
                    return
                elif key == Key.up:
                    self.popup.select_prev()
                    return
                elif key == Key.enter:
                    chosen = self.popup.get_selected()
                    if chosen:
                        self.popup.hide()
                        self.replace_word(chosen, self.popup.current_word)
                    return
            
            # Handle backspace
            if key == Key.backspace:
                if self.cursor_index > 0:
                    self.current_word_chars.pop(self.cursor_index - 1)
                    self.cursor_index -= 1
                else:
                    self.current_word_chars = []
                    self.cursor_index = 0
                
                if self.popup.visible:
                    self.popup.hide()
                return
            
            # Handle arrow keys - reset buffer
            if key in [Key.left, Key.right, Key.up, Key.down, Key.home, Key.end]:
                self.current_word_chars = []
                self.cursor_index = 0
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
                char = '\n'
            elif key == Key.tab:
                char = '\t'
            
            # Process delimiter
            if char and self.is_word_delimiter(char):
                if self.current_word_chars:
                    word = ''.join(self.current_word_chars)
                    self.process_word_completion(word)
                
                # Reset buffer
                self.current_word_chars = []
                self.cursor_index = 0
            elif char:
                # Add character to buffer
                if self.popup.visible:
                    self.popup.hide()
                
                self.current_word_chars.insert(self.cursor_index, char)
                self.cursor_index += 1
                
                # Limit buffer size
                if len(self.current_word_chars) > 50:
                    self.current_word_chars = self.current_word_chars[-50:]
                    self.cursor_index = len(self.current_word_chars)
        
        except Exception as e:
            print(f"⚠️ Key press error: {e}")
    
    def on_key_release(self, key):
        """Handle key release events"""
        if key == Key.ctrl_l or key == Key.ctrl_r:
            self.clipboard_check_active = False
    
    def _check_pasted_text(self):
        """Check clipboard content after paste"""
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    if text and text != self.last_clipboard_content:
                        self.last_clipboard_content = text
                        self.process_pasted_text(text)
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"⚠️ Clipboard check error: {e}")
    
    def toggle_enabled(self):
        """Toggle spell checking on/off"""
        self.enabled = not self.enabled
        status = "ENABLED ✅" if self.enabled else "DISABLED ⛔"
        print(f"\n🔄 Spell checking {status}")
        
        if not self.enabled:
            self.popup.hide()
            self.overlay.clear_all()
    
    def on_popup_close(self):
        """Handle popup close"""
        self.running = False
        print("\n🛑 Service stopping...")
    
    def run(self):
        """Start the service"""
        self.running = True
        
        def on_activate_toggle():
            self.toggle_enabled()
        
        # Setup hotkeys
        from pynput import keyboard as kb
        
        toggle_hotkey = kb.HotKey(
            kb.HotKey.parse('<ctrl>+<shift>+s'),
            on_activate_toggle
        )
        
        def for_canonical(f):
            return lambda k: f(listener.canonical(k))
        
        def on_press(key):
            for_canonical(toggle_hotkey.press)(key)
            if self.running:
                self.on_key_press(key)
        
        def on_release(key):
            for_canonical(toggle_hotkey.release)(key)
            if self.running:
                self.on_key_release(key)
        
        # Start keyboard listener
        listener = kb.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        
        # Periodic check for service status
        def check_running():
            if self.running:
                self.overlay.root.after(100, check_running)
            else:
                listener.stop()
                self.overlay.root.destroy()
                self.popup.root.destroy()
        
        self.overlay.root.after(100, check_running)
        
        # Run Tkinter mainloop
        try:
            self.overlay.root.mainloop()
        except KeyboardInterrupt:
            print("\n\n🛑 Service interrupted")
        except Exception as e:
            print(f"\n⚠️ Service error: {e}")
        finally:
            self.running = False
            if listener.running:
                listener.stop()
            
            # Print statistics
            print("\n" + "="*80)
            print("📊 Session Statistics")
            print("="*80)
            print(f"  Words checked: {self.words_checked}")
            print(f"  Errors found: {self.errors_found}")
            print("="*80)
            print("\n✅ Service stopped successfully\n")


def main():
    """Main entry point"""
    import signal
    
    # Ignore Ctrl+C (use double Esc instead)
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except Exception:
        pass
    
    try:
        print("\n🚀 Starting Real-Time Kannada Spell Checker...")
        print("   Loading NLP models and initializing UI...\n")
        
        service = RealtimeSpellChecker()
        service.run()
    except Exception as e:
        import traceback
        print(f"\n❌ Fatal Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
