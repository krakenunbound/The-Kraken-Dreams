# THE KRAKEN DREAMS - Changelog

All notable changes to this project will be documented in this file.

---

## [1.3.1] - 2025-12-07

### Added - Quality of Life Improvements
- **Window position memory** - App remembers window size and position between sessions
- **Speaker colors** - Each speaker gets a unique color in the transcript preview
- **12-color speaker palette** - D&D-themed colors (Fighter red, Wizard blue, etc.)
- **Colored timestamps** - Timestamps shown in dim color for better readability
- **Whisper model selection** - Choose transcription model (tiny, base, small, medium, large-v2)
- **Language selection** - Force specific language for transcription (auto, en, es, fr, de, etc.)
- **Timestamp format** - Option for hh:mm:ss format (via config)
- **Auto-transcribe** - Option to automatically start transcription after recording
- **Custom vocabulary** - D&D terms + custom character/place names (custom_vocabulary.txt)
- **Export formats** - Save transcripts as TXT, Markdown, or HTML with full styling
- **Keyboard shortcuts** - F9 record, Ctrl+T transcribe, Ctrl+S save, Ctrl+F search
- **Windows notifications** - Toast notifications when transcription completes
- **Discord integration** - Post session summaries directly to Discord via webhook
- **Full-text search** - Search across all transcripts (Ctrl+F or 🔍 button)
- **Obsidian export** - Export transcripts with wikilinks and YAML frontmatter
- **Session database** - SQLite storage for campaigns, sessions, characters, locations
- **Campaign tracker** - Link sessions to campaigns with character tracking
- **Punctuation improvements** - Automatic sentence boundary detection
- **Transcription settings section** - New settings panel for transcription options
- **Discord settings section** - Configure webhook URL in Settings


### Added - New Modules (Modular Architecture)
- `src/core/formatters.py` - Timestamp formatting and text utilities
- `src/core/search.py` - Transcript search engine
- `src/core/vocabulary.py` - D&D terms and custom vocabulary corrections
- `src/core/exporters.py` - Obsidian, Markdown, HTML export formats
- `src/core/database.py` - SQLite session/campaign database
- `src/core/punctuation.py` - Sentence boundary improvements
- `src/ui/search_dialog.py` - Search UI dialog
- `src/ui/settings_dialog.py` - Settings dialog (extracted from main)


### Changed
- Preview tab now displays speaker names in their assigned colors
- Window position saved on close, restored on startup
- Status bar shows number of speaker colors applied
- Transcription uses model and language from settings
- Export dialog now supports .md and .html with proper formatting
- Post to Discord button added to Bard's Tale tab
- Search button added to header toolbar

---



## [1.3.0] - 2025-12-06

### Added - Modular Code Architecture
- **Source package structure** - Code reorganized into `src/` directory with submodules
- **Theme module** (`src/core/theme.py`) - Kraken color palette and style configuration
- **Config module** (`src/core/config.py`) - Configuration management and paths
- **LLM providers module** (`src/core/llm_providers.py`) - Ollama and Groq integration
- **Recording module** (`src/core/recording.py`) - Audio recording functionality
- **Narrative module** (`src/core/narrative.py`) - Bard's Tale prompts and styles
- **Playback module** (`src/core/playback.py`) - Audio playback with speaker tracking
- **UI widgets module** (`src/ui/widgets.py`) - Reusable styled components
- **BUGS.md** - Bug tracking file with known issues
- **HOW_TO.md** - Quick-start guide in `docs/` folder

### Changed
- Main `kraken_suite.py` refactored to use modular imports
- All modules include comprehensive docstrings and comments
- Code follows modular design for maintainability (< 2K lines per file)

### Documentation
- Each module includes purpose documentation
- Functions have docstrings with argument descriptions
- Constants documented with usage context

---

## [1.2.3] - 2024-12-06

### Fixed - Transcription Thread Stability
- **Fixed transcription thread crash** - Proper error handling prevents silent failures
- **Improved logging handler cleanup** - No longer crashes if setup fails early
- **Log clears on start** - Fresh log for each transcription, easier to follow progress
- **Immediate feedback** - Shows "Starting transcription..." message right away

---

## [1.2.2] - 2024-12-06

### Fixed - Transcription Improvements
- **Detailed progress logging** - See every step: loading models, transcribing, diarizing, etc.
- **Fixed audio extraction bug** - Variable name typo that caused errors
- **Fixed "nul" file creation** - Removed stdout/stderr redirection that created invalid files
- **Better stop button** - Now properly stops between pipeline steps with clear feedback

### Changed
- Transcription log now shows step-by-step progress [1/7], [2/7], etc.
- GPU info displayed (name, memory) when CUDA is detected
- Audio duration and file size shown before processing
- Clear success/failure messages with speaker summary

---

## [1.2.1] - 2024-12-06

### Added - Audio Device Selection
- **Microphone selection** - Choose your preferred mic in Settings
- **System audio selection** - Select input devices (Stereo Mix) or output devices for loopback capture
- **Output device support** - Speakers/headphones shown with `[OUTPUT]` prefix for WASAPI loopback
- **Device preferences saved** - Your audio devices are remembered between sessions
- Both Settings dialog and Record tab now show input + output devices for system audio

---

## [1.2.0] - 2024-12-06

### Changed - "The Kraken Dreams"
- **Renamed application** from "Kraken Suite" to "The Kraken Dreams"
- **Settings dialog** accessible via ⚙️ button in header
- **Removed hardcoded API keys** - all keys now configurable in Settings

### Added - Settings Management
- **HuggingFace token** field for speaker diarization
- **Ollama configuration** - URL and default model
- **Groq configuration** - API key, URL, and default model
- **Persistent settings** saved to `kraken_config.json`

### Security
- API keys no longer stored in source code
- Settings file keeps credentials separate from code

---

## [1.1.0] - 2024-12-06

### Added - Speaker Avatars
- **Clickable avatar placeholders** in Speakers tab
- **Avatar assignment** via file dialog (PNG, JPG, GIF, BMP)
- **Current speaker display** with avatar during playback
- **Party members panel** in Bard's Tale tab showing all avatars
- **JSON persistence** - avatars saved/loaded with transcript segments

### Added - Organization
- **recordings/** subdirectory for audio files
- **transcripts/** subdirectory for transcript files
- **avatars/** subdirectory for avatar images
- **_archive/** folder for old unused scripts

### Changed
- Default recording save path now uses recordings/ folder
- Avatar images displayed as circular thumbnails (using PIL)

### Dependencies
- Added Pillow (PIL) for avatar image processing

---

## [1.0.0] - 2024-12-06

### Added - KRAKEN SUITE
- **Complete rewrite** as unified "Kraken Suite" application
- **Dark Kraken theme** with purple/teal bioluminescent colors
- **5-tab interface:**
  - Tab 1: RECORD - Audio recording with mic + system audio
  - Tab 2: TRANSCRIBE - WhisperX transcription with drag-drop
  - Tab 3: SPEAKERS - Speaker identification with playback
  - Tab 4: PREVIEW - Transcript editing
  - Tab 5: BARD'S TALE - AI narrative generation

### Added - Bard's Tale Feature
- **Ollama integration** for local LLM inference
- **Groq integration** for cloud LLM inference (free tier)
- **6 narrative styles:**
  - Epic Fantasy
  - Humorous Tavern Tale
  - Dramatic Chronicle
  - Bardic Ballad
  - Mysterious Legend
  - Heroic Saga
- Configurable chunk size for processing
- Progress tracking with stop functionality
- Automatic title generation
- Bardic closing lines

### Added - Recording Feature
- Direct audio recording without OBS
- Simultaneous mic + system audio capture
- Live level meters
- Auto-device detection (Yeti, Stereo Mix)
- Timer display

### Added - Documentation
- KRAKEN_README.md - Complete user manual
- CHANGELOG.md - Version history
- TODO.md - Planned features

---

## [0.3.0] - 2024-12-05

### Added
- Direct transcript file loading (drag-drop .txt/.json)
- Auto-switch to Speakers tab when loading transcripts
- Support for editing already-named speakers

### Fixed
- Speaker extraction now captures ALL speakers (not just SPEAKER_XX)
- File routing based on extension

---

## [0.2.0] - 2024-12-05

### Added
- Audio playback with speaker highlighting
- Click-to-seek on transcript lines
- Speaker "linger" effect (1.5s after speaking)
- Extended segment boundaries for better sync
- Load/save speaker mapping files

### Changed
- Improved speaker indicator timing
- Better segment boundary handling

---

## [0.1.0] - 2024-12-04

### Added - Initial Release
- `dnd_transcriber.py` - GUI application
- `dnd_scribe.py` - CLI transcription
- `assign_speakers.py` - CLI speaker assignment
- WhisperX integration (large-v2 model)
- Pyannote speaker diarization
- Hugging Face authentication
- Drag-and-drop file support
- Speaker name assignment
- JSON timing data export

### Fixed
- WhisperX API change (DiarizationPipeline import)
- Torch/torchvision version compatibility

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 1.3.1 | 2025-12-07 | Discord, search, hotkeys, notifications, 4 new modules |


| 1.3.0 | 2025-12-06 | Modular architecture, BUGS.md, HOW_TO.md |

| 1.2.3 | 2024-12-06 | Transcription thread stability |
| 1.2.2 | 2024-12-06 | Transcription progress logging, bug fixes |
| 1.2.1 | 2024-12-06 | Audio device selection in Settings |
| 1.2.0 | 2024-12-06 | "The Kraken Dreams", Settings dialog, no hardcoded keys |
| 1.1.0 | 2024-12-06 | Speaker avatars, folder organization |
| 1.0.0 | 2024-12-06 | Kraken Suite, Bard's Tale, Groq support |
| 0.3.0 | 2024-12-05 | Direct transcript loading |
| 0.2.0 | 2024-12-05 | Playback & speaker highlighting |
| 0.1.0 | 2024-12-04 | Initial release |

