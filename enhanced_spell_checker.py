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
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from kannada_wx_converter import kannada_to_wx, is_kannada_text, wx_to_kannada


PRONOUN_VARIANT_GROUPS = [
    {
        "base_root": "avaru",
        "base_prefix": "avar",
        "variants": [
            {"root": "avaru", "prefix": "avar"},
            {"root": "ivaru", "prefix": "ivar"},
            {"root": "yAru", "prefix": "yAr"},
            {"root": "evaru", "prefix": "evar"},
        ],
    },
    {
        "base_root": "avanu",
        "base_prefix": "avan",
        "variants": [
            {"root": "avanu", "prefix": "avan"},
            {"root": "ivanu", "prefix": "ivan"},
            {"root": "yAvanu", "prefix": "yAvan"},
            {"root": "evanu", "prefix": "evan"},
        ],
    },
    {
        "base_root": "avalYu",
        "base_prefix": "avalY",
        "variants": [
            {"root": "avalYu", "prefix": "avalY"},
            {"root": "ivalYu", "prefix": "ivalY"},
            {"root": "yAvalYu", "prefix": "yAvalY"},
            {"root": "evalYu", "prefix": "evalY"},
        ],
    },
    {
        "base_root": "avu",
        "base_prefix": "avu",
        "variants": [
            {"root": "avu", "prefix": "avu"},
            {"root": "ivu", "prefix": "ivu"},
            {"root": "yAvu", "prefix": "yAvu"},
            {"root": "evu", "prefix": "evu"},
        ],
    },
    {
        "base_root": "axu",
        "base_prefix": "ax",
        "variants": [
            {"root": "axu", "prefix": "ax"},
            {"root": "ixu", "prefix": "ix"},
            {"root": "yAvuxu", "prefix": "yAvux"},
            {"root": "exu", "prefix": "ex"},
        ],
    },
]

PRONOUN_ROOTS = {
    variant["root"]
    for group in PRONOUN_VARIANT_GROUPS
    for variant in group["variants"]
}
PRONOUN_ROOTS.update(group["base_root"] for group in PRONOUN_VARIANT_GROUPS)

NOUN_VARIANT_GROUPS = [
    {
        "label": "akka_avva",
        "base_root": "akka",
        "variants": [
            {"root": "avva"},
        ],
    },
]

PARADIGM_HEADER_PATTERN = re.compile(r"(?P<root>[A-Za-z]+)\((?P<tag>[A-Z]+\d*)\)")
PARADIGM_FILENAME_PATTERN = re.compile(r"^(?P<root>.*?)(?P<tag>[A-Z]+\d*)$")


class SimplifiedSpellChecker:
    """Simplified spell checker - dictionary lookup only"""

    def __init__(self) -> None:
        print("\n" + "=" * 70)
        print("Simplified Kannada Spell Checker")
        print("Dictionary Lookup Only (No POS/Chunking)")
        print("=" * 70)

        self.tokenize_func = None
        self._reset_paradigm_structures()

        self.load_tokenizer()
        self.load_dictionary()

        print("\n[ready] Ready!")

    def _reset_paradigm_structures(self) -> None:
        """Reset paradigm-related caches"""
        self.all_words: set[str] = set()
        self.generated_variants: Dict[str, set[str]] = defaultdict(set)
        self.pronoun_suffix_map: Dict[str, set[str]] = defaultdict(set)
        self.pronoun_paradigms: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.word_to_paradigms: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._paradigm_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.paradigm_words: set[str] = set()
        self.category_paradigms = self._init_category_paradigm_store()
        self.category_suffixes = self._init_category_suffix_store()
        self.root_categories: Dict[str, str] = {}

    @staticmethod
    def _init_category_paradigm_store() -> Dict[str, defaultdict]:
        return {
            "pronoun": defaultdict(list),
            "noun": defaultdict(list),
            "verb": defaultdict(list),
            "other": defaultdict(list),
        }

    @staticmethod
    def _init_category_suffix_store() -> Dict[str, defaultdict]:
        return {
            "pronoun": defaultdict(set),
            "noun": defaultdict(set),
            "verb": defaultdict(set),
            "other": defaultdict(set),
        }

    def load_tokenizer(self) -> None:
        """Load tokenizer if available"""
        print("\n[1/3] Loading tokenizer ...")
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), "Token"))
            from tokenizer_for_indian_languages_on_files import tokenize_sentence

            self.tokenize_func = tokenize_sentence
            print("  [ok] Tokenizer loaded")
        except Exception:
            print("  [warn] Falling back to regex tokenizer")
            self.tokenize_func = None

    def load_dictionary(self) -> None:
        """Load base dictionary and build temporary pronoun variants"""
        print("\n[2/3] Loading dictionary ...")

        self._reset_paradigm_structures()

        paradigm_summary = self._scan_paradigm_files()
        if paradigm_summary:
            ordered = [
                f"{name}:{paradigm_summary.get(name, 0)}"
                for name in ("pronoun", "noun", "verb", "other")
            ]
            print(f"  [dict] Cached paradigms -> {' | '.join(ordered)}")

        dict_path = "extended_dictionary.pkl"
        if os.path.exists(dict_path):
            with open(dict_path, "rb") as handle:
                extended = pickle.load(handle)
                if isinstance(extended, set):
                    self.all_words.update(extended)
                elif isinstance(extended, dict):
                    for words in extended.values():
                        if isinstance(words, set):
                            self.all_words.update(words)
                        elif isinstance(words, dict):
                            self.all_words.update(words.keys())
            print("  [dict] Loaded extended dictionary")

        added_variants = self._augment_pronoun_variants()
        if added_variants:
            print(f"  [variants] Added {added_variants:,} pronoun variants (temporary)")

        added_noun_variants = self._augment_noun_variants()
        if added_noun_variants:
            print(f"  [variants] Added {added_noun_variants:,} noun variants (temporary)")

        print(f"  [dict] Paradigm words (with temp): {len(self.paradigm_words):,}")

        print(f"\n  [total] {len(self.all_words):,} words")

    def _scan_paradigm_files(self) -> Dict[str, int]:
        """Read paradigm files into memory and categorize by word class"""
        summary_sets: Dict[str, set[str]] = defaultdict(set)
        paradigm_dir = os.path.join("paradigms", "all")
        if not os.path.exists(paradigm_dir):
            return {}

        for file_path in glob(os.path.join(paradigm_dir, "*.txt")):
            file_name = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line:
                        continue

                    parts = line.split(maxsplit=1)
                    surface = parts[0]
                    rule = parts[1] if len(parts) > 1 else ""

                    root, tag = self._extract_root_and_tag(rule, file_name)
                    category = self._resolve_category(root, tag)

                    record = {
                        "surface": surface,
                        "rule": rule,
                        "source_file": file_name,
                        "tag": tag,
                        "category": category,
                    }

                    self.all_words.add(surface)
                    self.paradigm_words.add(surface)
                    self._paradigm_cache.setdefault(root, []).append(record)
                    self.category_paradigms[category][root].append(record)
                    self.root_categories.setdefault(root, category)

                    if surface.startswith(root):
                        suffix = surface[len(root) :]
                        if suffix:
                            self.category_suffixes[category][root].add(suffix)

                    summary_sets[category].add(root)

        return {key: len(summary_sets.get(key, set())) for key in self.category_paradigms.keys()}

    def _extract_root_and_tag(self, rule: str, file_name: str) -> tuple[str, str]:
        """Derive root and tag information from a paradigm line or file name"""
        match = PARADIGM_HEADER_PATTERN.search(rule)
        if match:
            return match.group("root"), match.group("tag")

        stem = file_name.split("_", 1)[0]
        fallback = PARADIGM_FILENAME_PATTERN.match(stem)
        if fallback:
            return fallback.group("root"), fallback.group("tag")

        return stem, ""

    def _resolve_category(self, root: str, tag: str) -> str:
        """Map paradigm tag information to a coarse word class"""
        if root in PRONOUN_ROOTS or "PN" in tag:
            return "pronoun"

        tag_upper = tag.upper()
        if tag_upper.startswith("V") and not tag_upper.startswith("VN") and "PN" not in tag_upper:
            return "verb"

        if tag_upper.startswith("N") or tag_upper.startswith("VN") or tag_upper.startswith("EN") or tag_upper.startswith("IN"):
            return "noun"

        return self.root_categories.get(root, "other") or "other"

    def get_paradigm_records(self, root: str, category: Optional[str] = None) -> List[Dict[str, str]]:
        """Return cached paradigm records for a root, optionally restricted by category"""
        if category:
            return self.category_paradigms.get(category, {}).get(root, [])

        for group in ("pronoun", "noun", "verb", "other"):
            if root in self.category_paradigms[group]:
                return self.category_paradigms[group][root]
        return []

    def create_paradigm_variants(
        self,
        base_root: str,
        variant_root: str,
        category: Optional[str] = None,
        store: bool = True,
        extra_metadata: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate paradigm variants for any category and optionally store them"""
        base_records = self._load_paradigm_records(base_root)
        if not base_records:
            return []

        resolved_category = category or self.root_categories.get(base_root, "other") or "other"
        created: List[Dict[str, Any]] = []
        seen_surfaces: set[str] = set()
        metadata = extra_metadata or {}
        existing_surfaces: set[str] = set()

        if store:
            existing_surfaces = {
                entry["surface"]
                for entry in self.category_paradigms[resolved_category][variant_root]
            }

        for record in base_records:
            rule = record.get("rule", "")
            surface = self._apply_paradigm_rule(base_root, variant_root, rule)
            if not surface or surface in seen_surfaces:
                continue

            seen_surfaces.add(surface)
            was_present = surface in self.all_words
            info: Dict[str, Any] = {
                "surface": surface,
                "original_surface": record.get("surface", ""),
                "rule": rule,
                "source_file": record.get("source_file", ""),
                "base_root": base_root,
                "variant_root": variant_root,
                "category": resolved_category,
                "tag": record.get("tag", ""),
                "is_new": not was_present,
            }

            if surface.startswith(variant_root):
                suffix = surface[len(variant_root) :]
                if suffix:
                    info["suffix"] = suffix

            if metadata:
                info.update(metadata)

            if store:
                if not was_present:
                    self.all_words.add(surface)
                self.paradigm_words.add(surface)

                if surface not in existing_surfaces:
                    self.category_paradigms[resolved_category][variant_root].append(info)  # type: ignore[arg-type]
                    existing_surfaces.add(surface)

                self.root_categories.setdefault(variant_root, resolved_category)

                suffix_value = info.get("suffix")
                if suffix_value:
                    self.category_suffixes[resolved_category][variant_root].add(suffix_value)  # type: ignore[arg-type]

                word_records = self.word_to_paradigms[surface]
                if not any(
                    item.get("base_root") == base_root and item.get("variant_root") == variant_root
                    for item in word_records
                ):
                    word_records.append(info)

            created.append(info)

        return created

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text using configured tokenizer or fallback"""
        if self.tokenize_func:
            try:
                return self.tokenize_func(text, lang="kn")
            except Exception:
                pass
        return re.findall(r"[\u0C80-\u0CFF]+|[a-zA-Z]+", text)

    def edit_distance(self, s1: str, s2: str) -> int:
        """Levenshtein distance"""
        if len(s1) < len(s2):
            return self.edit_distance(s2, s1)
        if not s2:
            return len(s1)

        previous = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current = [i + 1]
            for j, c2 in enumerate(s2):
                current.append(min(previous[j + 1] + 1, current[j] + 1, previous[j] + (c1 != c2)))
            previous = current
        return previous[-1]

    def get_suggestions(self, word: str, max_results: int = 10) -> List[str]:
        """Get edit-distance suggestions for a word"""
        candidates = [(candidate, self.edit_distance(word, candidate)) for candidate in self.all_words]
        filtered = [item for item in candidates if item[1] <= 2]
        filtered.sort(key=lambda item: (item[1], item[0]))
        return [candidate for candidate, _ in filtered[:max_results]]

    def get_pronoun_paradigms(self, word: str) -> List[Dict[str, Any]]:
        """Return cached paradigm entries for a generated pronoun surface"""
        return self.word_to_paradigms.get(word, [])

    def check_text(self, text: str) -> List[Dict[str, List[str]]]:
        """Check text for spelling errors"""
        print(f"\n{'=' * 70}")
        print(f"Processing: {text[:50]}...")
        print(f"{'=' * 70}")

        was_kannada = is_kannada_text(text)
        if was_kannada:
            print("\n[step 0] Converting Kannada to WX ...")
            text = kannada_to_wx(text)
            print(f"  wx: {text}")

        print("\n[step 1] Tokenizing ...")
        tokens = self.tokenize(text)
        print(f"  tokens: {tokens}")

        print("\n[step 2] Checking ...")
        errors: List[Dict[str, List[str]]] = []

        for word in tokens:
            if len(word) <= 1:
                continue

            if word in self.all_words:
                print(f"  [ok] {word}: in dictionary")
                continue

            suggestions = self.get_suggestions(word)
            if was_kannada:
                suggestions = [wx_to_kannada(item) for item in suggestions]

            display = ", ".join(suggestions[:5]) if suggestions else "No suggestions"
            print(f"  [miss] {word}: {display}")
            errors.append({"word": word, "suggestions": suggestions})

        return errors

    def _augment_pronoun_variants(self) -> int:
        """Generate temporary pronoun variants and cache paradigm entries"""
        new_words: set[str] = set()

        for group in PRONOUN_VARIANT_GROUPS:
            base_root = group["base_root"]
            if not self._load_paradigm_records(base_root):
                continue

            for variant in group["variants"]:
                variant_root = variant["root"]
                variant_prefix = variant["prefix"]

                infos = self.create_paradigm_variants(
                    base_root,
                    variant_root,
                    category="pronoun",
                    store=True,
                    extra_metadata={"variant_prefix": variant_prefix},
                )

                existing = {entry["surface"] for entry in self.pronoun_paradigms[variant_root]}

                for info in infos:
                    surface = info["surface"]
                    if info.get("is_new"):
                        new_words.add(surface)

                    original = info.get("original_surface")
                    if isinstance(original, str) and original:
                        self.generated_variants[surface].add(original)

                    if surface.startswith(variant_prefix):
                        suffix = surface[len(variant_prefix) :]
                        if suffix:
                            self.pronoun_suffix_map[variant_prefix].add(suffix)

                    if surface not in existing:
                        self.pronoun_paradigms[variant_root].append(info)
                        existing.add(surface)

        return len(new_words)

    def _augment_noun_variants(self) -> int:
        """Generate temporary noun variants defined in NOUN_VARIANT_GROUPS"""
        new_words: set[str] = set()

        for group in NOUN_VARIANT_GROUPS:
            base_root = group["base_root"]
            if not self._load_paradigm_records(base_root):
                continue

            label = group.get("label", base_root)

            for variant in group.get("variants", []):
                variant_root = variant.get("root")
                if not variant_root:
                    continue

                infos = self.create_paradigm_variants(
                    base_root,
                    variant_root,
                    category="noun",
                    store=True,
                    extra_metadata={
                        "variant_group": label,
                        "variant_type": variant.get("type", "noun_variant"),
                    },
                )

                for info in infos:
                    if info.get("is_new"):
                        new_words.add(info["surface"])

        return len(new_words)

    def _load_paradigm_records(self, base_root: str) -> List[Dict[str, str]]:
        """Load paradigm lines for a base root with caching"""
        if base_root in self._paradigm_cache:
            return self._paradigm_cache[base_root]

        records: List[Dict[str, str]] = []
        pattern = os.path.join("paradigms", "all", f"{base_root}*.txt")
        for file_path in glob(pattern):
            with open(file_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    parts = line.strip().split(maxsplit=1)
                    if not parts:
                        continue
                    surface = parts[0]
                    rule = parts[1] if len(parts) > 1 else ""
                    records.append({
                        "surface": surface,
                        "rule": rule,
                        "source_file": os.path.basename(file_path),
                    })

        self._paradigm_cache[base_root] = records
        return records

    @staticmethod
    def _apply_paradigm_rule(base_root: str, variant_root: str, rule: str) -> str:
        """Apply a paradigm rule to transform base_root forms into variant_root forms"""
        if not rule:
            return variant_root

        word = variant_root
        for segment in rule.split("+"):
            if "_" not in segment:
                continue

            left, right = segment.split("_", 1)

            if "#" in right:
                word = word + left
                continue

            if "_" in right:
                base_piece, feat = right.split("_", 1)
            else:
                base_piece, feat = right, ""

            if base_piece and word.endswith(base_piece):
                word = word[: -len(base_piece)] + left
            else:
                word = word + left

            if feat:
                parts = feat.split("_")
                if len(parts) >= 2:
                    add_piece, old_piece = parts[0], parts[1]
                    if old_piece and word.endswith(old_piece):
                        word = word[: -len(old_piece)] + add_piece
                    else:
                        word = word + add_piece

        return word


# Alias for backward compatibility
EnhancedSpellChecker = SimplifiedSpellChecker


if __name__ == "__main__":
    checker = SimplifiedSpellChecker()

    print("\n[3/3] Sample checks ...")
    tests = [
        "nAnu bengalUralli iruwweVneV",
        "ನಾನು ಬೆಂಗಳೂರಲ್ಲಿ ಇರುತ್ತೇನೆ",
        "avarannu ivarannu yArannu",
    ]

    for sample in tests:
        result = checker.check_text(sample)
        status = "[ok] No errors" if not result else f"[issues] {len(result)} error(s)"
        print(f"\n{status}")
