# THE KRAKEN DREAMS - Bug Tracker

All known bugs and issues are documented here.

**Last Updated:** 2025-12-07 (v1.3.1)

---

## 🔴 Critical Bugs

*No critical bugs currently reported.*

---

## 🟠 Medium Priority

| ID | Description | Status | Found | Notes |
|----|-------------|--------|-------|-------|
| BUG-001 | Stereo Mix may not be enabled by default on Windows | Open | v1.0.0 | **Workaround:** Use `[OUTPUT]` device loopback in Settings |
| BUG-002 | Very long sessions (4+ hours) may cause memory issues | Open | v1.0.0 | **Workaround:** Split recordings into 2-3 hour chunks |
| BUG-003 | Some audio devices have sample rate mismatches | Open | v1.0.0 | May cause recording artifacts on certain hardware |

---

## 🟡 Low Priority

| ID | Description | Status | Found | Notes |
|----|-------------|--------|-------|-------|
| BUG-004 | First run downloads ~3GB of models | Info | v1.0.0 | Expected behavior, UX could be improved with progress indicator |
| BUG-005 | Bare `except:` clauses in some error handlers | Open | v1.3.1 | Minor - should use `except Exception:` for better practice |
| BUG-006 | Discord webhook posts may fail silently on network issues | Open | v1.3.1 | Error message shown, but could retry automatically |

---

## ✅ Fixed Bugs

| ID | Description | Fixed In | Notes |
|----|-------------|----------|-------|
| BUG-F001 | Transcription thread crash on errors | v1.2.3 | Added proper error handling |
| BUG-F002 | Log handler cleanup crash | v1.2.3 | Fixed early failure handling |
| BUG-F003 | Audio extraction variable name typo | v1.2.2 | Fixed in transcription pipeline |
| BUG-F004 | "nul" file creation from stdout redirect | v1.2.2 | Removed invalid file creation |
| BUG-F005 | Window position not saving | v1.3.1 | Added window geometry persistence |
| BUG-F006 | Hardcoded Whisper model (large-v2 only) | v1.3.1 | Now configurable in Settings |
| BUG-F007 | No notification when transcription completes | v1.3.1 | Added Windows toast notifications |
| BUG-F008 | Settings dialog too tall for 1080p screens | v1.3.1 | Added scrollable canvas with mousewheel support |


---

## 📋 Known Limitations

These are not bugs, but limitations of the current design:

1. **Windows Only** - Tkinter and audio libraries are Windows-focused
2. **GPU Memory** - Large Whisper models need 8GB+ VRAM
3. **Groq Rate Limits** - Free tier has 30 requests/minute cap
4. **WhisperX Dependency** - Requires Git for installation
5. **HuggingFace License** - Must accept model licenses before use

---

## 🐛 Reporting Bugs

When reporting a bug, please include:

1. **Steps to reproduce** - What you were doing when the bug occurred
2. **Expected behavior** - What should have happened
3. **Actual behavior** - What actually happened
4. **System info** - Windows version, GPU model, Python version
5. **Error messages** - Full error text from the Engine Log tab

### Where to Report
- GitHub Issues (if repo is public)
- Include the Engine Log output if available

---

## Bug Severity Levels

- 🔴 **Critical** - App crashes, data loss, security issues
- 🟠 **Medium** - Feature doesn't work, but workarounds exist
- 🟡 **Low** - Minor inconvenience, cosmetic issues
- ℹ️ **Info** - Expected behavior that could be improved
