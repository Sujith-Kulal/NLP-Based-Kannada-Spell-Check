#!/usr/bin/env python3
"""
Demo: Morphological Paradigm Generation for Kannada Spell Correction
----------------------------------------------------------------------
This demo shows how the new paradigm_logic.py module works both:
1. Standalone (without spell checker)
2. Integrated with enhanced_spell_checker.py
"""

print("=" * 80)
print("DEMO: MORPHOLOGICAL PARADIGM GENERATION")
print("=" * 80)

# ============================================================================
# DEMO 1: Standalone Usage (Just paradigm_logic.py)
# ============================================================================

print("\n\n" + "🔹" * 40)
print("DEMO 1: Standalone Paradigm Generation")
print("🔹" * 40)

from paradigm_logic import (
    apply_paradigm,
    generate_paradigms,
    initialize_paradigm_system,
    get_all_surface_forms,
)

# Example 1: Generate single paradigm form
print("\n📝 Example 1: Single paradigm transformation")
print("-" * 80)
base = "avaru"
variant = "ivaru"
rule = "annu_u#"

result = apply_paradigm(base, variant, rule)
print(f"Base: {base}")
print(f"Variant: {variant}")
print(f"Rule: {rule}")
print(f"Result: {result}")

# Example 2: Generate multiple forms for multiple variants
print("\n\n📝 Example 2: Multiple variants with multiple rules")
print("-" * 80)
base = "avaru"
variants = ["ivaru", "yAru", "evaru"]
rules = ["annu_u#", "inda_u#", "ige_u#", "a_u#"]

paradigms = generate_paradigms(base, variants, rules)
print(f"\nBase word: {base}")
print(f"Rules applied: {len(rules)}")
print(f"\nGenerated paradigms:\n")
for variant, forms in paradigms.items():
    print(f"  {variant}:")
    for i, form in enumerate(forms, 1):
        print(f"    {i}. {form}")

# Example 3: Initialize complete system
print("\n\n📝 Example 3: Full system initialization (startup)")
print("-" * 80)
print("Initializing complete paradigm system...")
all_paradigms = initialize_paradigm_system()

print(f"\n✅ System initialized successfully!")
print(f"   Total variant paradigms: {len(all_paradigms):,}")

# Extract all surface forms
all_forms = get_all_surface_forms(all_paradigms)
print(f"   Total unique surface forms: {len(all_forms):,}")

# Show samples
print(f"\n📋 Sample paradigms:")
for variant, forms in list(all_paradigms.items())[:5]:
    print(f"   {variant}: {forms[:4]}...")

print(f"\n📋 Sample surface forms (first 20):")
sample_forms = list(all_forms)[:20]
for i in range(0, len(sample_forms), 4):
    print(f"   {', '.join(sample_forms[i:i+4])}")


# ============================================================================
# DEMO 2: Integrated with Spell Checker
# ============================================================================

print("\n\n" + "🔹" * 40)
print("DEMO 2: Integration with Spell Checker")
print("🔹" * 40)

try:
    from enhanced_spell_checker import SimplifiedSpellChecker
    
    print("\n🚀 Initializing spell checker with morphological paradigms...")
    checker = SimplifiedSpellChecker(use_paradigm_generator=True)
    
    print("\n✅ Spell checker initialized successfully!")
    
    # Check if morphological paradigms were loaded
    if hasattr(checker, 'morphological_paradigms') and checker.morphological_paradigms:
        print(f"   Morphological paradigms loaded: {len(checker.morphological_paradigms):,} variants")
    
    # Check total dictionary size
    print(f"   Total words in dictionary: {len(checker.all_words):,}")
    
    # Test some words
    print("\n📝 Testing word lookups:")
    test_words = ["ivaru", "ivarannu", "ivarinda", "yAru", "yArannu", "nagu", "nagina"]
    
    for word in test_words:
        in_dict = word in checker.all_words
        status = "✅" if in_dict else "❌"
        print(f"   {status} '{word}' in dictionary: {in_dict}")
    
    print("\n📝 Testing spell correction (WX format):")
    test_sentences = [
        "ivaru baruwwAre",
        "yAru hewwAre",
        "nagu maguvina",
    ]
    
    for sentence in test_sentences:
        print(f"\n   Input: {sentence}")
        # Note: This is a simplified check - actual spell checking logic in the checker
        words = sentence.split()
        for word in words:
            in_dict = word in checker.all_words
            status = "✅ valid" if in_dict else "❌ unknown"
            print(f"      {word}: {status}")

except Exception as e:
    print(f"\n⚠️ Could not initialize spell checker: {e}")
    print("   (This is expected if extended_dictionary.pkl is missing)")
    import traceback
    traceback.print_exc()


# ============================================================================
# DEMO 3: Custom Configuration
# ============================================================================

print("\n\n" + "🔹" * 40)
print("DEMO 3: Custom Paradigm Configuration")
print("🔹" * 40)

# Define custom base paradigms and variants
custom_base_paradigms = {
    "magu": [
        "ina_u#",       # magu → magina
        "annu_u#",      # magu → magannu
        "ige_u#",       # magu → magige
        "alli_u#",      # magu → magalli
    ],
}

custom_variant_map = {
    "magu": ["nagu", "tagu"],  # Custom variants
}

print("\n📝 Custom configuration:")
print(f"   Base words: {list(custom_base_paradigms.keys())}")
print(f"   Variants: {custom_variant_map}")
print(f"   Rules per base: {[len(rules) for rules in custom_base_paradigms.values()]}")

# Generate with custom config
custom_paradigms = {}
for base, rules in custom_base_paradigms.items():
    variants = custom_variant_map.get(base, [])
    generated = generate_paradigms(base, variants, rules)
    custom_paradigms.update(generated)

print(f"\n✅ Generated {len(custom_paradigms)} custom paradigms")
for variant, forms in custom_paradigms.items():
    print(f"   {variant}: {forms}")


# ============================================================================
# Summary
# ============================================================================

print("\n\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
✅ Morphological paradigm generation system is working!

📝 What you can do:
   1. Use paradigm_logic.py standalone for paradigm generation
   2. Integrate with enhanced_spell_checker.py automatically
   3. Customize base paradigms and variants as needed
   4. Add new rules for different morphological transformations

📂 Files created:
   • paradigm_logic.py - Core morphological logic
   • demo_paradigm_logic.py - This demo file

🔧 Integration:
   • enhanced_spell_checker.py - Already integrated!
   • Paradigms load automatically during spell checker initialization
   • All surface forms added to dictionary for spell checking

🚀 Next steps:
   1. Add more base paradigms (nouns, verbs, adjectives)
   2. Define more morphological rules
   3. Test with real Kannada text
   4. Fine-tune transformations based on linguistic rules
""")

print("=" * 80)
print("Demo completed successfully! ✅")
print("=" * 80)
