#!/usr/bin/env python3
"""
Debug helper: check a single word or phrase with the EnhancedSpellChecker and print detailed info.

Usage:
  python tools/check_word.py "ನಮಸ್ಕಾರ"

This prints:
- whether text is detected as Kannada
- WX conversion (if any)
- tokens
- POS tagging
- paradigm lookup result and suggestions
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_spell_checker import EnhancedSpellChecker
from kannada_wx_converter import is_kannada_text, kannada_to_wx


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/check_word.py \"your text\"")
        sys.exit(1)

    text = sys.argv[1]
    print("Input:", text)

    print("\nInitializing spell checker (may take a few seconds)...")
    s = EnhancedSpellChecker()

    print("\n[STEP 0] Kannada detection and WX conversion")
    print("is_kannada_text:", is_kannada_text(text))
    if is_kannada_text(text):
        wx = kannada_to_wx(text)
        print("WX:", wx)
    else:
        wx = text

    print("\n[STEP 1] Tokenization")
    tokens = s.tokenize(wx)
    print("tokens:", tokens)

    print("\n[STEP 2] POS tagging")
    pos_tagged = s.pos_tag(tokens)
    print("pos_tagged:")
    for w,p in pos_tagged:
        print(f"  {w} -> {p}")

    print("\n[STEP 3-5] Paradigm check and suggestions")
    for w,p in pos_tagged:
        if len(w) <= 1:
            print(f"  Skipping short token: {w}")
            continue
        is_correct, suggestions = s.check_against_paradigm(w, p)
        print(f"  Word: {w} (POS={p}) -> is_correct={is_correct}")
        if not is_correct:
            print(f"    suggestions (default max_distance=2): {suggestions}")
            # show extended suggestions with larger distance
            ext = s.get_suggestions(w, s.all_words, max_suggestions=10, max_distance=4)
            print(f"    extended suggestions (max_distance=4): {ext}")


if __name__ == '__main__':
    main()
