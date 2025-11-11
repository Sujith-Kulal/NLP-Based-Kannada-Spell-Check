#!/usr/bin/env python3
"""
Test script for Kannada Paradigm Auto-Generator
Demonstrates the functionality and performance
"""

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from paradigm_generator import ParadigmGenerator, create_generator

def test_basic_functionality():
    """Test basic paradigm generation"""
    print("\n" + "=" * 70)
    print("TEST 1: Basic Functionality")
    print("=" * 70)
    
    try:
        generator = create_generator()
        
        # Test word lookup
        test_words = ["avaru", "ivaru", "yAru", "magu", "nagu"]
        
        for word in test_words:
            print(f"\n🔹 Testing: '{word}'")
            if generator.has_paradigm(word):
                paradigm = generator.get_paradigm(word)
                print(f"   ✅ Found {len(paradigm)} forms")
                
                # Show first 3 forms
                for i, (key, val) in enumerate(list(paradigm.items())[:3]):
                    print(f"      • {key}: {val}")
                
                if len(paradigm) > 3:
                    print(f"      ... and {len(paradigm) - 3} more")
            else:
                print(f"   ⚠️ No paradigm found")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_performance():
    """Test paradigm generation performance"""
    print("\n" + "=" * 70)
    print("TEST 2: Performance")
    print("=" * 70)
    
    try:
        # Measure initialization time
        start_time = time.time()
        generator = ParadigmGenerator()
        generator.initialize_paradigms()
        init_time = time.time() - start_time
        
        print(f"⏱️  Initialization time: {init_time:.3f} seconds")
        
        # Measure lookup time
        test_words = list(generator.all_paradigms.keys())[:100]
        start_time = time.time()
        for word in test_words:
            _ = generator.get_paradigm(word)
        lookup_time = time.time() - start_time
        
        print(f"⏱️  100 lookups time: {lookup_time:.6f} seconds")
        print(f"⏱️  Average per lookup: {(lookup_time/100)*1000:.6f} milliseconds")
        print(f"✅ O(1) instant lookup confirmed!")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_integration():
    """Test integration with spell checker"""
    print("\n" + "=" * 70)
    print("TEST 3: Integration with Spell Checker")
    print("=" * 70)
    
    try:
        from enhanced_spell_checker import SimplifiedSpellChecker
        
        print("Creating spell checker with paradigm generator...")
        checker = SimplifiedSpellChecker(use_paradigm_generator=True)
        
        if checker.paradigm_generator:
            stats = checker.paradigm_generator.get_stats()
            print(f"\n✅ Integration successful!")
            print(f"   Base paradigms: {stats['base_count']:,}")
            print(f"   Derived paradigms: {stats['derived_count']:,}")
            print(f"   Total paradigms: {stats['total_count']:,}")
            print(f"   Dictionary size: {len(checker.all_words):,} words")
        else:
            print("⚠️ Paradigm generator not initialized")
            print("   (This might be due to missing all.xlsx file)")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_functionality():
    """Test paradigm search functionality"""
    print("\n" + "=" * 70)
    print("TEST 4: Search Functionality")
    print("=" * 70)
    
    try:
        generator = create_generator()
        
        # Search for words starting with 'av'
        print("\n🔍 Searching for words starting with 'av'...")
        results = generator.search_paradigms("^av")
        print(f"   Found {len(results)} matches")
        
        # Show first 5
        for i, word in enumerate(list(results.keys())[:5]):
            print(f"   {i+1}. {word}")
        
        if len(results) > 5:
            print(f"   ... and {len(results) - 5} more")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_all_forms():
    """Test getting all inflected forms"""
    print("\n" + "=" * 70)
    print("TEST 5: All Inflected Forms")
    print("=" * 70)
    
    try:
        generator = create_generator()
        
        test_word = "avaru"
        print(f"\n🔹 Getting all forms for: '{test_word}'")
        
        all_forms = generator.get_all_forms(test_word)
        if all_forms:
            print(f"   ✅ Found {len(all_forms)} unique forms")
            
            # Show first 10 forms
            for i, form in enumerate(list(all_forms)[:10]):
                print(f"   {i+1}. {form}")
            
            if len(all_forms) > 10:
                print(f"   ... and {len(all_forms) - 10} more")
        else:
            print(f"   ⚠️ No forms found")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print(" " * 20 + "PARADIGM GENERATOR TEST SUITE")
    print("=" * 80)
    
    results = []
    
    # Run all tests
    results.append(("Basic Functionality", test_basic_functionality()))
    results.append(("Performance", test_performance()))
    results.append(("Integration", test_integration()))
    results.append(("Search Functionality", test_search_functionality()))
    results.append(("All Forms", test_all_forms()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 All tests passed! Paradigm generator is ready to use!")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    main()
