#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Check if avaralli is in the dictionary
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker

def check_dictionary():
    print("=" * 70)
    print("Checking Dictionary Contents")
    print("=" * 70)
    print()
    
    # Initialize spell checker
    checker = EnhancedSpellChecker()
    print()
    
    # Check specific words
    test_words = ['avaralli', 'ivaralli', 'ivaru', 'avaru']
    
    print(f"{'='*70}")
    print("Checking for specific words:")
    print(f"{'='*70}\n")
    
    for word in test_words:
        found_in = []
        
        # Check in each POS category
        for pos, words_dict in checker.pos_paradigms.items():
            if word in words_dict:
                found_in.append(pos)
        
        # Check in combined dictionary
        in_combined = word in checker.all_words
        
        if found_in:
            print(f"✅ '{word}' found in: {', '.join(found_in)}")
        else:
            print(f"❌ '{word}' NOT in any POS category")
        
        print(f"   In combined dict: {in_combined}")
        print()
    
    # Show dictionary sizes
    print(f"{'='*70}")
    print("Dictionary Sizes:")
    print(f"{'='*70}\n")
    for pos, words_dict in checker.pos_paradigms.items():
        print(f"{pos}: {len(words_dict):,} words")
    print(f"\nCombined: {len(checker.all_words):,} words")

if __name__ == "__main__":
    check_dictionary()
