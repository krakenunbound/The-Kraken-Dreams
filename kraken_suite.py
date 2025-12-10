"""
THE KRAKEN DREAMS - D&D Session Recording & Transcription
A dark-themed application for recording, transcribing, and organizing your tabletop sessions.

Version: 1.4.0
This is the main application entry point. Core functionality is organized in src/ modules.
"""


import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import time
import os
import re
import json
import subprocess
import gc
import requests
from datetime import datetime
try:
    import vlc
except ImportError:
    vlc = None

# =============================================================================
# MODULAR IMPORTS - Core functionality from src/ package
# =============================================================================
# These modules contain the reusable logic and constants, keeping this file
# focused on the UI orchestration and main application flow.
# =============================================================================

from src.core.config import (
    load_config, save_config, DEFAULT_CONFIG,
    APP_DIR, RECORDINGS_DIR, TRANSCRIPTS_DIR, AVATARS_DIR, CONFIG_FILE,
    ensure_directories
)
from src.core.theme import KRAKEN, apply_theme, SPEAKER_COLORS, assign_speaker_colors

from src.core.llm_providers import (
    OllamaProvider, GroqProvider, GROQ_MODELS, create_provider
)
from src.core.narrative import (
    NARRATIVE_STYLES, get_narrative_styles, 
    build_narrative_prompt, build_summary_prompt,
    get_title_prompt, get_closing_prompt
)
from src.ui.settings_dialog import SettingsDialog
from src.ui.search_dialog import SearchDialog
from src.core.vocabulary import VocabularyManager, create_default_vocabulary


# Ensure application directories exist
ensure_directories()

# =============================================================================
# OPTIONAL DEPENDENCIES
# =============================================================================

# Try to import PIL for avatar images

from src.core.transcription import TranscriptionManager
from src.ui.tabs import (
    setup_record_tab, setup_transcribe_tab, 
    setup_speakers_tab, setup_preview_tab, setup_bard_tab
)
from src.ui.widgets import create_button, create_section
from src.ui.video_player import VideoPlayerWindow

try:
    from PIL import Image, ImageTk, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Try to import drag-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# Try to import cross-platform notifications (optional)
# plyer works on Windows, Linux, and macOS
try:
    from plyer import notification as plyer_notification
    HAS_NOTIFICATIONS = True
except ImportError:
    HAS_NOTIFICATIONS = False
    plyer_notification = None



class KrakenSuite:
    def __init__(self, root):
        self.root = root
        self.root.title("THE KRAKEN DREAMS - D&D Session Tools")
        self.root.configure(bg=KRAKEN['bg_dark'])
        self.root.minsize(900, 650)

        # Load configuration
        self.config = load_config()
        
        # Restore window position and size from config
        self._restore_window_position()
        
        # Bind window close event to save position
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Transcription state
        self.selected_file = None
        self.is_transcribing = False

        # Playback state
        self.playback_process = None # Deprecated, kept for safety
        self.vlc_instance = vlc.Instance() if vlc else None
        self.player = self.vlc_instance.media_player_new() if self.vlc_instance else None
        self.is_playing = False
        self.is_paused = False
        self.is_scrubbing = False
        self.playback_start_time = None
        self.playback_offset = 0
        self.audio_duration = 0  # Total duration in seconds

        # Speaker thumbnails
        self.speaker_thumbnails = {}

        # Application State
        self.current_transcript = ""
        self.current_output_file = None
        self.current_media_file = None
        self.speakers = {}
        self.speaker_avatars = {}
        self.speaker_genders = {}
        self.segments_data = []
        self.temp_audio_file = None
        self.video_window = None

        # Bard logic state
        self.bard_running = False
        self.bard_stop_requested = False

        self.setup_styles()
        self.transcription_stop_requested = False
        self.setup_ui()
        self.load_settings_to_ui()
        
        # Bind global hotkeys
        self.transcription_manager = TranscriptionManager(self)
        self._setup_hotkeys()

    def _setup_hotkeys(self):
        """Set up global keyboard shortcuts."""
        # Ctrl+T to start transcription
        self.root.bind('<Control-t>', lambda e: self.start_transcription() if self.selected_file else None)
        # Ctrl+S to save transcript
        self.root.bind('<Control-s>', lambda e: self.save_transcript())
        # Ctrl+F to search transcripts
        self.root.bind('<Control-f>', lambda e: self.show_search_dialog())

    def show_search_dialog(self):
        """Open the search dialog to search across transcripts."""
        def on_open_file(filepath, line_number):
            """Callback when user wants to open a search result."""
            self.load_transcript_directly(filepath)
            self.notebook.select(self.preview_tab)
            # Try to scroll to the line
            self.preview_text.see(f"{line_number}.0")
        
        SearchDialog(self.root, on_open_callback=on_open_file)


    def _restore_window_position(self):
        """Restore window position and size from saved config."""
        width = self.config.get("window_width", 950)
        height = self.config.get("window_height", 750)
        x = self.config.get("window_x")
        y = self.config.get("window_y")
        
        if x is not None and y is not None:
            # Restore to saved position
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        else:
            # Center on screen (default behavior)
            self.root.geometry(f"{width}x{height}")
    
    def _save_window_position(self):
        """Save current window position and size to config."""
        # Get current geometry
        geometry = self.root.geometry()
        # Parse geometry string (e.g., "950x750+100+200")
        import re
        match = re.match(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', geometry)
        if match:
            width, height, x, y = map(int, match.groups())
            self.config["window_width"] = width
            self.config["window_height"] = height
            self.config["window_x"] = x
            self.config["window_y"] = y
            save_config(self.config)
    
    def _on_closing(self):
        """Handle window close event - save position and cleanup."""
        # Save window position
        self._save_window_position()
        
        # Stop any active playback
        if self.is_playing:
            self.stop_playback()
        
        # Destroy the window
        self.root.destroy()


    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Configure all ttk styles with Kraken theme
        self.style.configure('TFrame', background=KRAKEN['bg_dark'])
        self.style.configure('TLabel', background=KRAKEN['bg_dark'], foreground=KRAKEN['text'], font=('Segoe UI', 10))
        self.style.configure('TButton', background=KRAKEN['bg_widget'], foreground=KRAKEN['text'],
                           font=('Segoe UI', 10), padding=8, borderwidth=0)
        self.style.map('TButton', background=[('active', KRAKEN['accent']), ('pressed', KRAKEN['tentacle'])])

        self.style.configure('TNotebook', background=KRAKEN['bg_dark'], borderwidth=0)
        self.style.configure('TNotebook.Tab', background=KRAKEN['bg_mid'], foreground=KRAKEN['text_dim'],
                           font=('Segoe UI', 11, 'bold'), padding=[20, 10])
        self.style.map('TNotebook.Tab',
                      background=[('selected', KRAKEN['accent']), ('active', KRAKEN['tentacle'])],
                      foreground=[('selected', KRAKEN['text_bright']), ('active', KRAKEN['text'])])

        self.style.configure('TCombobox', fieldbackground=KRAKEN['bg_widget'], foreground=KRAKEN['text'],
                           background=KRAKEN['bg_widget'], arrowcolor=KRAKEN['accent'])

        self.style.configure('TLabelframe', background=KRAKEN['bg_dark'], foreground=KRAKEN['accent_light'])
        self.style.configure('TLabelframe.Label', background=KRAKEN['bg_dark'], foreground=KRAKEN['accent_light'],
                           font=('Segoe UI', 11, 'bold'))

        self.style.configure('Horizontal.TProgressbar', background=KRAKEN['biolum'],
                           troughcolor=KRAKEN['bg_widget'], borderwidth=0, thickness=8)

        self.style.configure('TEntry', fieldbackground=KRAKEN['bg_widget'], foreground=KRAKEN['text'])

    def setup_ui(self):
        # Main container
        main_container = tk.Frame(self.root, bg=KRAKEN['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True)

        # Header with title
        header = tk.Frame(main_container, bg=KRAKEN['bg_dark'], height=60)
        header.pack(fill=tk.X, padx=20, pady=(15, 5))
        header.pack_propagate(False)

        title_label = tk.Label(header, text="🐙 THE KRAKEN DREAMS", font=('Segoe UI', 20, 'bold'),
                              bg=KRAKEN['bg_dark'], fg=KRAKEN['accent_glow'])
        title_label.pack(side=tk.LEFT)

        subtitle = tk.Label(header, text="D&D Session Recording & Transcription", font=('Segoe UI', 10),
                           bg=KRAKEN['bg_dark'], fg=KRAKEN['text_dim'])
        subtitle.pack(side=tk.LEFT, padx=(15, 0), pady=(8, 0))

        # Settings button in header
        settings_btn = create_button(header, "⚙️ Settings", self.show_settings_dialog, small=True)
        settings_btn.pack(side=tk.RIGHT, padx=5)
        
        # Search button in header
        search_btn = create_button(header, "🔍 Search", self.show_search_dialog, small=True)
        search_btn.pack(side=tk.RIGHT, padx=5)


        # Notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Create tabs
        self.record_tab = tk.Frame(self.notebook, bg=KRAKEN['bg_dark'])
        self.transcribe_tab = tk.Frame(self.notebook, bg=KRAKEN['bg_dark'])
        self.speakers_tab = tk.Frame(self.notebook, bg=KRAKEN['bg_dark'])
        self.preview_tab = tk.Frame(self.notebook, bg=KRAKEN['bg_dark'])
        self.bard_tab = tk.Frame(self.notebook, bg=KRAKEN['bg_dark'])

        self.notebook.add(self.record_tab, text='  🎙️ RECORD  ')
        self.notebook.add(self.transcribe_tab, text='  📝 TRANSCRIBE  ')
        self.notebook.add(self.speakers_tab, text='  👥 SPEAKERS  ')
        self.notebook.add(self.preview_tab, text='  👁️ PREVIEW  ')
        self.notebook.add(self.bard_tab, text="  🎭 BARD'S TALE  ")

        setup_record_tab(self)
        setup_transcribe_tab(self)
        setup_speakers_tab(self)
        setup_preview_tab(self)
        setup_bard_tab(self)

        # Status bar
        self.status_bar = tk.Label(main_container, text="Ready to unleash the Kraken...",
                                   font=('Segoe UI', 9), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim'],
                                   anchor='w', padx=15, pady=5)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)



    def log(self, message):
        """Add message to STATUS log (Thread-safe) - user-friendly messages"""
        self.root.after(0, lambda: self._log_impl(message))

    def _log_impl(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def tech_log(self, message):
        """Add message to ENGINE LOG (Thread-safe) - technical/debug output"""
        self.root.after(0, lambda: self._tech_log_impl(message))

    def _tech_log_impl(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.tech_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.tech_log_text.see(tk.END)
        self.root.update_idletasks()

    def set_status(self, message):
        """Update status bar (Thread-safe)"""
        self.root.after(0, lambda: self.status_bar.config(text=message))

    def send_notification(self, title, message, duration=5):
        """Send a desktop notification (cross-platform via plyer)."""
        if HAS_NOTIFICATIONS and plyer_notification:
            try:
                # Run in thread to avoid blocking
                def show_notify():
                    plyer_notification.notify(
                        title=title,
                        message=message,
                        app_name="The Kraken Dreams",
                        timeout=duration
                    )
                threading.Thread(target=show_notify, daemon=True).start()
            except Exception:
                pass  # Notifications are optional, fail silently


    def apply_vocabulary_corrections(self, text):
        """
        Apply D&D vocabulary corrections to transcript text.
        Uses both built-in D&D terms and custom vocabulary file.
        
        Args:
            text (str): The transcript text to correct
            
        Returns:
            str: Corrected text
        """
        if not self.config.get("apply_vocabulary", True):
            return text
        
        vocab_file = os.path.join(APP_DIR, self.config.get("vocabulary_file", "custom_vocabulary.txt"))
        
        # Create default vocab file if it doesn't exist
        if not os.path.exists(vocab_file):
            create_default_vocabulary(vocab_file)
            self.log(f"  → Created vocabulary file: {os.path.basename(vocab_file)}")
        
        # Load vocabulary and apply corrections
        manager = VocabularyManager(vocab_file)
        corrected = manager.apply_corrections(text, use_dnd_terms=True)
        
        return corrected



    # ==================== TRANSCRIPTION FUNCTIONS ====================
    def browse_media_file(self, event=None):
        file_path = filedialog.askopenfilename(
            title="Select Audio/Video File",
            filetypes=[
                ("All Supported", "*.mp4 *.mkv *.webm *.avi *.mov *.mp3 *.wav *.m4a *.flac *.ogg *.txt *.json"),
                ("Media Files", "*.mp4 *.mkv *.webm *.avi *.mov *.mp3 *.wav *.m4a *.flac *.ogg"),
                ("Transcript Files", "*.txt *.json"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.handle_file_input(file_path)

    def on_file_drop(self, event):
        file_path = event.data.strip('{}')
        self.handle_file_input(file_path)

    def handle_file_input(self, file_path):
        if not os.path.exists(file_path):
            self.log(f"File not found: {file_path}")
            return

        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.txt', '.json']:
            self.load_transcript_directly(file_path)
        else:
            self.selected_file = file_path
            self.current_media_file = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"Selected: {filename}")
            self.drop_zone.config(text=f"🐙\n{filename[:15]}...", fg=KRAKEN['biolum'])
            self.log(f"Selected: {filename}")

    def start_transcription(self):
        if not self.selected_file:
            messagebox.showerror("Error", "Please select a file first")
            return

        if self.is_transcribing:
            return

        self.is_transcribing = True
        self.transcription_stop_requested = False
        self.transcribe_btn.config(state='disabled')
        self.stop_transcribe_btn.config(state='normal', bg=KRAKEN['warning'])
        self.transcribe_progress.start(10)

        # Clear both logs and show initial message
        self.log_text.delete(1.0, tk.END)
        self.tech_log_text.delete(1.0, tk.END)
        self.log(f"Starting transcription of: {os.path.basename(self.selected_file)}")
        self.log("Initializing transcription pipeline...")
        self.tech_log("=== TRANSCRIPTION STARTED ===")

        thread = threading.Thread(target=self.run_transcription, daemon=True)
        thread.start()

    def stop_transcription(self):
        """Request transcription stop"""
        if self.is_transcribing:
            self.transcription_stop_requested = True
            self.log("🛑 Stop requested... waiting for current step to finish...")
            self.stop_transcribe_btn.config(state='disabled')
            self.set_status("Stopping transcription...")

    def run_transcription(self):
        """Run transcription using the separated TranscriptionManager."""
        self.transcription_manager.run_transcription()

    def transcription_complete(self):
        self.is_transcribing = False
        self.transcribe_btn.config(state='normal')
        self.stop_transcribe_btn.config(state='disabled', bg=KRAKEN['bg_widget'])
        self.transcribe_progress.stop()

        self.populate_speakers_tab()
        self.populate_party_avatars()
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, self.current_transcript)

        self.notebook.select(self.speakers_tab)
        self.set_status("Transcription complete! Assign speaker names.")
        
        # Send Windows notification
        num_speakers = len(self.speakers)
        self.send_notification(
            "🐙 Transcription Complete!", 
            f"Found {num_speakers} speakers. Ready for name assignment."
        )


    def transcription_failed(self):
        self.is_transcribing = False
        self.transcribe_btn.config(state='normal')
        self.stop_transcribe_btn.config(state='disabled', bg=KRAKEN['bg_widget'])
        self.transcribe_progress.stop()
        self.set_status("Transcription process stopped or failed.")

    def extract_audio(self, media_file):
        self.temp_audio_file = os.path.join(os.path.dirname(media_file), "_temp_audio.wav")
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", media_file, "-vn", "-acodec", "pcm_s16le",
                "-ar", "44100", "-ac", "2", self.temp_audio_file
            ], capture_output=True, check=True)
            self.log("Audio extracted for playback")

            # Get audio duration using ffprobe
            try:
                result = subprocess.run([
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", self.temp_audio_file
                ], capture_output=True, text=True, check=True)
                self.audio_duration = float(result.stdout.strip())
                self.log(f"Audio duration: {self.format_time(self.audio_duration)}")
                # Update scrub bar range
                self.scrub_bar.config(to=self.audio_duration)
            except:
                # Fallback: estimate from segments
                if self.segments_data:
                    self.audio_duration = max(s.get("end", 0) for s in self.segments_data)
                    self.scrub_bar.config(to=self.audio_duration)
        except Exception as e:
            self.log(f"Could not extract audio: {e}")
            self.temp_audio_file = None

    # ==================== SPEAKER FUNCTIONS ====================
    def load_transcript_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Transcript File",
            filetypes=[("Text Files", "*.txt"), ("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if file_path:
            self.load_transcript_directly(file_path)

    def load_transcript_directly(self, file_path):
        self.current_output_file = file_path

        if file_path.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.segments_data = data.get("segments", [])
            self.current_media_file = data.get("media_file")
            # Load avatars and genders from JSON
            loaded_avatars = data.get("avatars", {})
            if loaded_avatars:
                self.speaker_avatars.update(loaded_avatars)
                self.log(f"Loaded {len(loaded_avatars)} avatar mappings")
            
            loaded_genders = data.get("genders", {})
            if loaded_genders:
                self.speaker_genders.update(loaded_genders)

            lines = ["D&D Session Transcription", "=" * 50, ""]
            for segment in self.segments_data:
                start = segment["start"]
                minutes = int(start // 60)
                seconds = int(start % 60)
                lines.append(f"[{minutes:02d}:{seconds:02d}] {segment['speaker']}: {segment['text']}")
            self.current_transcript = "\n".join(lines)

            if self.current_media_file and os.path.exists(self.current_media_file):
                self.extract_audio(self.current_media_file)
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                self.current_transcript = f.read()

            json_path = file_path.replace("_notes.txt", "_segments.json").replace(".txt", "_segments.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.segments_data = data.get("segments", [])
                self.current_media_file = data.get("media_file")
                # Load avatars and genders from JSON
                loaded_avatars = data.get("avatars", {})
                if loaded_avatars:
                    self.speaker_avatars.update(loaded_avatars)
                    self.log(f"Loaded {len(loaded_avatars)} avatar mappings")
                
                loaded_genders = data.get("genders", {})
                if loaded_genders:
                    self.speaker_genders.update(loaded_genders)

                if self.current_media_file and os.path.exists(self.current_media_file):
                    self.extract_audio(self.current_media_file)
            else:
                self.segments_data = []
                for line in self.current_transcript.split("\n"):
                    match = re.match(r'\[(\d+):(\d+)\] ([^:]+): (.+)', line)
                    if match:
                        mins, secs, speaker, text = match.groups()
                        start_time = int(mins) * 60 + int(secs)
                        self.segments_data.append({
                            "start": start_time, "end": start_time + 5,
                            "speaker": speaker.strip(), "text": text
                        })

        # Extract all speakers
        found_speakers = set()
        for line in self.current_transcript.split("\n"):
            match = re.match(r'\[\d+:\d+\] ([^:]+):', line)
            if match:
                speaker = match.group(1).strip()
                if speaker:
                    found_speakers.add(speaker)

        def sort_key(s):
            if s.startswith("SPEAKER_"):
                return (0, s)
            elif s == "UNKNOWN":
                return (2, s)
            return (1, s)

        found_speakers = sorted(found_speakers, key=sort_key)
        self.speakers = {s: s for s in found_speakers}

        self.log(f"Loaded {len(self.segments_data)} segments, {len(self.speakers)} speakers")
        self.populate_speakers_tab()
        self.populate_party_avatars()
        # Update preview with speaker colors
        self.update_preview_with_colors()
        self.notebook.select(self.speakers_tab)


    def on_speakers_canvas_resize(self, event):
        """Relayout speaker cards when canvas is resized"""
        if not hasattr(self, 'speaker_cards') or not self.speaker_cards:
            return

        canvas_width = event.width
        card_width = 380  # Fixed card width
        padding = 10

        # Calculate how many columns fit
        num_cols = max(1, (canvas_width - padding) // (card_width + padding))

        # Relayout cards in grid
        for i, card in enumerate(self.speaker_cards):
            row = i // num_cols
            col = i % num_cols
            x = padding + col * (card_width + padding)
            y = padding + row * (200 + padding)  # Approximate card height
            card.place(x=x, y=y, width=card_width)

        # Update frame size to fit all cards
        num_rows = (len(self.speaker_cards) + num_cols - 1) // num_cols
        total_height = padding + num_rows * (200 + padding)
        total_width = padding + num_cols * (card_width + padding)
        self.speakers_frame.config(width=max(total_width, canvas_width), height=total_height)

    def populate_speakers_tab(self):
        # Clear existing
        for widget in self.speakers_frame.winfo_children():
            widget.destroy()
        self.speaker_entries = {}
        self.speaker_gender_vars = {}  # Keep StringVar references for OptionMenu
        self.speaker_indicators = {}
        self.speaker_avatar_labels = {}
        self.speaker_avatar_images = {}  # Keep references to prevent garbage collection
        self.speaker_cards = []

        if not self.speakers:
            tk.Label(self.speakers_frame, text="No speakers found. Load a transcript first.",
                    font=('Segoe UI', 12), bg=KRAKEN['bg_dark'], fg=KRAKEN['text_dim']).place(x=50, y=50)
            return

        # Get sample quotes for each speaker (just 1 for compact view)
        speaker_samples = {s: [] for s in self.speakers}
        for segment in self.segments_data:
            spk = segment.get("speaker", "")
            if spk in speaker_samples and len(speaker_samples[spk]) < 1:
                text = segment.get("text", "")[:80]
                if text:
                    speaker_samples[spk].append(text)

        card_width = 380
        padding = 10

        for idx, speaker_id in enumerate(self.speakers):
            # Create card with fixed width - will be positioned by relayout
            card = tk.Frame(self.speakers_frame, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
            self.speaker_cards.append(card)

            # Row 1: Avatar + Speaker ID + Play button + Indicator
            row1 = tk.Frame(card, bg=KRAKEN['tentacle'])
            row1.pack(fill=tk.X)

            # Avatar (smaller, 60x60)
            avatar_container = tk.Frame(row1, bg=KRAKEN['bg_widget'], width=60, height=60)
            avatar_container.pack(side=tk.LEFT, padx=5, pady=5)
            avatar_container.pack_propagate(False)

            avatar_label = tk.Label(avatar_container, bg=KRAKEN['bg_widget'],
                                   text="📷", font=('Segoe UI', 18), cursor='hand2')
            avatar_label.pack(expand=True, fill=tk.BOTH)

            # Load existing avatar if available
            if speaker_id in self.speaker_avatars and os.path.exists(self.speaker_avatars[speaker_id]):
                self.load_avatar_image(speaker_id, avatar_label)

            avatar_label.bind('<Button-1>', lambda e, sid=speaker_id: self.set_speaker_avatar(sid))
            self.speaker_avatar_labels[speaker_id] = avatar_label

            # Speaking indicator
            indicator = tk.Label(row1, text="●", font=('Segoe UI', 14), bg=KRAKEN['tentacle'],
                                fg=KRAKEN['text_dim'])
            indicator.pack(side=tk.LEFT, padx=2)
            self.speaker_indicators[speaker_id] = indicator

            # Speaker ID label
            tk.Label(row1, text=speaker_id, font=('Segoe UI', 10, 'bold'), bg=KRAKEN['tentacle'],
                    fg=KRAKEN['text_bright']).pack(side=tk.LEFT, padx=3)

            # Play sample button
            play_btn = tk.Button(row1, text="▶", font=('Segoe UI', 9),
                                bg=KRAKEN['bg_widget'], fg=KRAKEN['accent_light'],
                                activebackground=KRAKEN['accent_light'], bd=0, padx=5,
                                cursor='hand2', command=lambda sid=speaker_id: self.play_speaker_sample(sid))
            play_btn.pack(side=tk.LEFT, padx=3)

            # Row 2: Name entry
            row2 = tk.Frame(card, bg=KRAKEN['bg_mid'])
            row2.pack(fill=tk.X, padx=5, pady=3)

            tk.Label(row2, text="Name:", font=('Segoe UI', 9), bg=KRAKEN['bg_mid'],
                    fg=KRAKEN['text']).pack(side=tk.LEFT)
            entry = tk.Entry(row2, width=28, font=('Segoe UI', 10), bg=KRAKEN['bg_widget'],
                           fg=KRAKEN['text'], insertbackground=KRAKEN['text'], relief='flat', bd=0)
            entry.pack(side=tk.LEFT, padx=5, ipady=2, fill=tk.X, expand=True)
            entry.insert(0, self.speakers.get(speaker_id, speaker_id))
            self.speaker_entries[speaker_id] = entry

            # Row 3: Gender selection
            row3 = tk.Frame(card, bg=KRAKEN['bg_mid'])
            row3.pack(fill=tk.X, padx=5, pady=3)

            tk.Label(row3, text="Gender:", font=('Segoe UI', 9), bg=KRAKEN['bg_mid'],
                    fg=KRAKEN['text']).pack(side=tk.LEFT)

            current_gender = self.speaker_genders.get(speaker_id, "")
            gender_var = tk.StringVar(value=current_gender)
            self.speaker_gender_vars[speaker_id] = gender_var
            gender_menu = tk.OptionMenu(row3, gender_var, "", "Male", "Female", "Unknown")
            gender_menu.config(bg=KRAKEN['bg_widget'], fg=KRAKEN['text'],
                              activebackground=KRAKEN['accent'], activeforeground=KRAKEN['text_bright'],
                              highlightthickness=0, width=10, font=('Segoe UI', 9))
            gender_menu["menu"].config(bg=KRAKEN['bg_widget'], fg=KRAKEN['text'],
                                       activebackground=KRAKEN['accent'], activeforeground=KRAKEN['text_bright'])
            gender_menu.pack(side=tk.LEFT, padx=5)

            # Row 4: Sample quote (if available)
            if speaker_samples.get(speaker_id):
                sample = speaker_samples[speaker_id][0]
                tk.Label(card, text=f'"{sample}..."', font=('Segoe UI', 8, 'italic'),
                        bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim'], wraplength=360,
                        anchor='w', justify='left').pack(fill=tk.X, padx=8, pady=(0, 5))

        # Initial layout - trigger resize event
        self.speakers_frame.update_idletasks()
        canvas_width = self.speakers_canvas.winfo_width()
        if canvas_width > 1:  # Canvas has been drawn
            # Manually trigger layout
            class FakeEvent:
                pass
            fake = FakeEvent()
            fake.width = canvas_width
            self.on_speakers_canvas_resize(fake)

    def set_speaker_avatar(self, speaker_id):
        """Open file dialog to set avatar for a speaker"""
        file_path = filedialog.askopenfilename(
            title=f"Select Avatar for {speaker_id}",
            initialdir=AVATARS_DIR,
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.speaker_avatars[speaker_id] = file_path
            if speaker_id in self.speaker_avatar_labels:
                self.load_avatar_image(speaker_id, self.speaker_avatar_labels[speaker_id])
            self.set_status(f"Avatar set for {speaker_id}")

    def load_avatar_image(self, speaker_id, label, size=56):
        """Load and display avatar image in label"""
        if not HAS_PIL:
            label.config(text="📷", font=('Segoe UI', 16))
            return

        try:
            img_path = self.speaker_avatars.get(speaker_id)
            if img_path and os.path.exists(img_path):
                img = Image.open(img_path)
                # Size passed in (default 56 for speaker cards in 60x60 container)
                avatar_size = size
                img = img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)

                # Make circular mask
                mask = Image.new('L', (avatar_size, avatar_size), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                img.putalpha(mask)

                photo = ImageTk.PhotoImage(img)
                self.speaker_avatar_images[speaker_id] = photo  # Keep reference
                label.config(image=photo, text="")
        except Exception as e:
            label.config(text="ERR", font=('Segoe UI', 10))
            self.log(f"Avatar load error: {e}")

    def load_current_speaker_avatar(self, speaker_id):
        """Load and display current speaker avatar (larger size)"""
        if not HAS_PIL:
            return

        try:
            img_path = self.speaker_avatars.get(speaker_id)
            if img_path and os.path.exists(img_path):
                img = Image.open(img_path)
                img = img.resize((70, 70), Image.Resampling.LANCZOS)

                # Make circular mask
                mask = Image.new('L', (70, 70), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 70, 70), fill=255)
                img.putalpha(mask)

                photo = ImageTk.PhotoImage(img)
                self.current_avatar_image = photo  # Keep reference
                self.current_avatar_label.config(image=photo, text="")
        except Exception as e:
            self.log(f"Current avatar load error: {e}")

    def load_mapping_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Mapping File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        old, new = line.strip().split("=", 1)
                        if old in self.speakers:
                            self.speakers[old] = new
            self.populate_speakers_tab()
            self.log(f"Loaded mapping: {file_path}")

    def save_mapping_file(self):
        file_path = filedialog.asksaveasfilename(
            title="Save Mapping File",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if file_path:
            # Update speakers from entries
            for speaker_id, entry in self.speaker_entries.items():
                self.speakers[speaker_id] = entry.get().strip() or speaker_id

            with open(file_path, "w", encoding="utf-8") as f:
                for old, new in self.speakers.items():
                    f.write(f"{old}={new}\n")
            self.log(f"Saved mapping: {file_path}")

    def apply_speaker_names(self):
        # Update speakers dict from entries
        for speaker_id, entry in self.speaker_entries.items():
            new_name = entry.get().strip()
            if new_name:
                self.speakers[speaker_id] = new_name
                
        # Update genders from StringVars (using stored vars to avoid garbage collection issues)
        for speaker_id, gender_var in self.speaker_gender_vars.items():
            gender = gender_var.get()
            self.speaker_genders[speaker_id] = gender

        # Update avatar mappings to use new names
        new_avatars = {}
        for old_id, avatar_path in self.speaker_avatars.items():
            if old_id in self.speakers:
                new_avatars[self.speakers[old_id]] = avatar_path
            else:
                new_avatars[old_id] = avatar_path
        self.speaker_avatars.clear()
        self.speaker_avatars.update(new_avatars)
        
        # Update gender mappings to use new names (if needed) - actually we map on speaker_id which might be old name
        # But wait, self.speakers keys are likely the original speaker_id (SPEAKER_00 etc) OR the previous name
        # The logic below iterates current self.speakers which maps old_id -> new_name
        
        # Let's rebuild gender dict with new names
        new_genders = {}
        for old_id, gender in self.speaker_genders.items():
            if old_id in self.speakers:
                new_genders[self.speakers[old_id]] = gender
            else:
                new_genders[old_id] = gender
        self.speaker_genders.clear()
        self.speaker_genders.update(new_genders)

        # Update transcript
        new_transcript = self.current_transcript
        for old_name, new_name in self.speakers.items():
            if old_name != new_name:
                new_transcript = new_transcript.replace(f"] {old_name}:", f"] {new_name}:")

        # Update segments
        for segment in self.segments_data:
            old_speaker = segment.get("speaker", "")
            if old_speaker in self.speakers:
                segment["speaker"] = self.speakers[old_speaker]

        self.current_transcript = new_transcript

        # Save text file
        if self.current_output_file:
            named_path = self.current_output_file.replace(".txt", "_named.txt").replace("_notes_named", "_named")
            with open(named_path, "w", encoding="utf-8") as f:
                f.write(self.current_transcript)
            self.log(f"Saved: {named_path}")

            # Save JSON with avatars
            json_path = named_path.replace(".txt", "_segments.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "media_file": self.current_media_file,
                    "segments": self.segments_data,
                    "avatars": self.speaker_avatars,
                    "genders": self.speaker_genders
                }, f, indent=2)
            self.log(f"Saved with avatars & genders: {json_path}")

        # Refresh speakers list with new names FIRST so colors work
        old_speakers = dict(self.speakers)
        self.speakers.clear()
        for old, new in old_speakers.items():
            self.speakers[new] = new
        
        # Update preview with speaker colors
        self.update_preview_with_colors()
        
        self.populate_speakers_tab()
        self.populate_party_avatars()

        self.notebook.select(self.preview_tab)
        self.set_status("Speaker names applied with colors!")


    # ==================== VIDEO PLAYER ====================
    def toggle_video_player(self):
        """Toggle the external video player window."""
        if hasattr(self, 'video_window') and self.video_window and not self.video_window.is_closed:
            self.video_window.on_close()
            self.video_window = None
            return

        # We can open the window even for audio files (for visualization or just black screen)
        # But mostly useful if we have a media file
        
        try:
            self.video_window = VideoPlayerWindow(self.root)
            
            # If currently playing, we need to refresh the player to use the Video File + HWND
            if self.is_playing and self.player:
                # Capture current position
                # stopping/playing causes a small blip but is necessary to attach HWND reliably on some systems
                current_time = self.player.get_time()
                is_audio_file = False
                
                # Check if we were playing the temp audio file? 
                # Actually, simply calling start_playback again with the new state (window open)
                # will force the logic in start_playback to pick the VIDEO file and attach HWND.
                
                self.player.stop()
                
                # Restart using standard logic (which now sees the window is open!)
                # We pass the time to seek to.
                seek_s = max(0, current_time / 1000.0)
                self.start_playback(start_time=seek_s)
                
        except Exception as e:
            self.log(f"Error opening video window: {e}")
            messagebox.showerror("Video Error", str(e))


    # ==================== PLAYBACK FUNCTIONS ====================
    def start_playback(self, start_time=0):
        """Start or resume playback from a specific time"""
        if not self.player:
            messagebox.showerror("Error", "VLC not found or initialized.")
            return

        # LOGIC CHANGE:
        # If Video Window is OPEN -> Use Video File (current_media_file)
        # If Video Window is CLOSED -> Use Audio File (temp_audio_file) to prevent VLC popup
        
        want_video = hasattr(self, 'video_window') and self.video_window and not self.video_window.is_closed
        
        if want_video and self.current_media_file and os.path.exists(self.current_media_file):
            media_path = self.current_media_file
        elif self.temp_audio_file and os.path.exists(self.temp_audio_file):
            media_path = self.temp_audio_file
        elif self.current_media_file and os.path.exists(self.current_media_file):
            # Fallback: No temp audio, must use video file even if window is closed
            # (We will try to suppress video in this edge case later if needed, but usually we have audio)
            media_path = self.current_media_file
        else:
            messagebox.showwarning("No Media", "No audio or video file available.")
            return

        # If paused and just resuming (and media seems correct?), just play
        # Note: If we switched from Audio->Video or Video->Audio, we must re-load, so we check media path
        current_media = self.player.get_media()
        # Complex check: get mrl from current media to see if it matches
        # For simplicity, if we are paused, we assume the user state hasn't changed drastically unless toggle_video was called.
        # But if toggle_video was called, it handles the switch. 
        # So here, standard Resume is safe.
        if self.is_paused and current_media:
             self.player.play()
             self.is_paused = False
             self.is_playing = True
             self.play_btn.config(state='disabled')
             self.pause_btn.config(state='normal')
             self.update_playback()
             return

        try:
            # Create new media
            media = self.vlc_instance.media_new(media_path)
            self.player.set_media(media)
            
            # Attach video window IF we decided we wanted video
            if want_video:
                hwnd = self.video_window.get_handle()
                self.player.set_hwnd(hwnd)
            else:
                # IMPORTANT: Ensure we don't hold onto an old HWND if we switched to audio
                self.player.set_hwnd(0) # 0 or None detaches on most systems

            self.player.play()
            
            if start_time > 0:
                 self._pending_seek = start_time
            else:
                 self._pending_seek = None

            self.is_playing = True
            self.is_paused = False
            
            # Update button states
            self.play_btn.config(state='disabled')
            self.pause_btn.config(state='normal')
            self.update_playback()
        except Exception as e:
            self.log(f"Playback error: {e}")

    def pause_playback(self):
        """Pause playback and remember position"""
        if self.player and self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.is_paused = True

            # Update button states
            self.play_btn.config(state='normal', text="▶ Resume")
            self.pause_btn.config(state='disabled')

    def stop_playback(self):
        """Stop playback completely"""
        if self.player:
            self.player.stop()
            self._pending_seek = None
        
        self.is_playing = False
        self.is_paused = False
        self.playback_start_time = None
        self.playback_offset = 0
        
        self.play_btn.config(state='normal', text="▶ Play")
        self.pause_btn.config(state='disabled')
        
        self.reset_speaker_indicators()
        # Reset text unless we are scrubbing
        if not getattr(self, 'is_scrubbing', False):
            self.playback_time.config(text=f"00:00 / {self.format_time(self.audio_duration)}")

    def format_time(self, seconds):
        """Format seconds as MM:SS"""
        mins, secs = int(seconds // 60), int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def skip_playback(self, delta_seconds):
        """Skip forward or backward by delta_seconds"""
        if not self.player:
            return

        # Calculate new position
        # Get current time from VLC if playing, or use offset if paused
        if self.is_playing:
            current_time = self.player.get_time() / 1000.0
            if current_time < 0: current_time = 0
        else:
            current_time = self.playback_offset
            
        new_pos = current_time + delta_seconds
        new_pos = max(0, min(new_pos, self.audio_duration))  # Clamp to valid range

        # Apply seek
        self.player.set_time(int(new_pos * 1000))
        self.playback_offset = new_pos
        
        self.playback_time.config(text=f"{self.format_time(new_pos)} / {self.format_time(self.audio_duration)}")
        self.scrub_var.set(new_pos)

    def on_scrub_start(self, event):
        """User started dragging scrub bar"""
        self.is_scrubbing = True
        # Note: We don't necessarily need to pause VLC, smooth seeking is possible
        # But stopping UI updates prevents fighting
    
    def on_scrub_end(self, event):
        """User released scrub bar"""
        self.is_scrubbing = False
        new_pos = self.scrub_var.get()
        if self.player:
            self.player.set_time(int(new_pos * 1000))
            # Ensure we are playing if we were
            if not self.is_playing and not self.is_paused:
                # If we were stopped, maybe start playing?
                # For now, just update offset
                self.playback_offset = new_pos

    def on_scrub(self, value):
        """Handle scrub bar movement"""
        if self.is_scrubbing and self.player:
            # Live seek while dragging (silver bullet!)
            # Only do this if system is fast enough? 
            # VLC handles it well usually.
            new_pos = float(value)
            # Debounce? Na, let's try raw power.
            self.player.set_time(int(new_pos * 1000))
            self.playback_time.config(text=f"{self.format_time(new_pos)} / {self.format_time(self.audio_duration)}")

    def play_speaker_sample(self, speaker_id):
        """Play a sample clip of a specific speaker"""
        # (Same setup logic...)
        if not self.player: return
        
        if not self.temp_audio_file or not os.path.exists(self.temp_audio_file):
             # Try fallback to media file
             if self.current_media_file:
                 pass # Logic below handles it
             else:
                 messagebox.showwarning("No Audio", "No media available")
                 return

        # Speaker segment finding logic...
        speaker_segments = [s for s in self.segments_data if s.get("speaker") == speaker_id]
        if not speaker_segments:
            # Show what speakers we have
            all_speakers = set(s.get("speaker", "") for s in self.segments_data)
            self.log(f"No segments for '{speaker_id}'. Available: {all_speakers}")
            return

        # Pick best segment logic...
        best_segment = None
        for seg in speaker_segments:
            if (seg.get("end", 0) - seg.get("start", 0)) >= 2:
                best_segment = seg
                break
        if not best_segment: best_segment = speaker_segments[0]

        start_time = max(0, best_segment.get("start", 0) - 0.5)
        play_duration = min(10, best_segment.get("end", 0) - start_time + 0.5)
        
        # Determine media
        media_path = self.current_media_file if self.current_media_file else self.temp_audio_file
        
        try:
            # Stop existing
            self.stop_playback()
            
            # Setup new playback
            media = self.vlc_instance.media_new(media_path)
            self.player.set_media(media)
            self.player.play()
            
            # Seek
            self._pending_seek = start_time
            # Schedule stop
            self._stop_time = start_time + play_duration
            
            self.is_playing = True
            self.is_paused = False
            self.play_btn.config(state='disabled')
            self.pause_btn.config(state='normal')
            self.update_playback()
            
        except Exception as e:
            self.log(f"Sample playback error: {e}")

    def update_playback(self):
        if not self.is_playing or not self.player:
            return

        # Check for end of media
        state = self.player.get_state()
        if state == vlc.State.Ended or state == vlc.State.Error:
            self.stop_playback()
            return
            
        # Handle pending seek (sometimes needed if set_time failed during start)
        if getattr(self, '_pending_seek', None) is not None:
             if self.player.is_playing():
                 self.player.set_time(int(self._pending_seek * 1000))
                 self._pending_seek = None

        # Get current time
        # VLC returns time in ms
        t_ms = self.player.get_time()
        elapsed = max(0, t_ms / 1000.0)
        self.playback_offset = elapsed 
        
        # Handle auto-stop (for speaker samples)
        if getattr(self, '_stop_time', None) is not None:
            if elapsed >= self._stop_time:
                self.stop_playback()
                self._stop_time = None
                return

        current_time = self.format_time(elapsed)
        total_time = self.format_time(self.audio_duration) if self.audio_duration > 0 else "--:--"
        self.playback_time.config(text=f"{current_time} / {total_time}")

        # Update scrub bar position (without triggering callback loop if we are careful)
        # If user is scrubbing, DON'T update the bar from playback
        if not getattr(self, 'is_scrubbing', False):
            self.scrub_var.set(elapsed)

        # Update speaker indicators
        self.update_speaker_indicators(elapsed)
        
        # Loop
        self.root.after(50, self.update_playback)

    def update_speaker_indicators(self, current_time):
        active_speakers = set()
        active_speaker_ids = set()
        for segment in self.segments_data:
            start = segment.get("start", 0) - 0.5
            end = segment.get("end", 0) + 0.5
            if start <= current_time <= end:
                speaker = segment.get("speaker", "")
                # Map to current name
                for old, new in self.speakers.items():
                    if old == speaker or new == speaker:
                        active_speakers.add(new if new else old)
                        active_speaker_ids.add(old)
                        break

        for speaker_id, indicator in self.speaker_indicators.items():
            display_name = self.speakers.get(speaker_id, speaker_id)
            if speaker_id in active_speakers or display_name in active_speakers:
                indicator.config(fg=KRAKEN['biolum'])
            else:
                indicator.config(fg=KRAKEN['text_dim'])

        # Update current speaker display
        if active_speakers:
            current_speaker = list(active_speakers)[0]
            self.current_speaker_name.config(text=current_speaker)

            # Find speaker_id for avatar lookup
            speaker_id = None
            for sid in active_speaker_ids:
                speaker_id = sid
                break

            # Show avatar if available
            if speaker_id and speaker_id in self.speaker_avatars:
                self.load_current_speaker_avatar(speaker_id)
            elif current_speaker in self.speaker_avatars:
                self.load_current_speaker_avatar(current_speaker)
            else:
                self.current_avatar_label.config(image='', text="👤", font=('Segoe UI', 28))
                self.current_avatar_image = None
        else:
            self.current_speaker_name.config(text="—")
            self.current_avatar_label.config(image='', text="👤", font=('Segoe UI', 28))
            self.current_avatar_image = None

    def reset_speaker_indicators(self):
        for indicator in self.speaker_indicators.values():
            indicator.config(fg=KRAKEN['text_dim'])

    # ==================== PREVIEW FUNCTIONS ====================
    def save_transcript(self):
        """Save transcript with format selection (TXT, Markdown, HTML)."""
        file_path = filedialog.asksaveasfilename(
            title="Save Transcript",
            defaultextension=".txt",
            filetypes=[
                ("Text Files", "*.txt"), 
                ("Markdown", "*.md"),
                ("HTML", "*.html"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            content = self.preview_text.get(1.0, tk.END).strip()
            
            if file_path.endswith('.md'):
                # Export as Markdown with formatting
                content = self._format_as_markdown(content)
            elif file_path.endswith('.html'):
                # Export as HTML with speaker colors
                content = self._format_as_html(content)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log(f"Saved: {file_path}")
            self.set_status(f"Exported to {os.path.basename(file_path)}")
    
    def _format_as_markdown(self, content):
        """Format transcript content as Markdown."""
        lines = content.split('\n')
        md_lines = [
            "# D&D Session Transcript",
            "",
            f"*Generated by The Kraken Dreams*",
            "",
            "---",
            ""
        ]
        
        current_speaker = None
        for line in lines:
            # Match [timestamp] Speaker: text format
            match = re.match(r'\[(\d+:\d+)\]\s+([^:]+):\s*(.*)', line)
            if match:
                timestamp, speaker, text = match.groups()
                if speaker != current_speaker:
                    md_lines.append(f"\n### {speaker}\n")
                    current_speaker = speaker
                md_lines.append(f"**[{timestamp}]** {text}")
            elif line.strip():
                md_lines.append(line)
        
        return '\n'.join(md_lines)
    
    def _format_as_html(self, content):
        """Format transcript content as HTML with styled speakers."""
        # Get speaker colors
        speaker_colors = self.config.get("speaker_colors", {})
        
        lines = content.split('\n')
        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            "<meta charset='utf-8'>",
            "<title>D&D Session Transcript</title>",
            "<style>",
            "body { background: #0a0a0f; color: #e0e0e8; font-family: 'Segoe UI', sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }",
            "h1 { color: #9d8dc7; }",
            ".timestamp { color: #8888a0; font-size: 0.9em; }",
            ".line { margin: 8px 0; }",
            "</style>",
            "</head><body>",
            "<h1>🐙 D&D Session Transcript</h1>",
            "<p><em>Generated by The Kraken Dreams</em></p>",
            "<hr>",
        ]
        
        for line in lines:
            match = re.match(r'\[(\d+:\d+)\]\s+([^:]+):\s*(.*)', line)
            if match:
                timestamp, speaker, text = match.groups()
                color = speaker_colors.get(speaker, "#e0e0e8")
                html_parts.append(
                    f"<div class='line'><span class='timestamp'>[{timestamp}]</span> "
                    f"<span style='color:{color};font-weight:bold;'>{speaker}:</span> {text}</div>"
                )
            elif line.strip():
                html_parts.append(f"<div class='line'>{line}</div>")
        
        html_parts.extend(["</body></html>"])
        return '\n'.join(html_parts)


    def copy_transcript(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.preview_text.get(1.0, tk.END))
        self.set_status("Transcript copied to clipboard")

    def update_preview_with_colors(self):
        """
        Update the preview text widget with speaker-specific colors.
        Each speaker gets a unique color to make following conversations easier.
        """
        # Clear and re-insert transcript
        self.preview_text.delete(1.0, tk.END)
        
        if not self.current_transcript:
            return
        
        # Get unique speaker names from current speakers
        speaker_names = list(set(self.speakers.values())) if self.speakers else []
        
        # Assign colors to speakers
        speaker_colors = assign_speaker_colors(speaker_names)
        
        # Configure tags for each speaker color
        for speaker_name, color in speaker_colors.items():
            tag_name = f"speaker_{speaker_name.replace(' ', '_')}"
            self.preview_text.tag_configure(tag_name, foreground=color)
        
        # Also save to config for persistence
        self.config["speaker_colors"] = speaker_colors
        
        # Insert transcript line by line, applying colors
        for line in self.current_transcript.split('\n'):
            # Match [timestamp] Speaker: text format
            match = re.match(r'(\[\d+:\d+\])\s+([^:]+):\s*(.*)', line)
            if match:
                timestamp, speaker, text = match.groups()
                
                # Insert timestamp (dim color)
                self.preview_text.insert(tk.END, timestamp + " ", "timestamp")
                
                # Insert speaker name with their color
                tag_name = f"speaker_{speaker.replace(' ', '_')}"
                if speaker in speaker_colors:
                    self.preview_text.insert(tk.END, speaker + ": ", tag_name)
                else:
                    self.preview_text.insert(tk.END, speaker + ": ")
                
                # Insert the text content
                self.preview_text.insert(tk.END, text + "\n")
            else:
                # No match, insert plain
                self.preview_text.insert(tk.END, line + "\n")
        
        # Configure timestamp tag
        self.preview_text.tag_configure("timestamp", foreground=KRAKEN['text_dim'])
        
        self.set_status(f"Preview updated with {len(speaker_colors)} speaker colors")

    # ==================== BARD'S TALE FUNCTIONS ====================

    def populate_party_avatars(self):
        """Populate the party avatars panel in Bard's Tale tab"""
        # Clear existing
        for widget in self.party_avatars_frame.winfo_children():
            widget.destroy()
        self.party_avatar_images = {}

        if not self.speakers:
            self.party_placeholder = tk.Label(self.party_avatars_frame,
                text="Load a transcript with speakers to see the party members here",
                font=('Segoe UI', 10, 'italic'), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim'])
            self.party_placeholder.pack(pady=10)
            return

        # Create horizontal row of party member cards
        for speaker_id in self.speakers:
            display_name = self.speakers.get(speaker_id, speaker_id)

            member_frame = tk.Frame(self.party_avatars_frame, bg=KRAKEN['bg_widget'], bd=1, relief='solid')
            member_frame.pack(side=tk.LEFT, padx=5, pady=5)

            # Avatar - use consistent 60x60 size for party display
            avatar_label = tk.Label(member_frame, bg=KRAKEN['bg_dark'])
            avatar_label.pack(padx=5, pady=(5, 2))
            party_avatar_size = 60

            # Try to load avatar
            if HAS_PIL:
                avatar_path = self.speaker_avatars.get(speaker_id) or self.speaker_avatars.get(display_name)
                if avatar_path and os.path.exists(avatar_path):
                    try:
                        img = Image.open(avatar_path)
                        img = img.resize((party_avatar_size, party_avatar_size), Image.Resampling.LANCZOS)
                        mask = Image.new('L', (party_avatar_size, party_avatar_size), 0)
                        draw = ImageDraw.Draw(mask)
                        draw.ellipse((0, 0, party_avatar_size, party_avatar_size), fill=255)
                        img.putalpha(mask)
                        photo = ImageTk.PhotoImage(img)
                        self.party_avatar_images[speaker_id] = photo
                        avatar_label.config(image=photo, width=party_avatar_size, height=party_avatar_size)
                    except Exception as e:
                        avatar_label.config(text="👤", font=('Segoe UI', 20), width=4, height=2)
                else:
                    avatar_label.config(text="👤", font=('Segoe UI', 20), width=4, height=2)
            else:
                avatar_label.config(text="👤", font=('Segoe UI', 20), width=4, height=2)

            # Name label
            tk.Label(member_frame, text=display_name, font=('Segoe UI', 9, 'bold'),
                    bg=KRAKEN['bg_widget'], fg=KRAKEN['text'], wraplength=80).pack(pady=(0, 5))

    def on_provider_change(self, event=None):
        """Handle provider selection change"""
        # Save provider to config
        self.config["llm_provider"] = self.llm_provider.get()
        # We don't save immediately to disk to avoid lag, but it will be saved next time config is saved
        self.refresh_models()

    def on_model_change(self, event=None):
        """Handle model selection change"""
        model = self.ollama_model.get()
        provider = self.llm_provider.get()
        
        if "Groq" in provider:
            self.config["groq_model"] = model
        else:
            self.config["ollama_model"] = model
            
        # Optional: Save config to disk immediately for robustness
        save_config(self.config)

    def refresh_models(self):
        """Refresh the model dropdown based on selected provider"""
        provider = self.llm_provider.get()
        if provider == "Groq (Cloud)":
            self.load_groq_models()
        else:
            self.load_ollama_models()

    def load_ollama_models(self):
        """Fetch and populate Ollama models from server"""
        ollama_url = self.config.get("ollama_url", "http://localhost:11434")
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                if model_names:
                    self.model_combo['values'] = model_names
                    # Try to use saved model, then current selection, then first in list
                    saved_model = self.config.get("ollama_model", "")
                    current = self.ollama_model.get()
                    if saved_model and saved_model in model_names:
                        self.ollama_model.set(saved_model)
                    elif current and current in model_names:
                        pass  # Keep current selection
                    else:
                        self.ollama_model.set(model_names[0])
                    self.set_status(f"Found {len(model_names)} Ollama models")
                else:
                    self.model_combo['values'] = ["(no models installed)"]
                    self.ollama_model.set("(no models installed)")
                    self.set_status("No Ollama models found. Run: ollama pull <model>")
            else:
                self.model_combo['values'] = ["(connection error)"]
                self.ollama_model.set("(connection error)")
        except requests.exceptions.ConnectionError:
            self.model_combo['values'] = ["(Ollama not running)"]
            self.ollama_model.set("(Ollama not running)")
            self.set_status(f"Cannot connect to Ollama at {ollama_url}")
        except Exception as e:
            self.model_combo['values'] = [f"(error)"]
            self.ollama_model.set("(error)")
            self.set_status(f"Error: {e}")

    def load_groq_models(self):
        """Populate Groq models from the llm_providers module"""
        # Use the centralized GROQ_MODELS list from src.core.llm_providers
        self.model_combo['values'] = GROQ_MODELS
        # Select saved model or first in list
        saved_model = self.config.get("groq_model", "")
        if saved_model and saved_model in GROQ_MODELS:
            self.ollama_model.set(saved_model)
        elif not self.ollama_model.get() or self.ollama_model.get() not in GROQ_MODELS:
            self.ollama_model.set(GROQ_MODELS[0])
        self.set_status(f"Loaded {len(GROQ_MODELS)} Groq models")


    def start_bard_tale(self):
        """Start the bard's tale generation"""
        if not self.current_transcript or len(self.current_transcript.strip()) < 100:
            messagebox.showwarning("No Transcript", "Please load or create a transcript first (in the PREVIEW tab)")
            return

        if self.bard_running:
            return

        self.bard_running = True
        self.bard_stop_requested = False
        self.bard_btn.config(state='disabled')
        if hasattr(self, 'summary_btn'):
            self.summary_btn.config(state='disabled')
        self.stop_bard_btn.config(state='normal')
        self.bard_text.delete(1.0, tk.END)
        self.bard_progress['value'] = 0

        thread = threading.Thread(target=self.run_bard_tale, daemon=True)
        thread.start()

    def stop_bard_tale(self):
        """Stop the bard's tale generation"""
        self.bard_stop_requested = True
        self.bard_status.config(text="Stopping...")

    def post_to_discord(self):
        """Post the current bard text to Discord via webhook."""
        webhook_url = self.config.get("discord_webhook", "")
        
        if not webhook_url:
            messagebox.showwarning(
                "No Webhook Configured", 
                "Please set your Discord webhook URL in Settings.\n\n"
                "To create a webhook:\n"
                "1. Go to your Discord server\n"
                "2. Server Settings → Integrations → Webhooks\n"
                "3. Create webhook and copy URL"
            )
            return
        
        # Get the bard text content
        content = self.bard_text.get(1.0, tk.END).strip()
        
        if not content or len(content) < 50:
            messagebox.showwarning("No Content", "Generate a tale or summary first!")
            return
        
        # Discord has a 2000 character limit per message
        # Split into multiple messages if needed
        max_length = 1900  # Leave some room for formatting
        
        try:
            # Prepare the first message with a header
            header = "🐙 **Session Recap from The Kraken Dreams**\n\n"
            
            if len(content) <= max_length:
                # Single message
                payload = {"content": header + content}
                response = requests.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status()
            else:
                # Split into chunks
                chunks = []
                remaining = content
                while remaining:
                    if len(remaining) <= max_length:
                        chunks.append(remaining)
                        break
                    
                    # Find a good break point (paragraph or sentence)
                    break_point = remaining.rfind('\n\n', 0, max_length)
                    if break_point == -1:
                        break_point = remaining.rfind('. ', 0, max_length)
                    if break_point == -1:
                        break_point = max_length
                    
                    chunks.append(remaining[:break_point + 1])
                    remaining = remaining[break_point + 1:].strip()
                
                # Send first chunk with header
                payload = {"content": header + chunks[0]}
                response = requests.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                
                # Send remaining chunks
                for chunk in chunks[1:]:
                    time.sleep(0.5)  # Rate limit friendly
                    payload = {"content": chunk}
                    response = requests.post(webhook_url, json=payload, timeout=10)
                    response.raise_for_status()
            
            self.set_status("Posted to Discord! 🎉")
            self.send_notification("Discord Post", "Session summary posted successfully!")
            messagebox.showinfo("Success", "Posted to Discord! 🐙")
            
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Discord Error", f"Failed to post to Discord:\n{str(e)}")


    def run_bard_tale(self):
        """Run the bard's tale generation in background"""
        try:
            bard = self.bard_name.get() or "Zhree"
            style = self.narrative_style.get()
            model = self.ollama_model.get()
            chunk_size = int(self.chunk_size.get() or 50)
            
            # Build character info string
            char_info_lines = []
            for speaker, gender in self.speaker_genders.items():
                if gender and gender != "Unknown":
                    char_info_lines.append(f"{speaker} ({gender})")
            char_info_str = ", ".join(char_info_lines)

            # Parse transcript into dialogue lines
            lines = []
            for line in self.current_transcript.split("\n"):
                match = re.match(r'\[\d+:\d+\] ([^:]+): (.+)', line)
                if match:
                    speaker, text = match.groups()
                    lines.append(f"{speaker}: {text}")

            if not lines:
                self.root.after(0, lambda: messagebox.showwarning("No Content", "No dialogue found in transcript"))
                self.root.after(0, self.bard_tale_complete)
                return

            # Get style instruction from the narrative module (NARRATIVE_STYLES)
            style_data = NARRATIVE_STYLES.get(style, NARRATIVE_STYLES["Epic Fantasy"])
            style_instruction = style_data.get("prompt_prefix", "").format(bard_name=bard)


            # Generate title first
            self.update_bard_status("Generating title...")

            title_prompt = f"""You are {bard}, a bard recounting an adventure. 
CHARACTERS: {char_info_str}

Based on this dialogue snippet, create a dramatic title for this tale (just the title, nothing else):

{chr(10).join(lines[:20])}"""

            title = self.call_llm(model, title_prompt)
            if self.bard_stop_requested:
                self.root.after(0, self.bard_tale_complete)
                return

            title = title.strip().strip('"').strip("'")
            self.root.after(0, lambda: self.append_bard_text(f"\n{title}\n\n", "title"))
            self.root.after(0, lambda: self.append_bard_text(f"As told by {bard} the Bard\n\n", "chapter"))

            # Process in chunks
            total_chunks = (len(lines) + chunk_size - 1) // chunk_size
            full_tale = ""

            for i in range(0, len(lines), chunk_size):
                if self.bard_stop_requested:
                    break

                chunk = lines[i:i + chunk_size]
                chunk_num = i // chunk_size + 1
                progress = int((chunk_num / total_chunks) * 100)

                self.update_bard_status(f"Weaving chapter {chunk_num} of {total_chunks}...")
                self.root.after(0, lambda p=progress: self.bard_progress.config(value=p))

                # Build context from previous content
                context = f"Previous narrative summary: {full_tale[-500:]}" if full_tale else "This is the beginning of the tale."

                prompt = f"""You are {bard}, a skilled bard from a D&D party. You are retelling your party's adventure as a story.

{style_instruction}
CHARACTERS: {char_info_str}

IMPORTANT RULES:
- Transform the dialogue into flowing narrative prose
- Remove filler words (um, uh, like, you know, etc.)
- Clean up incomplete sentences and stutters
- Keep character names and their actions accurate
- Add atmospheric descriptions between dialogue
- DO NOT add events that didn't happen - stay faithful to the transcript
- Write in third person narrative
- Make it engaging and immersive

{context}

Transform this section of dialogue into narrative:

{chr(10).join(chunk)}

Write the narrative (no meta-commentary, just the story):"""

                response = self.call_llm(model, prompt)
                if self.bard_stop_requested:
                    break

                if response:
                    full_tale += response + "\n\n"
                    self.root.after(0, lambda r=response: self.append_bard_text(r + "\n\n", "body"))

            # Add closing if completed
            if not self.bard_stop_requested:
                self.update_bard_status("Adding the bard's closing...")

                closing_prompt = f"""You are {bard} the bard. Write a brief, poetic closing line for this tale (1-2 sentences). Something like "And so ends..." or "Thus concludes...". Just the closing, nothing else."""

                closing = self.call_llm(model, closing_prompt)
                if closing:
                    self.root.after(0, lambda c=closing: self.append_bard_text(f"\n— {c.strip()}\n", "chapter"))

            self.root.after(0, self.bard_tale_complete)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, self.bard_tale_complete)

    def call_llm(self, model, prompt):
        """Call the selected LLM provider"""
        provider = self.llm_provider.get()
        if provider == "Groq (Cloud)":
            return self.call_groq(model, prompt)
        else:
            return self.call_ollama(model, prompt)

    def call_ollama(self, model, prompt):
        """Call Ollama API"""
        ollama_url = self.config.get("ollama_url", "http://localhost:11434")
        try:
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                    }
                },
                timeout=120
            )

            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                self.root.after(0, lambda: self.log(f"Ollama error: {response.status_code}"))
                return ""
        except Exception as e:
            self.root.after(0, lambda: self.log(f"Ollama error: {e}"))
            return ""

    def call_groq(self, model, prompt):
        """Call Groq API"""
        api_key = self.config.get("groq_api_key", "").strip()
        groq_url = self.config.get("groq_url", "https://api.groq.com/openai/v1/chat/completions")

        if not api_key:
            self.root.after(0, lambda: messagebox.showerror("Error",
                "Groq API key is required.\n\nClick Settings (⚙️) to add your key.\n\n"
                "Get a free key at:\nhttps://console.groq.com"))
            return ""

        try:
            response = requests.post(
                groq_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 4096
                },
                timeout=60
            )

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            elif response.status_code == 401:
                self.root.after(0, lambda: self.log("Groq error: Invalid API key"))
                return ""
            elif response.status_code == 429:
                self.root.after(0, lambda: self.log("Groq error: Rate limit exceeded, waiting..."))
                time.sleep(5)
                return self.call_groq(model, prompt)  # Retry
            else:
                error_msg = response.json().get("error", {}).get("message", response.status_code)
                self.root.after(0, lambda: self.log(f"Groq error: {error_msg}"))
                return ""
        except Exception as e:
            self.root.after(0, lambda: self.log(f"Groq error: {e}"))
            return ""

    def update_bard_status(self, message):
        """Update bard status label"""
        self.root.after(0, lambda: self.bard_status.config(text=message))
        self.root.after(0, lambda: self.set_status(message))

    def append_bard_text(self, text, tag=None):
        """Append text to bard output"""
        self.bard_text.insert(tk.END, text, tag)
        self.bard_text.see(tk.END)

    def bard_tale_complete(self):
        """Clean up after bard tale generation"""
        self.bard_running = False
        self.bard_stop_requested = False
        self.bard_btn.config(state='normal')
        if hasattr(self, 'summary_btn'):
            self.summary_btn.config(state='normal')
        self.stop_bard_btn.config(state='disabled')
        self.bard_progress['value'] = 100
        self.bard_status.config(text="Tale complete!" if not self.bard_stop_requested else "Stopped")
        self.set_status("The bard's tale has been woven!")

    def save_bard_tale(self):
        """Save the bard's tale to file"""
        file_path = filedialog.asksaveasfilename(
            title="Save Bard's Tale",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.bard_text.get(1.0, tk.END))
            self.set_status(f"Tale saved: {file_path}")

    def copy_bard_tale(self):
        """Copy the bard's tale to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.bard_text.get(1.0, tk.END))
        self.set_status("Tale copied to clipboard!")

    def start_session_summary(self):
        """Start the session summary generation"""
        if not self.current_transcript or len(self.current_transcript.strip()) < 100:
            messagebox.showwarning("No Transcript", "Please load or create a transcript first (in the PREVIEW tab)")
            return

        if self.bard_running:
            return

        self.bard_running = True
        self.bard_stop_requested = False
        self.bard_btn.config(state='disabled')
        if hasattr(self, 'summary_btn'):
            self.summary_btn.config(state='disabled')
        self.stop_bard_btn.config(state='normal')
        self.bard_text.delete(1.0, tk.END)
        self.bard_progress['value'] = 0

        thread = threading.Thread(target=self.run_session_summary, daemon=True)
        thread.start()

    def run_session_summary(self):
        """Run the session summary generation in background"""
        try:
            bard = self.bard_name.get() or "Zhree"
            model = self.ollama_model.get()
            
            # Build character info string
            char_info_lines = []
            for speaker, gender in self.speaker_genders.items():
                if gender and gender != "Unknown":
                    char_info_lines.append(f"{speaker} ({gender})")
            char_info_str = ", ".join(char_info_lines)
            
            # Parse transcript into lines
            lines = []
            for line in self.current_transcript.split("\n"):
                match = re.match(r'\[\d+:\d+\] ([^:]+): (.+)', line)
                if match:
                    speaker, text = match.groups()
                    lines.append(f"{speaker}: {text}")

            if not lines:
                self.root.after(0, lambda: messagebox.showwarning("No Content", "No dialogue found in transcript"))
                self.root.after(0, self.bard_tale_complete)
                return

            self.update_bard_status("Reading the scrolls for summary...")

            # Chunking strategies for summary
            # We use larger chunks for summary than for narrative
            summary_chunk_size = 200
            total_chunks = max(1, (len(lines) + summary_chunk_size - 1) // summary_chunk_size)

            intermediate_summaries = []

            for i in range(0, len(lines), summary_chunk_size):
                if self.bard_stop_requested:
                    break

                chunk = lines[i:i + summary_chunk_size]
                chunk_num = i // summary_chunk_size + 1
                progress = int((chunk_num / total_chunks) * 50)  # First half of progress

                self.update_bard_status(f"Summarizing part {chunk_num} of {total_chunks}...")
                self.root.after(0, lambda p=progress: self.bard_progress.config(value=p))

                # Create a summary of this chunk
                chunk_prompt = f"""You are {bard}, summarizing a D&D session.
CHARACTERS: {char_info_str}

Summarize the key events, decisions, and important dialogue from this section. Be concise but capture important details:

{chr(10).join(chunk)}

Summary of key events:"""

                chunk_summary = self.call_llm(model, chunk_prompt)
                if chunk_summary:
                    intermediate_summaries.append(chunk_summary)

            if self.bard_stop_requested:
                self.root.after(0, self.bard_tale_complete)
                return

            # If no intermediate summaries, use the raw lines directly
            if not intermediate_summaries:
                combined_summary = "\n".join(lines[:100])  # Use first 100 lines if LLM failed
            else:
                combined_summary = "\n\n".join(intermediate_summaries)

            # Final Summary
            self.update_bard_status("Writing the final recap...")
            self.root.after(0, lambda: self.bard_progress.config(value=75))

            final_prompt = f"""You are {bard}, the party's bard.
Based on these notes from our latest adventure, write a short, sweet, and to-the-point session recap suitable for a Discord announcement.
Use bullet points for key events. Keep it exciting but concise (under 200 words).

Notes:
{combined_summary}

Write the session recap:"""

            final_response = self.call_llm(model, final_prompt)
            
            if final_response:
                self.root.after(0, lambda: self.append_bard_text("📝 SESSION RECAP\n\n", "title"))
                self.root.after(0, lambda: self.append_bard_text(final_response, "body"))
                self.root.after(0, lambda: self.append_bard_text("\n\n(Ready for Discord)", "chapter"))

            self.root.after(0, self.bard_tale_complete)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, self.bard_tale_complete)

    # ==================== SETTINGS FUNCTIONS ====================
    def load_settings_to_ui(self):
        """Load saved settings into UI fields"""
        # Bard's Tale settings
        self.bard_name.set(self.config.get("bard_name", "Zhree"))
        self.chunk_size.set(str(self.config.get("chunk_size", 50)))
        # Refresh models from Ollama/Groq
        self.refresh_models()

    def save_settings_from_ui(self):
        """Save UI field values to config"""
        self.config["ollama_model"] = self.ollama_model.get()
        self.config["bard_name"] = self.bard_name.get()
        try:
            self.config["chunk_size"] = int(self.chunk_size.get())
        except:
            self.config["chunk_size"] = 50
        save_config(self.config)

    def show_settings_dialog(self):
        """
        Show the settings dialog.
        
        Uses the modular SettingsDialog from src.ui.settings_dialog module.
        The dialog handles all configuration for audio devices, API keys, and LLM providers.
        """
        def on_settings_saved():
            """Callback when settings are saved - refresh UI elements."""
            # Reload config from file to ensure we have the latest saved values
            self.config = load_config()
            self.refresh_models()
            self.set_status("Settings saved!")
        
        # Use the modular settings dialog
        SettingsDialog(self.root, self.config, on_settings_saved)




def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    app = KrakenSuite(root)
    root.mainloop()


if __name__ == "__main__":
    main()
