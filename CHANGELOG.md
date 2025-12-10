# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2025-12-08

### Added
- **OBS Studio Guide**: Added a dedicated scrollable section in the Record tab explaining how to use OBS Studio for high-quality session recording.
- **Scrollable Recording Tab**: Added a scroll bar to the Recording tab to ensure instructions are always visible on smaller screens.
- **How-To Guide**: Created a comprehensive `HOW_TO.md` manual for setup and usage.
- **Bug & Todo Tracking**: Created `BUGS.md` and `TODO.md` for project management.

### Changed
- **Removed Internal Recording**: Removed internal audio recording settings and logic in favor of OBS Studio integration for better stability and quality.
- **Settings Persistence**: Fixed an issue where Settings dialog comboboxes (Models, Languages) would go blank or lose their state. Now using persistent StringVars.
- **Bard's Tale Persistence**: Fixed LLM Provider and Model selections in the Bard's Tale tab resetting or vanishing. They now save to configuration immediately upon selection.
- **Documentation**: Updated `README.md` and added dependency setup instructions.
- **Refactoring**: Modularized code structure (`src/ui/tabs.py`, `src/core/transcription.py`) to reduce file sizes and improve maintainability.

### Fixed
- Fixed cut-off text in the Recording tab instructions.
- Fixed reliable persistence of selected LLM models and Whisper settings in the Settings dialog.
- Fixed "vanishing" settings in Bard's Tale tab when switching providers or restarting the app.

## [1.3.1] - 2025-12-05
### Added
- Initial Bard's Tale implementation.
- Speaker gender selection.
