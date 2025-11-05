#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test the Kannada text you provided: ಸಕಪ ರತಸಬಪ ದಸಲದಗ ರದಸ . ಹಪ .
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker

def test_your_text():
    print("=" * 70)
    print("Testing Your Kannada Text")
    print("=" * 70)
    print()
    
    # Your text
    text = "ಸಕಪ ರತಸಬಪ ದಸಲದಗ ರದಸ . ಹಪ ."
    
    print(f"Input: {text}")
    print()
    
    # Initialize spell checker
    checker = EnhancedSpellChecker()
    print()
    
    # Check the text
    errors = checker.check_text(text)
    
    print("\n" + "=" * 70)
    print("RESULTS:")
    print("=" * 70)
    
    if errors:
        print(f"\n❌ FOUND {len(errors)} ERROR(S):\n")
        for i, error in enumerate(errors, 1):
            word = error['word']
            pos = error['pos']
            suggestions = error['suggestions']
            
            print(f"{i}. Word: '{word}' (POS: {pos})")
            if suggestions:
                print(f"   Suggestions: {', '.join(suggestions[:5])}")
            else:
                print(f"   No suggestions found")
            print()
    else:
        print("\n✅ NO ERRORS - All words are correct!")
    
    print("=" * 70)

if __name__ == "__main__":
    test_your_text()
