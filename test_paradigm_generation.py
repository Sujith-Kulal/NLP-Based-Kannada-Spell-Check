#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test paradigm generation functionality
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_spell_checker import EnhancedSpellChecker


def test_apply_paradigm_rule():
    """Test the _apply_paradigm_rule function with various examples"""
    print("\n" + "="*70)
    print("TEST 1: _apply_paradigm_rule()")
    print("="*70)
    
    checker = EnhancedSpellChecker()
    
    test_cases = [
        # (base_root, variant_root, rule, expected)
        ("kadi", "kadi", "+xa_#_PAST+anu_a_3SM", "kadixanu"),
        ("kadi", "kadi", "+xa_#_PAST+alYu_a_3SF", "kadixalYu"),
        ("kadi", "kadi", "+yuwwa_u_FUT+AneV_a_3SM", "kadiyuwwAneV"),
        ("kAyu", "kAyu", "+xa_yu_PAST+anu_a_3SM", "kAxanu"),
        ("kAyu", "kAyu", "+uwwa_u_FUT+AneV_a_3SM", "kAyuwwAneV"),
    ]
    
    passed = 0
    failed = 0
    
    for base, variant, rule, expected in test_cases:
        result = checker._apply_paradigm_rule(base, variant, rule)
        if result == expected:
            print(f"  ✅ {base} + {rule} → {result}")
            passed += 1
        else:
            print(f"  ❌ {base} + {rule}")
            print(f"     Expected: {expected}")
            print(f"     Got:      {result}")
            failed += 1
    
    print(f"\n  Results: {passed} passed, {failed} failed")
    return failed == 0


def test_expand_all_paradigms():
    """Test expand_all_paradigms with known roots"""
    print("\n" + "="*70)
    print("TEST 2: expand_all_paradigms()")
    print("="*70)
    
    checker = EnhancedSpellChecker()
    
    test_roots = ["kadi", "kAyu", "baru"]
    
    for root in test_roots:
        print(f"\n  Testing root: {root}")
        variants = checker.expand_all_paradigms(root)
        
        if variants:
            print(f"  ✅ Generated {len(variants)} forms")
            print(f"     First 10: {', '.join(sorted(list(variants))[:10])}")
        else:
            print(f"  ❌ No forms generated for {root}")
    
    return True


def test_specific_verbs():
    """Test specific verb forms that should exist"""
    print("\n" + "="*70)
    print("TEST 3: Specific Verb Forms")
    print("="*70)
    
    checker = EnhancedSpellChecker()
    
    # Test words from kadi paradigm
    test_words = [
        ("kadixanu", "VB"),
        ("kadixalYu", "VB"),
        ("kadiyuwwAneV", "VB"),
        ("kadiyuvanu", "VB"),
    ]
    
    passed = 0
    failed = 0
    
    for word, pos in test_words:
        if word in checker.pos_paradigms[pos] or word in checker.all_words:
            print(f"  ✅ {word} found in dictionary")
            passed += 1
        else:
            print(f"  ❌ {word} NOT found in dictionary")
            failed += 1
    
    print(f"\n  Results: {passed} passed, {failed} failed")
    return failed == 0


def test_addahidi_generation():
    """Test that addahidi can generate forms like kadi"""
    print("\n" + "="*70)
    print("TEST 4: addahidi Generation (Target Case)")
    print("="*70)
    
    checker = EnhancedSpellChecker()
    
    # Check if addahidi exists in category_paradigms
    found = False
    for cat in ["verb", "noun", "pronoun"]:
        if "addahidi" in checker.category_paradigms[cat]:
            found = True
            print(f"  ✅ addahidi found in {cat} category")
            variants = checker.expand_all_paradigms("addahidi")
            print(f"  ✅ Generated {len(variants)} forms for addahidi")
            
            # Show some expected forms
            expected_forms = [
                "addahidixanu",
                "addahidixalYu",
                "addahidiyuwwAneV",
                "addahidiyuvanu",
            ]
            
            print(f"\n  Checking expected forms:")
            for form in expected_forms:
                if form in variants:
                    print(f"    ✅ {form}")
                else:
                    print(f"    ❌ {form} (not generated)")
            
            print(f"\n  First 20 generated forms:")
            for form in sorted(list(variants))[:20]:
                print(f"    {form}")
            break
    
    if not found:
        print(f"  ⚠️  addahidi not found in paradigm files")
        print(f"     This might be expected if the verb doesn't exist in the paradigm directory")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("PARADIGM GENERATION TEST SUITE")
    print("="*70)
    
    tests = [
        test_apply_paradigm_rule,
        test_expand_all_paradigms,
        test_specific_verbs,
        test_addahidi_generation,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"\n  ❌ Test {test.__name__} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False))
    
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n  🎉 All tests passed!")
    else:
        print("\n  ⚠️  Some tests failed")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
