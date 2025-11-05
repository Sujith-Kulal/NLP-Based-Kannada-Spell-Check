#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the complete auto-correction flow:
Kannada Input → WX Conversion → Spell Check → WX Suggestions → Kannada Output
"""

from enhanced_spell_checker import EnhancedSpellChecker
from kannada_wx_converter import wx_to_kannada, is_kannada_text

print("=" * 70)
print("Complete Auto-Correction Flow Test")
print("=" * 70)

# Initialize spell checker
spell_checker = EnhancedSpellChecker()

# Test word (misspelled Kannada)
test_word = "ಇವರಲಿ"  # ivarali - misspelled

print(f"\n📝 User types: {test_word}")
print(f"   Is Kannada: {is_kannada_text(test_word)}")

# Simulate the correction flow
print(f"\n{'='*70}")
print("STEP-BY-STEP PROCESS:")
print(f"{'='*70}")

# Check word using spell checker
errors = spell_checker.check_text(test_word)

if errors and len(errors) > 0:
    error = errors[0]
    word_wx = error.get('word', '')
    suggestions_wx = error.get('suggestions', [])
    
    print(f"\n📊 Spell Checker Results:")
    print(f"   Word (WX): {word_wx}")
    print(f"   Suggestions (WX): {', '.join(suggestions_wx[:5])}")
    
    if suggestions_wx:
        # Get best suggestion (in WX)
        best_suggestion_wx = suggestions_wx[0]
        
        # Convert back to Kannada
        best_suggestion_kannada = wx_to_kannada(best_suggestion_wx)
        
        print(f"\n✨ Auto-Correction:")
        print(f"   Best suggestion (WX): {best_suggestion_wx}")
        print(f"   Best suggestion (Kannada): {best_suggestion_kannada}")
        
        print(f"\n{'='*70}")
        print(f"FINAL RESULT:")
        print(f"{'='*70}")
        print(f"   Original:  {test_word}")
        print(f"   Corrected: {best_suggestion_kannada}")
        print(f"{'='*70}")
else:
    print(f"\n✅ Word '{test_word}' is correct (no suggestions)")

# Test more words
print(f"\n\n{'='*70}")
print("Additional Test Cases:")
print(f"{'='*70}")

test_cases = [
    ("ಬರಲಿ", "barali - correct word"),
    ("ಇವರ", "ivara - correct word"),
    ("ಮರ", "mara - correct word"),
]

for test, desc in test_cases:
    errors = spell_checker.check_text(test)
    if errors:
        suggestions = errors[0].get('suggestions', [])
        if suggestions:
            best_wx = suggestions[0]
            best_kannada = wx_to_kannada(best_wx)
            print(f"\n{test} ({desc})")
            print(f"  → Suggestion: {best_kannada}")
        else:
            print(f"\n{test} ({desc})")
            print(f"  → No suggestions")
    else:
        print(f"\n{test} ({desc})")
        print(f"  ✅ Correct!")
