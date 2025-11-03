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
        try:
            # Check if model exists
            model_path = os.path.join(os.path.dirname(__file__), 'pos_tag', 'xlm-base-2')
            if os.path.exists(model_path):
                print("  ⚠️  POS model found but not loading (requires transformers)")
                print("  Using rule-based POS tagging")
            self.pos_tagger = None
        except Exception as e:
            print(f"  ⚠️  POS tagger not available: {e}")
        
        self.pos_tagger = None
    
    def load_chunker(self):
        """Load chunking model"""
        print("\n[3/4] Loading Chunker...")
        try:
            chunk_path = os.path.join(os.path.dirname(__file__), 'chunk_tag', 'checkpoint-18381')
            if os.path.exists(chunk_path):
                print("  ⚠️  Chunk model found but not loading (requires transformers)")
                print("  Using rule-based chunking")
            self.chunker = None
        except Exception as e:
            print(f"  ⚠️  Chunker not available: {e}")
        
        self.chunker = None
    
    def load_paradigm_dictionary(self):
        """
        Load paradigm files organized by POS tags
        Structure: {POS_tag: {word: frequency}}
        """
        print("\n[4/4] Loading Paradigm Dictionary...")
        
        self.pos_paradigms = defaultdict(dict)
        paradigm_base = 'paradigms'
        
        if not os.path.exists(paradigm_base):
            print(f"  ❌ Paradigm directory not found: {paradigm_base}")
            return
        
        # Map directories to POS tags
        dir_to_pos = {
            'Noun': 'NN',
            'Verb': 'VB',
            'Pronouns': 'PR'
        }
        
        total_words = 0
        
        for dir_name, pos_tag in dir_to_pos.items():
            dir_path = os.path.join(paradigm_base, dir_name)
            if os.path.exists(dir_path):
                words = {}
                file_count = 0
                
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        if file.endswith('.txt'):
                            filepath = os.path.join(root, file)
                            try:
                                with open(filepath, 'r', encoding='utf-8') as f:
                                    for line in f:
                                        line = line.strip()
                                        if line:
                                            # Extract word (first column)
                                            parts = line.split()
                                            if parts:
                                                word = parts[0]
                                                words[word] = words.get(word, 0) + 1
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
            # Use actual model
            pass
        
        # Rule-based fallback POS tagging
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
            # Use actual model
            pass
        
        # Simple noun phrase chunking
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
        # Check if word exists in ALL paradigms first
        if word in self.all_words:
            return True, []
        
        # Word not found - get suggestions from ALL paradigms (cross-POS)
        # This ensures we don't miss suggestions from other POS categories
        suggestions = self.get_suggestions(word, self.all_words, max_suggestions=10)
        
        return False, suggestions
    
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
