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

# Try to import paradigm generator (optional enhancement)
try:
    from paradigm_generator import ParadigmGenerator
    PARADIGM_GENERATOR_AVAILABLE = True
except ImportError:
    PARADIGM_GENERATOR_AVAILABLE = False
    ParadigmGenerator = None

# Try to import morphological paradigm logic (optional enhancement)
try:
    from paradigm_logic import initialize_paradigm_system, get_all_surface_forms
    MORPHOLOGICAL_PARADIGM_AVAILABLE = True
except ImportError:
    MORPHOLOGICAL_PARADIGM_AVAILABLE = False
    initialize_paradigm_system = None
    get_all_surface_forms = None


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

    def __init__(self, use_paradigm_generator: bool = True) -> None:
        print("\n" + "=" * 70)
        print("Simplified Kannada Spell Checker")
        print("Dictionary Lookup + Dynamic Morphological Paradigm Expansion")
        print("=" * 70)

        self.tokenize_func = None
        self._reset_paradigm_structures()
        
        # Paradigm generator (optional enhancement)
        self.paradigm_generator = None
        self.use_paradigm_generator = use_paradigm_generator and PARADIGM_GENERATOR_AVAILABLE
        
        # Morphological paradigm system (optional enhancement)
        self.morphological_paradigms = None
        self.use_morphological_paradigms = MORPHOLOGICAL_PARADIGM_AVAILABLE

        # 1️⃣ Load tokenizer and dictionary
        self.load_tokenizer()
        self.load_dictionary()
        
        # 2️⃣ Initialize optional paradigm systems if available
        if self.use_paradigm_generator:
            self._initialize_paradigm_generator()
        if self.use_morphological_paradigms:
            self._initialize_morphological_paradigms()

        # 3️⃣ Auto-generate morphological variants dynamically
        print("\n[+] Generating temporary noun paradigms dynamically ...")
        generated_noun_forms = 0
        noun_suffix_rules = ["+na#", "+alli#", "+ige#", "+inda#", "+vu#"]

        for root in list(self.all_words):
            # Process only WX transliterated (Latin) words
            if len(root) < 3 or not re.match(r"^[a-zA-Z]+$", root):
                continue

            for rule in noun_suffix_rules:
                new_form = self._apply_paradigm_rule(root, root, rule)
                if new_form not in self.all_words:
                    self.all_words.add(new_form)
                    self.paradigm_words.add(new_form)
                    generated_noun_forms += 1

        print(f"  [auto-paradigms] Added {generated_noun_forms:,} noun forms to dictionary.")

        print("\n[+] Generating temporary verb paradigms dynamically ...")
        generated_verb_forms = 0
        verb_suffix_rules = ["u_i#", "u_i_tAne#", "u_i_daru#", "u_i_vu#", "+uva#"]

        for root in list(self.all_words):
            if len(root) < 3 or not re.match(r"^[a-zA-Z]+$", root):
                continue

            for rule in verb_suffix_rules:
                new_form = self._apply_paradigm_rule(root, root, rule)
                if new_form not in self.all_words:
                    self.all_words.add(new_form)
                    self.paradigm_words.add(new_form)
                    generated_verb_forms += 1

        print(f"  [auto-paradigms] Added {generated_verb_forms:,} verb forms to dictionary.")

        # 4️⃣ Auto-generate full paradigms from paradigm files
        self.auto_generate_full_paradigms()

        print(f"\n[ready] Total words (with paradigms): {len(self.all_words):,}")
        print("[✅] Ready for spell checking and morphological lookup!")

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
        print("\n[1/4] Loading tokenizer ...")
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), "Token"))
            from tokenizer_for_indian_languages_on_files import tokenize_sentence

            self.tokenize_func = tokenize_sentence
            print("  [ok] Tokenizer loaded")
        except Exception:
            print("  [warn] Falling back to regex tokenizer")
            self.tokenize_func = None
    
    def _initialize_paradigm_generator(self) -> None:
        """Initialize paradigm generator for dynamic paradigm expansion"""
        print("\n[2/4] Initializing Paradigm Generator ...")
        try:
            self.paradigm_generator = ParadigmGenerator()
            all_paradigms = self.paradigm_generator.initialize_paradigms()
            
            # Add ALL inflected forms to dictionary (not just base words!)
            added_count = 0
            
            # Method 1: Add all inflected forms directly
            if hasattr(self.paradigm_generator, 'all_inflected_forms'):
                for form in self.paradigm_generator.all_inflected_forms:
                    if form and form not in self.all_words:
                        self.all_words.add(form)
                        added_count += 1
            else:
                # Fallback: Extract from paradigms
                for word, forms in all_paradigms.items():
                    # Add base word
                    if word not in self.all_words:
                        self.all_words.add(word)
                        added_count += 1
                    # Add all inflected forms
                    for form in forms.values():
                        if form and form not in self.all_words:
                            self.all_words.add(form)
                            added_count += 1
            
            print(f"  [paradigm-gen] Added {added_count:,} paradigm forms to dictionary")
            if hasattr(self.paradigm_generator, 'stats'):
                stats = self.paradigm_generator.stats
                if 'total_inflected_forms' in stats:
                    print(f"  [paradigm-gen] Total unique forms: {stats['total_inflected_forms']:,}")
            print("  [ok] Paradigm generator ready")
        except Exception as e:
            print(f"  [warn] Paradigm generator failed: {e}")
            print("  [info] Continuing with standard paradigm loading")
            import traceback
            traceback.print_exc()
            self.paradigm_generator = None
            self.use_paradigm_generator = False
    
    def _initialize_morphological_paradigms(self) -> None:
        """Initialize morphological paradigm system for dynamic word form generation"""
        print("\n[3/4] Initializing Morphological Paradigm System ...")
        try:
            # Initialize the paradigm system with default configuration
            self.morphological_paradigms = initialize_paradigm_system()
            
            # Extract all surface forms and add to dictionary
            if self.morphological_paradigms:
                surface_forms = get_all_surface_forms(self.morphological_paradigms)
                added_count = 0
                for form in surface_forms:
                    if form and form not in self.all_words:
                        self.all_words.add(form)
                        added_count += 1
                
                print(f"  [morpho-paradigm] Added {added_count:,} morphological forms to dictionary")
                print(f"  [morpho-paradigm] Total variant paradigms: {len(self.morphological_paradigms):,}")
            print("  [ok] Morphological paradigm system ready")
        except Exception as e:
            print(f"  [warn] Morphological paradigm system failed: {e}")
            print("  [info] Continuing without morphological paradigm expansion")
            import traceback
            traceback.print_exc()
            self.morphological_paradigms = None
            self.use_morphological_paradigms = False

    def load_dictionary(self) -> None:
        """Load base dictionary and build temporary pronoun variants"""
        step_num = "3/4" if self.use_paradigm_generator else "2/3"
        print(f"\n[{step_num}] Loading dictionary ...")

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
        category_dirs = {
            "verb": os.path.join("paradigms", "Verb"),
            "noun": os.path.join("paradigms", "Noun"),
            "pronoun": os.path.join("paradigms", "Pronouns"),
        }

        # Fallback directory for legacy structure
        legacy_dir = os.path.join("paradigms", "all")

        def _iter_files(directory: str) -> List[str]:
            if not os.path.isdir(directory):
                return []
            # Support nested folders per paradigm
            pattern = os.path.join(directory, "**", "*.txt")
            return glob(pattern, recursive=True)

        # Load category-specific paradigms first
        for category, dir_path in category_dirs.items():
            for file_path in _iter_files(dir_path):
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
                        resolved_category = category

                        record = {
                            "surface": surface,
                            "rule": rule,
                            "source_file": file_name,
                            "tag": tag,
                            "category": resolved_category,
                        }

                        self.all_words.add(surface)
                        self.paradigm_words.add(surface)
                        self._paradigm_cache.setdefault(root, []).append(record)
                        self.category_paradigms[resolved_category][root].append(record)
                        self.root_categories.setdefault(root, resolved_category)

                        if surface.startswith(root):
                            suffix = surface[len(root) :]
                            if suffix:
                                self.category_suffixes[resolved_category][root].add(suffix)

                        summary_sets[resolved_category].add(root)

        # Legacy fallback to ensure older datasets still load
        for file_path in _iter_files(legacy_dir):
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
        search_dirs = [
            os.path.join("paradigms", "Verb"),
            os.path.join("paradigms", "Noun"),
            os.path.join("paradigms", "Pronouns"),
            os.path.join("paradigms", "all"),  # Legacy fallback
        ]

        for directory in search_dirs:
            if not os.path.isdir(directory):
                continue
            pattern = os.path.join(directory, "**", f"{base_root}*.txt")
            for file_path in glob(pattern, recursive=True):
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

    def auto_generate_full_paradigms(self) -> None:
        """
        Automatically generate full paradigm variants for all base words
        using paradigm rules and store them in memory for fast lookup.
        Works for verbs, nouns, and pronouns.
        """
        print("\n[+] Auto-generating full morphological paradigms ...")
        total_generated = 0

        processed_roots: set[str] = set()

        # Process known categories first for precise metadata
        for category in ("verb", "noun", "pronoun"):
            for base_root, records in self.category_paradigms[category].items():
                processed_roots.add(base_root)
                for record in records:
                    rule = record.get("rule", "")
                    surface = self._apply_paradigm_rule(base_root, base_root, rule)
                    if not surface or surface in self.all_words:
                        continue

                    self.all_words.add(surface)
                    self.paradigm_words.add(surface)
                    total_generated += 1

                    metadata = {
                        "base_root": base_root,
                        "rule": rule,
                        "category": category,
                        "source_file": record.get("source_file", ""),
                    }
                    self.word_to_paradigms[surface].append(metadata)

        # Handle any remaining paradigms (legacy or uncategorized)
        for base_root, records in self._paradigm_cache.items():
            if base_root in processed_roots:
                continue
            category = self.root_categories.get(base_root, "other")
            for record in records:
                rule = record.get("rule", "")
                surface = self._apply_paradigm_rule(base_root, base_root, rule)
                if not surface or surface in self.all_words:
                    continue

                self.all_words.add(surface)
                self.paradigm_words.add(surface)
                total_generated += 1

                metadata = {
                    "base_root": base_root,
                    "rule": rule,
                    "category": category,
                    "source_file": record.get("source_file", ""),
                }
                self.word_to_paradigms[surface].append(metadata)

        print(f"  [morph-paradigm] Generated {total_generated:,} forms")
        print("  [ok] Morphological paradigms ready")

    def expand_all_paradigms(self, root: str) -> set[str]:
        """Generate all possible paradigm variants for a given root."""
        all_forms: set[str] = set()
        for category in ("verb", "noun", "pronoun"):
            for record in self.category_paradigms.get(category, {}).get(root, []):
                surface = self._apply_paradigm_rule(root, root, record.get("rule", ""))
                if surface:
                    all_forms.add(surface)

        # Include uncategorized/legacy paradigms if available
        for record in self._paradigm_cache.get(root, []):
            surface = self._apply_paradigm_rule(root, root, record.get("rule", ""))
            if surface:
                all_forms.add(surface)

        return all_forms

    def _apply_paradigm_rule(self, base_root: str, variant_root: str, rule: str) -> str:
        """
        Apply a full morphological paradigm rule recursively (Flask-compatible).
        Handles + and _ segment chains and multiple morphological layers.
        """

        if not rule:
            return variant_root

        word = variant_root.strip()
        rule = rule.strip()

        segments = [seg.strip() for seg in rule.split("+") if seg.strip()]

        for seg in segments:
            parts = seg.split("_")
            cleaned = [p.replace("#", "") for p in parts if p]

            if not cleaned:
                continue

            if len(cleaned) == 1:
                word += cleaned[0]
                continue

            left, *rest = cleaned

            # Determine the segment that should be replaced if present
            replace_target = rest[-1] if rest else ""

            if replace_target and word.endswith(replace_target):
                word = word[: -len(replace_target)] + left
            else:
                word += left

            # Append intermediate morphemes (excluding the final replace target)
            for extra in rest[:-1]:
                if extra:
                    word += extra

        return word


# Alias for backward compatibility
EnhancedSpellChecker = SimplifiedSpellChecker


if __name__ == "__main__":
    checker = SimplifiedSpellChecker()

    # Determine step number based on whether paradigm generator was used
    step_num = "4/4" if checker.use_paradigm_generator else "3/3"
    print(f"\n[{step_num}] Sample checks ...")
    tests = [
        "nAnu bengalUralli iruwweVneV",
        "ನಾನು ಬೆಂಗಳೂರಲ್ಲಿ ಇರುತ್ತೇನೆ",
        "avarannu ivarannu yArannu",
    ]

    for sample in tests:
        result = checker.check_text(sample)
        status = "[ok] No errors" if not result else f"[issues] {len(result)} error(s)"
        print(f"\n{status}")
