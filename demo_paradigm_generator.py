#!/usr/bin/env python3
"""
Quick Demo: Paradigm Generator in Action
Shows the power of automatic paradigm expansion
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print(" " * 25 + "PARADIGM GENERATOR DEMO")
print("=" * 80)

# Demo 1: Standalone Paradigm Generator
print("\n📖 DEMO 1: Standalone Paradigm Generator\n")
print("-" * 80)

try:
    from paradigm_generator import create_generator
    
    print("Creating paradigm generator...")
    generator = create_generator()
    
    print("\n✅ SUCCESS! Let's explore some paradigms:\n")
    
    # Example 1: Pronouns
    print("Example 1: Pronoun Paradigms")
    print("-" * 40)
    for word in ["avaru", "ivaru", "yAru"]:
        if generator.has_paradigm(word):
            forms = generator.get_paradigm(word)
            print(f"• {word}: {len(forms)} forms")
        else:
            print(f"• {word}: Not found")
    
    # Example 2: Check related words
    print("\nExample 2: Related Words")
    print("-" * 40)
    related = generator.get_related_words("avaru")
    print(f"avaru → {', '.join(related) if related else 'None found'}")
    
    # Example 3: Statistics
    print("\nExample 3: Generation Statistics")
    print("-" * 40)
    stats = generator.get_stats()
    for key, value in stats.items():
        print(f"• {key.replace('_', ' ').title()}: {value:,}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("   Make sure check_pos/all.xlsx exists!")

# Demo 2: Integrated with Spell Checker
print("\n\n" + "=" * 80)
print("📝 DEMO 2: Integration with Spell Checker")
print("=" * 80 + "\n")

try:
    from enhanced_spell_checker import SimplifiedSpellChecker
    
    print("Creating spell checker with paradigm generator...")
    checker = SimplifiedSpellChecker(use_paradigm_generator=True)
    
    if checker.paradigm_generator:
        print("\n✅ Paradigm generator integrated successfully!")
        print(f"   Dictionary size: {len(checker.all_words):,} words")
        
        # Test spell checking
        print("\nTesting spell checking with paradigm forms:")
        print("-" * 40)
        
        test_words = ["avarannu", "ivarannu", "yArannu"]
        for word in test_words:
            is_valid = word in checker.all_words
            status = "✓" if is_valid else "✗"
            print(f"{status} {word}: {'Valid' if is_valid else 'Not found'}")
    else:
        print("⚠️  Paradigm generator not loaded")
        print("   (Spell checker works but without auto-generated paradigms)")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Demo 3: Performance Comparison
print("\n\n" + "=" * 80)
print("⚡ DEMO 3: Performance Test")
print("=" * 80 + "\n")

try:
    import time
    from paradigm_generator import ParadigmGenerator
    
    # Test initialization speed
    print("Testing initialization speed...")
    start = time.time()
    gen = ParadigmGenerator()
    gen.initialize_paradigms()
    init_time = time.time() - start
    
    print(f"✅ Initialized in {init_time:.3f} seconds")
    
    # Test lookup speed
    print("\nTesting lookup speed (1000 lookups)...")
    words = list(gen.all_paradigms.keys())[:1000]
    start = time.time()
    for word in words:
        _ = gen.get_paradigm(word)
    lookup_time = time.time() - start
    
    print(f"✅ 1000 lookups in {lookup_time:.6f} seconds")
    print(f"   Average: {(lookup_time/1000)*1000:.6f} ms per lookup")
    print(f"   Speed: O(1) instant dictionary access ⚡")
    
except Exception as e:
    print(f"❌ Error: {e}")

# Summary
print("\n\n" + "=" * 80)
print("📚 SUMMARY")
print("=" * 80)
print("""
The Paradigm Generator provides:

✅ Automatic paradigm expansion from base forms
✅ Instant O(1) lookups for all word forms
✅ Seamless integration with spell checker
✅ High performance (1000+ lookups per second)
✅ Memory-efficient in-memory storage

Usage:
------
Standalone:
    from paradigm_generator import create_generator
    generator = create_generator()
    paradigm = generator.get_paradigm("ivaru")

Integrated:
    from enhanced_spell_checker import SimplifiedSpellChecker
    checker = SimplifiedSpellChecker(use_paradigm_generator=True)
    result = checker.check_text("your text here")

For more info, see: PARADIGM_GENERATOR_README.md
""")

print("=" * 80)
print(" " * 30 + "DEMO COMPLETE!")
print("=" * 80)
