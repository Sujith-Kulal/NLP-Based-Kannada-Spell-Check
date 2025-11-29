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
from ctypes import wintypes, windll, byref, Structure, c_long, c_ulong, sizeof, c_int, POINTER, c_void_p
from typing import List, Optional, Tuple, Dict
import win32gui
import win32con
import win32api

# UI Automation for pixel-perfect text positioning (like Grammarly)
try:
    from comtypes import client
    from comtypes.automation import VARIANT
    import comtypes.gen.UIAutomationClient as UIA
    UI_AUTOMATION_AVAILABLE = True
except ImportError:
    UI_AUTOMATION_AVAILABLE = False
    print("⚠️ UI Automation not available. Install comtypes: pip install comtypes")

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


class TEXTMETRICW(Structure):
    """Structure for font metrics"""
    _fields_ = [
        ("tmHeight", c_long),
        ("tmAscent", c_long),
        ("tmDescent", c_long),
        ("tmInternalLeading", c_long),
        ("tmExternalLeading", c_long),
        ("tmAveCharWidth", c_long),
        ("tmMaxCharWidth", c_long),
        ("tmWeight", c_long),
        ("tmOverhang", c_long),
        ("tmDigitizedAspectX", c_long),
        ("tmDigitizedAspectY", c_long),
        ("tmFirstChar", wintypes.WCHAR),
        ("tmLastChar", wintypes.WCHAR),
        ("tmDefaultChar", wintypes.WCHAR),
        ("tmBreakChar", wintypes.WCHAR),
        ("tmItalic", wintypes.BYTE),
        ("tmUnderlined", wintypes.BYTE),
        ("tmStruckOut", wintypes.BYTE),
        ("tmPitchAndFamily", wintypes.BYTE),
        ("tmCharSet", wintypes.BYTE)
    ]


# ---------------------------------------------------------------------------
# Caret Position Tracker (Works in Any Application)
# ---------------------------------------------------------------------------

class CaretTracker:
    """
    Tracks the text caret position in real-time across all applications.
    Uses Win32 API + UI Automation for pixel-perfect positioning like Grammarly.
    
    ✅ FIX 1: Reads actual font metrics from target application
    ✅ FIX 2: Handles Windows DPI scaling correctly
    ✅ FIX 3: Uses UI Automation TextPattern2 for exact bounding boxes
    """
    
    def __init__(self):
        self._font_cache = {}  # hwnd -> font metrics
        self._dpi_cache = {}   # hwnd -> DPI scale factor
        self._uia = None
        
        # Initialize UI Automation (like Grammarly uses)
        if UI_AUTOMATION_AVAILABLE:
            try:
                self._uia = client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=UIA.IUIAutomation)
                print("✅ UI Automation initialized (Grammarly-style positioning enabled)")
            except Exception as e:
                print(f"⚠️ UI Automation init failed: {e}")
                self._uia = None
    
    def get_caret_position(self) -> Tuple[int, int, Optional[int]]:
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
            
            # ✅ FIX 2: Apply DPI scaling
            dpi_scale = self.get_dpi_scale_factor(hwnd)
            point.x = int(point.x * dpi_scale)
            point.y = int(point.y * dpi_scale)
            
            return (point.x, point.y, hwnd)
        
        except Exception as e:
            print(f"⚠️ Caret tracking error: {e}")
            return (0, 0, None)
    
    def get_window_rect(self, hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        """Get window rectangle (left, top, right, bottom) with DPI correction"""
        try:
            if not hwnd or not win32gui.IsWindow(hwnd):
                return None
            
            rect = win32gui.GetWindowRect(hwnd)
            
            # ✅ FIX 2: Apply DPI scaling to window coordinates
            dpi_scale = self.get_dpi_scale_factor(hwnd)
            if dpi_scale != 1.0:
                left, top, right, bottom = rect
                rect = (
                    int(left * dpi_scale),
                    int(top * dpi_scale),
                    int(right * dpi_scale),
                    int(bottom * dpi_scale)
                )
            
            return rect
        except Exception:
            return None
    
    def get_dpi_scale_factor(self, hwnd: int) -> float:
        """
        ✅ FIX 2: Get DPI scaling factor for the window.
        Critical for 4K displays and Windows scaling (125%, 150%, etc.)
        """
        if hwnd in self._dpi_cache:
            return self._dpi_cache[hwnd]
        
        try:
            # Get DPI for the window (Windows 10 1607+)
            dpi = windll.user32.GetDpiForWindow(hwnd)
            if dpi:
                # 96 DPI = 100% scaling (baseline)
                scale = dpi / 96.0
                self._dpi_cache[hwnd] = scale
                return scale
        except Exception:
            pass
        
        # Fallback: System DPI
        try:
            hdc = windll.user32.GetDC(0)
            dpi = windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            windll.user32.ReleaseDC(0, hdc)
            scale = dpi / 96.0
            self._dpi_cache[hwnd] = scale
            return scale
        except Exception:
            pass
        
        # Default: No scaling
        self._dpi_cache[hwnd] = 1.0
        return 1.0
    
    def get_font_metrics(self, hwnd: int) -> Optional[TEXTMETRICW]:
        """
        ✅ FIX 1: Read actual font metrics from the target application.
        Uses WM_GETFONT + GetTextMetricsW for accurate character dimensions.
        """
        if hwnd in self._font_cache:
            return self._font_cache[hwnd]
        
        try:
            # Get the font handle used by the window
            WM_GETFONT = 0x0031
            hfont = win32api.SendMessage(hwnd, WM_GETFONT, 0, 0)
            
            if hfont:
                # Get device context and select font
                hdc = windll.user32.GetDC(hwnd)
                old_font = windll.gdi32.SelectObject(hdc, hfont)
                
                # Get text metrics
                tm = TEXTMETRICW()
                result = windll.gdi32.GetTextMetricsW(hdc, byref(tm))
                
                # Restore and cleanup
                windll.gdi32.SelectObject(hdc, old_font)
                windll.user32.ReleaseDC(hwnd, hdc)
                
                if result:
                    self._font_cache[hwnd] = tm
                    return tm
        
        except Exception as e:
            print(f"⚠️ Font metrics error: {e}")
        
        return None
    
    def measure_text_width(self, text: str, hwnd: Optional[int] = None) -> int:
        """
        ✅ FIX 1: Measure the pixel width of text using ACTUAL font from target app.
        This replaces guessing with exact measurement.
        """
        try:
            if not hwnd:
                hwnd = windll.user32.GetForegroundWindow()
            
            # Get actual font metrics
            font_metrics = self.get_font_metrics(hwnd)
            
            # Get DPI scale factor
            dpi_scale = self.get_dpi_scale_factor(hwnd)
            
            # Get device context
            WM_GETFONT = 0x0031
            hfont = win32api.SendMessage(hwnd, WM_GETFONT, 0, 0)
            hdc = windll.user32.GetDC(hwnd)
            
            if hfont:
                old_font = windll.gdi32.SelectObject(hdc, hfont)
            
            # Measure text width with actual font
            size = SIZE()
            result = windll.gdi32.GetTextExtentPoint32W(hdc, text, len(text), byref(size))
            
            if hfont:
                windll.gdi32.SelectObject(hdc, old_font)
            windll.user32.ReleaseDC(hwnd, hdc)
            
            if result:
                # Apply DPI scaling
                width = int(size.cx * dpi_scale)
                return max(width, len(text) * 8)
            
            # Fallback: Use font metrics average char width
            if font_metrics:
                width = int(len(text) * font_metrics.tmAveCharWidth * dpi_scale)
                return width
            
            return len(text) * 12
        
        except Exception as e:
            print(f"⚠️ Text measurement error: {e}")
            # Fallback: Kannada characters are typically wider
            return len(text) * 14
    
    def get_word_bounding_box_uia(self, hwnd: int, word: str) -> Optional[Tuple[int, int, int, int]]:
        """
        ✅ FIX 3: Use UI Automation TextPattern2 to get pixel-perfect word bounding box.
        This is EXACTLY how Grammarly works - it uses UI Automation API.
        
        Returns:
            Tuple[left, top, right, bottom]: Screen coordinates of word bounding box
        """
        if not self._uia or not UI_AUTOMATION_AVAILABLE:
            return None
        
        try:
            # Get UI Automation element for the window
            element = self._uia.ElementFromHandle(hwnd)
            if not element:
                return None
            
            # Get TextPattern2 (supports GetBoundingRectangles)
            text_pattern = element.GetCurrentPattern(UIA.UIA_TextPattern2Id)
            if not text_pattern:
                # Fallback to TextPattern
                text_pattern = element.GetCurrentPattern(UIA.UIA_TextPatternId)
            
            if not text_pattern:
                return None
            
            # Get visible text range
            visible_range = text_pattern.GetVisibleRanges()
            if not visible_range or visible_range.Length == 0:
                return None
            
            # Search for the word in the text
            text_range = visible_range.GetElement(0)
            found_range = text_range.FindText(word, False, False)
            
            if not found_range:
                return None
            
            # ✅ THIS IS THE KEY: GetBoundingRectangles() gives pixel-perfect coordinates
            bounding_rects = found_range.GetBoundingRectangles()
            
            if bounding_rects and len(bounding_rects) >= 4:
                # Extract first bounding rectangle
                left = int(bounding_rects[0])
                top = int(bounding_rects[1])
                width = int(bounding_rects[2])
                height = int(bounding_rects[3])
                
                return (left, top, left + width, top + height)
        
        except Exception as e:
            print(f"⚠️ UI Automation error: {e}")
        
        return None

    def get_text_via_ui_automation(self, hwnd: Optional[int] = None) -> Optional[str]:
        """
        Get full visible text from a target window without simulating keystrokes.
        Uses UI Automation TextPattern so we never have to type Ctrl+A / Ctrl+C.
        """
        if not self._uia or not UI_AUTOMATION_AVAILABLE:
            return None
        
        try:
            if not hwnd:
                hwnd = windll.user32.GetForegroundWindow()
            if not hwnd:
                return None
            
            element = self._uia.ElementFromHandle(hwnd)
            if not element:
                return None
            
            text_pattern = None
            for pattern_id in (UIA.UIA_TextPattern2Id, UIA.UIA_TextPatternId):
                try:
                    text_pattern = element.GetCurrentPattern(pattern_id)
                except Exception:
                    text_pattern = None
                if text_pattern:
                    break
            
            if not text_pattern:
                return None
            
            text_range = None
            try:
                text_range = text_pattern.DocumentRange
            except Exception:
                text_range = None
            
            if not text_range:
                try:
                    visible_ranges = text_pattern.GetVisibleRanges()
                    if visible_ranges and visible_ranges.Length > 0:
                        text_range = visible_ranges.GetElement(0)
                except Exception:
                    text_range = None
            
            if not text_range:
                return None
            
            text = text_range.GetText(-1)
            if text is not None:
                return text
        
        except Exception as e:
            print(f"⚠️ UI Automation text fetch error: {e}")
        
        return None


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
        self._sync_thread: Optional[threading.Thread] = None
        self._ui_thread_id = threading.get_ident()
        self._pending_redraw = False
        
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

    def _run_on_ui_thread(self, func, *args, **kwargs):
        """Execute Tk work on the UI thread even when called from worker threads."""
        def invoke():
            try:
                func(*args, **kwargs)
            except Exception as exc:
                print(f"⚠️ Overlay UI task failed: {exc}")

        if threading.get_ident() == self._ui_thread_id:
            invoke()
        else:
            try:
                self.root.after(0, invoke)
            except Exception as dispatch_error:
                print(f"⚠️ Unable to marshal overlay call: {dispatch_error}")

    def _schedule_redraw(self):
        """Coalesce redraw requests so canvas ops stay on the Tk thread."""
        if self._pending_redraw:
            return

        def do_redraw():
            self._pending_redraw = False
            self._redraw_underlines()

        self._pending_redraw = True
        self._run_on_ui_thread(do_redraw)
    
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
        
        # Redraw all underlines from the Tk thread
        self._schedule_redraw()
    
    def remove_underline(self, word_id: str):
        """Remove a specific underline"""
        with self.lock:
            if word_id in self.underlines:
                del self.underlines[word_id]
        
        print(f"🗑️ Removed underline for: {word_id}")
        self._schedule_redraw()
    
    def clear_all_underlines(self):
        """Clear all underlines from the overlay"""
        with self.lock:
            self.underlines.clear()
        print("🧹 Cleared all underlines")
        self._run_on_ui_thread(lambda: self.canvas.delete('all'))
    
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
        if threading.get_ident() != self._ui_thread_id:
            self._run_on_ui_thread(self._redraw_underlines)
            return

        try:
            if not self.target_hwnd:
                return
            
            if not hasattr(self, 'caret_tracker'):
                self.caret_tracker = CaretTracker()
            
            window_rect = self.caret_tracker.get_window_rect(self.target_hwnd)
            if not window_rect:
                return
            
            win_left, win_top, win_right, win_bottom = window_rect
            
            try:
                self.canvas.delete('all')
            except Exception as canvas_error:
                print(f"⚠️ Canvas clear failed: {canvas_error}")
                return
            
            with self.lock:
                for word_id, info in list(self.underlines.items()):
                    rel_x = info['x'] - win_left
                    rel_y = info['y'] - win_top
                    
                    if info['style'] == 'wavy':
                        canvas_id = self._draw_wavy_underline(
                            rel_x, rel_y, info['width'], info['color']
                        )
                    else:
                        canvas_id = self._draw_straight_underline(
                            rel_x, rel_y, info['width'], info['color']
                        )
                    
                    info['canvas_id'] = canvas_id
        
        except Exception as e:
            print(f"⚠️ Error redrawing underlines: {e}")
    
    def show(self, target_hwnd: Optional[int] = None):
        """Show the overlay window and start tracking the target application."""

        def _do_show():
            if target_hwnd:
                self.target_hwnd = target_hwnd

            if not self.target_hwnd:
                self.target_hwnd = windll.user32.GetForegroundWindow()

            self._reposition_overlay()

            self.window.deiconify()
            self.window.lift()
            self.visible = True

            if not self._sync_thread or not self._sync_thread.is_alive():
                self._stop_sync.clear()
                self._sync_thread = threading.Thread(
                    target=self._sync_with_target,
                    name="OverlaySyncThread",
                    daemon=True,
                )
                self._sync_thread.start()

            print(f"👁️ Overlay visible over window: {self.target_hwnd}")

        self._run_on_ui_thread(_do_show)
    
    def hide(self):
        """Hide the overlay window"""
        def _do_hide():
            self.window.withdraw()
            self.visible = False
            print("🙈 Overlay hidden")

        self._run_on_ui_thread(_do_hide)
    
    def _reposition_overlay(self, rect: Optional[Tuple[int, int, int, int]] = None):
        """Position the overlay window exactly over the target window with DPI awareness"""
        if threading.get_ident() != self._ui_thread_id:
            self._run_on_ui_thread(lambda: self._reposition_overlay(rect))
            return

        try:
            if not self.target_hwnd:
                return
            
            if not hasattr(self, 'caret_tracker'):
                self.caret_tracker = CaretTracker()
            
            target_rect = rect or self.caret_tracker.get_window_rect(self.target_hwnd)
            if not target_rect:
                return
            
            left, top, right, bottom = target_rect
            width = right - left
            height = bottom - top
            
            if width <= 0 or height <= 0:
                return
            
            self.window.geometry(f"{width}x{height}+{left}+{top}")
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
                    self._run_on_ui_thread(self.hide)
                    break
                
                # Check if target window moved or resized (DPI-aware)
                if not hasattr(self, 'caret_tracker'):
                    self.caret_tracker = CaretTracker()
                
                rect = self.caret_tracker.get_window_rect(self.target_hwnd)
                if rect and rect != last_rect:
                    self._run_on_ui_thread(lambda r=rect: self._reposition_overlay(r))
                    last_rect = rect
                
                time.sleep(0.05)  # Update 20 times per second
            
            except Exception as e:
                print(f"❌ Overlay sync error (ignored): {e}")
                time.sleep(0.1)
                continue
    
    def destroy(self):
        """Clean up and destroy the overlay window"""
        self._stop_sync.set()
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=0.5)
        self.clear_all_underlines()

        def _do_destroy():
            try:
                self.window.destroy()
            except Exception as exc:
                print(f"⚠️ Error destroying overlay window: {exc}")

        self._run_on_ui_thread(_do_destroy)
        print("💥 Overlay destroyed")


# ---------------------------------------------------------------------------
# Word Position Calculator (For Underline Placement)
# ---------------------------------------------------------------------------

class WordPositionCalculator:
    """
    Calculates exact pixel positions for words in the text editor.
    Essential for placing underlines at the correct locations.
    
    Now uses UI Automation + font metrics + DPI scaling for 100% accuracy.
    """
    
    def __init__(self, caret_tracker: CaretTracker):
        self.tracker = caret_tracker
    
    def calculate_word_position(
        self,
        word: str,
        caret_x: int,
        caret_y: int,
        hwnd: Optional[int] = None
    ) -> Tuple[int, int, int]:
        """
        Calculate where to draw the underline for a word with pixel-perfect accuracy.
        
        ✅ FIX 3: Try UI Automation first (like Grammarly)
        ✅ FIX 1: Use actual font metrics if UIA fails
        ✅ FIX 2: Apply DPI scaling to all coordinates
        
        Args:
            word: The word to underline
            caret_x: Current caret X position (end of word)
            caret_y: Current caret Y position
            hwnd: Target window handle
        
        Returns:
            Tuple[start_x, start_y, width]: Position and width for underline
        """
        if not hwnd:
            hwnd = windll.user32.GetForegroundWindow()
        
        # ✅ FIX 3: Try UI Automation first (most accurate)
        bbox = self.tracker.get_word_bounding_box_uia(hwnd, word)
        if bbox:
            left, top, right, bottom = bbox
            width = right - left
            # Position underline at bottom of bounding box
            return (left, bottom + 2, width)
        
        # ✅ FIX 1: Fallback to font metrics measurement
        width = self.tracker.measure_text_width(word, hwnd)
        
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
    calculator = WordPositionCalculator(tracker)
    
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
                    word_x, word_y, word_width = calculator.calculate_word_position(
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
