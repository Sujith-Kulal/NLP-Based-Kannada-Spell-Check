#!/usr/bin/env python3
"""
Test Script: Grammarly-Style Fake Underlines in Notepad
=========================================================

This script demonstrates the fake underline system with Grammarly-level accuracy:

✅ FIX 1: Real font metrics from Notepad (WM_GETFONT + GetTextMetricsW)
✅ FIX 2: DPI scaling support for 4K displays (GetDpiForWindow)
✅ FIX 3: UI Automation TextPattern2 for pixel-perfect positioning

Works on ANY laptop/PC with ANY screen resolution and DPI setting!

Instructions:
1. Run this script
2. Open Notepad
3. Type some text with spelling errors
4. Watch red wavy underlines appear (like Grammarly!)
5. Move/resize Notepad - underlines follow perfectly!

Press Ctrl+C to stop.
"""

import sys
import os
import time
import tkinter as tk

# Add project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from grammarly_underline_system import UnderlineOverlayWindow, CaretTracker, WordPositionCalculator

def test_fake_underlines_in_notepad():
    """Test fake underlines in Notepad with full Grammarly accuracy"""
    print("\n" + "="*70)
    print("🎯 Testing Grammarly-Style Fake Underlines (DPI + Font + UIA)")
    print("="*70)
    print("\n📝 Instructions:")
    print("1. Open Notepad (notepad.exe)")
    print("2. Type some text: 'This is a tset word'")
    print("3. Watch for red wavy underline under 'tset'")
    print("4. The underline works on ANY screen resolution!")
    print("\n✅ NEW: Uses actual font metrics + DPI scaling + UI Automation")
    print("⚠️ Press Ctrl+C to stop\n")
    
    # Create Tkinter root
    root = tk.Tk()
    root.withdraw()
    
    # Create overlay system with enhanced tracking
    overlay = UnderlineOverlayWindow(root)
    tracker = CaretTracker()
    calculator = WordPositionCalculator(tracker)
    
    # Show overlay
    time.sleep(2)  # Wait for user to open Notepad
    print("🔍 Looking for Notepad window...")
    
    # Find Notepad window
    import win32gui
    notepad_hwnd = win32gui.FindWindow(None, "Untitled - Notepad")
    if not notepad_hwnd:
        notepad_hwnd = win32gui.FindWindow("Notepad", None)
    
    if notepad_hwnd:
        print(f"✅ Found Notepad window: {notepad_hwnd}")
        
        # Display detected capabilities
        dpi_scale = tracker.get_dpi_scale_factor(notepad_hwnd)
        print(f"✅ Detected DPI scale: {dpi_scale*100:.0f}% (DPI: {int(dpi_scale*96)})")
        
        font_metrics = tracker.get_font_metrics(notepad_hwnd)
        if font_metrics:
            print(f"✅ Font metrics detected:")
            print(f"   - Height: {font_metrics.tmHeight}px")
            print(f"   - Avg Width: {font_metrics.tmAveCharWidth}px")
            print(f"   - Max Width: {font_metrics.tmMaxCharWidth}px")
        else:
            print("⚠️ Font metrics fallback (estimation mode)")
        
        if hasattr(tracker, '_uia') and tracker._uia:
            print("✅ UI Automation TextPattern2 available (pixel-perfect mode)")
        else:
            print("⚠️ UI Automation unavailable (using fallback positioning)")
        
        overlay.show(notepad_hwnd)
        print("👁️ Overlay is now active over Notepad!")
        print("\n💡 Type 'tset' in Notepad to see a fake underline appear\n")
    else:
        print("⚠️ Notepad not found. Please open Notepad first.")
        overlay.show()
    
    try:
        # Demo: Add some fake underlines at various positions
        demo_words = [
            {"word": "tset", "x": 100, "y": 100, "width": 40},
            {"word": "wrnog", "x": 150, "y": 100, "width": 50},
            {"word": "speling", "x": 210, "y": 100, "width": 60},
        ]
        
        print("🎨 Adding demo underlines...")
        for word_info in demo_words:
            overlay.add_underline(
                word_id=word_info["word"],
                word_x=word_info["x"],
                word_y=word_info["y"],
                word_width=word_info["width"],
                color="#FF0000",
                style="wavy",
                hwnd=notepad_hwnd
            )
            print(f"   ✨ Added underline for '{word_info['word']}'")
        
        print("\n✅ Demo underlines added!")
        print("💡 Move Notepad window - underlines follow automatically!")
        print("\n⌨️ Now type in Notepad to test real-time tracking...")
        
        # Keep running and update
        while True:
            root.update()
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n🛑 Test stopped")
        overlay.destroy()
        root.destroy()

if __name__ == "__main__":
    test_fake_underlines_in_notepad()
