#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test spell checker with extended dictionary
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker

def test_words():
    print("=" * 70)
    print("Testing with Extended Dictionary")
    print("=" * 70)
    print()
    
    # Initialize spell checker
    checker = EnhancedSpellChecker()
    print()
    
    # Test words
    test_cases = [
        "ಇವರಲಿ",   # ivarali -> should suggest avaralli
        "ಕವದ",      # kavaxa -> should suggest similar words
    ]
    
    for kannada in test_cases:
        print(f"{'='*70}")
        print(f"Testing: {kannada}")
        print(f"{'='*70}\n")
        
        errors = checker.check_text(kannada)
        
        if errors:
            for error in errors:
                print(f"Word: {error['word']}")
                print(f"POS: {error['pos']}")
                print(f"Suggestions: {error['suggestions'][:10]}")
        else:
            print("✅ Word is correct!")
        
        print()

if __name__ == "__main__":
    test_words()
