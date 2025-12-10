# Bug List

## Active
- [ ] **Windows Defender**: Sometimes flags temporary audio extraction (`ffmpeg`) as suspicious activity on stricter policies.
- [ ] **Large Files**: Loading extremely large transcripts (>10 hours) can cause UI lag during text insertion. Need to implement chunked loading for the editor.
- [ ] **Theme**: High contrast mode in Windows might override custom Tkinter colors in some dialog borders.

## Resolved
- [x] **Bard's Tale Settings**: LLM Provider and Model selections were not persisting or would vanish. Fixed in v1.4.0 by binding immediate config updates.
- [x] **Settings Persistence**: Comboboxes in Settings dialog were losing values. Fixed in v1.4.0.
- [x] **Recording Tab Cutoff**: Instructions were cut off on small screens. Fixed with scrollbar in v1.4.0.
- [x] **Audio Recording**: System audio capture via python `sounddevice` was unreliable. Removed in favor of OBS Studio integration.
