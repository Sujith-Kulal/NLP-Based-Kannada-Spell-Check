#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick test for baravu word
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker

print("="*70)
print("Testing: ಬರವು (baravu)")
print("="*70)

checker = EnhancedSpellChecker()
errors1 = checker.check_text("ಬರವು")

if errors1:
    print(f"\n❌ Word is incorrect")
    print(f"📝 Suggestions: {errors1[0].get('suggestions', [])}")
else:
    print(f"\n✅ Word is correct (in dictionary)")

print("\n" + "="*70)
print("Testing: ಮರವು (maravu)")
print("="*70)

errors2 = checker.check_text("ಮರವು")

if errors2:
    print(f"\n❌ Word is incorrect")
    print(f"📝 Suggestions: {errors2[0].get('suggestions', [])}")
else:
    print(f"\n✅ Word is correct (in dictionary)")

print("\n" + "="*70)
print("Edit distance check:")
print("="*70)
distance = checker.levenshtein_distance("baravu", "maravu")
print(f"Distance between 'baravu' and 'maravu': {distance}")
