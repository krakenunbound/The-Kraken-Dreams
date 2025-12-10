# 🦑 The Kraken Dreams - How-To Guide

Welcome to the comprehensive user manual for The Kraken Dreams.

## 📋 Table of Contents
1. [Installation & Setup](#installation--setup)
2. [Recording Sessions](#recording-sessions)
3. [Transcribing](#transcribing)
4. [Managing Speakers](#managing-speakers)
5. [Generating Stories (The Bard's Tale)](#generating-stories-the-bards-tale)
6. [Searching](#searching)

---

## Installation & Setup

## Installation & Setup

This guide assumes you are starting from a fresh computer installation.

### 1. Install System Requirements
Before running the app, you need a few core tools.

#### 🪟 Windows
1. **Install Python 3.10+**:
   - Download the installer from [python.org/downloads](https://www.python.org/downloads/windows/).
   - **IMPORTANT:** During installation, check the box **"Add Python to PATH"**.
2. **Install FFmpeg**:
   - Open PowerShell (Press Start -> Type "PowerShell").
   - Run: `winget install ffmpeg`
3. **Install VLC Media Player**:
   - Download from [videolan.org](https://www.videolan.org/vlc/).
   - Install the **64-bit version** (this is standard on modern PCs).
4. **Install Git (Optional but recommended)**:
   - Run: `winget install git.git`

#### 🍎 MacOS (Apple Silicon & Intel)
1. **Install Homebrew** (The Package Manager for Mac):
   - Open Terminal (Command+Space, type "Terminal").
   - Paste this command (from [brew.sh](https://brew.sh)):
     `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
2. **Install Tools via Homebrew**:
   - Run: `brew install python@3.10 ffmpeg vlc git`

#### 🐧 Linux (Ubuntu/Debian)
1. **Install Packages** via apt:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv ffmpeg vlc git
   ```

### 2. Set Up The Application
Now that your system is ready, let's set up "The Kraken Dreams".

1. **Open your Terminal/PowerShell**.
2. **Navigate** to the folder where you have these files (e.g., `cd Downloads/The-Kraken-Dreams`).
3. **Install Dependencies**:

   **Windows Command:**
   ```powershell
   # 1. Install PyTorch (The AI Brain) - Check https://pytorch.org if you have a specific GPU
   pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121

   # 2. Install The Transcription Engine (WhisperX)
   pip install git+https://github.com/m-bain/whisperx.git

   # 3. Install The Interface Requirements
   pip install -r requirements.txt
   ```

   **MacOS / Linux Command:**
   ```bash
   # 1. Install PyTorch
   pip3 install torch torchvision torchaudio

   # 2. Install WhisperX
   pip3 install git+https://github.com/m-bain/whisperx.git

   # 3. Install App Requirements
   pip3 install -r requirements.txt
   ```

### 3. API Keys & AI Models (One-Time Setup)

#### Hugging Face Token (Required for Speaker ID)
*This tells the app "Who is speaking?".*
1. Go to [Hugging Face](https://huggingface.co/join) and create a free account.
2. Visit these two model pages and accept their user agreements (click "Agree"):
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
3. Go to [Settings -> Access Tokens](https://huggingface.co/settings/tokens).
4. Click **Create new token**, name it "Kraken", select **Read** permissions, and create it.
5. **Copy this token** (starts with `hf_...`). You will paste it into the Kraken settings.

#### LLM Provider (Optional - For Story Generation)
*If you want the "Bard's Tale" feature to turn transcripts into stories.*

*   **Option A: Groq (Recommended - Fast & Free)**
    1. Go to [console.groq.com](https://console.groq.com).
    2. Create an API Key.
    3. Copy it for the app.

*   **Option B: Ollama (Private & Local)**
    1. Download [Ollama](https://ollama.ai) and install it.
    2. Open a terminal and run `ollama pull llama3`.
    3. The app will detect it automatically.

---

## Recording Sessions

Internal recording has been deprecated in favor of **OBS Studio** (Open Broadcaster Software) for superior reliability.

1. **Install OBS Studio**: [obsproject.com](https://obsproject.com/download).
2. **Setup Audio**:
   - **Desktop Audio**: Captures Discord/Friends.
   - **Mic/Aux**: Captures You.
3. **Record**: Save as `.mkv` or `.mp4`.
4. **Locate**: Find files in your Videos folder.

> See the **Record Tab** in the app for a step-by-step visualized guide.

---

## Transcribing

1. Go to the **TRANSCRIBE** tab.
2. **Drag & Drop** your recording file onto the Kraken logo.
3. Click **BEGIN TRANSCRIPTION**.
4. Wait for the process:
   - *Loading Audio*
   - *Transcribing* (Whisper)
   - *Aligning*
   - *Diarizing* (Identifying Speakers)
5. Generally takes ~10-20% of the recording duration on a GPU.

---

## Managing Speakers

Once transcription is done, the app switches to the **SPEAKERS** tab.

1. **Identify**: Click the Play button (▶) on a speaker card to hear who it is.
   - **Tip:** The video player will jump to the exact moment so you can see who is talking.
2. **Rename**: Type the Character Name (e.g., "Grog") in the Name box.
3. **Context**: Select Gender (helps the AI write correct pronouns).
4. **Visuals**: Click the Avatar circle to assign a character image.
5. **Apply**: Click **APPLY NAMES** to update the transcript.

---

## Generating Stories (The Bard's Tale)

Turn your raw transcript into a story!

1. Go to **BARD'S TALE** tab.
2. **Settings**:
   - Choose a **Narrative Style** (e.g., "Dark Fantasy").
   - Choose your **Model** (Ollama or Groq).
3. Click **SPIN THE TALE**.
4. The AI will process the transcript in chunks and write a cohesive story.
5. **Save/Copy** the result to share with your party!

---

## Searching

Use high-performance global search to find moments across all your past sessions.

1. Press **Ctrl+F** or click **Search**.
2. Type a query (e.g., "Magic Sword").
3. Click a result to jump to that transcript.

---
*May your rolls be high and your stories legendary.*
