
# 📄 **Software Requirements Specification (SRS)**

## **NLP-Based Kannada Spell Checker**

---

# **1. Introduction**

## **1.1 Purpose**

This document defines the Software Requirements Specification (SRS) for the **NLP-Based Kannada Spell Checker**, a real-time spell-checking system that works across multiple Windows applications, including:

* Notepad
* Microsoft Word


The system provides:

* Real-time Kannada spell checking
* Grammarly-style underline overlays
* Dictionary + edit-distance-based suggestion engine
* Unicode ↔ WX transliteration
* System-wide keystroke monitoring
* Paste detection and full-document scanning (Notepad)

---

## **1.2 System Overview**

The system is composed of the following major subsystems:

1. **Spell Checking Engine**

   * Dictionary-based word matching
   * Edit distance (≤2) suggestion generation
   * WX-based transliteration for internal processing

2. **Typing Monitoring Engine**

   * Global keyboard hook
   * Word boundary detection
   * Caret position tracking
   * Paste detection

3. **Overlay Rendering Engine**

   * Transparent overlay window
   * Draws red/orange underlines
   * Follows caret, scroll, and window movement

4. **Suggestion Popup Engine**

   * Appears near caret
   * Displays correction suggestions
   * Allows click/keyboard selection

5. **Tokenizer & Transliteration Module**

   * Handles complex Kannada tokens
   * Unicode ↔ WX conversion

6. **DPI Scaling Utilities**

   * Ensures accurate underline placement across all screen DPIs

---

# **2. Overall Description**

## **2.1 System Context**

The system runs as a background Windows service and continuously monitors:

* Typed text from keyboard
* Pasted content
* Document-wide text (Notepad only)
* Caret location
* Window movement
* DPI scaling



---

## **2.2 Major Components**

### **2.2.1 Spell Checking Engine**

* Loads dictionary and pre-generated word forms
* Converts Kannada Unicode → WX
* Performs dictionary lookup
* Generates suggestions using edit distance
* Ranks candidates using similarity
* Uses fallback tokenizer when needed

---

### **2.2.2 Keyboard Monitoring & Word Processing Engine**

* Captures all keystrokes
* Tracks word boundaries
* Detects Kannada characters
* Detects backspace, delete, cursor movement
* Detects paste operations
* Scans entire document for pasted text (Notepad)
* Maintains per-word state for underline tracking

---

### **2.2.3 Grammarly-Style Underline Overlay Engine**

* Renders a transparent overlay on top of any editor
* Tracks caret position using UIAutomation
* Tracks window movements and scrolling
* Draws underlines with pixel-level accuracy
* Supports:

  * **Red underline** → Suggestions available
  * **Orange underline** → No suggestions
* Removes underline when corrected

---

### **2.2.4 Suggestion Popup Engine**

* Appears next to caret
* Supports keyboard navigation
* Supports click-to-correct actions
* Automatically hides after selection

---

### **2.2.5 Tokenization System**

* Handles punctuation-heavy text
* Detects abbreviations, URLs, dates, numbers

---

### **2.2.6 Transliteration Engine**

* Unicode → WX
* WX → Unicode
* Handles consonant + matra combinations
* Handles halant (್) rules

---

### **2.2.7 DPI Scaling Utilities**

* Ensures proper placement on multi-DPI displays
* Converts logical pixel values into DPI-aware scaling

---

# **3. Functional Requirements**

## **FR1: Real-Time Text Monitoring**

The system must detect:

* Keystrokes
* Word boundaries
* Cursor movement
* Backspace / delete
* Ctrl+A selection
* Paste operations
* Full document clearing (Notepad)

---

## **FR2: Word Extraction & Normalization**

* Identify Kannada word boundaries
* Handle multi-character clusters
* Convert Kannada → WX before processing

---

## **FR3: Spell Checking**

### **FR3.1 Dictionary Lookup**

* Load dictionary files from **paradigms/all/**
* Use cached dictionary for performance

### **FR3.2 Suggestion Generation**

* Compute edit distance (≤2)
* Filter based on word length
* Return top ranked suggestions

---

## **FR4: Overlay Underline Rendering**

Underlines should:

* Appear directly under incorrect words
* Follow text even when scrolling
* Update on window resize
* Auto-remove when corrected
* Use the following color scheme:

  * **Red** → Error with suggestions
  * **Orange** → Error with no suggestions

*(Blue underline removed as per your revision)*

---

## **FR5: Suggestion Popup**

* Should appear beside caret
* Provide interactive selection
* Insert corrected word into editor
* Hide after correction

---

## **FR6: Paste & Document Scanning**

* Detect paste events
* Extract new text block
* Spell-check full pasted segment
* Support multi-line paste operations

---

# **4. Non-Functional Requirements**

## **NFR1: Performance**

* Spell checking must respond within **40 ms**
* Overlay must repaint at **60 FPS**

## **NFR2: Usability**

* Underlines should not obstruct text
* Popup should be instant and aligned

## **NFR3: Reliability**

* Underlines must follow scroll, caret movement, and DPI changes

## **NFR4: Compatibility**

* Compatible with Windows 10 and 11
* Works on all major text editors

## **NFR5: Maintainability**

* Modular codebase
* Dictionary easily extendable

---

# **5. System Architecture Diagram**

```
┌────────────────────────────────────────────────────────────┐
│           Detect Active Interface (Editor Type)            │
│  • Notepad → Keyboard Hook + UIAutomation                  │
│  • MS Word → Win32 COM API + UIAutomation                  │
│  • Browser/Other → UIAutomation TextPattern2               │
└───────────────────────────────────────────┬────────────────┘
                                            ▼
                               Capture Input From Editor
                                            ▼
                         ┌──────────────────────────────────┐
                         │ IF NOTEPAD                      │
                         │ • Keystroke hook                │
                         │ • Word boundary detection       │
                         │ • Paste detection               │
                         └──────────────────────────────────┘
                         ┌──────────────────────────────────┐
                         │ IF MS WORD                      │
                         │ • Selection.Range.Text          │
                         │ • Caret tracking via COM        │
                         │ • Word-boundary extraction      │
                         └──────────────────────────────────┘
                                            ▼
                                 Extract Kannada Word
                                            ▼
                              Normalize (Unicode → WX)
                                            ▼
                                     Tokenize Word
                                            ▼
                        ┌────────────────────────────────────┐
                        │     Dictionary Lookup (Local)      │
                        └────────────────────────────────────┘
                            │                          │
                            ▼                          ▼
                 Word Found (Correct)      Word Not Found → Error
                            │                          │
                            ▼                          ▼
                    No Underline Needed    Generate Suggestions (Edit Distance)
                                                    ▼
                                          Rank Candidates (Top-N)
                                                    ▼
                      ┌──────────────────────────────────────────────────┐
                      │ Draw Underline Using Overlay Window              │
                      │ • Red → Suggestions available                    │
                      │ • Orange → No suggestions                        │
                      └──────────────────────────────────────────────────┘
                                                    ▼
                          Show Suggestion Popup (User Correction)
```

---

# **6. Limitations**

Confirmed from codebase:

* No phonetic rules
* No sandhi splitting
* No morphological analysis
* No POS tagging
* Dictionary + edit distance only
* Underline accuracy depends on UIAutomation support

---

# **7. Future Enhancements**

Recommended for next version:

* Kannada phonetic confusion model
* Morphological analyzer
* Sandhi splitter
* POS-based ranking
* Neural spell-correction model
* Grammar correction engine

---

# **8. Conclusion**

The NLP-Based Kannada Spell Checker provides a practical, editor-independent solution for real-time Kannada spell correction across Windows applications. By combining a dictionary-driven spell-checking engine with a Grammarly-style overlay underline system, the project successfully delivers features that are not available in standard editors like Notepad or Microsoft Word for Kannada text. The system captures typing and paste events, identifies spelling errors, generates suggestions using edit-distance algorithms, and visually highlights mistakes through precise overlay rendering.


