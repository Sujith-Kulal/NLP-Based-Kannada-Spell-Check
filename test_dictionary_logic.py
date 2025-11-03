#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enhanced_spell_checker import EnhancedSpellChecker

print("=" * 70)
print("Testing Dictionary Lookup Logic")
print("=" * 70)

spell_checker = EnhancedSpellChecker()

# Test cases
test_cases = [
    ("ivarali", "Should be WRONG (not in dictionary)"),
    ("barali", "Should be CORRECT (in VB paradigm)"),
    ("avaralli", "Should be CORRECT (in PR paradigm)"),
    ("ivaru", "Should be CORRECT (in dictionary from Excel)"),
    ("wrongword", "Should be WRONG (made up word)"),
]

print("\n" + "=" * 70)
print("Test Results:")
print("=" * 70)

for word, description in test_cases:
    is_correct, suggestions = spell_checker.check_against_paradigm(word, "NN")
    
    status = "✅ CORRECT" if is_correct else "❌ WRONG"
    
    print(f"\n{word:15} → {status}")
    print(f"  Description: {description}")
    
    if not is_correct and suggestions:
        print(f"  Suggestions: {', '.join(suggestions[:5])}")
    
    # Verify it's in dictionary
    in_dict = word in spell_checker.all_words
    print(f"  In dictionary: {'YES' if in_dict else 'NO'}")
    
    # Check which POS category
    if in_dict:
        found_in = []
        for pos, words in spell_checker.pos_paradigms.items():
            if word in words:
                found_in.append(pos)
        print(f"  Found in POS: {', '.join(found_in)}")

print("\n" + "=" * 70)
print("Dictionary Stats:")
print("=" * 70)
print(f"Total words in dictionary: {len(spell_checker.all_words):,}")
print(f"  NN (Nouns): {len(spell_checker.pos_paradigms['NN']):,}")
print(f"  VB (Verbs): {len(spell_checker.pos_paradigms['VB']):,}")
print(f"  PR (Pronouns): {len(spell_checker.pos_paradigms['PR']):,}")
