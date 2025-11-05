#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Find typos (words NOT in dictionary) that are distance 1 from real words
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker
from kannada_wx_converter import wx_to_kannada

print("="*70)
print("FINDING REAL TYPOS (words NOT in dictionary)")
print("="*70)

checker = EnhancedSpellChecker()

# Test words from the find_distance_1_words.py output
test_cases = [
    ("Aguva", "Ayuva"),  # From find_distance_1 output
    ("hoVravo", "hoVravu"),
    ("winnuwwAno", "winnuwwAnA"),
    ("ulYalAranA", "ulYalAranu"),
]

print("\n✅ VALID TEST CASES (Typo NOT in dict → Correct word IN dict):\n")

for typo_wx, correct_wx in test_cases:
    # Check if typo is NOT in dictionary
    typo_errors = checker.check_text(typo_wx)
    correct_errors = checker.check_text(correct_wx)
    
    typo_kannada = wx_to_kannada(typo_wx)
    correct_kannada = wx_to_kannada(correct_wx)
    
    typo_in_dict = (len(typo_errors) == 0)
    correct_in_dict = (len(correct_errors) == 0)
    
    if not typo_in_dict and correct_in_dict:
        print(f"✅ Type: {typo_kannada} ({typo_wx})")
        print(f"   Should correct to: {correct_kannada} ({correct_wx})")
        if typo_errors and typo_errors[0].get('suggestions'):
            print(f"   Actual suggestions: {typo_errors[0]['suggestions']}")
        print()
    else:
        print(f"❌ SKIP: {typo_wx} (typo_in_dict={typo_in_dict}, correct_in_dict={correct_in_dict})")
        print()

print("="*70)
print("CREATE SIMPLE TYPOS (delete last letter)")
print("="*70)

# Try simple strategy: take real words and delete 1 character
test_words = ["maravu", "avaru", "Ayuva", "hoVravu"]

for word in test_words:
    # Delete last character
    typo = word[:-1]
    
    typo_errors = checker.check_text(typo)
    word_errors = checker.check_text(word)
    
    typo_in_dict = (len(typo_errors) == 0)
    word_in_dict = (len(word_errors) == 0)
    
    if not typo_in_dict and word_in_dict:
        typo_kannada = wx_to_kannada(typo)
        word_kannada = wx_to_kannada(word)
        print(f"\n✅ Type: {typo_kannada} ({typo})")
        print(f"   Should correct to: {word_kannada} ({word})")
        if typo_errors and typo_errors[0].get('suggestions'):
            print(f"   Actual suggestions: {typo_errors[0]['suggestions'][:3]}")
