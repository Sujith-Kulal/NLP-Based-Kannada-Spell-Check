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
        if not self.visible or not self.suggestions:
            return None
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
        
        self.current_word = []
        self.enabled = True
        self.words_checked = 0
        self.last_word = ""  # Store last word for replacement
        self.running = False  # Service running flag
        self.replacing = False  # Flag to prevent re-showing popup during replacement
        self.last_esc_time = 0  # Track last Esc press for double-tap detection
        self.last_clipboard_content = ""  # Track clipboard for paste detection
        self.clipboard_check_active = False  # Flag to enable clipboard monitoring

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
    
    def is_word_delimiter(self, char):
        """Check if character is a word boundary"""
        if not char:
            return True
        return char in [' ', '\n', '\r', '\t', '.', ',', '!', '?', ';', ':']

    def is_kannada_char(self, char):
        """Check if character is Kannada"""
        return char and '\u0C80' <= char <= '\u0CFF'
    
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
                # Check the last word pasted
                last_pasted_word = words[-1]
                self.last_word = last_pasted_word
                print(f"🔍 Checking last pasted word: '{last_pasted_word}'")
                suggestions = self.get_suggestions(last_pasted_word)
                print(f"🔍 Suggestions found: {suggestions}")
                
                if suggestions:
                    print(f"✅ Showing suggestions for pasted word: '{last_pasted_word}'")
                    self.popup.show(suggestions)
                else:
                    print(f"ℹ️ No suggestions for: '{last_pasted_word}'")
                    self.popup.hide()
            else:
                print(f"⚠️ No Kannada words found or service disabled")
        except Exception as e:
            print(f"❌ Error checking pasted text: {e}")
            import traceback
            traceback.print_exc()
    
    def get_suggestions(self, word):
        """Return suggestion list for a word"""
        if not word or len(word) < 2:
            return []
        if not any(self.is_kannada_char(c) for c in word):
            return []
        was_kannada = is_kannada_text(word)
        try:
            errors = self.spell_checker.check_text(word)
            if errors:
                error = errors[0]
                suggestions = error.get('suggestions', [])
                if was_kannada:
                    from kannada_wx_converter import wx_to_kannada
                    suggestions = [wx_to_kannada(s) for s in suggestions]
                return suggestions[:5]
        except Exception:
            pass
        return []
    
    def replace_word(self, chosen_word):
        """Replace the misspelled word with chosen suggestion"""
        try:
            print(f"✅ Replacing with: '{chosen_word}'")
            self.replacing = True  # Set flag to prevent re-triggering
            self.popup.hide()  # Ensure popup is hidden
            time.sleep(0.05)
            
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
            
            # Add space after the word
            self.keyboard_controller.press(Key.space)
            self.keyboard_controller.release(Key.space)
            time.sleep(0.05)
            
            self.replacing = False  # Reset flag after replacement complete
            
        except Exception as e:
            print(f"⚠️ Replacement failed: {e}")
            self.replacing = False

    def on_press(self, key):
        """Handle key press events"""
        try:
            # Skip processing if we're in the middle of replacing
            if self.replacing:
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
            
            # Navigation controls for popup
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
                        self.replace_word(chosen)
                    return

            # Handle backspace - remove last character from buffer
            if key == Key.backspace:
                if self.current_word:
                    self.current_word.pop()
                    # Hide popup when backspacing
                    if self.popup.visible:
                        self.popup.hide()
                return
            
            # Handle delete key - clear the current word buffer
            if key == Key.delete:
                self.current_word = []
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

            if char and self.is_word_delimiter(char):
                # ✅ ALWAYS check and hide popup, even if word is empty
                if self.current_word and self.enabled and not self.replacing:
                    word = ''.join(self.current_word)
                    self.last_word = word  # Store the word for replacement
                    self.words_checked += 1
                    suggestions = self.get_suggestions(word)
                    if suggestions:
                        self.popup.show(suggestions)
                    else:
                        self.popup.hide()
                else:
                    # ✅ Hide popup if no word was typed (multiple spaces, etc.)
                    self.popup.hide()
                self.current_word = []
            elif char:
                # ✅ Hide popup while actively typing a new word
                if self.popup.visible:
                    self.popup.hide()
                self.current_word.append(char)
                if len(self.current_word) > 50:
                    self.current_word = self.current_word[-50:]
        except Exception:
            pass
    
    def on_release(self, key):
        """Handle key release events"""
        # Reset clipboard check flag when Ctrl is released
        if key == Key.ctrl_l or key == Key.ctrl_r:
            self.clipboard_check_active = False
    
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
        
        # Add periodic check to keep UI responsive
        def check_running():
            if self.running:
                self.popup.root.after(100, check_running)
            else:
                listener.stop()
                self.popup.root.destroy()
        
        self.popup.root.after(100, check_running)
        
        try:
            self.popup.root.mainloop()  # keep Tkinter UI active
        except Exception as e:
            print(f"\n⚠️ Service stopped: {e}")
        finally:
            if listener.running:
                listener.stop()
            print("\n✅ Service stopped successfully\n")


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
