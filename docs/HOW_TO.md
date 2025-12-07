# THE KRAKEN DREAMS - How-To Guide

A quick-start guide for common tasks. For full documentation, see [KRAKEN_README.md](../KRAKEN_README.md).

---

## 🎬 Quick Start (5 Minutes)

### First Launch
```bash
python kraken_suite.py
```

### Configure Settings
1. Click **⚙️ Settings** (top-right corner)
2. Set your **Audio Devices**:
   - Microphone: Your USB mic (e.g., "Yeti", "Blue Snowball")
   - System Audio: "Stereo Mix" or select an `[OUTPUT]` device
3. Enter your **HuggingFace Token** (required for speaker diarization)
4. Click **Save Settings**

---

## 🎙️ Recording a D&D Session

### Before Your Session
1. Open The Kraken Dreams
2. Go to **RECORD** tab
3. Test your mic levels (speak and watch the level meter)
4. Test system audio (play something on Discord)

### During Your Session
1. Click **🔴 START RECORDING** when ready
2. Keep the app open (you can minimize it)
3. Timer shows elapsed time

### After Your Session
1. Click **⬛ STOP RECORDING**
2. File auto-saves to `recordings/` folder
3. Note the filename for transcription

---

## 📝 Transcribing a Recording

### Step 1: Load Your File
- **Drag & Drop**: Drag your `.wav`, `.mp4`, or `.mp3` onto the Transcribe tab
- **Browse**: Click the file input and navigate to your file

### Step 2: Start Transcription
1. Click **BEGIN TRANSCRIPTION**
2. Watch the Engine Log for progress:
   - `[1/7] Loading Whisper model...`
   - `[2/7] Extracting audio...`
   - `[3/7] Transcribing...`
   - etc.
3. **Wait time**: ~10-20 minutes for a 2-hour session (GPU)

### Step 3: Review Results
- App auto-switches to **SPEAKERS** tab when done
- Review detected speakers

---

## 👥 Assigning Speaker Names

### Identify Voices
1. In **SPEAKERS** tab, click **▶️ Play** to start playback
2. Listen to each voice
3. The transcript highlights who's currently speaking

### Assign Names
1. Type each player's name in the text fields
2. Click the **📷 avatar** circle to add a character image
3. Click **APPLY NAMES** when done

### Save for Next Time
1. Click **Save Mapping**
2. Choose a filename (e.g., `my_dnd_group.txt`)
3. Next session: **Load Mapping** to reuse names

---

## 📖 Creating a Bard's Tale

### Prerequisites
- Transcript must be loaded (check **PREVIEW** tab)
- Either Ollama running locally, OR Groq API key configured

### Generate Story
1. Go to **BARD'S TALE** tab
2. Select provider:
   - **Ollama**: Local LLM (requires GPU with 8GB+ VRAM)
   - **Groq**: Cloud API (free tier, no GPU needed)
3. Choose a **Narrative Style**:
   - Epic Fantasy - Grand, sweeping narrative
   - Humorous Tavern Tale - Light-hearted, funny
   - Dramatic Chronicle - Serious, historical feel
   - Bardic Ballad - Poetic, song-like
   - Mysterious Legend - Dark, atmospheric
   - Heroic Saga - Action-focused
4. Click **🎭 SPIN THE TALE**
5. Wait for generation (Groq: ~2-5 min, Ollama: ~10-30 min)

### Save Your Story
- **Save Story**: Saves to a `.txt` file
- **Copy All**: Copies to clipboard for pasting

---

## 📋 Session Summary (Discord-Ready)

For a shorter recap perfect for Discord:

1. Go to **BARD'S TALE** tab
2. Click **📋 SESSION SUMMARY**
3. Copy the result to Discord

---

## 🔧 Troubleshooting Quick Fixes

### "No audio from system"
→ In Settings, try selecting an `[OUTPUT]` device for System Audio

### "Transcription stuck"
→ Check Engine Log for errors. May need more GPU memory.

### "Groq rate limit"
→ Wait 60 seconds and try again

### "Can't find my recording"
→ Check `recordings/` folder in the app directory

---

## 📁 Where Are My Files?

| What | Location |
|------|----------|
| Recordings | `recordings/dnd_session_*.wav` |
| Transcripts | `your_file_notes.txt` |
| Timing Data | `your_file_segments.json` |
| Named Transcript | `your_file_named.txt` |
| Avatars | `avatars/` folder |
| Settings | `kraken_config.json` |

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **F9** | Start/Stop Recording |
| **Ctrl+T** | Begin Transcription |
| **Ctrl+S** | Save Transcript |
| **Ctrl+F** | Search All Transcripts |
| **Tab** | Move between speaker name fields |
| **Enter** | Apply name and move to next speaker |


---

## 💡 Pro Tips

1. **Save speaker mappings** after first session - huge time saver
2. **Store avatars** in the `avatars/` folder for easy access
3. **Use Groq** for faster Bard's Tale generation
4. **Split long recordings** (4+ hours) to avoid memory issues
5. **Check the Engine Log** if something seems stuck

---

*For complete documentation, see [KRAKEN_README.md](../KRAKEN_README.md)*
