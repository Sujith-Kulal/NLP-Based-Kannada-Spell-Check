# Kannada Paradigm Auto-Generator

## 🚀 Overview

The Kannada Paradigm Auto-Generator is a high-performance system that automatically generates inflectional paradigms for Kannada words during startup. It loads base paradigms from an Excel file and dynamically creates paradigms for all related (derived) words, storing them in memory for instant O(1) lookup.

## ✨ Features

- **📖 Excel-based Configuration**: Load base paradigms from `check_pos/all.xlsx`
- **🔄 Automatic Derivation**: Generates paradigms for related words using prefix transformation rules
- **⚡ Lightning Fast**: O(1) instant lookups from in-memory dictionary
- **📊 Comprehensive Statistics**: Track generation metrics and performance
- **🔍 Search Capabilities**: Find paradigms by regex pattern
- **🔗 Integration Ready**: Seamlessly integrates with existing spell checker

## 📋 Requirements

```bash
pip install pandas openpyxl
```

## 🎯 How It Works

### Step 1: Load Base Paradigms

The system reads `check_pos/all.xlsx` and loads all base paradigms (PN1, PN2, N1, V1, etc.).

Example:
- `avaru` (PN3) - base pronoun paradigm
- `magu` (N7) - base noun paradigm
- `baruV` (V16) - base verb paradigm

### Step 2: Detect Related Words

Uses prefix replacement rules to find related words:

```python
PREFIX_PAIRS = [
    ("a", "i"),     # avaru → ivaru
    ("a", "yA"),    # avaru → yAru
    ("a", "e"),     # avanu → evanu
    ("ma", "na"),   # magu → nagu
]
```

### Step 3: Generate Paradigms

For each derived word, copies the base paradigm and applies prefix transformations:

- **Base**: `avaru` → `avarannu`, `avarinda`, `avarige`, ...
- **Derived**: `ivaru` → `ivarannu`, `ivarinda`, `ivarige`, ...
- **Derived**: `yAru` → `yArannu`, `yArinda`, `yArige`, ...

### Step 4: Store in Memory

All paradigms stored in Python dictionary for instant O(1) lookup. No database writes, no waiting!

## 🚦 Quick Start

### Basic Usage

```python
from paradigm_generator import create_generator

# Initialize generator (loads Excel and generates all paradigms)
generator = create_generator()

# Quick lookup - O(1) instant!
if generator.has_paradigm("ivaru"):
    paradigm = generator.get_paradigm("ivaru")
    print(f"Found {len(paradigm)} forms")
    for key, form in paradigm.items():
        print(f"{key}: {form}")
```

### Integration with Spell Checker

```python
from enhanced_spell_checker import SimplifiedSpellChecker

# Create spell checker with paradigm generator enabled
checker = SimplifiedSpellChecker(use_paradigm_generator=True)

# Check text - all paradigm forms are in dictionary now!
result = checker.check_text("avarannu ivarannu kaNDa")
```

## 🔧 Advanced Usage

### Search Paradigms

```python
# Find all words starting with 'av'
results = generator.search_paradigms("^av")
print(f"Found {len(results)} words")
```

### Get All Forms

```python
# Get all inflected forms of a word
forms = generator.get_all_forms("avaru")
print(f"Total forms: {len(forms)}")
```

### Get Related Words

```python
# Find all derived words for a base word
related = generator.get_related_words("avaru")
print(f"Related words: {related}")  # ['ivaru', 'yAru', 'evaru']
```

### Statistics

```python
stats = generator.get_stats()
print(f"Base paradigms: {stats['base_count']}")
print(f"Derived paradigms: {stats['derived_count']}")
print(f"Total paradigms: {stats['total_count']}")
```

## 📊 Performance

| Operation | Speed | Details |
|-----------|-------|---------|
| Initialization | ~2-5 seconds | Even for 10,000+ words |
| Lookup | O(1) | Instant dictionary access |
| Memory | Efficient | All paradigms in RAM |

### Benchmark Results

```
⏱️  Initialization time: 3.421 seconds
⏱️  100 lookups time: 0.000089 seconds
⏱️  Average per lookup: 0.000890 milliseconds
✅ O(1) instant lookup confirmed!
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_paradigm_generator.py
```

Tests include:
- ✅ Basic functionality
- ⏱️ Performance benchmarks
- 🔗 Integration with spell checker
- 🔍 Search functionality
- 📋 All forms retrieval

## 📁 Project Structure

```
NLP-Based-Kannada-Spell-Correction-System/
├── paradigm_generator.py         # Main paradigm generator
├── test_paradigm_generator.py    # Test suite
├── enhanced_spell_checker.py     # Integrated spell checker
├── check_pos/
│   └── all.xlsx                  # Base paradigms database
└── PARADIGM_GENERATOR_README.md  # This file
```

## 🎨 Customization

### Add New Prefix Rules

Edit `PREFIX_PAIRS` in `paradigm_generator.py`:

```python
PREFIX_PAIRS = [
    ("a", "i"),
    ("a", "yA"),
    ("a", "e"),
    ("ma", "na"),
    ("hu", "ku"),  # Add your custom rules
    ("ba", "ha"),
]
```

### Change Excel Path

```python
generator = ParadigmGenerator(excel_path="path/to/your/file.xlsx")
```

## 📚 API Reference

### ParadigmGenerator Class

#### Methods

- `__init__(excel_path: str)` - Initialize generator with Excel file path
- `initialize_paradigms() -> Dict` - Load and generate all paradigms
- `get_paradigm(word: str) -> Dict` - Get paradigm forms for a word
- `has_paradigm(word: str) -> bool` - Check if word has paradigm
- `get_all_forms(word: str) -> Set` - Get all inflected forms
- `search_paradigms(pattern: str) -> Dict` - Search by regex
- `get_related_words(base_word: str) -> List` - Get derived words
- `get_stats() -> Dict` - Get generation statistics

### Convenience Functions

- `initialize_paradigms(excel_path: str) -> Dict` - Quick initialization
- `create_generator(excel_path: str) -> ParadigmGenerator` - Create and initialize

## 🐛 Troubleshooting

### Excel File Not Found

```
FileNotFoundError: Excel file not found: check_pos/all.xlsx
```

**Solution**: Ensure `all.xlsx` exists in `check_pos/` directory.

### Missing Dependencies

```
ImportError: No module named 'pandas'
```

**Solution**: Install requirements:
```bash
pip install pandas openpyxl
```

### Integration Issues

If paradigm generator doesn't load in spell checker:

1. Check if `openpyxl` is installed
2. Verify `all.xlsx` exists and is readable
3. Check console output for error messages
4. Try standalone mode: `python paradigm_generator.py`

## 🎓 How to Extend

### Add New Word Categories

1. Add category detection in `generate_word_paradigm()`
2. Define category-specific transformation rules
3. Update `PREFIX_PAIRS` with new patterns

### Export Paradigms

```python
# Export all paradigms to dictionary
all_paradigms = generator.export_to_dict()

# Save to file
import json
with open('paradigms.json', 'w', encoding='utf-8') as f:
    json.dump(all_paradigms, f, ensure_ascii=False, indent=2)
```

## 🤝 Contributing

To add new features:

1. Fork the repository
2. Create your feature branch
3. Add tests to `test_paradigm_generator.py`
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

Part of NLP-Based-Kannada-Spell-Correction-System

## 🙏 Credits

Developed for efficient paradigm management in Kannada spell correction systems.

---

## 🎯 Next Steps

1. **Run the tests**: `python test_paradigm_generator.py`
2. **Test standalone**: `python paradigm_generator.py`
3. **Integrate**: Use with spell checker for enhanced suggestions
4. **Customize**: Add your own prefix rules and transformations

**Ready to use! Happy coding! 🚀**
