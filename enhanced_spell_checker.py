#!/usr/bin/env python3
"""
SIMPLIFIED Kannada Spell Checker (No POS/Chunking)
Direct dictionary lookup with temporary pronoun paradigm expansion
plus noun/verb paradigm caching
"""
import sys
import os
import re
import pickle
from glob import glob
from collections import defaultdict
from typing import Dict, List, Tuple

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from kannada_wx_converter import kannada_to_wx, is_kannada_text, wx_to_kannada

PARADIGM_CACHE_VERSION = 1
PARADIGM_CACHE_FILE = os.path.join("paradigms", "all_words_cache.pkl")

# ❌ REMOVED: Paradigm generator imports (not needed with pre-generated paradigms)
# All paradigms are now pre-generated and stored in paradigms/all/ folder


class SimplifiedSpellChecker:
    """Simplified spell checker - dictionary lookup only"""

    def __init__(self, use_paradigm_generator: bool = False) -> None:
        """
        Initialize spell checker with pre-generated paradigms
        NOTE: use_paradigm_generator parameter is kept for backward compatibility but ignored
        """
        print("\n" + "=" * 70)
        print("Simplified Kannada Spell Checker")
        print("Dictionary Lookup + Pre-Generated Morphological Paradigms")
        print("=" * 70)

        self.tokenize_func = None
        self._reset_paradigm_structures()

        # 1️⃣ Load tokenizer and dictionary
        self.load_tokenizer()
        self.load_dictionary()

        # 2️⃣ All paradigm variants are already generated and stored in paradigms/all/ folder
        # No dynamic generation needed - all words loaded from paradigms/all/

        print(f"\n[ready] Total words loaded from paradigms/all/: {len(self.all_words):,}")
        print("[✅] Ready for spell checking with fast lookup!")

    def _reset_paradigm_structures(self) -> None:
        """Reset dictionary caches"""
        self.all_words: set[str] = set()
        # SPEED OPTIMIZATION: Index words by length for faster filtering
        self.words_by_length: Dict[int, set[str]] = defaultdict(set)

    def _add_word_to_dictionary(self, word: str) -> None:
        """Add word to dictionary with length indexing for fast lookups"""
        if word and word not in self.all_words:
            self.all_words.add(word)
            self.words_by_length[len(word)].add(word)

    def _load_dictionary_cache(self, directory_mtime: float) -> Tuple[bool, int]:
        """Load cached dictionary words if cache is fresh"""
        if not os.path.exists(PARADIGM_CACHE_FILE):
            return False, 0

        try:
            with open(PARADIGM_CACHE_FILE, "rb") as handle:
                data = pickle.load(handle)
        except Exception:
            return False, 0

        if not isinstance(data, dict):
            return False, 0

        if data.get("version") != PARADIGM_CACHE_VERSION:
            return False, 0

        if data.get("dir_mtime") != directory_mtime:
            return False, 0

        words = data.get("words")
        if not isinstance(words, list):
            return False, 0

        total_surfaces = int(data.get("surface_count", len(words)))
        for word in words:
            self._add_word_to_dictionary(str(word))

        return True, total_surfaces

    def _write_dictionary_cache(self, directory_mtime: float, total_surfaces: int) -> None:
        """Persist dictionary words for faster future loads"""
        cache_payload = {
            "version": PARADIGM_CACHE_VERSION,
            "dir_mtime": directory_mtime,
            "surface_count": int(total_surfaces),
            "words": list(self.all_words),
        }

        try:
            os.makedirs(os.path.dirname(PARADIGM_CACHE_FILE), exist_ok=True)
            with open(PARADIGM_CACHE_FILE, "wb") as handle:
                pickle.dump(cache_payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as exc:
            print(f"  [warn] Unable to write dictionary cache: {exc}")

    def load_tokenizer(self) -> None:
        """Load tokenizer if available"""
        print("\n[1/4] Loading tokenizer ...")
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), "Token"))
            from tokenizer_for_indian_languages_on_files import tokenize_sentence

            self.tokenize_func = tokenize_sentence
            print("  [ok] Tokenizer loaded")
        except Exception:
            print("  [warn] Falling back to regex tokenizer")
            self.tokenize_func = None
    
    # ❌ REMOVED: _initialize_paradigm_generator() - Not needed with pre-generated paradigms
    # ❌ REMOVED: _initialize_morphological_paradigms() - Not needed with pre-generated paradigms

    def load_dictionary(self) -> None:
        """Load base dictionary and pre-generated paradigms from paradigms/all/ folder"""
        print(f"\n[2/3] Loading dictionary from paradigms/all/ ...")

        self._reset_paradigm_structures()

        total_surfaces = 0
        cache_hit = False
        directory_mtime = 0.0
        all_dir = os.path.join("paradigms", "all")

        if os.path.isdir(all_dir):
            try:
                directory_mtime = os.path.getmtime(all_dir)
            except OSError:
                directory_mtime = 0.0

            if directory_mtime:
                cache_hit, total_surfaces = self._load_dictionary_cache(directory_mtime)

        if cache_hit:
            print(f"  [dict] Loaded {len(self.all_words):,} words from cache (surface forms: {total_surfaces:,})")
        else:
            total_surfaces, directory_mtime = self._scan_paradigm_files()
            print(f"  [dict] Loaded {total_surfaces:,} surface forms from paradigms/all/")
            if directory_mtime:
                self._write_dictionary_cache(directory_mtime, total_surfaces)

        dict_path = "extended_dictionary.pkl"
        if os.path.exists(dict_path):
            with open(dict_path, "rb") as handle:
                extended = pickle.load(handle)
                words_to_add = []
                if isinstance(extended, set):
                    words_to_add = list(extended)
                elif isinstance(extended, dict):
                    for words in extended.values():
                        if isinstance(words, set):
                            words_to_add.extend(list(words))
                        elif isinstance(words, dict):
                            words_to_add.extend(list(words.keys()))
                
                # Build length index while loading dictionary
                for word in words_to_add:
                    self._add_word_to_dictionary(word)
            print("  [dict] Loaded extended dictionary with length indexing")

        print(f"\n  [total] {len(self.all_words):,} words")

    def _scan_paradigm_files(self) -> Tuple[int, float]:
        """Load all surface forms from paradigms/all/ into the dictionary"""
        all_dir = os.path.join("paradigms", "all")
        if not os.path.isdir(all_dir):
            return 0, 0.0

        dir_mtime = os.path.getmtime(all_dir)

        total_surfaces = 0
        for root_dir, _, files in os.walk(all_dir):
            for name in files:
                if not name.endswith(".txt"):
                    continue
                file_path = os.path.join(root_dir, name)
                with open(file_path, "r", encoding="utf-8") as handle:
                    for raw_line in handle:
                        stripped = raw_line.strip()
                        if not stripped:
                            continue
                        surface = stripped.split(maxsplit=1)[0]
                        self._add_word_to_dictionary(surface)
                        total_surfaces += 1

        return total_surfaces, dir_mtime

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text using configured tokenizer or fallback"""
        if self.tokenize_func:
            try:
                return self.tokenize_func(text, lang="kn")
            except Exception:
                pass
        return re.findall(r"[\u0C80-\u0CFF]+|[a-zA-Z]+", text)

    def edit_distance(self, s1: str, s2: str, max_dist: int = 3) -> int:
        """Levenshtein distance with early exit optimization"""
        if len(s1) < len(s2):
            return self.edit_distance(s2, s1, max_dist)
        
        # Early exit: if length difference > max_dist, distance will exceed max_dist
        len_diff = len(s1) - len(s2)
        if len_diff > max_dist:
            return len_diff
        
        if not s2:
            return len(s1)

        previous = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current = [i + 1]
            for j, c2 in enumerate(s2):
                current.append(min(previous[j + 1] + 1, current[j] + 1, previous[j] + (c1 != c2)))
            
            # Early exit: if all values in current row exceed max_dist, stop
            if all(val > max_dist for val in current):
                return max_dist + 1
            
            previous = current
        return previous[-1]

    def get_suggestions(self, word: str, max_results: int = 10) -> List[str]:
        """Get edit-distance suggestions for a word (ULTRA-OPTIMIZED with length indexing)"""
        if not word:
            return []
        
        word_len = len(word)
        word_lower = word.lower()
        
        # OPTIMIZATION 1: Use length index to get only relevant candidates (FAST!)
        # Instead of iterating 123k words, we only check a subset with similar lengths
        length_delta = 2 if word_len < 6 else 1
        candidates_by_length = []
        for length in range(max(1, word_len - length_delta), word_len + length_delta + 1):
            candidates_by_length.extend(self.words_by_length.get(length, []))
        
        # Determine prefix length requirement (longer words require longer shared prefix)
        prefix_len = 1
        if word_len >= 5:
            prefix_len = 2
        if word_len >= 8:
            prefix_len = 3

        # OPTIMIZATION 2: Prefix filtering for better accuracy
        candidates_filtered = []
        for candidate in candidates_by_length:
            candidate_lower = candidate.lower()

            if prefix_len > 0 and len(candidate_lower) >= prefix_len:
                if candidate_lower[:prefix_len] != word_lower[:prefix_len]:
                    continue

            # OPTIMIZATION 3: Prefix matching (if first 2 chars match, more likely to be similar)
            if word_len >= 3 and len(candidate) >= 3:
                # If first char doesn't match AND length is same, check more carefully
                if candidate_lower[:1] != word_lower[:1] and len(candidate) == word_len:
                    # Still include but with lower priority by checking first 2 chars
                    if word_len >= 4 and len(candidate) >= 4 and candidate_lower[:2] != word_lower[:2]:
                        continue
            
            candidates_filtered.append(candidate)
        
        # OPTIMIZATION 4: Calculate edit distance only for pre-filtered candidates
        # Use max_dist=2 for early exit in edit_distance
        candidates_with_dist = [
            (candidate, self.edit_distance(word, candidate, max_dist=2))
            for candidate in candidates_filtered
        ]
        
        # OPTIMIZATION 5: Filter by distance <= 2 and sort
        filtered = [item for item in candidates_with_dist if item[1] <= 2]
        filtered.sort(key=lambda item: (item[1], item[0]))
        
        return [candidate for candidate, _ in filtered[:max_results]]

    def check_text(self, text: str) -> List[Dict[str, List[str]]]:
        """Check text for spelling errors"""
        print(f"\n{'=' * 70}")
        print(f"Processing: {text[:50]}...")
        print(f"{'=' * 70}")

        print("\n[step 0] Tokenizing original text ...")
        tokens = self.tokenize(text)
        print(f"  tokens: {tokens}")

        print("\n[step 1] Normalizing tokens to WX ...")
        token_infos: List[tuple[str, str, bool]] = []
        normalized_tokens: List[str] = []
        for token in tokens:
            token_is_kannada = is_kannada_text(token)
            normalized = kannada_to_wx(token) if token_is_kannada else token
            token_infos.append((token, normalized, token_is_kannada))
            normalized_tokens.append(normalized)
        print(f"  normalized: {normalized_tokens}")

        print("\n[step 2] Checking ...")
        errors: List[Dict[str, List[str]]] = []

        for original, normalized, token_is_kannada in token_infos:
            if len(normalized) <= 1:
                continue

            if normalized in self.all_words:
                if original != normalized:
                    print(f"  [ok] {original} ({normalized}): in dictionary")
                else:
                    print(f"  [ok] {original}: in dictionary")
                continue

            suggestions = self.get_suggestions(normalized)
            display_suggestions = (
                [wx_to_kannada(item) for item in suggestions] if token_is_kannada else suggestions
            )

            deduped: List[str] = []
            seen: set[str] = set()
            for suggestion in display_suggestions:
                if suggestion not in seen:
                    deduped.append(suggestion)
                    seen.add(suggestion)

            display = ", ".join(deduped[:5]) if deduped else "No suggestions"
            print(f"  [miss] {original}: {display}")
            errors.append({"word": original, "suggestions": deduped})

        return errors


# Alias for backward compatibility
EnhancedSpellChecker = SimplifiedSpellChecker


if __name__ == "__main__":
    checker = SimplifiedSpellChecker()

    print(f"\n[3/3] Sample checks ...")
    tests = [
        "nAnu bengalUralli iruwweVneV",
        "ನಾನು ಬೆಂಗಳೂರಲ್ಲಿ ಇರುತ್ತೇನೆ",
        "avarannu ivarannu yArannu",
    ]

    for sample in tests:
        result = checker.check_text(sample)
        status = "[ok] No errors" if not result else f"[issues] {len(result)} error(s)"
        print(f"\n{status}")


