# Real-Time Kannada Spell Checker with Transparent Overlay

A comprehensive real-time spell checking system for Kannada text that works with Notepad and Microsoft Word, featuring transparent overlay with wavy underlines and intelligent suggestion popups.

## 🎯 Features

### Core Functionality
- **Real-Time Spell Checking**: Automatically checks Kannada words as you type
- **Transparent Overlay**: Non-intrusive wavy underlines drawn over misspelled words
- **Smart Suggestions**: Context-aware spelling suggestions with POS tagging
- **Universal Compatibility**: Works with Notepad and Microsoft Word
- **Paste Support**: Automatically checks all words when pasting text
- **Persistent Underlines**: Underlines stay visible until word is corrected

### Visual Indicators
- 🔴 **Red Wavy Underline**: Severely misspelled (no suggestions available)
- 🟠 **Orange Wavy Underline**: Misspelled (suggestions available)
- 💡 **Suggestion Popup**: Shows top 5 corrections near caret position

### Advanced Features
- **Multi-Method Caret Detection**:
  1. UIA TextPattern (best for Word)
  2. Win32 GUIThreadInfo (best for Notepad)
  3. Cursor position fallback
- **Overlay Auto-Sync**: Automatically adjusts to window scrolling and movement
- **Word Buffer Management**: Handles cursor movement, backspace, and editing
- **Keyboard Hook**: System-wide keyboard capture for seamless operation

## 📋 Architecture

```
→ Keyboard hook captures typed characters
→ Current Kannada word is built in buffer
→ Detect delimiter (space/enter/punctuation)
→ On word completion → send to Spell Checker
→ Spell Checker returns: {correct/incorrect, suggestions}

IF WORD IS CORRECT:
    → Remove underline (if any)
    → Clear popup

IF WORD IS INCORRECT:
    → Compute caret position via Win32 GUIThreadInfo
    → Try UIA TextPattern for accurate bounding rectangles
    → If UIA fails → compute coordinates using caret start/end
    → If caret fails → fallback to font-measure width
    → Compute underline start_x, underline_y, underline_width
    → Create/Update transparent overlay window
    → Draw wavy underline on Tkinter canvas
    → Store underline info in misspelled_words dict
    → Show suggestion popup near caret
    
→ User selects suggestion → Replace word → Remove underline
→ On scrolling/moving window → overlay auto-syncs
→ On paste → parse all Kannada words → check each
→ Underlines stay persistent until corrected
```

## 🔧 Installation

### Prerequisites
- Python 3.7 or higher
- Windows 10 or higher
- Administrator privileges (for keyboard hooks)

### Required Packages

```bash
pip install pywin32
pip install pynput
pip install comtypes
pip install uiautomation
pip install pyperclip
```

### Optional Packages (for better accuracy)
```bash
pip install transformers
pip install torch
```

## 🚀 Usage

### Method 1: Batch File (Recommended)
1. Double-click `start_realtime_spell_checker.bat`
2. Wait for models to load
3. Open Notepad or Word and start typing Kannada text

### Method 2: Command Line
```bash
python realtime_spell_checker.py
```

### Method 3: Python IDE
Run `realtime_spell_checker.py` directly in your IDE

## ⌨️ Keyboard Controls

| Key Combination | Action |
|----------------|---------|
| `Ctrl+Shift+S` | Toggle spell checking ON/OFF |
| `↑` | Select previous suggestion in popup |
| `↓` | Select next suggestion in popup |
| `Enter` | Replace word with selected suggestion |
| `Click` | Replace word with clicked suggestion |
| `Esc` | Hide suggestion popup |
| `Esc Esc` | Stop the service (press twice quickly) |

## 📝 How It Works

### 1. Typing Mode
- Type Kannada text in any supported editor
- Word buffer builds as you type
- On delimiter (space, enter, punctuation):
  - Word is sent to spell checker
  - If incorrect → underline appears + popup shows suggestions
  - If correct → no action

### 2. Paste Mode
- Press `Ctrl+V` to paste Kannada text
- System automatically extracts all Kannada words
- Each word is checked
- Underlines appear for all incorrect words
- Popup shows suggestions for last incorrect word

### 3. Correction Mode
- Use arrow keys or mouse to select suggestion
- Press Enter or click to replace word
- Underline disappears automatically
- Buffer resets for next word

### 4. Overlay Synchronization
- Overlay window automatically follows target window
- Updates position every 100ms
- Handles scrolling and window movement
- Stays on top of target application

## 🎨 UI Components

### Transparent Overlay Window
- Fully transparent background
- Click-through (doesn't block interactions)
- Draws wavy underlines using Tkinter canvas
- Sine wave pattern for smooth appearance
- Auto-hides when no errors present

### Suggestion Popup
- Windows-style popup with blue accent
- Nirmala UI font for proper Kannada rendering
- Mouse hover highlighting
- Keyboard navigation support
- Auto-positions near caret/cursor

## 🏗️ Technical Details

### Caret Position Detection
1. **UIA TextPattern** (Primary for Word)
   - Uses UI Automation framework
   - Gets TextPattern from focused control
   - Retrieves selection bounding rectangles
   - Most accurate for Microsoft Word

2. **Win32 GUIThreadInfo** (Primary for Notepad)
   - Uses Windows API
   - Gets caret window from GUI thread
   - Converts client to screen coordinates
   - Works well with simple editors

3. **Cursor Position** (Fallback)
   - Uses mouse cursor coordinates
   - Reliable but less accurate
   - Used when other methods fail

### Word Buffer Management
- Tracks current word being typed
- Maintains cursor index within word
- Handles:
  - Character insertion
  - Backspace/Delete
  - Arrow key navigation
  - Selection and replacement

### Spell Checking Pipeline
1. **Tokenization**: Split text into words
2. **POS Tagging**: Identify part of speech
3. **Chunking**: Group related words
4. **Paradigm Checking**: Validate against dictionary
5. **Edit Distance**: Generate suggestions (Levenshtein)

## 📊 Performance

- **Startup Time**: 3-5 seconds (model loading)
- **Check Latency**: <50ms per word
- **Memory Usage**: ~200-300 MB
- **CPU Usage**: Minimal (event-driven)
- **Overlay Update Rate**: 10 FPS (100ms interval)

## 🔍 Troubleshooting

### Issue: Underlines not appearing
**Solution**: 
- Make sure overlay window is not minimized
- Check if spell checking is enabled (Ctrl+Shift+S)
- Verify target window is in focus

### Issue: Caret position inaccurate
**Solution**:
- Install UIA packages: `pip install comtypes uiautomation`
- For Word, UIA provides better accuracy
- For Notepad, Win32 API works well

### Issue: Popup appears in wrong position
**Solution**:
- System uses multi-method fallback
- May default to cursor position as fallback
- Ensure application window is fully visible

### Issue: Service crashes on startup
**Solution**:
- Check all dependencies are installed
- Verify Python version (3.7+)
- Run with administrator privileges
- Check console for error messages

### Issue: Kannada text not recognized
**Solution**:
- Ensure text is in Kannada Unicode (ಕನ್ನಡ)
- System supports both Unicode and WX transliteration
- Check paradigm files are present in `paradigms/` folder

## 🔐 Security & Privacy

- **No Network Access**: All processing is local
- **No Data Collection**: No telemetry or tracking
- **Keyboard Hook**: Only captures keypresses, doesn't log them
- **Memory Only**: Word buffer is not persisted to disk
- **Admin Rights**: Required for global keyboard hooks (Windows security)

## 📁 File Structure

```
realtime_spell_checker.py          # Main application
start_realtime_spell_checker.bat   # Windows startup script
enhanced_spell_checker.py          # Spell checking engine
kannada_wx_converter.py            # Kannada-WX conversion
paradigms/                         # Dictionary files
  ├── Noun/                        # Noun paradigms
  ├── Verb/                        # Verb paradigms
  └── Pronouns/                    # Pronoun paradigms
```

## 🤝 Integration with Existing System

The real-time spell checker integrates with your existing NLP pipeline:

- Uses `EnhancedSpellChecker` for spell checking
- Supports WX transliteration via `kannada_wx_converter`
- Leverages paradigm files from `paradigms/` directory
- Compatible with POS tagging and chunking models

## 🆚 Comparison with Other Modes

| Feature | Real-Time Mode | Clipboard Mode | Notepad Overlay Mode |
|---------|---------------|----------------|---------------------|
| Underlines | ✅ Transparent overlay | ❌ Console only | ✅ Visual markers |
| Real-time | ✅ As you type | ❌ On copy | ⚠️ On select |
| Suggestions | ✅ Interactive popup | ✅ Console list | ✅ Console list |
| Replace | ✅ Automatic | ❌ Manual | ❌ Manual |
| Apps | Notepad, Word | All apps | Notepad only |
| Persistent | ✅ Until corrected | ❌ Per check | ❌ Per check |

## 🔮 Future Enhancements

Potential improvements for future versions:

1. **Context Menu Integration**: Right-click to see suggestions
2. **Dictionary Learning**: Add correctly typed words to dictionary
3. **Grammar Checking**: Beyond spell checking to grammar rules
4. **Multi-Language**: Support for other Indian languages
5. **Cloud Sync**: Sync personal dictionary across devices
6. **Voice Input**: Voice-to-text with spell checking
7. **Auto-Correction**: Optional automatic correction mode
8. **Customizable Colors**: User-defined underline colors
9. **Statistics Dashboard**: Track accuracy over time
10. **Browser Extension**: Similar functionality for web browsers

## 📄 License

Part of the NLP-Based Kannada Spell Correction System project.

## 👥 Support

For issues, questions, or contributions:
1. Check this README for common solutions
2. Review console output for error messages
3. Verify all dependencies are installed
4. Ensure paradigm files are present

## 🎓 Credits

- **NLP Pipeline**: Enhanced spell checker with POS tagging
- **UI Framework**: Tkinter (Python standard library)
- **Windows API**: pywin32 for system integration
- **Keyboard Hooks**: pynput for global key capture
- **UIA Support**: comtypes and uiautomation

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Python Version**: 3.7+  
