#!/usr/bin/env python3
"""
Pure Morphological Paradigm Generation Logic
---------------------------------------------
Core paradigm transformation engine for Kannada spell correction.
No Flask, no server - just pure transformation logic.

This module provides functions to generate paradigm forms for variant words
based on morphological transformation rules.
"""

import re
from typing import Dict, List, Optional, Set


def apply_paradigm(base_root: str, variant_root: str, rule: str) -> str:
    """
    Core morphological transformation logic.
    Generates derived word (surface form) for variant based on rule.

    Args:
        base_root (str): base form, e.g. 'avaru'
        variant_root (str): variant word, e.g. 'ivaru'
        rule (str): morphological rule like 'annu_u#' or 'alli_a#'

    Returns:
        str: transformed word (new surface form)
    
    Examples:
        >>> apply_paradigm('avaru', 'ivaru', 'annu_u#')
        'ivarannu'
        >>> apply_paradigm('amma', 'amma', 'alli_a#')
        'ammalli'
        >>> apply_paradigm('akka', 'akka', 'nalli_a#')
        'akkanalli'
    
    Rule Format:
        - 'suffix_old#' → Replace 'old' ending with 'suffix'
        - 'suffix_#' → Just add 'suffix' directly
        
    Examples:
        - 'annu_u#' → Remove 'u', add 'annu'
        - 'alli_a#' → Remove 'a', add 'alli'
        - 'nalli_a#' → Remove 'a', add 'nalli'
    """
    word = variant_root
    
    # Remove trailing '#' marker
    rule = rule.rstrip('#')
    
    # Split rule into new_suffix and old_suffix
    if '_' in rule:
        new_suffix, old_suffix = rule.split('_', 1)
    else:
        # No underscore - just add the suffix
        return word + rule
    
    # If old_suffix is empty or just '_', add new_suffix directly
    if not old_suffix or old_suffix == '':
        return word + new_suffix
    
    # Replace old suffix with new suffix
    if old_suffix and word.endswith(old_suffix):
        # Remove old suffix and add new suffix
        word = word[:-len(old_suffix)] + new_suffix
    else:
        # Old suffix not found - just add new suffix
        word = word + new_suffix
    
    return word


def generate_paradigms(base_root: str, variants: List[str], rules: List[str]) -> Dict[str, List[str]]:
    """
    Generates paradigms for multiple variant words of a base.

    Args:
        base_root (str): e.g. 'avaru'
        variants (list): e.g. ['ivaru', 'yAru']
        rules (list): e.g. ['a_i#', 'a_yA#']

    Returns:
        dict: { variant: [transformed forms] }
    
    Examples:
        >>> generate_paradigms('avaru', ['ivaru', 'yAru'], ['annu_u#', 'inda_u#'])
        {'ivaru': ['ivarannu', 'ivarinda'], 'yAru': ['yArannu', 'yArinda']}
    """
    all_forms = {}
    for variant in variants:
        forms = []
        for rule in rules:
            try:
                surface = apply_paradigm(base_root, variant, rule)
                forms.append(surface)
            except Exception as e:
                print(f"⚠️ Error generating for {variant} with rule '{rule}': {e}")
        all_forms[variant] = forms
    return all_forms


def generate_all_paradigms_from_config(base_paradigms: Dict[str, List[str]], 
                                       variant_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Auto-generate paradigms for all base words and their variants.
    This is the main function to call during system startup.

    Args:
        base_paradigms: Dict mapping base words to their morphological rules
                       e.g. {"avaru": ["annu_u#", "inda_u#"], "magu": ["u_ina#"]}
        variant_map: Dict mapping base words to their variants
                    e.g. {"avaru": ["ivaru", "yAru"], "magu": ["nagu"]}

    Returns:
        Dict mapping all variant words to their paradigm forms
    
    Example:
        >>> base_paradigms = {"avaru": ["annu_u#", "inda_u#"]}
        >>> variant_map = {"avaru": ["ivaru", "yAru"]}
        >>> result = generate_all_paradigms_from_config(base_paradigms, variant_map)
        >>> print(result)
        {'ivaru': ['ivarannu', 'ivarinda'], 'yAru': ['yArannu', 'yArinda']}
    """
    all_paradigms = {}
    
    for base, rules in base_paradigms.items():
        variants = variant_map.get(base, [])
        if variants:
            generated = generate_paradigms(base, variants, rules)
            all_paradigms.update(generated)
    
    return all_paradigms


def get_all_surface_forms(paradigms_dict: Dict[str, List[str]]) -> Set[str]:
    """
    Extract all unique surface forms from generated paradigms.
    Useful for adding to spell checker dictionary.

    Args:
        paradigms_dict: Output from generate_all_paradigms_from_config()

    Returns:
        Set of all unique surface forms
    
    Example:
        >>> paradigms = {'ivaru': ['ivarannu', 'ivarinda'], 'yAru': ['yArannu', 'yArinda']}
        >>> forms = get_all_surface_forms(paradigms)
        >>> print(sorted(forms))
        ['ivarannu', 'ivarinda', 'yArannu', 'yArinda']
    """
    all_forms = set()
    for variant, forms in paradigms_dict.items():
        all_forms.add(variant)  # Add the variant itself
        all_forms.update(forms)  # Add all its paradigm forms
    return all_forms


def extract_rules_from_paradigm_file(file_path: str) -> List[str]:
    """
    Extract morphological rules from a paradigm text file.
    
    Expected file format:
        surface_form rule
        surface_form rule
        ...
    
    Args:
        file_path: Path to paradigm file
    
    Returns:
        List of unique rules found in the file
    """
    rules = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) >= 2:
                    rule = parts[1]
                    rules.add(rule)
    except FileNotFoundError:
        print(f"⚠️ File not found: {file_path}")
    except Exception as e:
        print(f"⚠️ Error reading {file_path}: {e}")
    
    return list(rules)


# ==============================================================
# EXAMPLE CONFIGURATION
# ==============================================================

# Default base paradigms (you can customize this)
DEFAULT_BASE_PARADIGMS = {
    # Pronouns
    "avaru": [
        "annu_u#",      # avaru → avarannu (accusative)
        "inda_u#",      # avaru → avarinda (ablative)
        "ige_u#",       # avaru → avarige (dative)
        "a_u#",         # avaru → avara (genitive)
        "alli_u#",      # avaru → avaralli (locative) ✅
    ],
    "avanu": [
        "annu_u#",
        "inda_u#",
        "ige_u#",
        "a_u#",
        "alli_u#",      # ✅ locative
    ],
    "avalYu": [
        "annu_YU#",
        "inda_YU#",
        "ige_YU#",
        "a_YU#",
        "alli_YU#",     # ✅ locative
    ],
    
    # Nouns - Common base words
    "akka": [
        "nnu_a#",       # akka → akkannu (accusative)
        "inda_a#",      # akka → akkinda (ablative)
        "ige_a#",       # akka → akkige (dative)
        "na_a#",        # akka → akkana (genitive)
        "analli_a#",    # akka → akkanalli (locative) ✅✅✅ THIS IS THE KEY!
    ],
    "amma": [
        "annu_a#",      # amma → ammannu (accusative)
        "inda_a#",      # amma → amminda (ablative)
        "ige_a#",       # amma → ammige (dative)
        "ana_a#",       # amma → ammana (genitive)
        "analli_a#",    # amma → ammanalli (locative) ✅✅✅ YOUR REQUEST!
    ],
    "avva": [
        "annu_a#",      # avva → avvannu
        "inda_a#",      # avva → avvinda
        "ige_a#",       # avva → avvige
        "ana_a#",       # avva → avvana
        "analli_a#",    # avva → avvanalli (locative) ✅
    ],
    "magu": [
        "ina_u#",       # magu → magina
        "annu_u#",      # magu → magannu
        "ige_u#",       # magu → magige
        "alli_u#",      # magu → magalli (locative) ✅
        "uanalli_u#",   # magu → maguanalli (locative variant) ✅
    ],
    "huduga": [
        "annu_a#",      # huduga → hudugannu
        "inda_a#",      # huduga → huduginda
        "ige_a#",       # huduga → hudugige
        "ana_a#",       # huduga → hudugana
        "analli_a#",    # huduga → huduganalli (locative) ✅
    ],
}

# Default variant mapping
DEFAULT_VARIANT_MAP = {
    "avaru": ["ivaru", "yAru", "evaru"],
    "avanu": ["ivanu", "yAvanu", "evanu"],
    "avalYu": ["ivalYu", "yAvalYu", "evalYu"],
    "akka": ["akka"],        # Base form as variant
    "amma": ["amma"],        # ✅ YOUR KEY WORD!
    "avva": ["avva"],
    "magu": ["nagu"],
    "huduga": ["hudugi", "magalu"],
}


def initialize_paradigm_system(base_paradigms: Optional[Dict] = None,
                               variant_map: Optional[Dict] = None) -> Dict[str, List[str]]:
    """
    Main initialization function - call this during system startup.
    
    Args:
        base_paradigms: Optional custom paradigm configuration
        variant_map: Optional custom variant mapping
    
    Returns:
        Complete paradigm dictionary ready for use
    
    Example:
        >>> paradigms = initialize_paradigm_system()
        >>> print(f"Generated {len(paradigms)} variant paradigms")
        >>> print(f"Total surface forms: {len(get_all_surface_forms(paradigms))}")
    """
    if base_paradigms is None:
        base_paradigms = DEFAULT_BASE_PARADIGMS
    if variant_map is None:
        variant_map = DEFAULT_VARIANT_MAP
    
    print("🚀 Initializing morphological paradigm system...")
    paradigms = generate_all_paradigms_from_config(base_paradigms, variant_map)
    
    surface_forms = get_all_surface_forms(paradigms)
    
    print(f"✅ Generated {len(paradigms)} variant paradigms")
    print(f"✅ Total unique surface forms: {len(surface_forms)}")
    
    return paradigms


# ==============================================================
# COMMAND-LINE TESTING
# ==============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MORPHOLOGICAL PARADIGM GENERATION - DEMO")
    print("=" * 70)
    
    # Test 1: Single paradigm generation
    print("\n📝 Test 1: Single paradigm generation")
    print("-" * 70)
    base = "avaru"
    variants = ["ivaru", "yAru"]
    rules = ["annu_u#", "inda_u#", "ige_u#"]
    
    result = generate_paradigms(base, variants, rules)
    for variant, forms in result.items():
        print(f"\n{variant}:")
        for i, form in enumerate(forms, 1):
            print(f"  {i}. {form}")
    
    # Test 2: Full system initialization
    print("\n\n📝 Test 2: Full system initialization")
    print("-" * 70)
    all_paradigms = initialize_paradigm_system()
    
    # Show sample
    print("\n📋 Sample generated paradigms:")
    for variant, forms in list(all_paradigms.items())[:3]:
        print(f"\n{variant}: {forms[:3]}...")
    
    # Test 3: Extract all surface forms
    print("\n\n📝 Test 3: All surface forms")
    print("-" * 70)
    all_forms = get_all_surface_forms(all_paradigms)
    print(f"Total unique forms: {len(all_forms)}")
    print(f"Sample forms: {list(all_forms)[:10]}")
    
    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)
