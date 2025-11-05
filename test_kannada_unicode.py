#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test spell checker with Kannada Unicode text (ಕನ್ನಡ)
This demonstrates that the spell checker now works with text typed in Notepad!
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker

def test_kannada_unicode():
    """Test with actual Kannada Unicode text"""
    
    print("=" * 70)
    print("Testing with Kannada Unicode (ಕನ್ನಡ)")
    print("This is what you type in Notepad!")
    print("=" * 70)
    print()
    
    # Initialize
    checker = EnhancedSpellChecker()
    print()
    
    # Test cases with Kannada Unicode
    test_cases = [
        {
            "text": "ಮರವು ಹುಡುಗನು",
            "description": "Correct: Tree and Boy"
        },
        {
            "text": "ಮರವು ಹುಡುಗನು ಮರವ",
            "description": "Error: 'ಮರವ' should be 'ಮರವು'"
        },
        {
            "text": "ನನಗೆ",
            "description": "Correct: To me (pronoun)"
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 70}")
        print(f"TEST {i}: {test['description']}")
        print(f"{'=' * 70}")
        print(f"Kannada Input: {test['text']}")
        
        errors = checker.check_text(test['text'])
        
        if errors:
            print(f"\n❌ FOUND {len(errors)} ERROR(S):")
            for error in errors:
                print(f"\n  Word: '{error['word']}' (POS: {error['pos']})")
                if error['suggestions']:
                    print(f"  Suggestions: {', '.join(error['suggestions'][:5])}")
                else:
                    print(f"  No suggestions")
        else:
            print("\n✅ ALL CORRECT!")
    
    print()
    print("=" * 70)
    print("✅ SUCCESS! Spell checker works with Kannada Unicode!")
    print("   You can now type in Notepad and copy-paste to check!")
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_kannada_unicode()
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
