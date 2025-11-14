#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify persistent underline behavior

This script demonstrates that the underline:
1. Does NOT disappear after a timeout
2. Stays visible until explicitly hidden
3. Only disappears when word is corrected or replaced
"""

import tkinter as tk
import time
from typing import Optional

print("\n" + "="*70)
print("🧪 Testing Persistent Underline Behavior")
print("="*70 + "\n")

class TestUnderlineMarker:
    """Simple underline marker for testing"""
    
    def __init__(self, master: tk.Tk):
        self.master = master
        self._hide_job: Optional[str] = None
        self.visible = False
        self._bg_color = "#00FF00"
        
        self.window = tk.Toplevel(master)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        try:
            self.window.wm_attributes("-transparentcolor", self._bg_color)
        except tk.TclError:
            self.window.attributes("-alpha", 0.85)
        self.window.withdraw()
        
        self.canvas = tk.Canvas(self.window, height=4, width=100, 
                               bg=self._bg_color, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
    
    def show_persistent(self, x: int, y: int, width: int, color: str):
        """Show underline that persists until manually hidden"""
        self.canvas.config(width=width + 4, height=4)
        self.canvas.delete("underline")
        self.canvas.create_line(2, 2, width + 2, 2, fill=color, width=2, 
                              capstyle=tk.ROUND, tags="underline")
        
        self.window.geometry(f"+{x}+{y}")
        self.window.deiconify()
        self.window.lift()
        self.visible = True
        
        # Cancel any existing hide job
        if self._hide_job is not None:
            self.window.after_cancel(self._hide_job)
            self._hide_job = None
        
        print(f"✅ Persistent underline shown at ({x}, {y}) - NO AUTO-HIDE")
    
    def show_temporary(self, x: int, y: int, width: int, color: str, duration_ms: int):
        """Show underline that auto-hides after duration"""
        self.canvas.config(width=width + 4, height=4)
        self.canvas.delete("underline")
        self.canvas.create_line(2, 2, width + 2, 2, fill=color, width=2, 
                              capstyle=tk.ROUND, tags="underline")
        
        self.window.geometry(f"+{x}+{y}")
        self.window.deiconify()
        self.window.lift()
        self.visible = True
        
        # Set auto-hide timer
        if self._hide_job is not None:
            self.window.after_cancel(self._hide_job)
        self._hide_job = self.window.after(duration_ms, self.hide)
        
        print(f"⏱️ Temporary underline shown - will hide after {duration_ms}ms")
    
    def hide(self):
        """Hide the underline"""
        if self._hide_job is not None:
            self.window.after_cancel(self._hide_job)
            self._hide_job = None
        
        if self.visible:
            self.window.withdraw()
            self.visible = False
            print("❌ Underline hidden")


def run_test():
    """Run the test"""
    root = tk.Tk()
    root.title("Persistent Underline Test")
    root.geometry("600x400+100+100")
    
    marker = TestUnderlineMarker(root)
    
    # Instructions
    label = tk.Label(root, text="Persistent Underline Test", 
                    font=("Arial", 16, "bold"), pady=20)
    label.pack()
    
    info = tk.Label(root, text=
        "This test demonstrates persistent underline behavior:\n\n"
        "1. Click 'Show Persistent' - underline stays forever\n"
        "2. Click 'Show Temporary' - underline disappears after 3 seconds\n"
        "3. Click 'Hide' to manually remove persistent underline\n\n"
        "The persistent underline will NOT auto-hide!",
        font=("Arial", 11), justify=tk.LEFT, pady=10)
    info.pack()
    
    # Timer label
    timer_label = tk.Label(root, text="Time elapsed: 0s", 
                          font=("Arial", 12), fg="blue")
    timer_label.pack(pady=10)
    
    start_time = [time.time()]
    
    def update_timer():
        elapsed = int(time.time() - start_time[0])
        timer_label.config(text=f"Time elapsed: {elapsed}s")
        if marker.visible:
            timer_label.config(fg="green", 
                             text=f"Time elapsed: {elapsed}s - Underline STILL VISIBLE ✓")
        else:
            timer_label.config(fg="gray", 
                             text=f"Time elapsed: {elapsed}s - Underline hidden")
        root.after(1000, update_timer)
    
    def show_persistent():
        start_time[0] = time.time()
        marker.show_persistent(300, 200, 150, "#FF3B30")
        info.config(text="🔒 PERSISTENT underline shown\nWatch the timer - it will stay visible!", 
                   fg="red", font=("Arial", 12, "bold"))
    
    def show_temporary():
        start_time[0] = time.time()
        marker.show_temporary(300, 200, 150, "#F57C00", 3000)
        info.config(text="⏱️ TEMPORARY underline shown\nWatch it disappear after 3 seconds...", 
                   fg="orange", font=("Arial", 12, "bold"))
    
    def hide_marker():
        marker.hide()
        info.config(text="✅ Underline manually hidden", 
                   fg="black", font=("Arial", 12))
    
    # Buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=20)
    
    btn_persistent = tk.Button(button_frame, text="Show Persistent\n(No auto-hide)", 
                               command=show_persistent, width=20, height=3,
                               bg="#FF3B30", fg="white", font=("Arial", 10, "bold"))
    btn_persistent.pack(side=tk.LEFT, padx=5)
    
    btn_temporary = tk.Button(button_frame, text="Show Temporary\n(3 sec auto-hide)", 
                             command=show_temporary, width=20, height=3,
                             bg="#F57C00", fg="white", font=("Arial", 10, "bold"))
    btn_temporary.pack(side=tk.LEFT, padx=5)
    
    btn_hide = tk.Button(button_frame, text="Hide\n(Manual)", 
                        command=hide_marker, width=20, height=3,
                        bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
    btn_hide.pack(side=tk.LEFT, padx=5)
    
    update_timer()
    
    print("\n✅ Test window opened - try the buttons!")
    print("="*70 + "\n")
    
    root.mainloop()


if __name__ == "__main__":
    run_test()
