#!/usr/bin/env python3
"""
Kannada Paradigm Auto-Generator
--------------------------------
Loads paradigms for base words and dynamically generates paradigms
for all related (derived) words during server startup.

Optimized for use inside NLP-Based-Kannada-Spell-Correction-System
"""

import os
import re
import pandas as pd
import pickle
from collections import defaultdict
from typing import Dict, List, Tuple, Set, Any

# ==============================================================
# CONFIGURATION
# ==============================================================

# Path to Excel file that contains paradigms (like all.xlsx)
EXCEL_PATH = "check_pos/all.xlsx"
# Cache file for fast loading (pickle format)
CACHE_PATH = "check_pos/all_paradigms.pkl"

# Pattern to detect related words (simple heuristic: change of prefix)
PREFIX_PAIRS = [
    ("a", "i"),     # avaru → ivaru
    ("a", "yA"),    # avaru → yAru
    ("a", "e"),     # avanu → evanu
    ("ma", "na"),   # magu → nagu
    ("hu", "ku"),   # huduga → kuduga (hypothetical)
    ("ba", "ha"),   # baruV → haruV (hypothetical)
]

# Additional suffix transformations for verb conjugations
VERB_SUFFIX_PATTERNS = [
    ("u", "a"),     # baruV → baraV
    ("u", "i"),     # baruV → bariV
    ("a", "i"),     # kala → kali
    ("V", "VV"),    # hoVru → hoVVru
]

# ==============================================================


class ParadigmGenerator:
    """Main class for paradigm generation and management"""
    
    def __init__(self, excel_path: str = EXCEL_PATH):
        """Initialize the paradigm generator with Excel file path"""
        self.excel_path = excel_path
        self.base_paradigms: Dict[str, Dict[str, str]] = {}
        self.all_paradigms: Dict[str, Dict[str, str]] = {}
        self.all_inflected_forms: Set[str] = set()
        self.related_map: Dict[str, List[str]] = defaultdict(list)
        self.stats = {
            'base_count': 0,
            'derived_count': 0,
            'total_count': 0,
            'total_inflected_forms': 0,
            'rules_applied': 0
        }
    
    def load_base_paradigms(self) -> Dict[str, Dict[str, str]]:
        """Load base paradigms from Excel into a dictionary
        If a word appears multiple times, merge all its paradigm forms
        Uses pickle cache for 100x faster loading"""
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"Excel file not found: {self.excel_path}")

        # Check if we have a cached pickle file that's newer than the Excel
        cache_path = CACHE_PATH
        use_cache = False
        
        if os.path.exists(cache_path):
            cache_mtime = os.path.getmtime(cache_path)
            excel_mtime = os.path.getmtime(self.excel_path)
            if cache_mtime >= excel_mtime:
                use_cache = True
        
        # Load from cache if available and up-to-date
        if use_cache:
            print(f"⚡ Loading paradigms from cache: {cache_path}")
            try:
                with open(cache_path, 'rb') as f:
                    paradigms = pickle.load(f)
                self.base_paradigms = paradigms
                self.stats['base_count'] = len(paradigms)
                print(f"✅ Loaded {len(paradigms):,} unique base paradigms from cache (FAST!)")
                return paradigms
            except Exception as e:
                print(f"⚠️  Cache load failed ({e}), falling back to Excel...")
                use_cache = False
        
        # Load from Excel (slow path)
        print(f"📖 Loading paradigms from: {self.excel_path}")
        df = pd.read_excel(self.excel_path)
        paradigms = {}

        # Skip the header row (index 0 which contains "Pradigms")
        # Start from row 1 onwards
        skipped = 0
        total_rows = 0
        
        for idx in range(1, len(df)):  # Start from row 1, skip row 0
            row = df.iloc[idx]
            total_rows += 1
            
            # Get the base word from the second column (NP1)
            base_word_raw = row.iloc[1]
            
            # Skip if base_word is invalid
            if pd.isna(base_word_raw):
                skipped += 1
                continue
                
            base_word = str(base_word_raw).strip().lower()
            if not base_word or base_word == "nan" or base_word == "":
                skipped += 1
                continue
            
            # Extract all paradigm forms from all columns (skip Sl No and base word column)
            paradigm_forms = {}
            for col_idx in range(2, len(df.columns)):  # Start from 3rd column (index 2)
                col_name = df.columns[col_idx]
                value = row.iloc[col_idx]
                if pd.notna(value):
                    val_str = str(value).strip()
                    if val_str and val_str.lower() != "nan":
                        paradigm_forms[col_name] = val_str
            
            if paradigm_forms:  # Only add if there are actual paradigm forms
                # If word already exists, MERGE the paradigms (don't overwrite!)
                if base_word in paradigms:
                    paradigms[base_word].update(paradigm_forms)
                else:
                    paradigms[base_word] = paradigm_forms

        self.base_paradigms = paradigms
        self.stats['base_count'] = len(paradigms)
        self.stats['total_rows_processed'] = total_rows
        print(f"✅ Loaded {len(paradigms):,} unique base paradigms from {total_rows:,} rows ({skipped} skipped).")
        
        # Save to cache for next time (super fast loading!)
        try:
            print(f"💾 Saving cache to: {cache_path}")
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'wb') as f:
                pickle.dump(paradigms, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"✅ Cache saved! Next load will be 100x faster.")
        except Exception as e:
            print(f"⚠️  Failed to save cache: {e}")
        
        return paradigms

    def find_related_words(self, base_words: List[str]) -> Dict[str, List[str]]:
        """
        Build a related-word mapping dynamically using prefix rules.
        E.g., avaru → ivaru, yAru
        """
        related_map = defaultdict(list)
        
        for base in base_words:
            for (src, tgt) in PREFIX_PAIRS:
                if base.startswith(src):
                    # Generate derived word by replacing prefix
                    derived = re.sub(f"^{src}", tgt, base)
                    if derived != base:  # Don't add self-references
                        related_map[base].append(derived)
                        self.stats['rules_applied'] += 1
        
        self.related_map = dict(related_map)
        print(f"🔗 Found {len(related_map)} base words with {sum(len(v) for v in related_map.values())} derived forms")
        return dict(related_map)

    def generate_word_paradigm(
        self, 
        word: str, 
        base_word: str, 
        base_paradigm: Dict[str, str]
    ) -> Dict[str, str]:
        """Generate paradigm for derived word based on its base word paradigm."""
        # Compute difference (prefix replacement)
        prefix_pattern = None
        replacement = None
        
        for (src, tgt) in PREFIX_PAIRS:
            if word.startswith(tgt) and base_word.startswith(src):
                prefix_pattern = re.compile(f"^{src}")
                replacement = tgt
                break
        
        # If no prefix pattern found, try to infer from the words
        if not prefix_pattern:
            # Find common prefix length
            min_len = min(len(word), len(base_word))
            common_len = 0
            for i in range(min_len):
                if word[i] == base_word[i]:
                    common_len = i + 1
                else:
                    break
            
            if common_len > 0 and common_len < min_len:
                # Words differ after common prefix
                old_prefix = base_word[:common_len + 1]
                new_prefix = word[:len(word) - len(base_word) + len(old_prefix)]
                prefix_pattern = re.compile(f"^{re.escape(old_prefix)}")
                replacement = new_prefix

        # Copy base paradigm and replace prefix in all forms
        new_paradigm = {}
        for key, val in base_paradigm.items():
            if isinstance(val, str):
                if prefix_pattern and replacement:
                    new_form = prefix_pattern.sub(replacement, val)
                    new_paradigm[key] = new_form
                else:
                    new_paradigm[key] = val  # fallback (no prefix change)
        
        return new_paradigm

    def initialize_paradigms(self) -> Dict[str, Dict[str, str]]:
        """Main startup function that prepares all paradigms in memory."""
        print("\n" + "=" * 70)
        print("🚀 KANNADA PARADIGM AUTO-GENERATOR")
        print("=" * 70)
        
        # Step 1: Load base paradigms from Excel
        self.load_base_paradigms()
        
        # Step 2: Find related words (for prefix transformations)
        base_words = list(self.base_paradigms.keys())
        self.find_related_words(base_words)
        
        # Step 3: Add base paradigms AND all their inflected forms
        print("\n📝 Extracting all paradigm forms...")
        all_inflected_forms = set()
        
        for base_word, forms in self.base_paradigms.items():
            self.all_paradigms[base_word] = forms
            # Add ALL inflected forms from this paradigm
            for form_name, form_value in forms.items():
                if form_value and form_value.strip():
                    all_inflected_forms.add(form_value.strip().lower())

        # Step 4: Generate derived paradigms (prefix transformations)
        derived_count = 0
        for base_word, related_words in self.related_map.items():
            for derived in related_words:
                if derived not in self.all_paradigms:  # Avoid overwriting existing paradigms
                    derived_paradigm = self.generate_word_paradigm(
                        derived, 
                        base_word, 
                        self.base_paradigms[base_word]
                    )
                    self.all_paradigms[derived] = derived_paradigm
                    derived_count += 1
                    
                    # Add all inflected forms from derived paradigm too
                    for form_name, form_value in derived_paradigm.items():
                        if form_value and form_value.strip():
                            all_inflected_forms.add(form_value.strip().lower())

        self.stats['derived_count'] = derived_count
        self.stats['total_count'] = len(self.all_paradigms)
        self.stats['total_inflected_forms'] = len(all_inflected_forms)
        
        # Store all inflected forms for easy lookup
        self.all_inflected_forms = all_inflected_forms
        
        print(f"\n📊 GENERATION SUMMARY:")
        print(f"   Base paradigms: {self.stats['base_count']:,}")
        print(f"   Derived paradigms: {self.stats['derived_count']:,}")
        print(f"   Total paradigms in memory: {self.stats['total_count']:,}")
        print(f"   Total inflected forms: {self.stats['total_inflected_forms']:,}")
        print(f"   Transformation rules applied: {self.stats['rules_applied']:,}")
        print("=" * 70)
        
        return self.all_paradigms

    def get_paradigm(self, word: str) -> Dict[str, str]:
        """Get paradigm forms for a word (instant O(1) lookup)"""
        return self.all_paradigms.get(word, {})
    
    def has_paradigm(self, word: str) -> bool:
        """Check if a word has a paradigm"""
        return word in self.all_paradigms
    
    def get_all_forms(self, word: str) -> Set[str]:
        """Get all inflected forms of a word"""
        paradigm = self.get_paradigm(word)
        if not paradigm:
            return set()
        return set(paradigm.values())
    
    def search_paradigms(self, pattern: str) -> Dict[str, Dict[str, str]]:
        """Search paradigms by regex pattern"""
        regex = re.compile(pattern, re.IGNORECASE)
        return {
            word: forms 
            for word, forms in self.all_paradigms.items() 
            if regex.search(word)
        }
    
    def get_stats(self) -> Dict[str, int]:
        """Get generation statistics"""
        return self.stats.copy()
    
    def export_to_dict(self) -> Dict[str, Dict[str, str]]:
        """Export all paradigms as a dictionary"""
        return self.all_paradigms.copy()
    
    def get_related_words(self, base_word: str) -> List[str]:
        """Get all derived words for a base word"""
        return self.related_map.get(base_word, [])


# ==============================================================
# CONVENIENCE FUNCTIONS
# ==============================================================

def initialize_paradigms(excel_path: str = EXCEL_PATH) -> Dict[str, Dict[str, str]]:
    """Convenience function to initialize paradigms"""
    generator = ParadigmGenerator(excel_path)
    return generator.initialize_paradigms()


def create_generator(excel_path: str = EXCEL_PATH) -> ParadigmGenerator:
    """Create and initialize a ParadigmGenerator instance"""
    generator = ParadigmGenerator(excel_path)
    generator.initialize_paradigms()
    return generator


# ==============================================================

if __name__ == "__main__":
    # Create generator and initialize
    generator = create_generator()
    
    # Example: test lookup
    print("\n" + "=" * 70)
    print("🧪 TESTING PARADIGM LOOKUPS")
    print("=" * 70)
    
    test_words = ["avaru", "ivaru", "yAru", "magu", "nagu"]
    
    for word in test_words:
        print(f"\n🔹 Word: '{word}'")
        if generator.has_paradigm(word):
            paradigm = generator.get_paradigm(word)
            print(f"   ✅ Paradigm found with {len(paradigm)} forms")
            
            # Show first 3 forms
            for i, (key, val) in enumerate(list(paradigm.items())[:3]):
                print(f"      {key}: {val}")
            
            if len(paradigm) > 3:
                print(f"      ... and {len(paradigm) - 3} more forms")
            
            # Show related words
            related = generator.get_related_words(word)
            if related:
                print(f"   🔗 Related forms: {', '.join(related)}")
        else:
            print(f"   ❌ No paradigm found")
    
    # Show statistics
    print("\n" + "=" * 70)
    print("📊 FINAL STATISTICS")
    print("=" * 70)
    stats = generator.get_stats()
    for key, value in stats.items():
        print(f"   {key.replace('_', ' ').title()}: {value:,}")
    
    print("\n✅ READY FOR USE!")
