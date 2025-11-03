#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kannada Spell Checker with Popup Suggestions
Works with Notepad - Shows a popup window with errors and suggestions
"""

import sys
import os
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker
from kannada_wx_converter import wx_to_kannada

try:
    import pyperclip
except ImportError:
    print("❌ Error: pyperclip not installed")
    print("Install: pip install pyperclip")
    sys.exit(1)


class SpellCheckPopup:
    """Popup window showing spell check results"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Kannada Spell Checker - Live Results")
        self.root.geometry("600x500")
        self.root.configure(bg='#f0f0f0')
        
        # Configure window to stay on top
        self.root.attributes('-topmost', True)
        
        # Status label
        self.status_label = tk.Label(
            self.root,
            text="⏳ Waiting for text... (Copy text with Ctrl+C)",
            font=("Arial", 12, "bold"),
            bg='#f0f0f0',
            fg='#666'
        )
        self.status_label.pack(pady=10)
        
        # Results area
        self.results_frame = ttk.Frame(self.root)
        self.results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrolled text for results
        self.results_text = scrolledtext.ScrolledText(
            self.results_frame,
            font=("Nirmala UI", 11),  # Better Kannada font support
            wrap=tk.WORD,
            bg='white',
            fg='black'
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for colors
        self.results_text.tag_config('correct', foreground='green', font=("Nirmala UI", 11, "bold"))
        self.results_text.tag_config('error', foreground='red', font=("Nirmala UI", 12, "bold"))
        self.results_text.tag_config('error_underline', foreground='red', font=("Nirmala UI", 12, "bold"), underline=True)
        self.results_text.tag_config('suggestion', foreground='blue', font=("Nirmala UI", 11))
        self.results_text.tag_config('header', foreground='#333', font=("Arial", 11, "bold"))
        self.results_text.tag_config('word_correct', foreground='#2E7D32', background='#E8F5E9')
        self.results_text.tag_config('word_error_no_suggestion', foreground='white', background='#D32F2F', underline=True)
        self.results_text.tag_config('word_error_with_suggestion', foreground='#B71C1C', background='#FFEBEE', underline=True)
        
        # Statistics
        self.stats_label = tk.Label(
            self.root,
            text="Checks: 0 | Errors: 0 | Corrections suggested: 0",
            font=("Arial", 9),
            bg='#f0f0f0',
            fg='#666'
        )
        self.stats_label.pack(pady=5)
        
        # Controls label
        controls = tk.Label(
            self.root,
            text="📋 Copy text in Notepad (Ctrl+C) to check spelling | Press Ctrl+C here to exit",
            font=("Arial", 8),
            bg='#f0f0f0',
            fg='#999'
        )
        controls.pack(pady=5)
        
        # Statistics
        self.total_checks = 0
        self.total_errors = 0
        self.total_suggestions = 0
        
    def update_status(self, message, color='#666'):
        """Update status label"""
        self.status_label.config(text=message, fg=color)
    
    def update_stats(self):
        """Update statistics"""
        self.stats_label.config(
            text=f"Checks: {self.total_checks} | Errors: {self.total_errors} | Corrections suggested: {self.total_suggestions}"
        )
    
    def show_results(self, text, errors):
        """Display spell check results with visual highlighting"""
        self.results_text.delete('1.0', tk.END)
        
        # Header
        timestamp = time.strftime("%H:%M:%S")
        self.results_text.insert(tk.END, f"⏰ Check at {timestamp}\n", 'header')
        self.results_text.insert(tk.END, "─" * 60 + "\n\n")
        
        # Show text with visual highlighting (red underlines for errors)
        self.results_text.insert(tk.END, "📝 Your Text with Visual Marking:\n", 'header')
        self._show_highlighted_text(text, errors)
        self.results_text.insert(tk.END, "\n\n")
        
        # Detailed results
        if errors:
            self.results_text.insert(tk.END, f"❌ Found {len(errors)} Error(s):\n\n", 'error')
            
            errors_with_no_suggestions = 0
            
            for i, error in enumerate(errors, 1):
                word = error['word']
                pos = error['pos']
                suggestions = error['suggestions']
                
                self.results_text.insert(tk.END, f"{i}. ", 'header')
                
                # Use red underline for words without suggestions
                if not suggestions:
                    self.results_text.insert(tk.END, f"{word}", 'error_underline')
                    errors_with_no_suggestions += 1
                else:
                    self.results_text.insert(tk.END, f"{word}", 'error')
                
                self.results_text.insert(tk.END, f" ({pos})\n")
                
                if suggestions:
                    self.results_text.insert(tk.END, "   💡 Suggestions: ", 'header')
                    self.results_text.insert(tk.END, f"{', '.join(suggestions[:5])}\n", 'suggestion')
                    self.total_suggestions += len(suggestions[:5])
                else:
                    self.results_text.insert(tk.END, "   ⚠️  ", 'header')
                    self.results_text.insert(tk.END, "No suggestions found - ", 'error_underline')
                    self.results_text.insert(tk.END, "word may be severely misspelled\n")
                
                self.results_text.insert(tk.END, "\n")
            
            # Summary
            if errors_with_no_suggestions > 0:
                self.results_text.insert(tk.END, f"⚠️  {errors_with_no_suggestions} word(s) ", 'header')
                self.results_text.insert(tk.END, "underlined in red", 'error_underline')
                self.results_text.insert(tk.END, " - no suggestions available\n")
        else:
            self.results_text.insert(tk.END, "✅ Perfect! No errors found.\n", 'correct')
        
        # Update stats
        self.total_checks += 1
        self.total_errors += len(errors)
        self.update_stats()
    
    def _show_highlighted_text(self, text, errors):
        """Show text with visual highlighting for errors"""
        # Create error word set for quick lookup
        error_words = {}
        for error in errors:
            word = error['word']
            has_suggestions = len(error.get('suggestions', [])) > 0
            error_words[word] = has_suggestions
        
        # Tokenize and display with highlighting
        words = text.split()
        for i, word in enumerate(words):
            # Clean word (remove punctuation for checking)
            clean_word = word.strip('.,!?;:()[]{}\"\'')
            
            if clean_word in error_words:
                # Error word - highlight with red background and underline
                if error_words[clean_word]:
                    # Has suggestions - lighter red background
                    self.results_text.insert(tk.END, word, 'word_error_with_suggestion')
                else:
                    # No suggestions - dark red background with underline
                    self.results_text.insert(tk.END, word, 'word_error_no_suggestion')
            else:
                # Correct word
                self.results_text.insert(tk.END, word)
            
            # Add space between words
            if i < len(words) - 1:
                self.results_text.insert(tk.END, " ")


class SpellCheckerService:
    """Background service with popup window"""
    
    def __init__(self):
        print("\n" + "="*70)
        print("🎯 Kannada Spell Checker with Popup Window")
        print("="*70)
        print("\nInitializing...")
        
        self.checker = EnhancedSpellChecker()
        self.popup = SpellCheckPopup()
        self.last_clipboard = ""
        self.running = True
        
        print("\n✅ Service started!")
        print("📋 Copy Kannada text in Notepad to see spell check results in popup")
        print("="*70 + "\n")
    
    def monitor_clipboard(self):
        """Monitor clipboard in background thread"""
        while self.running:
            try:
                current_text = pyperclip.paste()
                
                # Check if clipboard changed and has Kannada content
                if current_text and current_text != self.last_clipboard:
                    if len(current_text.strip()) > 0:
                        self.last_clipboard = current_text
                        
                        # Update status
                        self.popup.update_status("🔍 Checking...", '#FF9800')
                        self.popup.root.update()
                        
                        # Check spelling
                        errors = self.checker.check_text(current_text)
                        
                        # Show results
                        self.popup.show_results(current_text, errors)
                        
                        # Update status
                        if errors:
                            self.popup.update_status(f"❌ Found {len(errors)} error(s)", 'red')
                        else:
                            self.popup.update_status("✅ Perfect spelling!", 'green')
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                print(f"⚠️  Error: {e}")
                time.sleep(2)
    
    def run(self):
        """Start the service"""
        # Start clipboard monitoring in background
        monitor_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        monitor_thread.start()
        
        # Run GUI main loop
        try:
            self.popup.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            print("\n✅ Service stopped")


if __name__ == "__main__":
    try:
        service = SpellCheckerService()
        service.run()
    except KeyboardInterrupt:
        print("\n\n✅ Service stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
