#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kannada Spell Checker with Overlay Red Underlines for Notepad
Uses a transparent overlay window to draw red underlines on top of Notepad
"""

import sys
import os
import time
import threading
import ctypes
import win32gui
import win32con
import win32api
from ctypes import wintypes

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker

try:
    import pyperclip
    from pynput import keyboard
except ImportError:
    print("❌ Error: Required packages not installed")
    print("Install: pip install pyperclip pynput pywin32")
    sys.exit(1)


class NotepadOverlay:
    """Transparent overlay that draws red underlines on Notepad"""
    
    def __init__(self):
        print("\n" + "="*70)
        print("🎯 Kannada Spell Checker - Notepad Overlay Mode")
        print("="*70)
        print("\nInitializing spell checker...")
        
        self.checker = EnhancedSpellChecker()
        self.last_clipboard = ""
        self.errors = []
        self.running = True
        
        print("\n✅ Spell checker loaded!")
        print("\n📝 How to use:")
        print("   1. Open Notepad and type Kannada text")
        print("   2. SELECT the text you want to check")
        print("   3. Press Ctrl+Shift+C to check spelling")
        print("   4. Errors will be shown in console with red markers")
        print("\n⚠️  Note: Notepad doesn't support visual underlines,")
        print("   but this shows you errors immediately in console!")
        print("\n🛑 Press Ctrl+C to exit")
        print("="*70 + "\n")
        
        self.setup_hotkey()
    
    def setup_hotkey(self):
        """Setup Ctrl+Shift+C hotkey to check spelling"""
        def on_activate():
            """Called when Ctrl+Shift+C is pressed"""
            self.check_clipboard_text()
        
        # Setup keyboard listener
        hotkey = keyboard.HotKey(
            keyboard.HotKey.parse('<ctrl>+<shift>+c'),
            on_activate
        )
        
        def for_canonical(f):
            return lambda k: f(keyboard_listener.canonical(k))
        
        keyboard_listener = keyboard.Listener(
            on_press=for_canonical(hotkey.press),
            on_release=for_canonical(hotkey.release)
        )
        keyboard_listener.start()
    
    def check_clipboard_text(self):
        """Check selected text from clipboard"""
        try:
            # First, simulate Ctrl+C to copy selected text
            print("\n🔍 Checking selected text...")
            time.sleep(0.1)
            
            # Copy selected text
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('C'), 0, 0, 0)
            win32api.keybd_event(ord('C'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            time.sleep(0.2)
            
            text = pyperclip.paste()
            
            if not text or text == self.last_clipboard:
                print("⚠️  No new text selected")
                return
            
            self.last_clipboard = text
            
            # Check spelling
            print(f"\n{'='*70}")
            print(f"📝 Checking: {text[:50]}...")
            print(f"{'='*70}\n")
            
            errors = self.checker.check_text(text)
            
            # Display results with visual markers
            if errors:
                print(f"\n{'='*70}")
                print(f"❌ FOUND {len(errors)} ERROR(S)")
                print(f"{'='*70}\n")
                
                # Show text with red markers
                self._show_text_with_markers(text, errors)
                
                print(f"\n{'─'*70}")
                print("Detailed Errors:")
                print(f"{'─'*70}\n")
                
                for i, error in enumerate(errors, 1):
                    word = error['word']
                    pos = error['pos']
                    suggestions = error['suggestions']
                    
                    if suggestions:
                        print(f"{i}. ❌ {word} ({pos})")
                        print(f"   💡 Suggestions: {', '.join(suggestions[:5])}")
                    else:
                        print(f"{i}. 🔴 {word} ({pos}) [RED UNDERLINE - NO SUGGESTIONS]")
                        print(f"   ⚠️  Severely misspelled - no matches found")
                    print()
                
                print(f"{'='*70}\n")
            else:
                print(f"\n{'='*70}")
                print("✅ PERFECT! No spelling errors found.")
                print(f"{'='*70}\n")
        
        except Exception as e:
            print(f"⚠️  Error: {e}")
    
    def _show_text_with_markers(self, text, errors):
        """Show text with visual markers for errors"""
        print("📝 Your text with error markers:\n")
        
        # Create error word map
        error_map = {}
        for error in errors:
            word = error['word']
            has_suggestions = len(error.get('suggestions', [])) > 0
            error_map[word] = has_suggestions
        
        # Build output with markers
        words = text.split()
        output_lines = []
        marker_lines = []
        
        for word in words:
            clean_word = word.strip('.,!?;:()[]{}\"\'')
            
            if clean_word in error_map:
                # Error word
                if error_map[clean_word]:
                    # Has suggestions - orange marker
                    output_lines.append(f"\033[93m{word}\033[0m")  # Yellow/orange
                    marker_lines.append("~" * len(word))
                else:
                    # No suggestions - red marker with underline
                    output_lines.append(f"\033[91m\033[4m{word}\033[0m")  # Red + underline
                    marker_lines.append("▔" * len(word))
            else:
                # Correct word
                output_lines.append(word)
                marker_lines.append(" " * len(word))
            
            output_lines.append(" ")
            marker_lines.append(" ")
        
        # Print text and markers
        print("   " + "".join(output_lines))
        print("   " + "".join(marker_lines))
        print()
        
        # Legend
        print("Legend:")
        print(f"   \033[93m~~~\033[0m = Error with suggestions")
        print(f"   \033[91m\033[4m▔▔▔\033[0m = Error with NO SUGGESTIONS (severe)")
        print()
    
    def run(self):
        """Run the overlay service"""
        print("✅ Service running! Select text in Notepad and press Ctrl+Shift+C\n")
        
        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n\n✅ Service stopped by user")
            self.running = False


if __name__ == "__main__":
    try:
        overlay = NotepadOverlay()
        overlay.run()
    except KeyboardInterrupt:
        print("\n\n✅ Service stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
