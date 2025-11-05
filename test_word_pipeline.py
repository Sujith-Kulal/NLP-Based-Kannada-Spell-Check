#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal pipeline tester for a single word or sentence.
Usage:
  python test_word_pipeline.py <text to check> [--kannada-out]

Prints:
- Tokens (WX)
- POS tags
- Chunks
- POS-aware paradigm check (correct or suggestions)
"""
import sys
import os
import argparse

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker
from kannada_wx_converter import normalize_text, is_kannada_text, wx_to_kannada


def main():
    parser = argparse.ArgumentParser(description="Test token → POS → chunk → paradigm-check for input text")
    parser.add_argument("text", nargs=argparse.REMAINDER, help="Word or sentence to check (Kannada or WX). Put it before flags.")
    parser.add_argument("--kannada-out", action="store_true", dest="kn_out", help="Show suggestions in Kannada script")
    args = parser.parse_args()

    if not args.text:
        print("Provide a word or sentence. Example: python test_word_pipeline.py ಇವರಲಿ --kannada-out")
        sys.exit(1)

    # If user put flags after the word, they are part of text due to REMAINDER.
    # Strip known flag from the tail just in case.
    parts = args.text
    if parts and parts[-1] == "--kannada-out":
        parts = parts[:-1]
    raw_text = " ".join(parts).strip()

    checker = EnhancedSpellChecker()

    # Normalize to WX if Kannada
    text_wx = normalize_text(raw_text)

    # Step 1: Tokenize
    tokens = checker.tokenize(text_wx)

    # Step 2: POS tag
    pos_tagged = checker.pos_tag(tokens)

    # Step 3: Chunk
    chunks = checker.chunk(pos_tagged)

    # Output
    print("\n" + "=" * 70)
    print("INPUT:")
    print(f"  Raw: {raw_text}")
    print(f"  WX : {text_wx}")

    print("\nTOKENS (WX):")
    print("  ", tokens)

    print("\nPOS TAGS:")
    for w, p in pos_tagged:
        print(f"  {w} → {p}")

    print("\nCHUNKS:")
    for ctype, words in chunks:
        print(f"  [{ctype}: {' '.join(words)}]")

    print("\nPARADIGM CHECK (POS-aware):")
    for w, p in pos_tagged:
        if len(w) <= 1:
            continue
        ok, suggestions = checker.check_against_paradigm(w, p)
        if ok:
            print(f"  ✅ {w} ({p}) is correct")
        else:
            if args.kn_out and is_kannada_text(raw_text):
                kannada_sug = [wx_to_kannada(s) for s in suggestions[:10]]
                print(f"  ❌ {w} ({p}) → Suggestions (KN): {', '.join(kannada_sug) if kannada_sug else 'None'}")
            else:
                print(f"  ❌ {w} ({p}) → Suggestions (WX): {', '.join(suggestions[:10]) if suggestions else 'None'}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
