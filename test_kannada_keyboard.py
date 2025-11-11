#!/usr/bin/env python3
"""
Test Kannada Keyboard Input
This script helps diagnose if Kannada characters are being captured correctly
"""

from pynput import keyboard

def is_kannada_char(char):
    """Check if character is Kannada Unicode"""
    if not char:
        return False
    return '\u0C80' <= char <= '\u0CFF'

def on_press(key):
    """Display what character was captured"""
    try:
        char = None
        if hasattr(key, 'char'):
            char = key.char
        
        if char:
            is_kan = is_kannada_char(char)
            unicode_val = f"U+{ord(char):04X}" if char else "N/A"
            print(f"Captured: '{char}' | Unicode: {unicode_val} | Kannada: {'✅' if is_kan else '❌'}")
        elif key == keyboard.Key.esc:
            print("\n🛑 Stopping test...")
            return False
    except Exception as e:
        print(f"Error: {e}")

print("="*70)
print("🧪 Kannada Keyboard Test")
print("="*70)
print("\nInstructions:")
print("1. Make sure this window is in focus")
print("2. Switch to Kannada keyboard (Win+Space)")
print("3. Type some Kannada characters")
print("4. Check if they show as 'Kannada: ✅'")
print("5. Press ESC to stop\n")
print("Starting capture...\n")

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()

print("✅ Test complete!")
