# 🚀 Paradigm Generator - Quick Reference

## 📦 Installation

```bash
pip install pandas openpyxl
```

## 🎯 Quick Start

### Option 1: Integrated with Spell Checker (Recommended)

```python
from enhanced_spell_checker import SimplifiedSpellChecker

# Automatically uses paradigm generator
checker = SimplifiedSpellChecker()
# Dictionary now has 106K+ words (including all paradigm forms!)

# Check text
result = checker.check_text("your kannada text")
```

### Option 2: Standalone Usage

```python
from paradigm_generator import create_generator

# Initialize (one-time ~25 sec startup)
generator = create_generator()

# Instant O(1) lookups
paradigm = generator.get_paradigm("amka")
```

## 📋 Common Operations

### Check if word has paradigm
```python
if generator.has_paradigm("word"):
    print("Found!")
```

### Get all forms of a word
```python
forms = generator.get_all_forms("amka")
print(f"Total forms: {len(forms)}")
```

### Search paradigms by pattern
```python
results = generator.search_paradigms("^am")  # Words starting with 'am'
```

### Get statistics
```python
stats = generator.get_stats()
print(f"Total: {stats['total_count']:,} paradigms")
```

### Get related words
```python
related = generator.get_related_words("amka")
# Returns: ['imka', 'yAmka', 'emka'] if rules match
```

## 🧪 Testing

```bash
# Full test suite
python test_paradigm_generator.py

# Interactive demo
python demo_paradigm_generator.py

# Quick check
python check_loaded_words.py
```

## ⚙️ Configuration

### Disable paradigm generator
```python
checker = SimplifiedSpellChecker(use_paradigm_generator=False)
```

### Use custom Excel file
```python
from paradigm_generator import ParadigmGenerator

gen = ParadigmGenerator(excel_path="your_file.xlsx")
gen.initialize_paradigms()
```

### Add custom rules
Edit `paradigm_generator.py`:
```python
PREFIX_PAIRS = [
    ("a", "i"),
    ("a", "yA"),
    # Add your rules here
]
```

## 📊 Current Stats

- **Base Paradigms**: 7,988
- **Derived**: 9,721
- **Total**: 17,709
- **Speed**: 0.0002 ms per lookup
- **Dictionary Growth**: +10,835 words

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| Excel file not found | Ensure `check_pos/all.xlsx` exists |
| Missing openpyxl | `pip install openpyxl` |
| Word not found | Check if in base file or matches rules |
| Slow startup | Normal (~25 sec for 17K paradigms) |

## 📚 Files

- `paradigm_generator.py` - Main engine
- `PARADIGM_GENERATOR_README.md` - Full docs
- `IMPLEMENTATION_SUMMARY.md` - Complete summary
- `demo_paradigm_generator.py` - Examples
- `test_paradigm_generator.py` - Tests

## 💡 Tips

1. **First Run**: Allow 25 seconds for initialization
2. **Production**: Consider caching generated paradigms
3. **Memory**: ~50 MB for 17K paradigms
4. **Debugging**: Use `search_paradigms()` to find words
5. **Tuning**: Adjust `PREFIX_PAIRS` for your needs

## 🎯 Use Cases

✅ Spell checking with automatic paradigm forms  
✅ Word validation for morphological analysis  
✅ Dictionary expansion for NLP tasks  
✅ Paradigm-based suggestion generation  
✅ Related word discovery

---

**Need more help?** See `PARADIGM_GENERATOR_README.md`
