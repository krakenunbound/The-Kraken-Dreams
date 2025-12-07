# THE KRAKEN DREAMS - User Manual

> This is the complete user manual. For quick setup, see [README.md](README.md).  
> See [screenshots](screenshots/) for UI previews.

---

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Recording Sessions](#recording-sessions)
4. [Transcription](#transcription)
5. [Speaker Assignment](#speaker-assignment)
6. [Bard's Tale (AI Narratives)](#bards-tale)
7. [Export Options](#export-options)
8. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

1. **Python 3.10-3.12** - [Download](https://www.python.org/downloads/)
   - ✅ Check "Add Python to PATH" during install
   
2. **FFmpeg** - Required for audio processing
   ```
   winget install ffmpeg
   ```

3. **Git** - Required for WhisperX installation
   ```
   winget install Git.Git
   ```

4. **NVIDIA CUDA** (Optional, for GPU acceleration)
   - [Download CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)
   - Verify with `nvidia-smi`

### Python Dependencies

**For NVIDIA GPU (recommended):**
```bash
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
pip install git+https://github.com/m-bain/whisperx.git
pip install -r requirements.txt
```

**For CPU only:**
```bash
pip install torch torchvision torchaudio
pip install git+https://github.com/m-bain/whisperx.git
pip install -r requirements.txt
```

### HuggingFace Setup (Required)

1. Create account at [huggingface.co](https://huggingface.co/join)
2. Accept model licenses (click "Agree and access repository"):
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
3. Create API token at [Settings → Tokens](https://huggingface.co/settings/tokens)
4. Enter token in app Settings

---

## Configuration

### First-Time Setup

1. Run `python kraken_suite.py`
2. Click **⚙️ Settings**
3. Configure:
   - **Audio Devices** - Microphone and system audio source
   - **HuggingFace Token** - Required for transcription
   - **Whisper Model** - Choose speed vs. accuracy (tiny → large-v2)
   - **LLM Provider** - Ollama (local) or Groq (cloud) for Bard's Tale

### Audio Device Setup

For **system audio capture** (Discord, etc.):

1. **Stereo Mix** (if available)
   - Enable in Windows Sound settings → Recording → Show Disabled Devices
   
2. **Output Loopback** (recommended)
   - In Settings, select an `[OUTPUT]` device for System Audio
   - This captures whatever your speakers/headphones play

### LLM Setup for Bard's Tale

**Option A: Ollama (Local)**
- Requires 8GB+ VRAM
- Install from [ollama.ai](https://ollama.ai)
- Run: `ollama pull llama3.1:8b`

**Option B: Groq (Cloud - Free)**
- No GPU required
- Get API key at [console.groq.com](https://console.groq.com)
- Free tier: 30 requests/minute, 14,400/day

---

## Recording Sessions

1. Go to **RECORD** tab
2. Verify audio devices in dropdowns
3. Click **START RECORDING** (or press **F9**)
4. Record your session
5. Click **STOP RECORDING** (or press **F9** again)
6. File saves automatically to `recordings/`

### Tips
- Use **Auto-transcribe** option to start transcription immediately after recording
- Check audio levels before starting (meters should show activity)

---

## Transcription

1. Go to **TRANSCRIBE** tab
2. Drag-and-drop your audio/video file (or click Browse)
3. Click **BEGIN TRANSCRIPTION** (or press **Ctrl+T**)
4. Wait for processing:
   - GPU: ~10-20 minutes for 2-hour session
   - CPU: ~1-2 hours for 2-hour session

### Output Files
| File | Description |
|------|-------------|
| `*_notes.txt` | Raw transcript with timestamps |
| `*_segments.json` | Segment data with timing |
| `*_named.txt` | Transcript with speaker names |
| `*_named_segments.json` | Named segments with avatars |

### Custom Vocabulary

Edit `custom_vocabulary.txt` to add:
- Character names
- Location names
- Custom corrections (e.g., "barovia → Barovia")

---

## Speaker Assignment

1. After transcription, go to **SPEAKERS** tab
2. Click **▶️ Play** to listen
3. Identify who's speaking (transcript highlights active speaker)
4. Type names in the entry fields
5. Select **gender** for each speaker (helps AI use correct pronouns)
6. Click avatar circle to assign character images
7. Click **APPLY NAMES**
8. Optionally **Save Mapping** for future sessions

### Tips
- Press Enter in a name field to jump to the next speaker
- Reuse saved mappings - same voice usually gets same speaker ID

---

## Bard's Tale

Transform your transcript into a narrative story using AI.

1. Go to **BARD'S TALE** tab
2. Select **LLM Provider** (Ollama or Groq)
3. Choose a **Model** from the dropdown
4. Set the **Bard's Name** (default: Zhree)
5. Select **Narrative Style**:
   - Epic Fantasy
   - Humorous Tavern Tale
   - Dramatic Chronicle
   - Bardic Ballad
   - Mysterious Legend
   - Heroic Saga
6. Click **🎭 SPIN THE TALE**
7. Wait for generation (Groq: 2-5 min, Ollama: 10-30 min)

### Session Summary
Click **📜 Summarize** for a shorter Discord-ready recap.

### Post to Discord
1. Configure webhook URL in Settings
2. Generate a summary
3. Click **💬 Post to Discord**

---

## Export Options

### Save Formats
- **Plain Text (.txt)** - Simple, portable
- **Markdown (.md)** - Headers and formatting
- **Obsidian (.md)** - Wikilinks and YAML frontmatter
- **HTML (.html)** - Styled with speaker colors

### Obsidian Export
Includes YAML frontmatter with campaign metadata and wikilinks to character notes.

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| "No module named 'whisperx'" | `pip install git+https://github.com/m-bain/whisperx.git` |
| "CUDA not available" | Reinstall PyTorch with CUDA command |
| "401 Unauthorized" (HuggingFace) | Accept model licenses, regenerate token |
| No system audio | Use `[OUTPUT]` device for loopback |
| Drag-drop not working | `pip install tkinterdnd2` |
| Avatars not showing | `pip install Pillow` |
| Out of memory | Use smaller Whisper model or Groq instead of Ollama |
| Groq rate limit | Wait 60 seconds, auto-retries |

### Enable Stereo Mix (Windows)
1. Right-click speaker icon → Sound settings
2. Sound Control Panel → Recording tab
3. Right-click → Show Disabled Devices
4. Right-click Stereo Mix → Enable

---

## Tips & Best Practices

1. **First session**: Save speaker mapping for reuse
2. **Long recordings**: Split sessions over 3-4 hours
3. **Audio quality**: Clear audio = better transcription
4. **Groq for speed**: Much faster than local Ollama
5. **Smaller chunks**: More narrative detail, slower generation
6. **Check the log**: Engine Log shows detailed progress and errors

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F9 | Toggle Recording |
| Ctrl+T | Start Transcription |
| Ctrl+S | Save Transcript |
| Ctrl+F | Search Transcripts |

---

## Credits

- [WhisperX](https://github.com/m-bain/whisperx) - Speech recognition
- [Pyannote](https://github.com/pyannote/pyannote-audio) - Speaker diarization
- [Ollama](https://ollama.ai) - Local LLM inference
- [Groq](https://groq.com) - Cloud LLM API

---

*Release the Kraken! 🐙*
