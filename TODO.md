# TODO List

## High Priority
- [ ] **Tests**: Implement unit tests for core logic (transcription pipeline, narrative generation).
- [ ] **Validation**: Verify `ripgrep` availability and usage for search features.
- [ ] **Refactoring**: Ensure all files remain under 2000 lines. `kraken_suite.py` is getting large and should be split further (UI components to `src/ui`).

## Features
- [ ] Add direct OBS WebSocket integration to start/stop recording from the app.
- [ ] Add more narrative styles to `src/core/narrative.py`.
- [ ] Implement "Campaign Consultant" chat mode using RAG over previous session transcripts.

## Documentation
- [ ] Add video tutorial links to `HOW_TO.md`.
- [ ] Create API documentation for internal modules.

## Technical
- [ ] Investigate packaging with PyInstaller for easier distribution.
- [ ] optimize `whisperx` alignment speed.
