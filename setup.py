#!/usr/bin/env python3
"""
Setup and Installation Script for Enhanced Kannada Spell Checker
Installs dependencies and prepares the environment
"""
import subprocess
import sys
import os

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(text.center(70))
    print("="*70 + "\n")

def print_section(text):
    """Print section header"""
    print("\n" + "-"*70)
    print(f"  {text}")
    print("-"*70)

def check_python_version():
    """Check if Python version is compatible"""
    print_header("STEP 1: Checking Python Version")
    
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Python 3.7+ is required")
        return False
    
    print("✅ Python version is compatible")
    return True

def install_dependencies():
    """Install required Python packages"""
    print_header("STEP 2: Installing Dependencies")
    
    packages = [
        ('pyperclip', 'Clipboard monitoring'),
        ('plyer', 'System notifications'),
    ]
    
    optional_packages = [
        ('pystray', 'System tray icon (optional)'),
        ('pillow', 'Image support (optional)'),
    ]
    
    print("Installing required packages...\n")
    
    failed = []
    
    for package, description in packages:
        print(f"📦 Installing {package} ({description})...")
        try:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package],
                check=True,
                capture_output=True
            )
            print(f"  ✅ {package} installed")
        except subprocess.CalledProcessError:
            print(f"  ❌ Failed to install {package}")
            failed.append(package)
    
    print("\nInstalling optional packages...\n")
    
    for package, description in optional_packages:
        print(f"📦 Installing {package} ({description})...")
        try:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package],
                check=True,
                capture_output=True
            )
            print(f"  ✅ {package} installed")
        except subprocess.CalledProcessError:
            print(f"  ⚠️  {package} installation failed (optional)")
    
    if failed:
        print(f"\n❌ Critical packages failed: {', '.join(failed)}")
        print("   Please install manually: pip install " + " ".join(failed))
        return False
    
    print("\n✅ All required dependencies installed")
    return True

def check_project_structure():
    """Verify project structure"""
    print_header("STEP 3: Checking Project Structure")
    
    required_dirs = [
        'paradigms',
        'token',
        'pos_tag',
        'chunk_tag',
        'check_pos'
    ]
    
    missing = []
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"  ✅ {dir_name}/ found")
        else:
            print(f"  ⚠️  {dir_name}/ not found")
            missing.append(dir_name)
    
    if missing:
        print(f"\n⚠️  Some directories are missing: {', '.join(missing)}")
        print("   The spell checker will use fallback methods for missing components")
    else:
        print("\n✅ All required directories found")
    
    return True

def check_paradigm_files():
    """Check paradigm files"""
    print_header("STEP 4: Checking Paradigm Files")
    
    if not os.path.exists('paradigms'):
        print("❌ paradigms/ directory not found")
        return False
    
    paradigm_types = ['Noun', 'Verb', 'Pronouns']
    total_files = 0
    
    for ptype in paradigm_types:
        pdir = os.path.join('paradigms', ptype)
        if os.path.exists(pdir):
            files = [f for f in os.listdir(pdir) if f.endswith('.txt')]
            print(f"  ✅ {ptype}: {len(files)} files")
            total_files += len(files)
        else:
            print(f"  ⚠️  {ptype}: directory not found")
    
    if total_files > 0:
        print(f"\n✅ Total: {total_files} paradigm files found")
        return True
    else:
        print("\n❌ No paradigm files found")
        return False

def create_test_file():
    """Create a test file with sample Kannada text"""
    print_header("STEP 5: Creating Test File")
    
    test_content = """Sample Kannada Text for Testing
================================

Test 1: Simple words (copy this line):
ಕನ್ನಡ ಭಾಷೆ ಸುಂದರ

Test 2: Mixed correct and incorrect (copy this line):
maravu huduganu baranu

Test 3: From paradigm files (copy this line):
maravu maragalYu huduganu

Instructions:
1. Run: python enhanced_spell_checker.py
2. Copy any test line above
3. See results in console and notifications

The spell checker will:
- Tokenize the text
- Assign POS tags
- Chunk into phrases
- Check against paradigms
- Provide suggestions for errors
"""
    
    try:
        with open('TEST_SAMPLES.txt', 'w', encoding='utf-8') as f:
            f.write(test_content)
        print("✅ Created TEST_SAMPLES.txt with sample text")
        return True
    except Exception as e:
        print(f"⚠️  Could not create test file: {e}")
        return True  # Non-critical

def print_usage_instructions():
    """Print usage instructions"""
    print_header("✅ SETUP COMPLETE!")
    
    print("🚀 How to Run:\n")
    print("  python enhanced_spell_checker.py\n")
    
    print("="*70)
    print("\n📝 Usage Instructions:\n")
    print("1. Start the spell checker:")
    print("   python enhanced_spell_checker.py\n")
    
    print("2. The service will monitor your clipboard")
    print("   You'll see this message:")
    print("   '📋 CLIPBOARD MONITORING STARTED'\n")
    
    print("3. Open ANY text editor:")
    print("   - Notepad")
    print("   - Microsoft Word")
    print("   - VS Code")
    print("   - Browser text area")
    print("   - Any application!\n")
    
    print("4. Type Kannada text or use samples from TEST_SAMPLES.txt\n")
    
    print("5. Select and COPY the text (Ctrl+C)\n")
    
    print("6. The spell checker will:")
    print("   ✅ Tokenize your text")
    print("   ✅ Assign POS tags (Noun, Verb, etc.)")
    print("   ✅ Chunk into phrases")
    print("   ✅ Check against paradigm dictionary")
    print("   ✅ Show suggestions for errors")
    print("   ✅ Display notifications\n")
    
    print("="*70)
    print("\n📊 What You'll See:\n")
    print("Console Output:")
    print("  - Detailed pipeline steps")
    print("  - Token analysis")
    print("  - POS tags")
    print("  - Chunk structure")
    print("  - Error detection")
    print("  - Suggestions\n")
    
    print("Notifications:")
    print("  - Error count")
    print("  - Misspelled words with POS tags")
    print("  - Top suggestions")
    print("  - Success messages\n")
    
    print("="*70)
    print("\n💡 Pro Tips:\n")
    print("• Use TEST_SAMPLES.txt for quick testing")
    print("• Check console for detailed pipeline analysis")
    print("• Suggestions are POS-aware (same grammatical category)")
    print("• Press Ctrl+C to stop the service")
    print("• The service must be running while you work\n")
    
    print("="*70)
    print("\n🏗️ Architecture:\n")
    print("  User Input (ANY Editor)")
    print("       ↓")
    print("  Clipboard Monitor")
    print("       ↓")
    print("  [1] Tokenization")
    print("       ↓")
    print("  [2] POS Tagging (Noun/Verb/etc.)")
    print("       ↓")
    print("  [3] Chunking (Phrase structure)")
    print("       ↓")
    print("  [4] Paradigm Checking (POS-specific)")
    print("       ↓")
    print("  [5] Suggestions (Edit distance)")
    print("       ↓")
    print("  Notifications + Console Output\n")
    
    print("="*70)
    print("\n📁 Project Files:\n")
    print("  enhanced_spell_checker.py  - Main spell checker service")
    print("  setup.py                   - This setup script")
    print("  TEST_SAMPLES.txt           - Sample text for testing")
    print("  paradigms/                 - Word paradigm files")
    print("  token/                     - Tokenization module")
    print("  pos_tag/                   - POS tagging models")
    print("  chunk_tag/                 - Chunking models")
    print("  check_pos/                 - POS checking utilities\n")
    
    print("="*70)
    print("\n🎯 Example Session:\n")
    print("$ python enhanced_spell_checker.py")
    print("")
    print("Enhanced Kannada Spell Checker")
    print("Tokenization → POS → Chunking → Paradigm Checking")
    print("...")
    print("📋 CLIPBOARD MONITORING STARTED")
    print("")
    print("[You copy: 'maravu huduganu marauv']")
    print("")
    print("[STEP 1] Tokenizing...")
    print("  Tokens: ['maravu', 'huduganu', 'marauv']")
    print("")
    print("[STEP 2] POS Tagging...")
    print("  maravu → NN")
    print("  huduganu → NN")
    print("  marauv → NN")
    print("")
    print("[STEP 3] Chunking...")
    print("  [NP: maravu huduganu marauv]")
    print("")
    print("[STEP 4-5] Checking Paradigms...")
    print("  ✅ maravu (NN): Correct")
    print("  ✅ huduganu (NN): Correct")
    print("  ❌ marauv (NN): maravu, marave, maravo")
    print("")
    print("❌ FOUND 1 ERROR(S)")
    print("")
    print("📢 ❌ Error 1/1: marauv (NN)")
    print("   Suggestions: maravu, marave, maravo\n")
    
    print("="*70)
    print("\n🎉 Ready to use! Start with:")
    print("   python enhanced_spell_checker.py\n")

def main():
    """Main setup function"""
    print("\n" + "="*70)
    print("KANNADA SPELL CHECKER - SETUP & INSTALLATION".center(70))
    print("="*70)
    
    steps = [
        ("Python Version", check_python_version),
        ("Dependencies", install_dependencies),
        ("Project Structure", check_project_structure),
        ("Paradigm Files", check_paradigm_files),
        ("Test File", create_test_file),
    ]
    
    for step_name, step_func in steps:
        if not step_func():
            print(f"\n⚠️  Setup warning in: {step_name}")
            print("   Some features may not work correctly")
            response = input("\n   Continue anyway? (Y/n): ")
            if response.lower() == 'n':
                print("\n❌ Setup cancelled")
                sys.exit(1)
    
    print_usage_instructions()
    
    print("="*70)
    print("✅ Setup completed successfully!".center(70))
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
