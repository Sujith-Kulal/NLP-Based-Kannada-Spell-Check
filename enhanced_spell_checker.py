#!/usr/bin/env python3
"""
Enhanced Kannada Spell Checker with Full NLP Pipeline
Architecture: Tokenization → POS Tagging → Chunking → Paradigm Checking → Suggestions
Works with ANY editor via clipboard monitoring
Supports both Kannada Unicode (ಕನ್ನಡ) and WX transliteration
"""
import sys
import os
import time
import re
import pickle
from datetime import datetime
from collections import defaultdict

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Kannada-WX converter
from kannada_wx_converter import kannada_to_wx, is_kannada_text, normalize_text

# Clipboard monitoring
try:
    import pyperclip
except ImportError:
    print("❌ Error: pyperclip not installed")
    print("Install: pip install pyperclip")
    sys.exit(1)

# Notifications
try:
    from plyer import notification
    HAS_NOTIFICATIONS = True
except ImportError:
    print("⚠️  Warning: plyer not available (notifications disabled)")
    HAS_NOTIFICATIONS = False


class EnhancedSpellChecker:
    """
    Enhanced spell checker with full NLP pipeline:
    1. Tokenization
    2. POS Tagging
    3. Chunking
    4. Paradigm Checking (POS-aware)
    5. Edit Distance Suggestions
    """
    
    def __init__(self):
        print("\n" + "="*70)
        print("Enhanced Kannada Spell Checker")
        print("Tokenization → POS → Chunking → Paradigm Checking")
        print("="*70)
        
        self.running = True
        self.last_clipboard = ""
        self.check_count = 0
        self.error_count = 0
        
        # Load components
        self.load_tokenizer()
        self.load_pos_tagger()
        self.load_chunker()
        self.load_paradigm_dictionary()
        
        print("\n✅ All components loaded successfully!")
    
    def load_tokenizer(self):
        """Load tokenization module"""
        print("\n[1/4] Loading Tokenizer...")
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), 'token'))
            from tokenizer_for_indian_languages_on_files import tokenize_sentence
            self.tokenize_func = tokenize_sentence
            print("  ✅ Tokenizer loaded")
        except Exception as e:
            print(f"  ⚠️  Tokenizer not available: {e}")
            print("  Using fallback tokenizer")
            self.tokenize_func = None
    
    def load_pos_tagger(self):
        """Load POS tagging model"""
        print("\n[2/4] Loading POS Tagger...")
        self.pos_tagger = None
        self.pos_model_name = "Rule-based"
        
        try:
            # Check if model exists
            model_path = os.path.join(os.path.dirname(__file__), 'pos_tag', 'xlm-base-2')
            if os.path.exists(model_path):
                try:
                    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
                    print(f"  📦 Found model: {model_path}")
                    print(f"  🔄 Loading xlm-base-2 transformer model...")
                    
                    tokenizer = AutoTokenizer.from_pretrained(model_path)
                    model = AutoModelForTokenClassification.from_pretrained(model_path)
                    self.pos_tagger = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
                    self.pos_model_name = "xlm-base-2 (HF Transformer)"
                    
                    print(f"  ✅ POS model loaded: xlm-base-2")
                    print(f"  🎯 Using: Hugging Face Transformer Model")
                except ImportError:
                    print("  ⚠️  POS model found but transformers not installed")
                    print("  💡 Run: pip install transformers torch")
                    print("  📌 Using rule-based POS tagging")
                except Exception as e:
                    print(f"  ⚠️  Could not load POS model: {e}")
                    print("  📌 Using rule-based POS tagging")
            else:
                print(f"  ℹ️  No POS model found at: pos_tag/xlm-base-2")
                print(f"  📌 Using rule-based POS tagging")
        except Exception as e:
            print(f"  ⚠️  POS tagger error: {e}")
            print("  📌 Using rule-based POS tagging")
    
    def load_chunker(self):
        """Load chunking model"""
        print("\n[3/4] Loading Chunker...")
        self.chunker = None
        self.chunk_model_name = "Rule-based"
        
        try:
            chunk_path = os.path.join(os.path.dirname(__file__), 'chunk_tag', 'checkpoint-18381')
            if os.path.exists(chunk_path):
                try:
                    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
                    print(f"  📦 Found model: {chunk_path}")
                    print(f"  🔄 Loading checkpoint-18381 transformer model...")
                    
                    tokenizer = AutoTokenizer.from_pretrained(chunk_path)
                    model = AutoModelForTokenClassification.from_pretrained(chunk_path)
                    self.chunker = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
                    self.chunk_model_name = "checkpoint-18381 (HF Transformer)"
                    
                    print(f"  ✅ Chunk model loaded: checkpoint-18381")
                    print(f"  🎯 Using: Hugging Face Transformer Model")
                except ImportError:
                    print("  ⚠️  Chunk model found but transformers not installed")
                    print("  💡 Run: pip install transformers torch")
                    print("  📌 Using rule-based chunking")
                except Exception as e:
                    print(f"  ⚠️  Could not load Chunk model: {e}")
                    print("  📌 Using rule-based chunking")
            else:
                print(f"  ℹ️  No Chunk model found at: chunk_tag/checkpoint-18381")
                print(f"  📌 Using rule-based chunking")
        except Exception as e:
            print(f"  ⚠️  Chunker error: {e}")
            print("  📌 Using rule-based chunking")
    
    def load_paradigm_dictionary(self):
        """
        Load paradigm files organized by POS tags
        Structure: {POS_tag: {word: frequency}}
        Also loads paradigm rules for generation
        """
        print("\n[4/4] Loading Paradigm Dictionary...")
        
        self.pos_paradigms = defaultdict(dict)
        self.category_paradigms = {"verb": {}, "noun": {}, "pronoun": {}}
        paradigm_base = 'paradigms'
        
        if not os.path.exists(paradigm_base):
            print(f"  ❌ Paradigm directory not found: {paradigm_base}")
            return
        
        # Map directories to POS tags and categories
        dir_to_pos = {
            'Noun': 'NN',
            'Verb': 'VB',
            'Pronouns': 'PR'
        }
        
        dir_to_category = {
            'Noun': 'noun',
            'Verb': 'verb',
            'Pronouns': 'pronoun'
        }
        
        total_words = 0
        
        for dir_name, pos_tag in dir_to_pos.items():
            dir_path = os.path.join(paradigm_base, dir_name)
            if os.path.exists(dir_path):
                words = {}
                file_count = 0
                category = dir_to_category[dir_name]
                
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        if file.endswith('.txt'):
                            filepath = os.path.join(root, file)
                            try:
                                with open(filepath, 'r', encoding='utf-8') as f:
                                    for line in f:
                                        line = line.strip()
                                        if line:
                                            # Extract word (first column) and rule (second column)
                                            parts = line.split()
                                            if parts:
                                                word = parts[0]
                                                words[word] = words.get(word, 0) + 1
                                                
                                                # Parse paradigm rule for generation
                                                if len(parts) >= 2:
                                                    rule_str = parts[1]
                                                    # Extract base root from rule: base(Type)+rule
                                                    if '(' in rule_str and ')' in rule_str:
                                                        base_root = rule_str.split('(')[0]
                                                        # Extract the rule part after the base(Type)
                                                        rule_part = rule_str.split(')')[1] if ')' in rule_str else ''
                                                        
                                                        if base_root not in self.category_paradigms[category]:
                                                            self.category_paradigms[category][base_root] = []
                                                        
                                                        self.category_paradigms[category][base_root].append({
                                                            'surface': word,
                                                            'rule': rule_part
                                                        })
                                file_count += 1
                            except Exception as e:
                                pass
                
                if words:
                    self.pos_paradigms[pos_tag] = words
                    print(f"  {pos_tag} ({dir_name}): {len(words):,} words from {file_count} files")
                    total_words += len(words)
        
        # Load extended dictionary from Excel files (if available)
        extended_dict_path = 'extended_dictionary.pkl'
        if os.path.exists(extended_dict_path):
            try:
                with open(extended_dict_path, 'rb') as f:
                    extended_dict = pickle.load(f)
                
                excel_words = 0
                for pos_tag, words in extended_dict.items():
                    # Merge with existing paradigms
                    for word, freq in words.items():
                        if word not in self.pos_paradigms[pos_tag]:
                            self.pos_paradigms[pos_tag][word] = freq
                            excel_words += 1
                
                print(f"\n  📊 Extended dictionary loaded:")
                print(f"     Added {excel_words:,} additional words from Excel files")
            except Exception as e:
                print(f"  ⚠️  Could not load extended dictionary: {e}")
        
        # Create combined dictionary for fallback
        self.all_words = {}
        for pos_dict in self.pos_paradigms.values():
            self.all_words.update(pos_dict)
        
        print(f"\n  ✅ Total: {total_words:,} words across {len(self.pos_paradigms)} POS categories")
        print(f"  ✅ Combined dictionary: {len(self.all_words):,} unique words")
        
        # Show paradigm rule statistics
        total_rules = sum(len(rules) for cat_rules in self.category_paradigms.values() for rules in cat_rules.values())
        total_roots = sum(len(cat_rules) for cat_rules in self.category_paradigms.values())
        print(f"  ✅ Loaded {total_rules:,} paradigm rules for {total_roots} base roots")
        
        # Auto-generate full paradigms
        self.auto_generate_full_paradigms()
    
    def _apply_paradigm_rule(self, base_root: str, variant_root: str, rule: str) -> str:
        """
        Apply a full morphological paradigm rule recursively (Flask-compatible).
        Handles + and _ segment chains and multiple morphological layers.
        
        Args:
            base_root: Original base root from paradigm file
            variant_root: Current variant being built
            rule: Rule string like "+xa_#_PAST+anu_a_3SM"
        
        Returns:
            Generated surface form
        
        Rule format:
            +morpheme1_placeholder_tag+morpheme2_placeholder_tag
        where:
            - morpheme is what gets added/replaced
            - placeholder can be # or the morpheme to replace
            - tag is metadata (tense, person, etc.)
        """
        if not rule:
            return variant_root

        word = variant_root.strip()
        rule = rule.strip()

        # Split multiple + segments
        segments = [seg.strip() for seg in rule.split('+') if seg.strip()]
        
        for seg in segments:
            # Handle (a_b_c_d...) recursive sequences
            parts = seg.split('_')
            
            # Remove # symbols and filter empty strings
            cleaned = [p for p in parts if p and p != '#']
            
            # If nothing left after cleaning, skip this segment
            if not cleaned:
                continue
            
            # First part is the morpheme to add
            # Second part (if exists and not a tag) might be what to replace
            if len(cleaned) == 1:
                # Simple append: just the morpheme
                word += cleaned[0]
            elif len(cleaned) >= 2:
                morpheme = cleaned[0]
                placeholder = cleaned[1]
                
                # Check if placeholder is actually a replacement target
                # (not an ALL_CAPS tag like PAST, FUT, etc.)
                if placeholder.isupper() or placeholder[0].isupper():
                    # It's a tag, not a replacement - just append the morpheme
                    word += morpheme
                else:
                    # Try to replace the placeholder with the morpheme
                    if word.endswith(placeholder):
                        word = word[:-len(placeholder)] + morpheme
                    else:
                        # Placeholder not found at end, just append
                        word += morpheme

        return word
    
    def expand_all_paradigms(self, root: str):
        """
        Generate all possible paradigm variants (Verb/Noun/Pronoun) for a given base.
        
        Args:
            root: Base root to expand
        
        Returns:
            Set of all generated surface forms
        """
        all_forms = set()
        categories = ["verb", "noun", "pronoun"]
        
        for cat in categories:
            base_records = self.category_paradigms[cat].get(root, [])
            for rec in base_records:
                new_word = self._apply_paradigm_rule(root, root, rec["rule"])
                all_forms.add(new_word)
        
        return all_forms
    
    def auto_generate_full_paradigms(self):
        """
        Pre-build all paradigms for every base root and add to dictionary.
        This generates the complete paradigm dictionary in memory.
        """
        print("\n  🔄 Auto-generating full paradigms...")
        
        generated_count = 0
        
        for cat in ("verb", "noun", "pronoun"):
            for root in self.category_paradigms[cat].keys():
                for record in self.category_paradigms[cat][root]:
                    surface = self._apply_paradigm_rule(root, root, record["rule"])
                    if surface not in self.all_words:
                        self.all_words[surface] = 1
                        generated_count += 1
                        
                        # Also add to appropriate POS paradigm
                        if cat == "verb" and surface not in self.pos_paradigms['VB']:
                            self.pos_paradigms['VB'][surface] = 1
                        elif cat == "noun" and surface not in self.pos_paradigms['NN']:
                            self.pos_paradigms['NN'][surface] = 1
                        elif cat == "pronoun" and surface not in self.pos_paradigms['PR']:
                            self.pos_paradigms['PR'][surface] = 1
        
        print(f"  ✅ Generated {generated_count:,} additional paradigm forms")
    
    def tokenize(self, text):
        """
        STEP 1: Tokenization
        Uses your token/tokenizer_for_indian_languages_on_files.py
        """
        if self.tokenize_func:
            try:
                tokens = self.tokenize_func(text, lang='kn')
                return tokens
            except:
                pass
        
        # Fallback: simple tokenization
        # Split on whitespace and punctuation
        tokens = re.findall(r'[\u0C80-\u0CFF]+|[a-zA-Z]+', text)
        return [t for t in tokens if t.strip()]
    
    def pos_tag(self, tokens):
        """
        STEP 2: POS Tagging
        Uses your pos_tag/xlm-base-2 model
        For now: rule-based fallback with pronoun patterns
        """
        if self.pos_tagger:
            # Use actual HF transformer model
            print(f"  🎯 Using POS model: {self.pos_model_name}")
            try:
                text = " ".join(tokens)
                results = self.pos_tagger(text)
                pos_tagged = []
                for i, token in enumerate(tokens):
                    if i < len(results):
                        pos = results[i]["entity_group"]
                    else:
                        pos = "NN"  # Default
                    pos_tagged.append((token, pos))
                return pos_tagged
            except Exception as e:
                print(f"  ⚠️  Model error, falling back to rule-based: {e}")
        
        # Rule-based fallback POS tagging
        print(f"  🎯 Using POS method: {self.pos_model_name}")
        pos_tagged = []
        
        # Pronoun stem patterns (from paradigm files)
        pronoun_stems = [
            'ivan', 'ival', 'ivar', 'iva', 'iv',  # ivanu, ivalu, ivaru (this person)
            'avan', 'aval', 'avar', 'ava', 'av',  # avanu, avalu, avaru (that person)
            'nAn', 'nAv', 'nIn', 'nIv',           # nAnu, nAvu, nInu, nIvu (I, we, you)
            'wAn', 'wAv', 'Ad', 'ix', 'ex',       # wAnu, wAvu, Adu, ixu, exu (it)
            'yAr', 'yAv', 'eV', 'A',              # yAru, yAvu, eVru (who, which)
        ]
        
        # Verb suffixes (common verb endings)
        verb_suffixes = ['ali', 'iri', 'udu', 'enu', 'aru', 'are', 'avu', 'ave', 
                        'uwwA', 'uwaV', 'ida', 'ide', 'al', 'ir', 'uv']
        
        for token in tokens:
            # Check if word exists in specific paradigm
            if token in self.pos_paradigms.get('VB', {}):
                pos = 'VB'
            elif token in self.pos_paradigms.get('PR', {}):
                pos = 'PR'
            else:
                # Use pattern matching for unknown words
                pos = 'NN'  # Default to noun
                
                # Check pronoun patterns
                for stem in pronoun_stems:
                    if token.startswith(stem):
                        pos = 'PR'
                        break
                
                # Check verb patterns (if not already tagged as PR)
                if pos == 'NN':
                    for suffix in verb_suffixes:
                        if token.endswith(suffix):
                            pos = 'VB'
                            break
            
            pos_tagged.append((token, pos))
        
        return pos_tagged
    
    def chunk(self, pos_tagged):
        """
        STEP 3: Chunking
        Uses your chunk_tag/checkpoint-18381 model
        For now: rule-based fallback
        """
        if self.chunker:
            # Use actual HF transformer model
            print(f"  🎯 Using Chunker model: {self.chunk_model_name}")
            try:
                tokens = [word for word, pos in pos_tagged]
                text = " ".join(tokens)
                results = self.chunker(text)
                
                chunks = []
                current_np = []
                
                for i, (word, pos) in enumerate(pos_tagged):
                    if i < len(results):
                        chunk_tag = results[i]["entity_group"]
                        if chunk_tag.startswith("B-"):
                            if current_np:
                                chunks.append(('NP', current_np))
                                current_np = []
                            current_np = [word]
                        elif chunk_tag.startswith("I-"):
                            current_np.append(word)
                        else:
                            if current_np:
                                chunks.append(('NP', current_np))
                                current_np = []
                            chunks.append((pos, [word]))
                    else:
                        if pos == 'NN':
                            current_np.append(word)
                        else:
                            if current_np:
                                chunks.append(('NP', current_np))
                                current_np = []
                            chunks.append((pos, [word]))
                
                if current_np:
                    chunks.append(('NP', current_np))
                
                return chunks
            except Exception as e:
                print(f"  ⚠️  Model error, falling back to rule-based: {e}")
        
        # Simple noun phrase chunking
        print(f"  🎯 Using Chunker method: {self.chunk_model_name}")
        chunks = []
        current_np = []
        
        for word, pos in pos_tagged:
            if pos == 'NN':
                current_np.append(word)
            else:
                if current_np:
                    chunks.append(('NP', current_np))
                    current_np = []
                chunks.append((pos, [word]))
        
        if current_np:
            chunks.append(('NP', current_np))
        
        return chunks
    
    def check_against_paradigm(self, word, pos_tag):
        """
        STEP 4: Paradigm Checking
        Check if word exists in paradigm for given POS tag
        Returns: (is_correct, suggestions)
        """
        # Strict category check: only mark correct if the word is present under its POS
        if pos_tag in self.pos_paradigms and word in self.pos_paradigms[pos_tag]:
            return True, []

        # Start with category-scoped suggestions
        same_pos_candidates = self.pos_paradigms.get(pos_tag, {})
        suggestions = self.get_suggestions(word, same_pos_candidates, max_suggestions=10)

        # Pronoun-specific bridging to keep i-/a- stems aligned with paradigm data
        if pos_tag == 'PR':
            bridged = self._pronoun_bridge_suggestions(word)
            if bridged:
                seen = set()
                ordered = []
                for candidate in bridged + suggestions:
                    if candidate not in seen:
                        ordered.append(candidate)
                        seen.add(candidate)
                suggestions = ordered[:10]

        # Backfill with cross-POS suggestions only if we still need more options
        if len(suggestions) < 10:
            remaining = 10 - len(suggestions)
            cross_pos = self.get_suggestions(word, self.all_words, max_suggestions=remaining)
            cross_pos = [w for w in cross_pos if w not in suggestions]
            suggestions.extend(cross_pos)

        return False, suggestions

    def _pronoun_bridge_suggestions(self, word):
        """Generate pronoun suggestions that respect i↔a stem swaps while
        preserving suffix expectations such as ali↔alli."""
        pr_dict = self.pos_paradigms.get('PR', {})
        if not word or not pr_dict:
            return []

        from itertools import count

        ranking = {}
        order_counter = count()

        def add_candidate(value, priority):
            if not value:
                return
            if value in ranking:
                current_priority, order = ranking[value]
                if priority < current_priority:
                    ranking[value] = (priority, order)
            else:
                ranking[value] = (priority, next(order_counter))

        original_prefix = 'i' if word.startswith('i') else 'a' if word.startswith('a') else None
        swap_prefix = None
        if original_prefix == 'i':
            swap_prefix = 'a'
        elif original_prefix == 'a':
            swap_prefix = 'i'

        # Handle common ali↔alli toggles when the swapped form exists in paradigms
        suffix_pairs = [('ali', 'alli'), ('alli', 'ali')]
        for src_suffix, dst_suffix in suffix_pairs:
            if word.endswith(src_suffix):
                alt_form = word[:-len(src_suffix)] + dst_suffix
                swapped_alt = None
                if swap_prefix and len(word) > 1:
                    swapped_alt = swap_prefix + word[1:-len(src_suffix)] + dst_suffix
                if swapped_alt and swapped_alt in pr_dict:
                    add_candidate(alt_form, 0)
                elif alt_form in pr_dict:
                    add_candidate(alt_form, 0)

        # Look at the swapped stem inside PR dictionary and project suggestions back
        if swap_prefix and len(word) > 1:
            swapped_word = swap_prefix + word[1:]
            if swapped_word in pr_dict:
                add_candidate(swapped_word, 2)

            # Pull suggestions for the swapped word within the pronoun dictionary
            swapped_suggestions = self.get_suggestions(swapped_word, pr_dict, max_suggestions=10)
            for suggestion in swapped_suggestions:
                add_candidate(suggestion, 3)
                if suggestion.startswith(swap_prefix):
                    reverted = original_prefix + suggestion[1:] if original_prefix else suggestion
                    add_candidate(reverted, 1)

        # If we are still short on ideas, fall back to edit distance within PR
        if len(ranking) < 5:
            backup = self.get_suggestions(word, pr_dict, max_suggestions=5)
            for suggestion in backup:
                add_candidate(suggestion, 4)

        ordered = [value for value, _ in sorted(ranking.items(), key=lambda item: (item[1][0], item[1][1]))]
        return ordered
    
    def levenshtein_distance(self, s1, s2):
        """Calculate Levenshtein edit distance"""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        
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
    
    def get_suggestions(self, word, paradigm, max_suggestions=10, max_distance=3):
        """
        STEP 5: Edit Distance Suggestions
        Get spelling suggestions from paradigm
        Increased to edit distance 3 for better suggestions
        """
        suggestions = []
        
        # Filter candidates by length (more lenient)
        candidates = [
            w for w in paradigm.keys()
            if abs(len(w) - len(word)) <= max_distance + 1
        ]
        
        # Calculate distances
        for candidate in candidates:
            distance = self.levenshtein_distance(word, candidate)
            if distance <= max_distance:
                freq = paradigm.get(candidate, 0)
                suggestions.append((candidate, distance, freq))
        
        # Sort by distance (ascending), then frequency (descending)
        suggestions.sort(key=lambda x: (x[1], -x[2]))
        
        return [s[0] for s in suggestions[:max_suggestions]]
    
    def check_text(self, text):
        """
        Full NLP Pipeline:
        Tokenize → POS Tag → Chunk → Check Paradigms → Get Suggestions
        Automatically converts Kannada Unicode to WX transliteration
        """
        print(f"\n{'='*70}")
        print(f"Processing: {text[:50]}...")
        print(f"{'='*70}")
        
        # STEP 0: Convert Kannada to WX if needed
        if is_kannada_text(text):
            print("\n[STEP 0] Converting Kannada Unicode to WX...")
            original_text = text
            text = kannada_to_wx(text)
            print(f"  Original: {original_text[:100]}")
            print(f"  WX: {text}")
        
        # STEP 1: Tokenization
        print("\n[STEP 1] Tokenizing...")
        tokens = self.tokenize(text)
        print(f"  Tokens: {tokens}")
        
        if not tokens:
            return []
        
        # STEP 2: POS Tagging
        print("\n[STEP 2] POS Tagging...")
        pos_tagged = self.pos_tag(tokens)
        for word, pos in pos_tagged:
            print(f"  {word} → {pos}")
        
        # STEP 3: Chunking
        print("\n[STEP 3] Chunking...")
        chunks = self.chunk(pos_tagged)
        for chunk_type, words in chunks:
            print(f"  [{chunk_type}: {' '.join(words)}]")
        
        # STEP 4 & 5: Check against paradigms and get suggestions
        print("\n[STEP 4-5] Checking Paradigms & Getting Suggestions...")
        errors = []
        
        for word, pos_tag in pos_tagged:
            # Skip very short words
            if len(word) <= 1:
                continue
            
            # Check word against paradigm for its POS
            is_correct, suggestions = self.check_against_paradigm(word, pos_tag)
            
            if not is_correct:
                print(f"  ❌ {word} ({pos_tag}): {', '.join(suggestions) if suggestions else 'No suggestions'}")
                errors.append({
                    'word': word,
                    'pos': pos_tag,
                    'suggestions': suggestions
                })
            else:
                print(f"  ✅ {word} ({pos_tag}): Correct")
        
        return errors
    
    def show_notification(self, title, message, timeout=5):
        """Show system notification"""
        if HAS_NOTIFICATIONS:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Kannada Spell Checker",
                    timeout=timeout
                )
            except Exception as e:
                pass
        
        # Always print to console
        print(f"\n📢 {title}")
        print(f"   {message}")
    
    def monitor_clipboard(self):
        """Monitor clipboard for Kannada text"""
        print("\n" + "="*70)
        print("📋 CLIPBOARD MONITORING STARTED")
        print("="*70)
        print("\n📝 How to use:")
        print("  1. Open ANY editor (Notepad, Word, VS Code, Browser)")
        print("  2. Type Kannada text")
        print("  3. Select and COPY the text (Ctrl+C)")
        print("  4. Get instant spell check with POS-aware suggestions!")
        print("\n⚠️  Press Ctrl+C to stop the service")
        print("="*70 + "\n")
        
        while self.running:
            try:
                current = pyperclip.paste()
                
                # Check if clipboard changed
                if current != self.last_clipboard and current.strip():
                    # Check if contains Kannada Unicode or non-ASCII text
                    has_kannada = any('\u0C80' <= c <= '\u0CFF' for c in current)
                    has_text = any(ord(c) > 127 for c in current)
                    
                    if has_kannada or has_text:
                        self.check_count += 1
                        
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Check #{self.check_count}")
                        
                        # Run full pipeline
                        errors = self.check_text(current)
                        
                        # Show results
                        if errors:
                            self.error_count += len(errors)
                            
                            print(f"\n{'='*70}")
                            print(f"❌ FOUND {len(errors)} ERROR(S)")
                            print(f"{'='*70}")
                            
                            # Show notifications for first 3 errors
                            for i, error in enumerate(errors[:3], 1):
                                word = error['word']
                                pos = error['pos']
                                suggestions = error['suggestions']
                                
                                title = f"❌ Error {i}/{len(errors)}: {word} ({pos})"
                                if suggestions:
                                    message = f"Suggestions: {', '.join(suggestions[:3])}"
                                else:
                                    message = "No suggestions found"
                                
                                self.show_notification(title, message, 5)
                                time.sleep(0.5)
                            
                            if len(errors) > 3:
                                self.show_notification(
                                    f"ℹ️ {len(errors)-3} More Error(s)",
                                    "Check console for details",
                                    3
                                )
                        else:
                            print(f"\n{'='*70}")
                            print("✅ NO ERRORS - ALL WORDS CORRECT!")
                            print(f"{'='*70}")
                            
                            self.show_notification(
                                "✅ Perfect Spelling!",
                                "No errors found in your text",
                                3
                            )
                    
                    self.last_clipboard = current
                
            except Exception as e:
                print(f"\n⚠️  Error: {e}")
                import traceback
                traceback.print_exc()
            
            time.sleep(1)  # Check every second
    
    def run(self):
        """Start the service"""
        try:
            self.monitor_clipboard()
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("STOPPING SERVICE")
            print("="*70)
            self.stop()
    
    def stop(self):
        """Stop the service"""
        self.running = False
        
        print(f"\n📊 Session Statistics:")
        print(f"  Checks performed: {self.check_count}")
        print(f"  Total errors found: {self.error_count}")
        
        print("\n✅ Service stopped successfully")
        print("="*70 + "\n")


def main():
    """Main entry point"""
    try:
        service = EnhancedSpellChecker()
        service.run()
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
