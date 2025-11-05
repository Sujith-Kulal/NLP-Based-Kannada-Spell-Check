#!/usr/bin/env python3
"""
Kannada Smart Keyboard Service (Phase 2 - Background Auto-Correct Prototype)
==============================================================================

This service monitors keyboard input system-wide and auto-corrects Kannada text
in real-time using your existing NLP spell-checker.

Features:
- Monitors keyboard input using Windows hooks
- Detects word boundaries (space, punctuation)
- Auto-corrects misspelled Kannada words
- Works in ANY application (Notepad, Word, Browser, etc.)

Requirements:
    pip install pywin32 pynput

Usage:
    python smart_keyboard_service.py

Press Ctrl+Shift+K to toggle auto-correct ON/OFF
Press Ctrl+C to exit
"""

import sys
import os
import time
import threading
from collections import deque
import ctypes
from ctypes import wintypes

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import spell checker
from enhanced_spell_checker import EnhancedSpellChecker
from kannada_wx_converter import is_kannada_text

# Windows keyboard hooks
try:
    import win32api
    import win32con
    import win32gui
    import win32clipboard
    from pynput import keyboard
    from pynput.keyboard import Key, Controller
except ImportError:
    print("❌ Error: Required packages not installed")
    print("Install: pip install pywin32 pynput")
    sys.exit(1)


class SmartKeyboardService:
    """
    Background service that monitors keyboard input and auto-corrects Kannada words
    """
    
    def __init__(self):
        print("\n" + "="*70)
        print("🎯 Kannada Smart Keyboard Service - Phase 2 Prototype")
        print("="*70)
        
        self.spell_checker = EnhancedSpellChecker()
        self.keyboard_controller = Controller()
        
        # Current word buffer
        self.current_word = []
        self.enabled = True
        self.last_correction_time = 0
        
        # Statistics
        self.corrections_made = 0
        self.words_checked = 0
        
        print("\n✅ Smart Keyboard Service initialized!")
        print("\n📝 Controls:")
        print("   Ctrl+Shift+K : Toggle auto-correct ON/OFF")
        print("   Ctrl+C       : Exit service")
        print("\n🚀 Service is now running...")
        print("   Type Kannada text in any application to see auto-correction!")
        print("="*70 + "\n")
    
    def is_word_delimiter(self, char):
        """Check if character is a word boundary"""
        if not char:
            return True
        return char in [' ', '\n', '\r', '\t', '.', ',', '!', '?', ';', ':', '-', '(', ')', '[', ']', '{', '}']
    
    def is_kannada_char(self, char):
        """Check if character is Kannada"""
        if not char:
            return False
        return '\u0C80' <= char <= '\u0CFF'
    
    def get_auto_correction(self, word):
        """
        Get auto-correction suggestion for a word
        Returns: (should_correct, corrected_word)
        """
        if not word or len(word) < 2:
            return False, word
        
        # Only check Kannada words
        if not any(self.is_kannada_char(c) for c in word):
            return False, word
        
        # Track that original was Kannada
        was_kannada = is_kannada_text(word)
        
        # Check word using spell checker
        try:
            errors = self.spell_checker.check_text(word)
            
            if errors and len(errors) > 0:
                error = errors[0]
                suggestions = error.get('suggestions', [])
                
                if suggestions and len(suggestions) > 0:
                    # Get first (best) suggestion (in WX format)
                    suggestion = suggestions[0]
                    
                    # Convert WX suggestion back to Kannada if original was Kannada
                    if was_kannada:
                        from kannada_wx_converter import wx_to_kannada
                        suggestion = wx_to_kannada(suggestion)
                    
                    return True, suggestion
        except Exception as e:
            pass
        
        return False, word
    
    def perform_correction(self, original, corrected, delimiter=' '):
        """
        Replace the current word with corrected version
        Uses backspace + type simulation
        """
        try:
            # Wait a tiny bit for the delimiter to be processed
            time.sleep(0.05)

            # Remove the delimiter the user just typed (space, newline, punctuation)
            if delimiter:
                self.keyboard_controller.press(Key.backspace)
                self.keyboard_controller.release(Key.backspace)
                time.sleep(0.01)

            # Select the previous word using Ctrl+Shift+Left so composed glyphs are captured
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

            # Type corrected word
            self.keyboard_controller.type(corrected)
            time.sleep(0.01)

            # Re-insert the original delimiter
            if delimiter == ' ':
                self.keyboard_controller.press(Key.space)
                self.keyboard_controller.release(Key.space)
            elif delimiter == '\n':
                self.keyboard_controller.press(Key.enter)
                self.keyboard_controller.release(Key.enter)
            else:
                self.keyboard_controller.type(delimiter)
            
            self.corrections_made += 1
            
            print(f"✅ Auto-corrected: '{original}' → '{corrected}'")
            
        except Exception as e:
            print(f"⚠️  Correction failed: {e}")
    
    def on_press(self, key):
        """Handle key press events"""
        try:
            # Get character
            char = None
            if hasattr(key, 'char'):
                char = key.char
            elif key == Key.space:
                char = ' '
            elif key == Key.enter:
                char = '\n'
            elif key == Key.tab:
                char = '\t'
            
            # Check if it's a delimiter (space, enter, punctuation)
            if char and self.is_word_delimiter(char):
                # Word boundary reached - check if we should correct
                if self.current_word and self.enabled:
                    word = ''.join(self.current_word)
                    self.words_checked += 1
                    
                    # Get correction suggestion
                    should_correct, corrected = self.get_auto_correction(word)
                    
                    if should_correct and corrected != word:
                        # Perform auto-correction
                        self.perform_correction(word, corrected, delimiter=char)
                
                # Reset word buffer
                self.current_word = []
            
            # Add character to current word
            elif char:
                self.current_word.append(char)
                
                # Limit buffer size
                if len(self.current_word) > 50:
                    self.current_word = self.current_word[-50:]
        
        except Exception as e:
            pass
    
    def on_release(self, key):
        """Handle key release events"""
        pass
    
    def toggle_enabled(self):
        """Toggle auto-correct on/off"""
        self.enabled = not self.enabled
        status = "ENABLED ✅" if self.enabled else "DISABLED ⛔"
        print(f"\n🔄 Auto-correct {status}")
        
        # Show Windows notification
        try:
            from plyer import notification
            notification.notify(
                title="Kannada Smart Keyboard",
                message=f"Auto-correct {status}",
                timeout=2
            )
        except:
            pass
    
    def run(self):
        """Start the keyboard monitoring service"""
        # Create hotkey listener for Ctrl+Shift+K
        def on_activate_toggle():
            self.toggle_enabled()
        
        from pynput import keyboard as kb
        
        # Setup global hotkey
        hotkey = kb.HotKey(
            kb.HotKey.parse('<ctrl>+<shift>+k'),
            on_activate_toggle
        )
        
        # Create keyboard listener
        def for_canonical(f):
            return lambda k: f(listener.canonical(k))
        
        listener = kb.Listener(
            on_press=lambda k: (for_canonical(hotkey.press)(k), self.on_press(k)),
            on_release=lambda k: (for_canonical(hotkey.release)(k), self.on_release(k))
        )
        
        try:
            listener.start()
            
            # Keep running and show statistics
            while True:
                time.sleep(10)
                if self.words_checked > 0:
                    print(f"📊 Stats: {self.words_checked} words checked, {self.corrections_made} corrections made")
        
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("STOPPING SERVICE")
            print("="*70)
            print(f"\n📊 Final Statistics:")
            print(f"   Words checked: {self.words_checked}")
            print(f"   Corrections made: {self.corrections_made}")
            print(f"   Correction rate: {(self.corrections_made/max(self.words_checked,1)*100):.1f}%")
            print("\n✅ Service stopped successfully")
            print("="*70 + "\n")
            listener.stop()


def main():
    """Main entry point"""
    try:
        print("\n🎯 Starting Kannada Smart Keyboard Service...")
        print("   This may take a moment while loading NLP models...\n")
        
        service = SmartKeyboardService()
        service.run()
    
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
