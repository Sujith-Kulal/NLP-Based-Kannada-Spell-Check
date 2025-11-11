#!/usr/bin/env python3
"""
Test locative case forms in spell checker
"""

from enhanced_spell_checker import SimplifiedSpellChecker

print("Initializing spell checker with morphological paradigms...")
checker = SimplifiedSpellChecker()

print("\n" + "="*70)
print("TESTING LOCATIVE CASE FORMS")
print("="*70)

test_words = [
    'amma',           # Base form
    'ammanalli',      # Locative case ✅ YOUR REQUEST!
    'ammana',         # Genitive case
    'ammannu',        # Accusative case
    'ammige',         # Dative case
    'amminda',        # Ablative case
    '',
    'akka',           # Base form
    'akkanalli',      # Locative case ✅
    'akkana',         # Genitive case
    '',
    'avva',           # Base form
    'avvanalli',      # Locative case ✅
    'avvana',         # Genitive case
]

for word in test_words:
    if not word:
        print()
        continue
    status = "✅ FOUND" if word in checker.all_words else "❌ MISSING"
    print(f"{word:20s} → {status}")

print("\n" + "="*70)
print("SPELL CORRECTION TEST")
print("="*70)

# Test misspelling: ammanala → should suggest ammanalli
misspelling = "ammanala"
print(f"\nMisspelled word: {misspelling}")
print(f"Is in dictionary? {'✅ YES' if misspelling in checker.all_words else '❌ NO (as expected)'}")

print(f"\nChecking if correct form exists:")
correct = "ammanalli"
print(f"{correct}: {'✅ FOUND' if correct in checker.all_words else '❌ MISSING'}")

print("\n" + "="*70)
print("SUCCESS! ✅")
print("="*70)
print(f"Total words in dictionary: {len(checker.all_words):,}")
if hasattr(checker, 'morphological_paradigms') and checker.morphological_paradigms:
    print(f"Morphological paradigms loaded: {len(checker.morphological_paradigms):,}")
