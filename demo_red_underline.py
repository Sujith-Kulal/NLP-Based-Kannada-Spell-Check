#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demo: Show what the red underline popup looks like
"""

import tkinter as tk
from tkinter import scrolledtext

def demo_popup():
    root = tk.Tk()
    root.title("Kannada Spell Checker - Visual Example")
    root.geometry("700x600")
    root.configure(bg='#f0f0f0')
    
    # Title
    title = tk.Label(
        root,
        text="📝 Red Underline for Words WITHOUT Suggestions",
        font=("Arial", 14, "bold"),
        bg='#f0f0f0',
        fg='#333'
    )
    title.pack(pady=10)
    
    # Results area
    results_text = scrolledtext.ScrolledText(
        root,
        font=("Nirmala UI", 12),
        wrap=tk.WORD,
        bg='white',
        fg='black'
    )
    results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Configure tags
    results_text.tag_config('header', foreground='#333', font=("Arial", 11, "bold"))
    results_text.tag_config('error', foreground='red', font=("Nirmala UI", 12, "bold"))
    results_text.tag_config('error_underline', foreground='red', font=("Nirmala UI", 14, "bold"), underline=True)
    results_text.tag_config('word_error_no_suggestion', foreground='white', background='#D32F2F', underline=True, font=("Nirmala UI", 14, "bold"))
    results_text.tag_config('word_error_with_suggestion', foreground='#B71C1C', background='#FFEBEE', underline=True, font=("Nirmala UI", 12))
    results_text.tag_config('suggestion', foreground='blue', font=("Nirmala UI", 11))
    results_text.tag_config('normal', font=("Nirmala UI", 12))
    
    # Example content
    results_text.insert(tk.END, "📝 Your Text with Visual Marking:\n\n", 'header')
    
    # Show the problematic text with highlighting
    results_text.insert(tk.END, "ಸಕಪ", 'word_error_no_suggestion')  # Red background + underline
    results_text.insert(tk.END, " ")
    results_text.insert(tk.END, "ರತಸಬಪ", 'word_error_no_suggestion')  # Red background + underline
    results_text.insert(tk.END, " ")
    results_text.insert(tk.END, "ದಸಲದಗ", 'word_error_no_suggestion')  # Red background + underline
    results_text.insert(tk.END, " ")
    results_text.insert(tk.END, "ರದಸ", 'word_error_no_suggestion')  # Red background + underline
    results_text.insert(tk.END, " . ")
    results_text.insert(tk.END, "ಹಪ", 'word_error_no_suggestion')  # Red background + underline
    results_text.insert(tk.END, " .\n\n")
    
    # Legend
    results_text.insert(tk.END, "═" * 60 + "\n\n", 'header')
    results_text.insert(tk.END, "Legend:\n", 'header')
    results_text.insert(tk.END, "• ", 'normal')
    results_text.insert(tk.END, "Red background + underline", 'word_error_no_suggestion')
    results_text.insert(tk.END, " = No suggestions found\n", 'normal')
    results_text.insert(tk.END, "• ", 'normal')
    results_text.insert(tk.END, "Light red + underline", 'word_error_with_suggestion')
    results_text.insert(tk.END, " = Has suggestions\n\n", 'normal')
    
    # Detailed errors
    results_text.insert(tk.END, "❌ Found 5 Error(s):\n\n", 'error')
    
    results_text.insert(tk.END, "1. ", 'header')
    results_text.insert(tk.END, "ಸಕಪ", 'error_underline')
    results_text.insert(tk.END, " (sakapa) - NN\n")
    results_text.insert(tk.END, "   ⚠️  ", 'header')
    results_text.insert(tk.END, "No suggestions found - ", 'error_underline')
    results_text.insert(tk.END, "word may be severely misspelled\n\n")
    
    results_text.insert(tk.END, "2. ", 'header')
    results_text.insert(tk.END, "ರತಸಬಪ", 'error_underline')
    results_text.insert(tk.END, " (rawasabapa) - NN\n")
    results_text.insert(tk.END, "   ⚠️  ", 'header')
    results_text.insert(tk.END, "No suggestions found - ", 'error_underline')
    results_text.insert(tk.END, "word may be severely misspelled\n\n")
    
    results_text.insert(tk.END, "... and 3 more errors\n\n")
    
    # Summary
    results_text.insert(tk.END, "⚠️  5 word(s) ", 'header')
    results_text.insert(tk.END, "underlined in red", 'error_underline')
    results_text.insert(tk.END, " - no suggestions available\n\n", 'normal')
    
    results_text.insert(tk.END, "═" * 60 + "\n\n", 'header')
    results_text.insert(tk.END, "💡 TIP: Try copying correct Kannada words like:\n", 'header')
    results_text.insert(tk.END, "   ಮರವು (tree), ಹುಡುಗನು (boy), ನನಗೆ (to me)\n\n", 'normal')
    results_text.insert(tk.END, "Or words with typos like:\n", 'header')
    results_text.insert(tk.END, "   ಮರವ → will suggest: ಮರವು, ಮರವೆ, etc.\n", 'suggestion')
    
    # Make read-only
    results_text.config(state=tk.DISABLED)
    
    # Close button
    close_btn = tk.Button(
        root,
        text="Close Demo",
        command=root.destroy,
        font=("Arial", 10, "bold"),
        bg='#2196F3',
        fg='white',
        padx=20,
        pady=5
    )
    close_btn.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    demo_popup()
