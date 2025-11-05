#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for Enhanced Kannada Spell Checker
Demonstrates the 5-step NLP pipeline without clipboard monitoring
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker

def test_spell_checker():
    """Test the spell checker with sample Kannada text"""
    
    print("=" * 70)
    print("Testing Enhanced Kannada Spell Checker")
    print("=" * 70)
    print()
    
    # Initialize spell checker
    print("Initializing spell checker...")
    checker = EnhancedSpellChecker()
    print()
    
    # Test cases (WX transliteration format)
    test_cases = [
        {
            "text": "maravu huduganu baruwaane",
            "description": "Correct Kannada sentence (all words valid)"
        },
        {
            "text": "maravu huduganu marauv",
            "description": "Contains error: 'marauv' (should be 'maravu')"
        },
        {
            "text": "avanu nanage pustaka koVtata",
            "description": "Mixed: pronoun, verb, noun"
        },
        {
            "text": "huduga mara kANuwaanu",
            "description": "Boy sees tree (testing verb forms)"
        }
    ]
    
    # Test each case
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 70}")
        print(f"TEST CASE {i}: {test['description']}")
        print(f"{'=' * 70}")
        print(f"Input: {test['text']}")
        print()
        
        # Process text
        errors = checker.check_text(test['text'])
        
        if errors:
            print(f"\n❌ FOUND {len(errors)} ERROR(S):")
            for error in errors:
                print(f"\n  Word: '{error['word']}' (POS: {error['pos']})")
                if error['suggestions']:
                    print(f"  Suggestions: {', '.join(error['suggestions'][:5])}")
                else:
                    print(f"  No suggestions found")
        else:
            print("\n✅ NO ERRORS FOUND - All words are correct!")
    
    print()
    print("=" * 70)
    print("Testing Complete!")
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_spell_checker()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
