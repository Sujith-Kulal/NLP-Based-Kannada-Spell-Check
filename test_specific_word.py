#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test specific Kannada word: ಇವರಲ್ಲಿ
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker
from kannada_wx_converter import kannada_to_wx

def test_word():
    word = "ಇವರಲ್ಲಿ"
    
    print("=" * 70)
    print(f"Testing Kannada word: {word}")
    print("=" * 70)
    print()
    
    # Convert to WX
    wx_word = kannada_to_wx(word)
    print(f"Kannada Unicode: {word}")
    print(f"WX Transliteration: {wx_word}")
    print()
    
    # Initialize spell checker
    print("Loading spell checker...")
    checker = EnhancedSpellChecker()
    print()
    
    # Check the word
    print("=" * 70)
    print("SPELL CHECK RESULTS:")
    print("=" * 70)
    print()
    
    errors = checker.check_text(word)
    
    if errors:
        print(f"❌ '{word}' is NOT in dictionary")
        print(f"   WX form '{wx_word}' not found")
        print()
        for error in errors:
            suggestions = error['suggestions']
            pos = error['pos']
            print(f"   POS Tag: {pos}")
            if suggestions:
                print(f"   💡 Suggestions ({len(suggestions)}):")
                for i, sugg in enumerate(suggestions[:10], 1):
                    print(f"      {i}. {sugg}")
            else:
                print(f"   ⚠️  No suggestions found")
    else:
        print(f"✅ '{word}' IS in dictionary!")
        print(f"   WX form '{wx_word}' is CORRECT")
        print(f"   This is a valid Kannada word ✓")
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    test_word()
