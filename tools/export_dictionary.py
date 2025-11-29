#!/usr/bin/env python3
"""
Export all words from SimplifiedSpellChecker dictionary to a text file.

Usage:
    python tools/export_dictionary.py
    python tools/export_dictionary.py output_filename.txt
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_spell_checker import SimplifiedSpellChecker


def export_dictionary(output_file: str = "all_words_dictionary.txt") -> None:
    """Export all words from the spell checker to a text file."""
    print("\n" + "=" * 70)
    print("Dictionary Export Tool")
    print("=" * 70)
    
    # Initialize spell checker (this loads all paradigms)
    print("\nInitializing spell checker...")
    checker = SimplifiedSpellChecker(use_paradigm_generator=False)
    
    # Get all words
    all_words = sorted(checker.all_words)
    total_words = len(all_words)
    
    print(f"\n[export] Writing {total_words:,} words to {output_file} ...")
    
    # Write to file
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        for word in all_words:
            f.write(word + "\n")
    
    print(f"[✓] Successfully exported {total_words:,} words")
    print(f"[✓] File saved: {output_path}")
    
    # Show sample
    print(f"\n[sample] First 10 words:")
    for word in all_words[:10]:
        print(f"  - {word}")
    
    print(f"\n[sample] Last 10 words:")
    for word in all_words[-10:]:
        print(f"  - {word}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    output_filename = sys.argv[1] if len(sys.argv) > 1 else "all_words_dictionary.txt"
    export_dictionary(output_filename)
