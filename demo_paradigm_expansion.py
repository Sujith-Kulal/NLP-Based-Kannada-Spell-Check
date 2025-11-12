#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script to show full paradigm generation capability

Usage:
    python demo_paradigm_expansion.py <root_word>
    
Examples:
    python demo_paradigm_expansion.py kadi
    python demo_paradigm_expansion.py baru
    python demo_paradigm_expansion.py kAyu
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker


def demo_paradigm_expansion(root):
    """Demonstrate full paradigm expansion for a given root"""
    print("\n" + "="*70)
    print(f"PARADIGM EXPANSION DEMO: {root}")
    print("="*70)
    
    print("\nInitializing spell checker...")
    checker = EnhancedSpellChecker()
    
    print("\n" + "="*70)
    print(f"Expanding paradigms for: {root}")
    print("="*70)
    
    # Check if root exists in any category
    found_in = []
    for cat in ["verb", "noun", "pronoun"]:
        if root in checker.category_paradigms[cat]:
            found_in.append(cat)
            rule_count = len(checker.category_paradigms[cat][root])
            print(f"  ✅ Found in {cat} category with {rule_count} rules")
    
    if not found_in:
        print(f"  ❌ Root '{root}' not found in any paradigm category")
        print("\n  Available roots in each category:")
        for cat in ["verb", "noun", "pronoun"]:
            roots = list(checker.category_paradigms[cat].keys())
            if roots:
                print(f"\n    {cat.upper()} ({len(roots)} roots):")
                for r in sorted(roots)[:10]:
                    print(f"      - {r}")
                if len(roots) > 10:
                    print(f"      ... and {len(roots) - 10} more")
        return
    
    # Generate all paradigm forms
    print(f"\n{'='*70}")
    print("GENERATING ALL PARADIGM FORMS")
    print("="*70)
    
    all_forms = checker.expand_all_paradigms(root)
    
    print(f"\n  ✅ Generated {len(all_forms)} inflected forms")
    
    # Show forms by category if available
    print(f"\n{'='*70}")
    print("SAMPLE FORMS (First 50)")
    print("="*70)
    
    sorted_forms = sorted(list(all_forms))
    for i, form in enumerate(sorted_forms[:50], 1):
        print(f"  {i:3d}. {form}")
    
    if len(all_forms) > 50:
        print(f"\n  ... and {len(all_forms) - 50} more forms")
    
    # Verify they're in the dictionary
    print(f"\n{'='*70}")
    print("DICTIONARY VERIFICATION")
    print("="*70)
    
    in_dict_count = sum(1 for form in all_forms if form in checker.all_words)
    print(f"  ✅ {in_dict_count}/{len(all_forms)} forms are in the dictionary")
    
    # Show some specific examples
    print(f"\n{'='*70}")
    print("EXAMPLE INFLECTIONS")
    print("="*70)
    
    # Group by common patterns
    examples = {
        'Past tense (3rd person)': [f for f in sorted_forms if 'xa' in f[:10]][:5],
        'Future tense': [f for f in sorted_forms if 'uwwa' in f or 'yuva' in f][:5],
        'Other forms': sorted_forms[:5]
    }
    
    for category, forms in examples.items():
        if forms:
            print(f"\n  {category}:")
            for form in forms:
                print(f"    - {form}")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("\n" + "="*70)
        print("PARADIGM EXPANSION DEMO")
        print("="*70)
        print("\nUsage:")
        print("  python demo_paradigm_expansion.py <root_word>")
        print("\nExamples:")
        print("  python demo_paradigm_expansion.py kadi")
        print("  python demo_paradigm_expansion.py baru")
        print("  python demo_paradigm_expansion.py kAyu")
        print("\n" + "="*70)
        
        # Show available roots
        print("\nLoading paradigm data...")
        checker = EnhancedSpellChecker()
        
        print("\n" + "="*70)
        print("AVAILABLE ROOT WORDS")
        print("="*70)
        
        for cat in ["verb", "noun", "pronoun"]:
            roots = list(checker.category_paradigms[cat].keys())
            if roots:
                print(f"\n{cat.upper()} ({len(roots)} roots):")
                for r in sorted(roots)[:15]:
                    print(f"  - {r}")
                if len(roots) > 15:
                    print(f"  ... and {len(roots) - 15} more")
        
        sys.exit(1)
    
    root = sys.argv[1]
    demo_paradigm_expansion(root)


if __name__ == "__main__":
    main()
