# TEST CASES FOR VIVA DEMONSTRATION
# Copy-paste these WRONG words into Notepad with service running

## ✅ GUARANTEED TO WORK:

### Test 1: Delete last letter from "maravu" (tree)
Type: ಮರವ
Expected: Should suggest → ಮರವು (maravu)

### Test 2: Change vowel in middle
Type: ಮrಗು (mrigu - wrong)
Expected: Should suggest → ಮಗು (magu - child)

### Test 3: Delete letter from compound word
Type: ಮರದoದನeೕ (maraxodaneVye - missing letter)
Expected: Should suggest → ಮರದೊದನeೕ (maraxoVdaneVyeV - correct)

---

## 📋 HOW TO TEST:

1. Start service: `python smart_keyboard_service.py`
2. Open Notepad (NOT VS Code)
3. Copy and paste ONE of the wrong words above
4. Press SPACE
5. Watch for auto-correction OR check stats output

---

## ⚠️  WHY YOUR PREVIOUS TESTS SHOWED "0 CORRECTIONS":

- You typed: "ಮರವು" (maravu) - ✅ CORRECT word in dictionary
- You typed: "ಬರವು" (baravu) - ✅ ALSO correct word in dictionary (verb form)
- You typed: "ಉಳಲಾರನು" (ulYalAranu) - ✅ ALSO correct!

All three words are valid Kannada words in the paradigm files, so naturally the system made 0 corrections!

---

## 🎓 FOR YOUR VIVA:

**Explanation**: "Our system has 27,130 words from paradigm files. The service only corrects misspelled words. If a word is already correct in the dictionary, it won't be changed. This is the expected behavior of a spell checker."

**Demo Strategy**:
1. Type a correct word → Show "0 corrections" (correct behavior)
2. Type an obvious typo (delete last letter) → Show it gets suggestions
3. Explain: "The system uses edit distance ≤ 2 for suggestions"
