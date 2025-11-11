#!/usr/bin/env python3
"""
SIMPLIFIED Kannada Spell Checker (No POS/Chunking)
Direct dictionary lookup
"""
import sys
import os
import re
import pickle

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from kannada_wx_converter import kannada_to_wx, is_kannada_text, wx_to_kannada


class SimplifiedSpellChecker:
    """Simplified spell checker - dictionary lookup only"""
    
    def __init__(self):
        print("\n" + "="*70)
        print("Simplified Kannada Spell Checker")
        print("Dictionary Lookup Only (No POS/Chunking)")
        print("="*70)
        
        self.load_tokenizer()
        self.load_dictionary()
        
        print("\n✅ Ready!")
    
    def load_tokenizer(self):
        """Load tokenizer"""
        print("\n[1/2] Loading Tokenizer...")
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), 'Token'))
            from tokenizer_for_indian_languages_on_files import tokenize_sentence
            self.tokenize_func = tokenize_sentence
            print("  ✅ Tokenizer loaded")
        except:
            print("  ⚠️  Using fallback tokenizer")
            self.tokenize_func = None
    
    def load_dictionary(self):
        """Load dictionary"""
        print("\n[2/2] Loading Dictionary...")
        
        self.all_words = set()
        
        # Load from paradigm txt files
        paradigm_base = 'paradigms/all'
        if os.path.exists(paradigm_base):
            for file in os.listdir(paradigm_base):
                if file.endswith('.txt'):
                    with open(os.path.join(paradigm_base, file), 'r', encoding='utf-8') as f:
                        for line in f:
                            parts = line.strip().split()
                            if parts:
                                self.all_words.add(parts[0])
            print(f"  📂 Loaded from paradigm files")
        
        # Load from Excel-generated dictionary
        if os.path.exists('extended_dictionary.pkl'):
            with open('extended_dictionary.pkl', 'rb') as f:
                extended = pickle.load(f)
                if isinstance(extended, set):
                    self.all_words.update(extended)
                elif isinstance(extended, dict):
                    for words in extended.values():
                        if isinstance(words, (dict, set)):
                            self.all_words.update(words if isinstance(words, set) else words.keys())
            print(f"  📊 Loaded extended dictionary")
        
        print(f"\n  ✅ Total: {len(self.all_words):,} words")
    
    def tokenize(self, text):
        """Tokenize text"""
        if self.tokenize_func:
            try:
                return self.tokenize_func(text, lang='kn')
            except:
                pass
        return re.findall(r'[\u0C80-\u0CFF]+|[a-zA-Z]+', text)
    
    def edit_distance(self, s1, s2):
        """Levenshtein distance"""
        if len(s1) < len(s2):
            return self.edit_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current = [i + 1]
            for j, c2 in enumerate(s2):
                current.append(min(previous[j + 1] + 1, current[j] + 1, previous[j] + (c1 != c2)))
            previous = current
        return previous[-1]
    
    def get_suggestions(self, word, max_results=10):
        """Get suggestions"""
        suggestions = [(w, self.edit_distance(word, w)) for w in self.all_words]
        suggestions = [(w, d) for w, d in suggestions if d <= 2]
        suggestions.sort(key=lambda x: (x[1], x[0]))
        return [w for w, d in suggestions[:max_results]]
    
    def check_text(self, text):
        """Check text for errors"""
        print(f"\n{'='*70}")
        print(f"Processing: {text[:50]}...")
        print(f"{'='*70}")
        
        was_kannada = is_kannada_text(text)
        if was_kannada:
            print("\n[STEP 0] Converting Kannada → WX...")
            text = kannada_to_wx(text)
            print(f"  WX: {text}")
        
        print("\n[STEP 1] Tokenizing...")
        tokens = self.tokenize(text)
        print(f"  Tokens: {tokens}")
        
        print("\n[STEP 2] Checking...")
        errors = []
        
        for word in tokens:
            if len(word) <= 1:
                continue
            
            if word in self.all_words:
                print(f"  ✅ {word}: Correct")
            else:
                suggestions = self.get_suggestions(word)
                if was_kannada and suggestions:
                    suggestions = [wx_to_kannada(s) for s in suggestions]
                
                print(f"  ❌ {word}: {', '.join(suggestions[:5]) if suggestions else 'No suggestions'}")
                errors.append({'word': word, 'suggestions': suggestions})
        
        return errors


# Alias for backward compatibility
EnhancedSpellChecker = SimplifiedSpellChecker


if __name__ == "__main__":
    checker = SimplifiedSpellChecker()
    
    tests = [
        "nAnu bengalUralli iruwweVneV",
        "ನಾನು ಬೆಂಗಳೂರಲ್ಲಿ ಇರುತ್ತೇನೆ",
    ]
    
    for test in tests:
        errors = checker.check_text(test)
        print(f"\n{'✅ No errors' if not errors else f'❌ {len(errors)} error(s)'}")
