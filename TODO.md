# THE KRAKEN DREAMS - Roadmap

**Last Updated:** 2025-12-07 (v1.3.1)

---

## 🚀 Future Features

### High Priority
- [ ] **Batch processing** - Process multiple recordings at once
- [ ] **Extract run_transcription** - Move 324-line function to separate module
- [ ] **Tab UI extraction** - Move tab setup to src/ui/tabs/

### Bard's Tale
- [ ] **Chapter breaks** - Auto-detect scene changes
- [ ] **Character profiles** - Generate character descriptions from dialogue
- [ ] **Custom prompts** - User-defined narrative styles
- [ ] **More LLM providers** - OpenAI, Anthropic options

### Recording
- [ ] **System tray** - Minimize to tray while recording

### Speaker Identification
- [ ] **Voice profiles** - Learn and remember voices across sessions (ML required)
- [ ] **Confidence scores** - Show diarization certainty
- [ ] **Manual segment editing** - Fix misidentified segments

### UI/UX
- [ ] **Theme options** - Light mode, custom colors
- [ ] **Font selection** - Choose fonts and sizes

### Export & Integration
- [ ] **Notion export** - API integration
- [ ] **Google Docs** - Direct upload (requires OAuth)

---

## ✅ Completed in v1.3.1

| Feature | Description |
|---------|-------------|
| Whisper model selection | Tiny → Large-v2 options |
| Language selection | Force specific transcription language |
| Custom vocabulary | D&D terms + custom names |
| Punctuation improvements | Better sentence boundaries |
| Timestamp format | hh:mm:ss option |
| Speaker colors | Color-coded transcripts |
| Window memory | Remembers position/size |
| Keyboard shortcuts | F9, Ctrl+T, Ctrl+S, Ctrl+F |
| Windows notifications | Toast when done |
| Full-text search | Ctrl+F to search transcripts |
| Discord webhook | Post to Discord |
| Obsidian export | Wikilinks + YAML |
| Session database | SQLite campaigns |
| Campaign tracker | Characters, locations |
| Export formats | TXT, MD, HTML |

---

## ✅ Completed in Earlier Versions

### v1.3.0
- Modular architecture (src/ package)
- Settings dialog extracted
- BUGS.md and HOW_TO.md

### v1.2.x
- Audio device selection
- Output loopback capture
- Settings persistence
- API key management

### v1.1.0
- Speaker avatars
- Party avatars display
- Folder organization

### v1.0.0
- Dual audio recording
- WhisperX transcription
- Pyannote diarization
- Bard's Tale generation
- Ollama + Groq support

---

## 💡 Contributing Ideas

Have a feature request? Suggestions welcome for:
- New narrative styles
- VTT integrations
- Speaker identification improvements
- UI enhancements

---

*See [BUGS.md](BUGS.md) for known issues.*
