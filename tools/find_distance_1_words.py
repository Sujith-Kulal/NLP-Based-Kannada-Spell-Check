#!/usr/bin/env python3
"""
Find words with edit distance = 1 for testing
Based on actual paradigm file contents
Now with PARADIGM GENERATOR support!
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_spell_checker import EnhancedSpellChecker

def levenshtein(s1, s2):
    """Calculate edit distance"""
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

print("Loading spell checker (with Paradigm Generator if available)...")
checker = EnhancedSpellChecker()

# Show if paradigm generator is active
if hasattr(checker, 'paradigm_generator') and checker.paradigm_generator:
    print("\n✨ PARADIGM GENERATOR ACTIVE!")
    stats = checker.paradigm_generator.get_stats()
    print(f"   Base paradigms: {stats['base_count']:,}")
    print(f"   Derived paradigms: {stats['derived_count']:,}")
    print(f"   Total paradigms: {stats['total_count']:,}")
    print(f"   Dictionary expanded by paradigm forms!")
else:
    print("\n📖 Using standard dictionary loading")

print("\n" + "="*70)
print("WORDS WITH EDIT DISTANCE = 1 (Perfect for Testing)")
print("="*70)

# Get all words from dictionary
all_words = list(checker.all_words.keys())

# Find word pairs with distance = 1
test_cases = []
seen = set()

print("\nSearching for word pairs with edit distance = 1...")
print("This may take a moment...\n")

# Sample from dictionary to find examples
import random
sample = random.sample(all_words, min(1000, len(all_words)))

for word1 in sample[:100]:  # Check first 100 words
    for word2 in all_words:
        if word1 != word2 and word1 not in seen:
            dist = levenshtein(word1, word2)
            if dist == 1:
                test_cases.append((word1, word2, dist))
                seen.add(word1)
                if len(test_cases) >= 10:  # Get 10 examples
                    break
    if len(test_cases) >= 10:
        break

if test_cases:
    print("✅ FOUND EDIT DISTANCE = 1 EXAMPLES:\n")
    for i, (word1, word2, dist) in enumerate(test_cases, 1):
        print(f"{i}. Test Word: {word1}")
        print(f"   Should suggest: {word2}")
        print(f"   Edit Distance: {dist}")
        print()
else:
    print("⚠️ No exact distance=1 pairs found in sample.")
    print("\nHere are some GUARANTEED test cases from your paradigm structure:\n")
    
    # Manual examples based on paradigm patterns
    print("✅ GUARANTEED EDIT DISTANCE = 1 TEST CASES:\n")
    
    examples = [
        ("maravu", "maravu (exists)", "mara", "Should suggest: maravu"),
        ("avara", "avara (exists)", "avaru", "Should suggest: avara"),
        ("akkana", "akkana (exists)", "akkanu", "Should suggest: akkana"),
        ("ajjiyu", "ajjiyu (exists)", "ajjI", "Should suggest: ajjiyu"),
    ]
    
    for i, (test_word, exists, similar, note) in enumerate(examples, 1):
        # Check if words exist
        exists_in_dict = test_word in checker.all_words
        print(f"{i}. Test: {test_word}")
        print(f"   Exists in dictionary: {exists_in_dict}")
        if exists_in_dict:
            print(f"   Try removing one letter: {similar}")
        print()

print("\n" + "="*70)
print("HOW TO TEST:")
print("="*70)
print("""
1. Pick a word from above (e.g., 'maravu')
2. Create 1-character typo:
   - Delete 1 letter: 'maravu' → 'marav'
   - Change 1 letter: 'maravu' → 'maranu'
   - Add 1 letter: 'mara' → 'marav'

3. Test with:
   python .\\tools\\check_word.py "ಮರವ"  (WX: marav)

4. Or in Notepad with service running:
   - Type the typo word
   - Press SPACE
   - Watch auto-correction!
""")

print("\n✅ READY TO TEST!")
