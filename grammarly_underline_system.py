#!/usr/bin/env python3
"""
Grammarly-Style Fake Underline System for Kannada Spell Checker
================================================================================

This module creates transparent overlay windows that draw colored underlines
on top of ANY application (Notepad, Word, Browser, etc.) just like Grammarly.

The underlines are NOT real - they are fake overlays positioned above the text.

Features:
- Transparent window overlay that follows target application
- Real-time caret position tracking using Win32 API
- Smooth underline rendering (wavy red lines for errors)
- Automatically syncs when window moves/scrolls
- Click-through transparency for normal text editing
- Works in Notepad, Word, Chrome, VS Code, etc.

Architecture:
    1. Monitor target application window
    2. Track caret position in real-time
    3. Calculate word boundaries and positions
    4. Create transparent overlay window above target
    5. Draw underlines at exact pixel positions
    6. Update overlay when window moves/scrolls

Usage:
    overlay = UnderlineOverlayWindow()
    overlay.add_underline(word_x, word_y, word_width, color="#FF0000")
    overlay.show()
"""

import sys
import time
import threading
import tkinter as tk
from ctypes import wintypes, windll, byref, Structure, c_long, c_ulong, sizeof, c_int
from typing import List, Optional, Tuple, Dict
import win32gui
import win32con
import win32api

# ---------------------------------------------------------------------------
# Win32 API Structures for Caret and Window Tracking
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


class SIZE(Structure):
    """Structure for text measurement"""
    _fields_ = [("cx", c_long), ("cy", c_long)]


# ---------------------------------------------------------------------------
# Caret Position Tracker (Works in Any Application)
# ---------------------------------------------------------------------------

class CaretTracker:
    """
    Tracks the text caret position in real-time across all applications.
    Uses Win32 API to get accurate caret coordinates.
    """
    
    @staticmethod
    def get_caret_position() -> Tuple[int, int, Optional[int]]:
        """
        Get the current caret position in screen coordinates.
        
        Returns:
            Tuple[x, y, hwnd]: Screen coordinates and target window handle
        """
        try:
            # Get foreground window
            hwnd = windll.user32.GetForegroundWindow()
            if not hwnd:
                return (0, 0, None)
            
            # Get thread info for the window
            thread_id = windll.user32.GetWindowThreadProcessId(hwnd, 0)
            gui_info = GUITHREADINFO(cbSize=sizeof(GUITHREADINFO))
            result = windll.user32.GetGUIThreadInfo(thread_id, byref(gui_info))
            
            if not result:
                return (0, 0, hwnd)
            
            # Get caret window
            caret_hwnd = gui_info.hwndCaret
            if not caret_hwnd:
                caret_hwnd = gui_info.hwndFocus
            
            if not caret_hwnd:
                return (0, 0, hwnd)
            
            # Get caret rectangle and convert to screen coordinates
            caret_rect = gui_info.rcCaret
            point = POINT(caret_rect.left, caret_rect.bottom)
            windll.user32.ClientToScreen(caret_hwnd, byref(point))
            
            return (point.x, point.y, hwnd)
        
        except Exception as e:
            print(f"⚠️ Caret tracking error: {e}")
            return (0, 0, None)
    
    @staticmethod
    def get_window_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        """Get window rectangle (left, top, right, bottom)"""
        try:
            if not hwnd or not win32gui.IsWindow(hwnd):
                return None
            return win32gui.GetWindowRect(hwnd)
        except Exception:
            return None
    
    @staticmethod
    def measure_text_width(text: str, hwnd: Optional[int] = None) -> int:
        """
        Measure the pixel width of text in the target application.
        Critical for positioning underlines accurately under Kannada text.
        """
        try:
            if not hwnd:
                hwnd = windll.user32.GetForegroundWindow()
            
            hdc = windll.user32.GetDC(hwnd)
            if not hdc:
                return len(text) * 12  # Fallback estimation
            
            size = SIZE()
            result = windll.gdi32.GetTextExtentPoint32W(hdc, text, len(text), byref(size))
            windll.user32.ReleaseDC(hwnd, hdc)
            
            if result:
                return max(size.cx, len(text) * 8)
            return len(text) * 12
        
        except Exception:
            # Fallback: Kannada characters are typically wider
            return len(text) * 14


# ---------------------------------------------------------------------------
# Transparent Overlay Window (The "Fake" Underline Layer)
# ---------------------------------------------------------------------------

class UnderlineOverlayWindow:
    """
    Transparent window that sits on top of the target application
    and draws fake underlines. This is the core of Grammarly-style underlining.
    
    Key Features:
    - Completely transparent background (click-through)
    - Always on top of target window
    - Draws colored underlines at exact positions
    - Auto-repositions when target window moves
    - Supports wavy underlines for spelling errors
    """
    
    def __init__(self, master_root: Optional[tk.Tk] = None):
        """
        Initialize the overlay window.
        
        Args:
            master_root: Parent Tkinter root (if exists), or create new one
        """
        self.root = master_root if master_root else tk.Tk()
        self.underlines: Dict[str, dict] = {}  # word_id -> {x, y, width, color, hwnd}
        self.target_hwnd: Optional[int] = None
        self.visible = False
        self.lock = threading.Lock()
        self._stop_sync = threading.Event()
        
        # Create transparent overlay window
        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)  # No title bar
        self.window.attributes('-topmost', True)  # Always on top
        self.window.attributes('-alpha', 1.0)  # Fully visible canvas
        
        # Make background transparent (click-through for green areas)
        self._bg_color = "#00FF00"  # Chroma key color
        try:
            self.window.wm_attributes("-transparentcolor", self._bg_color)
        except tk.TclError:
            # Fallback for systems without transparency support
            try:
                self.window.attributes("-alpha", 0.3)
            except tk.TclError:
                pass
        
        # Create canvas for drawing underlines
        self.canvas = tk.Canvas(
            self.window,
            width=1920,  # Full screen width
            height=1080,  # Full screen height
            bg=self._bg_color,
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill='both', expand=True)
        
        # Hide initially
        self.window.withdraw()
        
        print("✅ Grammarly-style underline overlay initialized")
    
    def add_underline(
        self,
        word_id: str,
        word_x: int,
        word_y: int,
        word_width: int,
        color: str = "#FF0000",
        style: str = "wavy",
        hwnd: Optional[int] = None
    ):
        """
        Add a fake underline at the specified position.
        
        Args:
            word_id: Unique identifier for this underline (usually the word itself)
            word_x: X coordinate (screen coordinates)
            word_y: Y coordinate (screen coordinates)
            word_width: Width of the underline in pixels
            color: Underline color (default red for errors)
            style: "wavy" for spelling errors, "straight" for grammar
            hwnd: Target window handle for tracking
        """
        with self.lock:
            self.underlines[word_id] = {
                'x': word_x,
                'y': word_y,
                'width': word_width,
                'color': color,
                'style': style,
                'hwnd': hwnd or self.target_hwnd,
                'canvas_id': None
            }
        
        # Redraw all underlines
        self._redraw_underlines()
    
    def remove_underline(self, word_id: str):
        """Remove a specific underline"""
        with self.lock:
            if word_id in self.underlines:
                # Delete from canvas
                canvas_id = self.underlines[word_id].get('canvas_id')
                if canvas_id:
                    try:
                        self.canvas.delete(canvas_id)
                    except:
                        pass
                del self.underlines[word_id]
        
        print(f"🗑️ Removed underline for: {word_id}")
    
    def clear_all_underlines(self):
        """Clear all underlines from the overlay"""
        with self.lock:
            self.canvas.delete('all')
            self.underlines.clear()
        print("🧹 Cleared all underlines")
    
    def _draw_wavy_underline(self, x: int, y: int, width: int, color: str) -> int:
        """
        Draw a wavy underline (like Grammarly uses for spelling errors).
        
        Returns:
            Canvas item ID
        """
        # Create wavy pattern
        points = []
        amplitude = 2  # Wave height
        wavelength = 4  # Wave frequency
        
        for i in range(0, width, 2):
            offset = amplitude * ((i // wavelength) % 2)
            points.extend([x + i, y + offset])
        
        # Draw wavy line
        if len(points) >= 4:
            return self.canvas.create_line(
                *points,
                fill=color,
                width=2,
                smooth=True,
                tags='underline'
            )
        else:
            # Fallback to straight line for very short words
            return self.canvas.create_line(
                x, y, x + width, y,
                fill=color,
                width=2,
                tags='underline'
            )
    
    def _draw_straight_underline(self, x: int, y: int, width: int, color: str) -> int:
        """Draw a straight underline (for grammar or other issues)"""
        return self.canvas.create_line(
            x, y, x + width, y,
            fill=color,
            width=2,
            tags='underline'
        )
    
    def _redraw_underlines(self):
        """Redraw all underlines on the canvas"""
        try:
            # Get current window position to calculate relative coordinates
            if not self.target_hwnd:
                return
            
            window_rect = CaretTracker.get_window_rect(self.target_hwnd)
            if not window_rect:
                return
            
            win_left, win_top, win_right, win_bottom = window_rect
            
            # Clear canvas
            self.canvas.delete('all')
            
            # Redraw each underline
            with self.lock:
                for word_id, info in list(self.underlines.items()):
                    # Calculate position relative to overlay window
                    rel_x = info['x'] - win_left
                    rel_y = info['y'] - win_top
                    
                    # Draw underline
                    if info['style'] == 'wavy':
                        canvas_id = self._draw_wavy_underline(
                            rel_x, rel_y, info['width'], info['color']
                        )
                    else:
                        canvas_id = self._draw_straight_underline(
                            rel_x, rel_y, info['width'], info['color']
                        )
                    
                    # Store canvas ID for later removal
                    info['canvas_id'] = canvas_id
        
        except Exception as e:
            print(f"⚠️ Error redrawing underlines: {e}")
    
    def show(self, target_hwnd: Optional[int] = None):
        """
        Show the overlay window and start tracking the target application.
        
        Args:
            target_hwnd: Window handle of the target application to overlay
        """
        if target_hwnd:
            self.target_hwnd = target_hwnd
        
        if not self.target_hwnd:
            # Get current foreground window
            self.target_hwnd = windll.user32.GetForegroundWindow()
        
        # Position overlay over target window
        self._reposition_overlay()
        
        # Show window
        self.window.deiconify()
        self.window.lift()
        self.visible = True
        
        # Start synchronization thread
        if not self._stop_sync.is_set():
            threading.Thread(target=self._sync_with_target, daemon=True).start()
        
        print(f"👁️ Overlay visible over window: {self.target_hwnd}")
    
    def hide(self):
        """Hide the overlay window"""
        self.window.withdraw()
        self.visible = False
        print("🙈 Overlay hidden")
    
    def _reposition_overlay(self):
        """Position the overlay window exactly over the target window"""
        try:
            if not self.target_hwnd:
                return
            
            rect = CaretTracker.get_window_rect(self.target_hwnd)
            if not rect:
                return
            
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top
            
            # Position overlay
            self.window.geometry(f"{width}x{height}+{left}+{top}")
            
            # Redraw underlines with new positioning
            self._redraw_underlines()
        
        except Exception as e:
            print(f"⚠️ Error repositioning overlay: {e}")
    
    def _sync_with_target(self):
        """
        Background thread that keeps the overlay synchronized with the target window.
        Continuously monitors window position and updates overlay.
        """
        last_rect = None
        
        while not self._stop_sync.is_set():
            try:
                if not self.visible or not self.target_hwnd:
                    time.sleep(0.1)
                    continue
                
                # Check if target window still exists
                if not win32gui.IsWindow(self.target_hwnd):
                    print("⚠️ Target window closed, hiding overlay")
                    self.hide()
                    break
                
                # Check if target window moved or resized
                rect = CaretTracker.get_window_rect(self.target_hwnd)
                if rect and rect != last_rect:
                    self._reposition_overlay()
                    last_rect = rect
                
                # Check if target window is no longer foreground
                fg_hwnd = windll.user32.GetForegroundWindow()
                if fg_hwnd != self.target_hwnd:
                    # Target lost focus - could hide overlay or keep it visible
                    # For now, keep visible for demonstration
                    pass
                
                time.sleep(0.05)  # Update 20 times per second
            
            except Exception as e:
                print(f"⚠️ Sync error: {e}")
                time.sleep(0.5)
    
    def destroy(self):
        """Clean up and destroy the overlay window"""
        self._stop_sync.set()
        self.clear_all_underlines()
        try:
            self.window.destroy()
        except:
            pass
        print("💥 Overlay destroyed")


# ---------------------------------------------------------------------------
# Word Position Calculator (For Underline Placement)
# ---------------------------------------------------------------------------

class WordPositionCalculator:
    """
    Calculates exact pixel positions for words in the text editor.
    Essential for placing underlines at the correct locations.
    """
    
    @staticmethod
    def calculate_word_position(
        word: str,
        caret_x: int,
        caret_y: int,
        hwnd: Optional[int] = None
    ) -> Tuple[int, int, int]:
        """
        Calculate where to draw the underline for a word.
        Assumes caret is at the END of the word.
        
        Args:
            word: The word to underline
            caret_x: Current caret X position (end of word)
            caret_y: Current caret Y position
            hwnd: Target window handle
        
        Returns:
            Tuple[start_x, start_y, width]: Position and width for underline
        """
        # Measure text width
        width = CaretTracker.measure_text_width(word, hwnd)
        
        # Calculate start position (caret is at end, move back by width)
        start_x = caret_x - width
        start_y = caret_y + 2  # Slightly below text baseline
        
        return (start_x, start_y, width)


# ---------------------------------------------------------------------------
# Demo/Testing Code
# ---------------------------------------------------------------------------

def demo_fake_underline_system():
    """
    Demo showing how the fake underline system works.
    Open Notepad and type some text to see underlines appear.
    """
    print("\n" + "="*70)
    print("🎯 Grammarly-Style Fake Underline Demo")
    print("="*70)
    print("\n📝 Instructions:")
    print("1. Open Notepad (or any text editor)")
    print("2. Start typing")
    print("3. Watch fake underlines appear below words")
    print("4. The underlines are NOT real - they're transparent overlays!")
    print("\n⚠️ Press Ctrl+C to stop\n")
    
    root = tk.Tk()
    root.withdraw()
    
    # Create overlay system
    overlay = UnderlineOverlayWindow(root)
    overlay.show()
    
    # Simulate adding underlines as user types
    # In real usage, this would be triggered by spell checker
    tracker = CaretTracker()
    
    try:
        word_count = 0
        while True:
            # Get current caret position
            x, y, hwnd = tracker.get_caret_position()
            
            if hwnd:
                # Demo: Add a fake underline every 2 seconds
                if word_count % 40 == 0:  # Every 2 seconds at 50ms intervals
                    # Simulate a misspelled word
                    word = f"word{word_count//40}"
                    word_x, word_y, word_width = WordPositionCalculator.calculate_word_position(
                        word, x, y, hwnd
                    )
                    
                    overlay.add_underline(
                        word_id=word,
                        word_x=word_x,
                        word_y=word_y,
                        word_width=80,  # Fixed width for demo
                        color="#FF0000",
                        style="wavy",
                        hwnd=hwnd
                    )
                    print(f"✨ Added underline at ({word_x}, {word_y})")
                
                word_count += 1
            
            root.update()
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n🛑 Demo stopped")
        overlay.destroy()
        root.destroy()


if __name__ == "__main__":
    demo_fake_underline_system()
