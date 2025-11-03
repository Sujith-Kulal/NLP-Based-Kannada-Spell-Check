#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extract words from Excel files and add to spell checker dictionary
This will help improve spell checking by including all paradigm forms
"""

import sys
import os
from openpyxl import load_workbook
import pickle

def extract_words_from_excel(filepath, pos_type):
    """Extract all words from an Excel paradigm file"""
    print(f"\n{'='*70}")
    print(f"📊 Processing: {os.path.basename(filepath)}")
    print(f"{'='*70}\n")
    
    words = {}
    
    try:
        wb = load_workbook(filepath, data_only=True)
        ws = wb.active  # Get first sheet
        
        max_row = ws.max_row
        max_col = ws.max_column
        
        print(f"   Dimensions: {max_row} rows × {max_col} columns")
        
        word_count = 0
        
        # Skip header row, start from row 3
        for row_idx in range(3, max_row + 1):
            for col_idx in range(2, max_col + 1):  # Skip first column (serial number)
                cell = ws.cell(row=row_idx, column=col_idx)
                value = cell.value
                
                if value and isinstance(value, str):
                    value = value.strip()
                    
                    # Skip empty strings and numbers
                    if value and not value.replace('.', '').replace(',', '').isdigit():
                        # Extract the base word (before space or parenthesis)
                        word = value.split()[0].split('(')[0].strip()
                        
                        if word and len(word) > 1:
                            words[word] = words.get(word, 0) + 1
                            word_count += 1
            
            # Progress indicator
            if row_idx % 1000 == 0:
                print(f"   Processed {row_idx}/{max_row} rows...")
        
        wb.close()
        
        unique_words = len(words)
        print(f"\n   ✅ Extracted {word_count} word occurrences")
        print(f"   ✅ Unique words: {unique_words}")
        
        return words
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {}

def main():
    check_pos_dir = r"d:\NLP-Based-Kannada-Spell-Correction-System\check_pos"
    
    # Excel files
    excel_files = [
        ("Noun Distribution.xlsx", "NN"),
        ("Verb Distribution.xlsx", "VB"),
        ("Pronoun Distribution .xlsx", "PR")
    ]
    
    print("\n" + "="*70)
    print("📚 BUILDING EXTENDED DICTIONARY FROM EXCEL FILES")
    print("="*70)
    
    all_words = {
        'NN': {},
        'VB': {},
        'PR': {}
    }
    
    total_words = 0
    
    for filename, pos_type in excel_files:
        filepath = os.path.join(check_pos_dir, filename)
        
        if os.path.exists(filepath):
            words = extract_words_from_excel(filepath, pos_type)
            all_words[pos_type] = words
            total_words += len(words)
        else:
            print(f"\n⚠️  File not found: {filename}")
    
    # Save to pickle file
    output_file = "extended_dictionary.pkl"
    output_path = os.path.join(os.path.dirname(__file__), output_file)
    
    print(f"\n{'='*70}")
    print("💾 SAVING EXTENDED DICTIONARY")
    print(f"{'='*70}\n")
    
    with open(output_path, 'wb') as f:
        pickle.dump(all_words, f)
    
    print(f"   ✅ Saved to: {output_file}")
    print(f"   ✅ Total unique words: {total_words}")
    print(f"      • Nouns: {len(all_words['NN'])}")
    print(f"      • Verbs: {len(all_words['VB'])}")
    print(f"      • Pronouns: {len(all_words['PR'])}")
    
    # Test if specific words are included
    print(f"\n{'='*70}")
    print("🔍 CHECKING FOR SPECIFIC WORDS")
    print(f"{'='*70}\n")
    
    test_words = [
        ('avaralli', 'PR'),
        ('ivaralli', 'PR'),
        ('ivaru', 'PR')
    ]
    
    for word, pos in test_words:
        if word in all_words[pos]:
            print(f"   ✅ '{word}' found in {pos} dictionary")
        else:
            print(f"   ❌ '{word}' NOT found in {pos} dictionary")
    
    print(f"\n{'='*70}")
    print("✅ DONE - Dictionary file created!")
    print(f"{'='*70}\n")
    print("Next step: Update enhanced_spell_checker.py to use this dictionary")

if __name__ == "__main__":
    main()
