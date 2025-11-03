#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pickle
import os

# Load dictionaries
print("Loading dictionaries...")

# Load paradigm words
paradigm_dir = "paradigms"
all_words = {}

for pos_category in ['Noun', 'Verb', 'Pronouns']:
    pos_path = os.path.join(paradigm_dir, pos_category)
    if os.path.exists(pos_path):
        for filename in os.listdir(pos_path):
            if filename.endswith('_word_split.txt'):
                filepath = os.path.join(pos_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split()
                            if parts:
                                word = parts[0]
                                all_words[word] = all_words.get(word, 0) + 1

# Load extended dictionary
if os.path.exists('extended_dictionary.pkl'):
    with open('extended_dictionary.pkl', 'rb') as f:
        extended_dict = pickle.load(f)
        for pos_dict in extended_dict.values():
            for word in pos_dict:
                all_words[word] = all_words.get(word, 0) + 1

print(f"Total words: {len(all_words)}")

# Search for words
search_terms = ['maxada', 'mada', 'kada', 'vada', 'avaralli', 'avarali', 'avara']

print("\nSearching for words:")
print("=" * 50)
for term in search_terms:
    if term in all_words:
        print(f"✅ '{term}' FOUND (frequency: {all_words[term]})")
    else:
        print(f"❌ '{term}' NOT FOUND")
        # Find similar words
        similar = [w for w in all_words.keys() if term in w or w in term]
        if similar:
            print(f"   Similar: {', '.join(similar[:10])}")
