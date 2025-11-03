#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kannada Unicode ↔ WX Transliteration Converter
Converts between Kannada script (ಕನ್ನಡ) and WX notation (kannaDa)
"""

# Kannada Unicode to WX mapping
KANNADA_TO_WX = {
    # Vowels
    'ಅ': 'a', 'ಆ': 'A', 'ಇ': 'i', 'ಈ': 'I', 'ಉ': 'u', 'ಊ': 'U',
    'ಋ': 'q', 'ೠ': 'Q', 'ಌ': 'L', 'ೡ': 'lY',
    'ಎ': 'e', 'ಏ': 'eV', 'ಐ': 'E',
    'ಒ': 'o', 'ಓ': 'oV', 'ಔ': 'O',
    
    # Vowel signs (matras)
    'ಾ': 'A', 'ಿ': 'i', 'ೀ': 'I', 'ು': 'u', 'ೂ': 'U',
    'ೃ': 'q', 'ೄ': 'Q', 'ೢ': 'L', 'ೣ': 'lY',
    'ೆ': 'e', 'ೇ': 'eV', 'ೈ': 'E',
    'ೊ': 'o', 'ೋ': 'oV', 'ೌ': 'O',
    
    # Consonants
    'ಕ': 'ka', 'ಖ': 'Ka', 'ಗ': 'ga', 'ಘ': 'Ga', 'ಙ': 'fa',
    'ಚ': 'ca', 'ಛ': 'Ca', 'ಜ': 'ja', 'ಝ': 'Ja', 'ಞ': 'Fa',
    'ಟ': 'ta', 'ಠ': 'Ta', 'ಡ': 'da', 'ಢ': 'Da', 'ಣ': 'Na',
    'ತ': 'wa', 'ಥ': 'Wa', 'ದ': 'xa', 'ಧ': 'Xa', 'ನ': 'na',
    'ಪ': 'pa', 'ಫ': 'Pa', 'ಬ': 'ba', 'ಭ': 'Ba', 'ಮ': 'ma',
    'ಯ': 'ya', 'ರ': 'ra', 'ಱ': 'rY', 'ಲ': 'la', 'ಳ': 'lY',
    'ವ': 'va', 'ಶ': 'Sa', 'ಷ': 'Ra', 'ಸ': 'sa', 'ಹ': 'ha',
    
    # Special
    'ಂ': 'M', 'ಃ': 'H', '್': '', 'ಽ': '.a',
    
    # Numbers
    '೦': '0', '೧': '1', '೨': '2', '೩': '3', '೪': '4',
    '೫': '5', '೬': '6', '೭': '7', '೮': '8', '೯': '9',
}

# WX to Kannada Unicode mapping (reverse)
WX_TO_KANNADA = {v: k for k, v in KANNADA_TO_WX.items() if v}

def kannada_to_wx(text):
    """
    Convert Kannada Unicode text to WX transliteration
    
    Args:
        text (str): Kannada text (e.g., "ಮರವು")
    
    Returns:
        str: WX transliteration (e.g., "maravu")
    
    Example:
        >>> kannada_to_wx("ಮರವು")
        'maravu'
        >>> kannada_to_wx("ಹುಡುಗ")
        'huduga'
    """
    result = []
    i = 0
    
    while i < len(text):
        char = text[i]
        
        # Skip virama (halant) - handled with consonants
        if char == '್':
            i += 1
            continue
        
        # Check for consonant + virama (halant) - no inherent 'a'
        if i + 1 < len(text) and text[i + 1] == '್':
            wx = KANNADA_TO_WX.get(char, char)
            # Remove inherent 'a' from consonant
            if wx.endswith('a'):
                wx = wx[:-1]
            result.append(wx)
            i += 1  # Skip the consonant, virama handled in next iteration
            continue
        
        # Check for consonant + vowel sign (matra)
        if i + 1 < len(text):
            next_char = text[i + 1]
            # Check if next character is a vowel sign (matra)
            if next_char in ['ಾ', 'ಿ', 'ೀ', 'ು', 'ೂ', 'ೃ', 'ೄ', 'ೢ', 'ೣ', 
                             'ೆ', 'ೇ', 'ೈ', 'ೊ', 'ೋ', 'ೌ', 'ಂ', 'ಃ']:
                consonant = KANNADA_TO_WX.get(char, char)
                matra = KANNADA_TO_WX.get(next_char, next_char)
                
                # Remove inherent 'a' from consonant and add matra
                if consonant.endswith('a'):
                    consonant = consonant[:-1]
                
                result.append(consonant + matra)
                i += 2
                continue
        
        # Single character (vowel or consonant with inherent 'a')
        result.append(KANNADA_TO_WX.get(char, char))
        i += 1
    
    return ''.join(result)

def wx_to_kannada(text):
    """
    Convert WX transliteration to Kannada Unicode
    
    Args:
        text (str): WX text (e.g., "maravu")
    
    Returns:
        str: Kannada text (e.g., "ಮರವು")
    
    Example:
        >>> wx_to_kannada("maravu")
        'ಮರವು'
        >>> wx_to_kannada("huduga")
        'ಹುಡುಗ'
    """
    # Map WX consonants (without inherent 'a')
    consonants = {
        'k': 'ಕ', 'K': 'ಖ', 'g': 'ಗ', 'G': 'ಘ', 'f': 'ಙ',
        'c': 'ಚ', 'C': 'ಛ', 'j': 'ಜ', 'J': 'ಝ', 'F': 'ಞ',
        't': 'ಟ', 'T': 'ಠ', 'd': 'ಡ', 'D': 'ಢ', 'N': 'ಣ',
        'w': 'ತ', 'W': 'ಥ', 'x': 'ದ', 'X': 'ಧ', 'n': 'ನ',
        'p': 'ಪ', 'P': 'ಫ', 'b': 'ಬ', 'B': 'ಭ', 'm': 'ಮ',
        'y': 'ಯ', 'r': 'ರ', 'l': 'ಲ', 'L': 'ಳ',
        'v': 'ವ', 'S': 'ಶ', 'R': 'ಷ', 's': 'ಸ', 'h': 'ಹ',
    }
    
    # Map WX vowels (independent)
    independent_vowels = {
        'a': 'ಅ', 'A': 'ಆ', 'i': 'ಇ', 'I': 'ಈ', 'u': 'ಉ', 'U': 'ಊ',
        'q': 'ಋ', 'Q': 'ೠ', 'e': 'ಎ', 'E': 'ಐ',
        'o': 'ಒ', 'O': 'ಔ',
    }
    
    # Map WX vowel signs (dependent - added to consonants)
    vowel_signs = {
        'A': 'ಾ', 'i': 'ಿ', 'I': 'ೀ', 'u': 'ು', 'U': 'ೂ',
        'q': 'ೃ', 'Q': 'ೄ', 'e': 'ೆ', 'E': 'ೈ',
        'o': 'ೊ', 'O': 'ೌ',
    }
    
    # Special patterns
    special_patterns = {
        'eV': 'ೇ',   # ē vowel sign
        'oV': 'ೋ',   # ō vowel sign
        'lY': 'ಳ',   # retroflex l
        'rY': 'ಱ',   # special r
    }
    
    result = []
    i = 0
    
    while i < len(text):
        # Try special patterns first (2-3 chars)
        matched = False
        for pattern_len in [3, 2]:
            if i + pattern_len <= len(text):
                pattern = text[i:i+pattern_len]
                if pattern in special_patterns:
                    result.append(special_patterns[pattern])
                    i += pattern_len
                    matched = True
                    break
        
        if matched:
            continue
        
        char = text[i]
        
        # Check if it's a consonant
        if char in consonants:
            # Look ahead for vowel
            if i + 1 < len(text):
                next_char = text[i + 1]
                
                # Check for two-char vowel patterns (eV, oV)
                if i + 2 < len(text):
                    two_char_vowel = text[i+1:i+3]
                    if two_char_vowel in ['eV', 'oV']:
                        # Consonant + long vowel
                        result.append(consonants[char])
                        result.append(special_patterns[two_char_vowel])
                        i += 3
                        continue
                
                # Check for single-char vowel sign
                if next_char in vowel_signs:
                    # Consonant + vowel sign
                    result.append(consonants[char])
                    result.append(vowel_signs[next_char])
                    i += 2
                    continue
                elif next_char == 'a':
                    # Consonant + inherent 'a' (just the consonant)
                    result.append(consonants[char])
                    i += 2
                    continue
                elif next_char in consonants:
                    # Consonant + consonant = add virama
                    result.append(consonants[char])
                    result.append('್')  # Virama/halant
                    i += 1
                    continue
            
            # Consonant at end of word = add virama
            if i == len(text) - 1:
                result.append(consonants[char])
                result.append('್')
                i += 1
                continue
            
            # Default: consonant with inherent 'a'
            result.append(consonants[char])
            i += 1
            continue
        
        # Check if it's an independent vowel
        if char in independent_vowels:
            result.append(independent_vowels[char])
            i += 1
            continue
        
        # Special characters
        if char == 'M':
            result.append('ಂ')  # Anusvara
            i += 1
            continue
        elif char == 'H':
            result.append('ಃ')  # Visarga
            i += 1
            continue
        
        # Default: keep character as-is
        result.append(char)
        i += 1
    
    return ''.join(result)

def is_kannada_text(text):
    """
    Check if text contains Kannada Unicode characters
    
    Args:
        text (str): Text to check
    
    Returns:
        bool: True if text contains Kannada characters
    """
    kannada_range = range(0x0C80, 0x0CFF)  # Kannada Unicode block
    return any(ord(char) in kannada_range for char in text)

def normalize_text(text):
    """
    Normalize text - convert Kannada to WX if needed
    
    Args:
        text (str): Input text (Kannada or WX)
    
    Returns:
        str: Normalized WX text
    """
    if is_kannada_text(text):
        return kannada_to_wx(text)
    return text

if __name__ == "__main__":
    # Test conversions
    print("=" * 70)
    print("Kannada ↔ WX Converter Test")
    print("=" * 70)
    print()
    
    # Test cases
    test_cases = [
        ("ಮರ", "mara", "tree"),
        ("ಮರವು", "maravu", "tree (nominative)"),
        ("ಹುಡುಗ", "huduga", "boy"),
        ("ಹುಡುಗನು", "huduganu", "boy (nominative)"),
        ("ನನಗೆ", "nanage", "to me"),
        ("ಅವನು", "avanu", "he"),
        ("ಬರುತ್ತಾನೆ", "baruwaane", "comes"),
    ]
    
    print("Kannada → WX Conversion:")
    print("-" * 70)
    for kannada, expected_wx, meaning in test_cases:
        converted = kannada_to_wx(kannada)
        status = "✅" if converted == expected_wx else "❌"
        print(f"{status} {kannada:15} → {converted:15} (expected: {expected_wx:15}) [{meaning}]")
    
    print()
    print("=" * 70)
    print(f"\n✅ Converter ready to use!")
    print(f"   is_kannada_text('ಮರ'): {is_kannada_text('ಮರ')}")
    print(f"   is_kannada_text('mara'): {is_kannada_text('mara')}")
