#!/usr/bin/env python
# -*- coding: utf-8 -*-

def edit_distance(s1, s2):
    """Calculate Levenshtein edit distance between two strings"""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row are one character longer than s2
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

# Test edit distances
word = "ivarali"
candidates = ["avaralli", "ivaralli", "avaru", "ivaru", "avarali"]

print(f"Edit distances from '{word}':")
print("=" * 50)
for candidate in candidates:
    dist = edit_distance(word, candidate)
    print(f"  {word} → {candidate}: {dist}")
    
    # Show character-level alignment
    print(f"    '{word}' ({len(word)} chars)")
    print(f"    '{candidate}' ({len(candidate)} chars)")
    print()
