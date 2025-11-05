#!/usr/bin/env python3
"""
Test Script for Kannada Smart Keyboard
======================================

This script helps verify that all components are working correctly
before running the full smart keyboard service.
"""

import sys
import os

def test_imports():
    """Test if all required packages are installed"""
    print("🧪 Testing imports...")
    
    required = {
        'pywin32': ['win32api', 'win32con', 'win32gui'],
        'pynput': ['pynput.keyboard'],
        'pyperclip': ['pyperclip'],
        'plyer': ['plyer.notification']
    }
    
    all_ok = True
    
    for package, modules in required.items():
        for module in modules:
            try:
                __import__(module)
                print(f"  ✅ {module}")
            except ImportError as e:
                print(f"  ❌ {module} - {e}")
                all_ok = False
    
    return all_ok

def test_spell_checker():
    """Test if spell checker loads correctly"""
    print("\n🧪 Testing spell checker...")
    
    try:
        from enhanced_spell_checker import EnhancedSpellChecker
        print("  ✅ Spell checker import successful")
        
        # Try to initialize (this loads paradigms)
        print("  ⏳ Loading NLP models (this may take a moment)...")
        checker = EnhancedSpellChecker()
        print("  ✅ Spell checker initialized successfully")
        
        # Try a simple check
        test_word = "test"
        errors = checker.check_text(test_word)
        print(f"  ✅ Spell check test completed (found {len(errors)} errors)")
        
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_paradigm_files():
    """Test if paradigm files exist"""
    print("\n🧪 Testing paradigm files...")
    
    paradigm_dirs = ['Noun', 'Verb', 'Pronouns']
    base_path = 'paradigms'
    
    if not os.path.exists(base_path):
        print(f"  ❌ Paradigm directory not found: {base_path}")
        return False
    
    all_ok = True
    total_files = 0
    
    for dir_name in paradigm_dirs:
        dir_path = os.path.join(base_path, dir_name)
        if os.path.exists(dir_path):
            files = [f for f in os.listdir(dir_path) if f.endswith('.txt')]
            total_files += len(files)
            print(f"  ✅ {dir_name}: {len(files)} files")
        else:
            print(f"  ❌ {dir_name}: directory not found")
            all_ok = False
    
    print(f"  📊 Total: {total_files} paradigm files")
    return all_ok

def test_windows_hooks():
    """Test if Windows hooks can be created"""
    print("\n🧪 Testing Windows hooks...")
    
    try:
        from pynput import keyboard
        
        # Try to create a listener (but don't start it)
        def dummy_on_press(key):
            pass
        
        listener = keyboard.Listener(on_press=dummy_on_press)
        print("  ✅ Keyboard listener created successfully")
        return True
    except Exception as e:
        print(f"  ❌ Error creating listener: {e}")
        return False

def main():
    """Run all tests"""
    print("="*70)
    print("🎯 Kannada Smart Keyboard - Component Test")
    print("="*70)
    
    tests = [
        ("Package Imports", test_imports),
        ("Paradigm Files", test_paradigm_files),
        ("Windows Hooks", test_windows_hooks),
        ("Spell Checker", test_spell_checker),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*70)
    print("📊 Test Summary")
    print("="*70)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print(f"\n  Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! You're ready to run the smart keyboard service.")
        print("\n▶️  Next step: python smart_keyboard_service.py")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above before running the service.")
        
        if not results["Package Imports"]:
            print("\n💡 Tip: Install missing packages with:")
            print("   pip install pywin32 pynput pyperclip plyer")
    
    print("="*70)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
