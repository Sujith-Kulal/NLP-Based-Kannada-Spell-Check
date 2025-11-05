#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pickle
import os
from collections import defaultdict

# Load paradigm dictionary
pos_paradigms = defaultdict(dict)
paradigm_base = 'paradigms'

dir_to_pos = {
    'Noun': 'NN',
    'Verb': 'VB',
    'Pronouns': 'PR'
}

for dir_name, pos_tag in dir_to_pos.items():
    dir_path = os.path.join(paradigm_base, dir_name)
    if os.path.exists(dir_path):
        words = {}
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.txt'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    parts = line.split()
                                    if parts:
                                        word = parts[0]
                                        words[word] = words.get(word, 0) + 1
                    except Exception as e:
                        pass
        pos_paradigms[pos_tag] = words

# Load extended dictionary
if os.path.exists('extended_dictionary.pkl'):
    with open('extended_dictionary.pkl', 'rb') as f:
        extended_dict = pickle.load(f)
        for pos_tag, words in extended_dict.items():
            for word, freq in words.items():
                if word not in pos_paradigms[pos_tag]:
                    pos_paradigms[pos_tag][word] = freq

print("=" * 70)
print("Checking 'ivarali' and related pronoun forms")
print("=" * 70)

# Check ivarali in different categories
test_words = ['ivarali', 'ivaru', 'ivara', 'avarali', 'avaralli', 'avaru', 'avara']

for word in test_words:
    print(f"\n{word}:")
    found_in = []
    for pos_tag, word_dict in pos_paradigms.items():
        if word in word_dict:
            found_in.append(f"{pos_tag} (freq={word_dict[word]})")
    
    if found_in:
        print(f"  ✅ Found in: {', '.join(found_in)}")
    else:
        print(f"  ❌ NOT FOUND in any paradigm")

# Check pronoun patterns
print("\n" + "=" * 70)
print("Pronoun patterns in PR paradigm:")
print("=" * 70)

pr_words = pos_paradigms['PR']
print(f"\nTotal PR words: {len(pr_words)}")

# Find words starting with 'i' or 'a'
i_words = [w for w in pr_words.keys() if w.startswith('i')]
a_words = [w for w in pr_words.keys() if w.startswith('a')]

print(f"\nPR words starting with 'i': {len(i_words)}")
if i_words:
    print(f"  Examples: {', '.join(sorted(i_words)[:20])}")

print(f"\nPR words starting with 'a': {len(a_words)}")
if a_words:
    print(f"  Examples: {', '.join(sorted(a_words)[:20])}")

# Show all pronoun paradigm files
print("\n" + "=" * 70)
print("Pronoun paradigm files:")
print("=" * 70)
pr_dir = os.path.join(paradigm_base, 'Pronouns')
if os.path.exists(pr_dir):
    for file in sorted(os.listdir(pr_dir)):
        if file.endswith('.txt'):
            print(f"  {file}")
