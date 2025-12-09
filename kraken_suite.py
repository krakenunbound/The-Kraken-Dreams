"""
THE KRAKEN DREAMS - D&D Session Recording & Transcription
A dark-themed application for recording, transcribing, and organizing your tabletop sessions.

Version: 1.3.1
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
        self.playback_process = None
        self.is_playing = False
        self.is_paused = False
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

        self.setup_styles()
        self.transcription_stop_requested = False
        self.setup_ui()
        self.load_settings_to_ui()
        
        # Bind global hotkeys
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
        settings_btn = self.create_button(header, "⚙️ Settings", self.show_settings_dialog, small=True)
        settings_btn.pack(side=tk.RIGHT, padx=5)
        
        # Search button in header
        search_btn = self.create_button(header, "🔍 Search", self.show_search_dialog, small=True)
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

        self.setup_record_tab()
        self.setup_transcribe_tab()
        self.setup_speakers_tab()
        self.setup_preview_tab()
        self.setup_bard_tab()

        # Status bar
        self.status_bar = tk.Label(main_container, text="Ready to unleash the Kraken...",
                                   font=('Segoe UI', 9), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim'],
                                   anchor='w', padx=15, pady=5)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ==================== TAB 1: RECORD (OBS Guide) ====================
    def setup_record_tab(self):
        container = tk.Frame(self.record_tab, bg=KRAKEN['bg_dark'])
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Header
        tk.Label(container, text="🎬 Recording Your D&D Session", font=('Segoe UI', 18, 'bold'),
                bg=KRAKEN['bg_dark'], fg=KRAKEN['accent_glow']).pack(anchor='w', pady=(0, 5))
        tk.Label(container, text="Use OBS Studio to capture both your microphone and Discord/system audio",
                font=('Segoe UI', 10), bg=KRAKEN['bg_dark'], fg=KRAKEN['text_dim']).pack(anchor='w', pady=(0, 20))

        # Download section
        download_frame = tk.Frame(container, bg=KRAKEN['bg_mid'], padx=15, pady=15)
        download_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(download_frame, text="Step 1: Download OBS Studio (Free)", font=('Segoe UI', 12, 'bold'),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['accent_light']).pack(anchor='w')

        link_frame = tk.Frame(download_frame, bg=KRAKEN['bg_mid'])
        link_frame.pack(fill=tk.X, pady=(10, 5))
        tk.Label(link_frame, text="https://obsproject.com/download", font=('Segoe UI', 11),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['biolum']).pack(side=tk.LEFT)

        def open_obs_website():
            import webbrowser
            webbrowser.open("https://obsproject.com/download")

        open_btn = tk.Button(link_frame, text="Open Download Page", font=('Segoe UI', 10),
                            bg=KRAKEN['accent'], fg=KRAKEN['text_bright'], bd=0, padx=15, pady=5,
                            cursor='hand2', command=open_obs_website)
        open_btn.pack(side=tk.LEFT, padx=(20, 0))

        # Setup instructions
        setup_frame = tk.Frame(container, bg=KRAKEN['bg_mid'], padx=15, pady=15)
        setup_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(setup_frame, text="Step 2: Configure OBS for Audio Recording", font=('Segoe UI', 12, 'bold'),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['accent_light']).pack(anchor='w', pady=(0, 10))

        instructions = [
            "1. Open OBS Studio and go to Settings → Output",
            "2. Set Output Mode to 'Advanced', then select Recording tab",
            "3. Set Recording Format to 'mp4' or 'mkv' (mkv is safer if OBS crashes)",
            "4. Set Audio Encoder to 'FFmpeg AAC' or similar",
            "",
            "5. Go to Settings → Audio",
            "6. Set Sample Rate to 48kHz",
            "7. Desktop Audio: Select your speakers/headphones (captures Discord)",
            "8. Mic/Auxiliary Audio: Select your microphone",
            "",
            "9. Add a Window Capture source → select your Discord voice chat window",
            "   (This helps identify speakers later - you'll see who's talking!)",
            "10. Click 'Start Recording' when your session begins",
            "11. Click 'Stop Recording' when done - file saves automatically",
        ]

        for instruction in instructions:
            if instruction == "":
                tk.Frame(setup_frame, height=5, bg=KRAKEN['bg_mid']).pack()
            else:
                tk.Label(setup_frame, text=instruction, font=('Segoe UI', 10),
                        bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], anchor='w').pack(anchor='w', pady=1)

        # Tips section
        tips_frame = tk.Frame(container, bg=KRAKEN['bg_mid'], padx=15, pady=15)
        tips_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(tips_frame, text="Step 3: After Recording", font=('Segoe UI', 12, 'bold'),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['accent_light']).pack(anchor='w', pady=(0, 10))

        tips = [
            "• Find your recording in: C:\\Users\\[You]\\Videos (default OBS location)",
            "• Drag the file onto the TRANSCRIBE tab, or click to browse",
            "• The Kraken will transcribe and identify speakers automatically",
            "",
            "Why capture Discord video?",
            "• Discord shows a green ring around whoever is speaking",
            "• Play back the video while assigning voices in the Speakers tab",
            "• Much easier than trying to recognize voices by ear alone!",
            "",
            "Pro Tips:",
            "• Name your OBS profile 'D&D Session' for quick access",
            "• Use Scene Collections to save your Discord capture setup",
            "• Check audio meters in OBS before starting - both should show activity",
        ]

        for tip in tips:
            if tip == "":
                tk.Frame(tips_frame, height=5, bg=KRAKEN['bg_mid']).pack()
            else:
                tk.Label(tips_frame, text=tip, font=('Segoe UI', 10),
                        bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], anchor='w').pack(anchor='w', pady=1)

    # ==================== TAB 2: TRANSCRIBE ====================
    def setup_transcribe_tab(self):
        container = tk.Frame(self.transcribe_tab, bg=KRAKEN['bg_dark'])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Top section - file selection (compact)
        top_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # Drop zone - smaller, on the left
        self.drop_zone = tk.Label(top_frame,
            text="🐙\nDrop file or click",
            font=('Segoe UI', 11), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim'],
            relief='ridge', bd=2, cursor='hand2', justify='center', width=20)
        self.drop_zone.pack(side=tk.LEFT, padx=(0, 15), ipady=15)
        self.drop_zone.bind('<Button-1>', self.browse_media_file)

        # Setup drag and drop if available
        if HAS_DND:
            try:
                self.drop_zone.drop_target_register(DND_FILES)
                self.drop_zone.dnd_bind('<<Drop>>', self.on_file_drop)
            except:
                pass

        # Right side - file info and buttons
        right_frame = tk.Frame(top_frame, bg=KRAKEN['bg_dark'])
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # File info
        self.file_label = tk.Label(right_frame, text="No file selected", font=('Segoe UI', 12),
                                  bg=KRAKEN['bg_dark'], fg=KRAKEN['text_dim'], anchor='w')
        self.file_label.pack(fill=tk.X, pady=(5, 10))

        # Button row
        btn_frame = tk.Frame(right_frame, bg=KRAKEN['bg_dark'])
        btn_frame.pack(fill=tk.X)

        # Transcribe button
        self.transcribe_btn = self.create_button(btn_frame, "🔮 BEGIN TRANSCRIPTION", self.start_transcription, large=True)
        self.transcribe_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Stop button
        self.stop_transcribe_btn = self.create_button(btn_frame, "⏹ STOP", self.stop_transcription, large=True)
        self.stop_transcribe_btn.pack(side=tk.LEFT)
        self.stop_transcribe_btn.config(state='disabled')

        # Progress bar
        self.transcribe_progress = ttk.Progressbar(right_frame, mode='indeterminate', length=300)
        self.transcribe_progress.pack(fill=tk.X, pady=(10, 0))

        # ===== SPLIT LOG AREA =====
        # Use PanedWindow for resizable split
        paned = tk.PanedWindow(container, orient=tk.VERTICAL, bg=KRAKEN['tentacle'],
                               sashwidth=8, sashrelief='raised')
        paned.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # TOP: Status log (user-friendly messages)
        status_frame = tk.Frame(paned, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
        status_header = tk.Label(status_frame, text="📜 STATUS - What's happening",
                                font=('Segoe UI', 10, 'bold'), bg=KRAKEN['tentacle'],
                                fg=KRAKEN['text_bright'], anchor='w', padx=10, pady=5)
        status_header.pack(fill=tk.X)
        self.log_text = tk.Text(status_frame, font=('Consolas', 11), bg=KRAKEN['bg_widget'],
                               fg=KRAKEN['biolum'], insertbackground=KRAKEN['text'], relief='flat',
                               wrap=tk.WORD, padx=10, pady=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        status_scroll = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        status_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=status_scroll.set)
        paned.add(status_frame, minsize=120)

        # BOTTOM: Technical/engine log (copy-paste friendly)
        tech_frame = tk.Frame(paned, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
        tech_header = tk.Label(tech_frame, text="🔧 ENGINE LOG - Copy this for debugging",
                              font=('Segoe UI', 10, 'bold'), bg='#1a1a2e',
                              fg='#888888', anchor='w', padx=10, pady=5)
        tech_header.pack(fill=tk.X)
        self.tech_log_text = tk.Text(tech_frame, font=('Consolas', 9), bg='#0d0d1a',
                                    fg='#aaaaaa', insertbackground=KRAKEN['text'], relief='flat',
                                    wrap=tk.NONE, padx=10, pady=10)
        self.tech_log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Horizontal scrollbar for long lines
        tech_hscroll = ttk.Scrollbar(tech_frame, orient=tk.HORIZONTAL, command=self.tech_log_text.xview)
        tech_hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        tech_scroll = ttk.Scrollbar(self.tech_log_text, command=self.tech_log_text.yview)
        tech_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tech_log_text.config(yscrollcommand=tech_scroll.set, xscrollcommand=tech_hscroll.set)
        paned.add(tech_frame, minsize=100)

        # Initial messages
        self.log("Ready. Select a file to transcribe.")
        self.tech_log("Engine log initialized. Technical output from WhisperX/Pyannote will appear here.")

    # ==================== TAB 3: SPEAKERS ====================
    def setup_speakers_tab(self):
        container = tk.Frame(self.speakers_tab, bg=KRAKEN['bg_dark'])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Top controls
        top_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
        top_frame.pack(fill=tk.X, pady=(0, 10))

        self.create_button(top_frame, "📂 Load Transcript", self.load_transcript_file, small=True).pack(side=tk.LEFT, padx=5)
        self.create_button(top_frame, "📥 Load Mapping", self.load_mapping_file, small=True).pack(side=tk.LEFT, padx=5)
        self.create_button(top_frame, "💾 Save Mapping", self.save_mapping_file, small=True).pack(side=tk.LEFT, padx=5)

        # Current speaker display (large avatar during playback) - fixed size 80x80
        current_speaker_frame = tk.Frame(top_frame, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
        current_speaker_frame.pack(side=tk.RIGHT, padx=(20, 0))

        # Use a frame with fixed size to contain the avatar
        avatar_container = tk.Frame(current_speaker_frame, bg=KRAKEN['bg_widget'], width=80, height=80)
        avatar_container.pack(side=tk.LEFT, padx=5, pady=5)
        avatar_container.pack_propagate(False)  # Prevent resizing

        self.current_avatar_label = tk.Label(avatar_container, bg=KRAKEN['bg_widget'],
                                            text="👤", font=('Segoe UI', 28))
        self.current_avatar_label.pack(expand=True, fill=tk.BOTH)
        self.current_avatar_image = None  # Keep reference

        current_info_frame = tk.Frame(current_speaker_frame, bg=KRAKEN['bg_mid'])
        current_info_frame.pack(side=tk.LEFT, padx=10, pady=5)

        tk.Label(current_info_frame, text="NOW SPEAKING", font=('Segoe UI', 8),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(anchor='w')
        self.current_speaker_name = tk.Label(current_info_frame, text="—", font=('Segoe UI', 12, 'bold'),
                                            bg=KRAKEN['bg_mid'], fg=KRAKEN['biolum'])
        self.current_speaker_name.pack(anchor='w')

        # Playback controls frame
        playback_frame = tk.Frame(top_frame, bg=KRAKEN['bg_dark'])
        playback_frame.pack(side=tk.RIGHT, padx=(0, 10))

        # Row 1: Play/Pause/Stop and time
        controls_row = tk.Frame(playback_frame, bg=KRAKEN['bg_dark'])
        controls_row.pack(fill=tk.X)

        self.play_btn = self.create_button(controls_row, "▶ Play", self.start_playback, small=True)
        self.play_btn.pack(side=tk.LEFT, padx=2)

        self.pause_btn = self.create_button(controls_row, "⏸ Pause", self.pause_playback, small=True)
        self.pause_btn.pack(side=tk.LEFT, padx=2)
        self.pause_btn.config(state='disabled')

        self.stop_btn = self.create_button(controls_row, "⏹ Stop", self.stop_playback, small=True)
        self.stop_btn.pack(side=tk.LEFT, padx=2)

        # Skip buttons
        tk.Button(controls_row, text="⏪-10s", font=('Segoe UI', 9), bg=KRAKEN['bg_widget'],
                 fg=KRAKEN['text'], activebackground=KRAKEN['accent'], bd=0, padx=6,
                 command=lambda: self.skip_playback(-10)).pack(side=tk.LEFT, padx=2)
        tk.Button(controls_row, text="⏪-5s", font=('Segoe UI', 9), bg=KRAKEN['bg_widget'],
                 fg=KRAKEN['text'], activebackground=KRAKEN['accent'], bd=0, padx=6,
                 command=lambda: self.skip_playback(-5)).pack(side=tk.LEFT, padx=2)
        tk.Button(controls_row, text="+5s⏩", font=('Segoe UI', 9), bg=KRAKEN['bg_widget'],
                 fg=KRAKEN['text'], activebackground=KRAKEN['accent'], bd=0, padx=6,
                 command=lambda: self.skip_playback(5)).pack(side=tk.LEFT, padx=2)
        tk.Button(controls_row, text="+10s⏩", font=('Segoe UI', 9), bg=KRAKEN['bg_widget'],
                 fg=KRAKEN['text'], activebackground=KRAKEN['accent'], bd=0, padx=6,
                 command=lambda: self.skip_playback(10)).pack(side=tk.LEFT, padx=2)

        self.playback_time = tk.Label(controls_row, text="00:00 / 00:00", font=('Consolas', 11),
                                     bg=KRAKEN['bg_dark'], fg=KRAKEN['accent_light'])
        self.playback_time.pack(side=tk.LEFT, padx=10)

        # Row 2: Scrub bar (seek slider)
        scrub_row = tk.Frame(playback_frame, bg=KRAKEN['bg_dark'])
        scrub_row.pack(fill=tk.X, pady=(5, 0))

        self.scrub_var = tk.DoubleVar(value=0)
        self.scrub_bar = tk.Scale(scrub_row, from_=0, to=100, orient=tk.HORIZONTAL,
                                  variable=self.scrub_var, showvalue=False, length=300,
                                  bg=KRAKEN['bg_widget'], fg=KRAKEN['accent'],
                                  troughcolor=KRAKEN['bg_dark'], highlightthickness=0,
                                  sliderrelief='flat', command=self.on_scrub)
        self.scrub_bar.pack(fill=tk.X, expand=True)

        # Main content - speakers list with canvas scroll
        main_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollable speaker list
        self.speakers_canvas = tk.Canvas(main_frame, bg=KRAKEN['bg_dark'], highlightthickness=0)
        speakers_scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=self.speakers_canvas.yview)
        self.speakers_frame = tk.Frame(self.speakers_canvas, bg=KRAKEN['bg_dark'])

        self.speakers_frame.bind('<Configure>', lambda e: self.speakers_canvas.configure(scrollregion=self.speakers_canvas.bbox('all')))
        self.speakers_window = self.speakers_canvas.create_window((0, 0), window=self.speakers_frame, anchor='nw')
        self.speakers_canvas.configure(yscrollcommand=speakers_scrollbar.set)

        self.speakers_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        speakers_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel
        self.speakers_canvas.bind_all('<MouseWheel>', lambda e: self.speakers_canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))

        # Bind canvas resize to relayout speaker cards
        self.speakers_canvas.bind('<Configure>', self.on_speakers_canvas_resize)
        self.speaker_cards = []  # Store card widgets for relayout

        # Bottom controls
        bottom_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
        bottom_frame.pack(fill=tk.X, pady=(15, 0))

        self.apply_btn = self.create_button(bottom_frame, "✨ APPLY NAMES", self.apply_speaker_names, large=True)
        self.apply_btn.pack()

        # Speaker entry widgets storage
        self.speaker_entries = {}
        self.speaker_indicators = {}
        self.speaker_cards = []  # For grid layout

    # ==================== TAB 4: PREVIEW ====================
    def setup_preview_tab(self):
        container = tk.Frame(self.preview_tab, bg=KRAKEN['bg_dark'])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Top controls
        top_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
        top_frame.pack(fill=tk.X, pady=(0, 10))

        self.create_button(top_frame, "💾 Save As...", self.save_transcript, small=True).pack(side=tk.LEFT, padx=5)
        self.create_button(top_frame, "📋 Copy All", self.copy_transcript, small=True).pack(side=tk.LEFT, padx=5)

        # Preview text area
        preview_frame = tk.Frame(container, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_text = tk.Text(preview_frame, font=('Consolas', 10), bg=KRAKEN['bg_widget'],
                                   fg=KRAKEN['text'], insertbackground=KRAKEN['text'], relief='flat',
                                   wrap=tk.WORD, padx=15, pady=15)
        self.preview_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        preview_scroll = ttk.Scrollbar(preview_frame, command=self.preview_text.yview)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_text.config(yscrollcommand=preview_scroll.set)

    # ==================== TAB 5: BARD'S TALE ====================
    def setup_bard_tab(self):
        container = tk.Frame(self.bard_tab, bg=KRAKEN['bg_dark'])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Header
        header_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
        header_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(header_frame, text="🎭 The Bard's Tale", font=('Segoe UI', 16, 'bold'),
                bg=KRAKEN['bg_dark'], fg=KRAKEN['accent_glow']).pack(side=tk.LEFT)

        tk.Label(header_frame, text="Transform your session into a narrative story, as told by Zhree the Bard",
                font=('Segoe UI', 10, 'italic'), bg=KRAKEN['bg_dark'], fg=KRAKEN['text_dim']).pack(side=tk.LEFT, padx=(15, 0))

        # Settings section
        settings_frame = self.create_section(container, "⚙️ SETTINGS")
        settings_frame.pack(fill=tk.X, pady=(0, 15))

        # Provider selection
        provider_row = tk.Frame(settings_frame, bg=KRAKEN['bg_mid'])
        provider_row.pack(fill=tk.X, pady=5)
        tk.Label(provider_row, text="LLM Provider:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], width=15, anchor='w').pack(side=tk.LEFT)
        self.llm_provider = tk.StringVar(value="Ollama (Local)")
        provider_combo = ttk.Combobox(provider_row, textvariable=self.llm_provider, width=22, state='readonly',
                                      values=["Ollama (Local)", "Groq (Cloud)"])
        provider_combo.pack(side=tk.LEFT, padx=(10, 0))
        provider_combo.bind('<<ComboboxSelected>>', self.on_provider_change)

        # Model selection (dropdown populated from Ollama/Groq)
        model_row = tk.Frame(settings_frame, bg=KRAKEN['bg_mid'])
        model_row.pack(fill=tk.X, pady=5)
        tk.Label(model_row, text="Model:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], width=15, anchor='w').pack(side=tk.LEFT)
        self.ollama_model = tk.StringVar(value="")
        self.model_combo = ttk.Combobox(model_row, textvariable=self.ollama_model, width=30, state='readonly')
        self.model_combo.pack(side=tk.LEFT, padx=(10, 10))
        self.refresh_models_btn = self.create_button(model_row, "🔄 Refresh", self.refresh_models, small=True)
        self.refresh_models_btn.pack(side=tk.LEFT, padx=5)

        # Bard name
        bard_row = tk.Frame(settings_frame, bg=KRAKEN['bg_mid'])
        bard_row.pack(fill=tk.X, pady=5)
        tk.Label(bard_row, text="Bard's Name:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], width=15, anchor='w').pack(side=tk.LEFT)
        self.bard_name = tk.StringVar(value="Zhree")
        tk.Entry(bard_row, textvariable=self.bard_name, font=('Segoe UI', 10),
                bg=KRAKEN['bg_widget'], fg=KRAKEN['text'], insertbackground=KRAKEN['text'],
                relief='flat', width=25).pack(side=tk.LEFT, padx=(10, 0), ipady=4)

        # Style selection (uses styles from src.core.narrative module)
        style_row = tk.Frame(settings_frame, bg=KRAKEN['bg_mid'])
        style_row.pack(fill=tk.X, pady=5)
        tk.Label(style_row, text="Narrative Style:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], width=15, anchor='w').pack(side=tk.LEFT)
        self.narrative_style = tk.StringVar(value="Epic Fantasy")
        style_combo = ttk.Combobox(style_row, textvariable=self.narrative_style, width=22, state='readonly',
                                   values=get_narrative_styles())
        style_combo.pack(side=tk.LEFT, padx=(10, 0))


        # Chunk size
        chunk_row = tk.Frame(settings_frame, bg=KRAKEN['bg_mid'])
        chunk_row.pack(fill=tk.X, pady=5)
        tk.Label(chunk_row, text="Process in chunks:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], width=15, anchor='w').pack(side=tk.LEFT)
        self.chunk_size = tk.StringVar(value="50")
        tk.Entry(chunk_row, textvariable=self.chunk_size, font=('Segoe UI', 10),
                bg=KRAKEN['bg_widget'], fg=KRAKEN['text'], insertbackground=KRAKEN['text'],
                relief='flat', width=10).pack(side=tk.LEFT, padx=(10, 0), ipady=4)
        tk.Label(chunk_row, text="lines at a time (smaller = more detail, larger = faster)",
                font=('Segoe UI', 9), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(side=tk.LEFT, padx=(10, 0))

        # Action buttons
        button_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
        button_frame.pack(fill=tk.X, pady=10)

        self.bard_btn = self.create_button(button_frame, "🎭 SPIN THE TALE", self.start_bard_tale, large=True)
        self.bard_btn.pack(side=tk.LEFT, padx=5)

        self.summary_btn = self.create_button(button_frame, "📜 Summarize", self.start_session_summary, large=True)
        self.summary_btn.pack(side=tk.LEFT, padx=5)

        self.stop_bard_btn = self.create_button(button_frame, "⏹ Stop", self.stop_bard_tale, small=True)
        self.stop_bard_btn.pack(side=tk.LEFT, padx=5)
        self.stop_bard_btn.config(state='disabled')
        
        self.discord_btn = self.create_button(button_frame, "💬 Post to Discord", self.post_to_discord, small=True)
        self.discord_btn.pack(side=tk.LEFT, padx=5)

        self.create_button(button_frame, "💾 Save Tale", self.save_bard_tale, small=True).pack(side=tk.RIGHT, padx=5)
        self.create_button(button_frame, "📋 Copy Tale", self.copy_bard_tale, small=True).pack(side=tk.RIGHT, padx=5)


        # Progress
        progress_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
        progress_frame.pack(fill=tk.X, pady=5)

        self.bard_progress = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.bard_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.bard_status = tk.Label(progress_frame, text="Ready to weave tales...", font=('Segoe UI', 9),
                                   bg=KRAKEN['bg_dark'], fg=KRAKEN['text_dim'])
        self.bard_status.pack(side=tk.LEFT)

        # Party members with avatars
        party_frame = self.create_section(container, "🎭 THE PARTY")
        party_frame.pack(fill=tk.X, pady=(0, 10))

        self.party_avatars_frame = tk.Frame(party_frame, bg=KRAKEN['bg_mid'])
        self.party_avatars_frame.pack(fill=tk.X)

        # Placeholder text
        self.party_placeholder = tk.Label(self.party_avatars_frame,
            text="Load a transcript with speakers to see the party members here",
            font=('Segoe UI', 10, 'italic'), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim'])
        self.party_placeholder.pack(pady=10)

        # Storage for party avatar images
        self.party_avatar_images = {}

        # Output area
        output_frame = tk.Frame(container, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Add a nice header bar
        tale_header = tk.Frame(output_frame, bg=KRAKEN['tentacle'])
        tale_header.pack(fill=tk.X)
        tk.Label(tale_header, text="📜 THE TALE", font=('Segoe UI', 10, 'bold'),
                bg=KRAKEN['tentacle'], fg=KRAKEN['text_bright'], anchor='w', padx=10, pady=5).pack(fill=tk.X)

        self.bard_text = tk.Text(output_frame, font=('Georgia', 11), bg=KRAKEN['bg_widget'],
                                fg=KRAKEN['text'], insertbackground=KRAKEN['text'], relief='flat',
                                wrap=tk.WORD, padx=20, pady=15, spacing1=5, spacing2=3)
        self.bard_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        bard_scroll = ttk.Scrollbar(output_frame, command=self.bard_text.yview)
        bard_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.bard_text.config(yscrollcommand=bard_scroll.set)

        # Configure text tags for styling
        self.bard_text.tag_configure("title", font=('Georgia', 14, 'bold'), foreground=KRAKEN['accent_glow'],
                                     spacing1=10, spacing3=10, justify='center')
        self.bard_text.tag_configure("chapter", font=('Georgia', 12, 'bold italic'), foreground=KRAKEN['biolum'],
                                     spacing1=15, spacing3=5)
        self.bard_text.tag_configure("body", font=('Georgia', 11), foreground=KRAKEN['text'])

        # State
        self.bard_running = False
        self.bard_stop_requested = False

    # ==================== HELPER METHODS ====================
    def create_section(self, parent, title):
        """Create a styled section frame with title"""
        frame = tk.Frame(parent, bg=KRAKEN['bg_mid'], bd=1, relief='solid')

        title_bar = tk.Frame(frame, bg=KRAKEN['tentacle'])
        title_bar.pack(fill=tk.X)
        tk.Label(title_bar, text=title, font=('Segoe UI', 10, 'bold'), bg=KRAKEN['tentacle'],
                fg=KRAKEN['text_bright'], anchor='w', padx=10, pady=5).pack(fill=tk.X)

        content = tk.Frame(frame, bg=KRAKEN['bg_mid'], padx=15, pady=10)
        content.pack(fill=tk.BOTH, expand=True)

        return content

    def create_button(self, parent, text, command, small=False, large=False):
        """Create a styled button"""
        if large:
            font = ('Segoe UI', 12, 'bold')
            padx, pady = 30, 12
            bg = KRAKEN['accent']
        elif small:
            font = ('Segoe UI', 9)
            padx, pady = 12, 5
            bg = KRAKEN['bg_widget']
        else:
            font = ('Segoe UI', 10)
            padx, pady = 15, 8
            bg = KRAKEN['bg_widget']

        btn = tk.Button(parent, text=text, font=font, bg=bg, fg=KRAKEN['text'],
                       activebackground=KRAKEN['accent_light'], activeforeground=KRAKEN['text_bright'],
                       bd=0, cursor='hand2', padx=padx, pady=pady, command=command)
        return btn

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
        """Run transcription with detailed progress feedback"""
        import sys
        import logging
        import warnings

        # Initialize variables for cleanup
        gui_handler = None
        loggers_to_capture = []
        original_showwarning = warnings.showwarning

        try:
            # Log immediately to confirm thread started
            self.log("Transcription thread started...")

            # Create a custom logging handler that sends messages to the TECH log
            class GUILogHandler(logging.Handler):
                def __init__(handler_self, tech_log_func):
                    super().__init__()
                    handler_self.tech_log_func = tech_log_func

                def emit(handler_self, record):
                    msg = handler_self.format(record)
                    if msg.strip():
                        handler_self.tech_log_func(f"[{record.name}] [{record.levelname}] {msg}")

            # Create handler for capturing library output -> goes to ENGINE LOG
            gui_handler = GUILogHandler(self.tech_log)
            gui_handler.setLevel(logging.INFO)
            gui_handler.setFormatter(logging.Formatter('%(message)s'))

            # Attach handler to relevant loggers
            loggers_to_capture = [
                'whisperx', 'whisperx.asr', 'whisperx.vads', 'whisperx.vads.pyannote',
                'pyannote', 'pyannote.audio', 'faster_whisper'
            ]
            for logger_name in loggers_to_capture:
                logger = logging.getLogger(logger_name)
                logger.addHandler(gui_handler)
                logger.setLevel(logging.INFO)

            # Also capture warnings -> goes to ENGINE LOG
            def custom_showwarning(message, category, filename, lineno, file=None, line=None):
                self.tech_log(f"[WARNING] {category.__name__}: {message}")
            warnings.showwarning = custom_showwarning

            # ===== STEP 1: Check prerequisites =====
            self.log("=" * 50)
            self.log("STARTING TRANSCRIPTION PIPELINE")
            self.log("=" * 50)

            if self.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # Check for HuggingFace token
            hf_token = self.config.get("hf_token", "").strip()
            if not hf_token:
                self.root.after(0, lambda: messagebox.showerror("Missing API Key",
                    "HuggingFace token is required for speaker diarization.\n\n"
                    "Click Settings (⚙️) to add your token.\n\n"
                    "Get a free token at:\nhttps://huggingface.co/settings/tokens"))
                self.root.after(0, self.transcription_failed)
                return

            # ===== STEP 2: Import libraries =====
            self.log("")
            self.log("[1/7] Loading libraries...")
            self.tech_log("Importing whisperx...")
            self.log("  → Importing WhisperX...")
            import whisperx
            self.tech_log("Importing DiarizationPipeline from whisperx.diarize...")
            self.log("  → Importing Diarization Pipeline...")
            from whisperx.diarize import DiarizationPipeline
            self.tech_log("Importing torch...")
            self.log("  → Importing PyTorch...")
            import torch
            self.tech_log(f"torch version: {torch.__version__}, CUDA available: {torch.cuda.is_available()}")
            self.log("  ✓ Libraries loaded successfully")

            if self.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 3: Setup device =====
            self.log("")
            self.log("[2/7] Setting up compute device...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cuda":
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
                self.log(f"  → GPU: {gpu_name}")
                self.log(f"  → VRAM: {gpu_memory:.1f} GB")
                self.log(f"  ✓ Using CUDA acceleration")
            else:
                self.log("  → No CUDA GPU detected")
                self.log("  ✓ Using CPU (slower)")

            if self.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 4: Load audio =====
            self.log("")
            self.log("[3/7] Loading audio file...")
            self.log(f"  → File: {os.path.basename(self.selected_file)}")
            file_size = os.path.getsize(self.selected_file) / (1024 * 1024)
            self.log(f"  → Size: {file_size:.1f} MB")
            self.log("  → Extracting audio (ffmpeg)...")
            self.tech_log(f"whisperx.load_audio('{self.selected_file}')")
            audio = whisperx.load_audio(self.selected_file)
            duration_seconds = len(audio) / 16000  # WhisperX uses 16kHz
            duration_minutes = duration_seconds / 60
            hours = int(duration_minutes // 60)
            mins = int(duration_minutes % 60)
            self.tech_log(f"Audio loaded: {len(audio)} samples, {duration_seconds:.1f}s")
            self.log(f"  → Duration: {hours}h {mins}m")
            self.log("  ✓ Audio loaded")

            if self.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 5: Transcribe with Whisper =====
            self.log("")
            self.log("[4/7] Loading Whisper model...")
            
            # Get model from config (default to large-v2 for best accuracy)
            whisper_model = self.config.get("whisper_model", "large-v2")
            whisper_language = self.config.get("whisper_language", "auto")
            self.log(f"  → Model: {whisper_model}")
            self.log(f"  → Language: {whisper_language}")
            compute_type = "float16" if device == "cuda" else "int8"
            self.log(f"  → Compute type: {compute_type}")
            self.log("  → Downloading/loading model weights...")
            self.tech_log(f"whisperx.load_model('{whisper_model}', device='{device}', compute_type='{compute_type}')")
            model = whisperx.load_model(whisper_model, device, compute_type=compute_type)
            self.tech_log("Whisper model loaded successfully")
            self.log("  ✓ Whisper model ready")


            self.log("")
            self.log("[5/7] Transcribing audio...")
            self.log("  → This is the longest step - please wait...")
            batch_size = 16 if device == "cuda" else 4
            self.log(f"  → Batch size: {batch_size}")
            
            # Use specified language or auto-detect
            if whisper_language and whisper_language != "auto":
                self.log(f"  → Using language: {whisper_language}")
                self.tech_log(f"model.transcribe(audio, batch_size={batch_size}, language='{whisper_language}') - STARTING")
                result = model.transcribe(audio, batch_size=batch_size, language=whisper_language)
            else:
                self.log("  → Detecting language...")
                self.tech_log(f"model.transcribe(audio, batch_size={batch_size}) - STARTING")
                result = model.transcribe(audio, batch_size=batch_size)
            
            self.tech_log("model.transcribe() - COMPLETED")
            detected_language = result.get("language", whisper_language if whisper_language != "auto" else "en")
            num_segments = len(result.get("segments", []))
            self.tech_log(f"Result: language={detected_language}, segments={num_segments}")

            self.log(f"  → Language: {detected_language}")
            self.log(f"  → Segments found: {num_segments}")
            self.log("  ✓ Transcription complete")

            if self.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # Free memory
            self.log("  → Releasing Whisper memory...")
            del model
            gc.collect()
            if device == "cuda":
                torch.cuda.empty_cache()
            self.log("  ✓ Memory released")

            # ===== STEP 6: Align words =====
            self.log("")
            self.log("[6/7] Aligning words to audio...")
            self.log(f"  → Loading alignment model ({detected_language})...")
            self.tech_log(f"whisperx.load_align_model(language_code='{detected_language}', device='{device}')")
            model_a, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
            self.tech_log("Alignment model loaded")
            self.log("  ✓ Alignment model loaded")
            self.log("  → Aligning transcript...")
            self.tech_log("whisperx.align() - STARTING")
            result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
            self.tech_log("whisperx.align() - COMPLETED")
            self.log("  ✓ Alignment complete")

            # Free memory
            self.log("  → Releasing alignment model...")
            del model_a
            gc.collect()
            self.tech_log("Alignment model released from memory")

            if self.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 7: Speaker diarization =====
            self.log("")
            self.log("[7/7] Identifying speakers...")
            self.log("  → Loading Pyannote diarization model...")
            self.log("  → Authenticating with HuggingFace...")
            self.tech_log(f"DiarizationPipeline(use_auth_token=hf_token, device='{device}')")
            diarize_model = DiarizationPipeline(use_auth_token=hf_token, device=device)
            self.tech_log("Pyannote diarization model loaded")
            self.log("  ✓ Diarization model loaded")
            self.log("  → Analyzing voices (this takes a while)...")
            self.log("  → Detecting who speaks when...")
            self.tech_log("diarize_model(audio) - STARTING speaker diarization")
            diarize_segments = diarize_model(audio)
            self.tech_log(f"diarize_model() - COMPLETED, got {type(diarize_segments)}")
            self.log("  ✓ Speaker diarization complete")

            if self.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 8: Assign speakers to segments =====
            self.log("")
            self.log("Assigning speakers to transcript...")
            self.tech_log("whisperx.assign_word_speakers() - STARTING")
            result = whisperx.assign_word_speakers(diarize_segments, result)
            self.tech_log("whisperx.assign_word_speakers() - COMPLETED")
            self.log("  ✓ Speakers assigned")

            if self.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 9: Build transcript =====
            self.log("")
            self.log("Building transcript...")
            base_name = os.path.splitext(os.path.basename(self.selected_file))[0]
            output_dir = os.path.dirname(self.selected_file)

            lines = ["D&D Session Transcription", "=" * 50, f"File: {base_name}", ""]
            self.segments_data = []
            found_speakers = set()

            for segment in result["segments"]:
                speaker = segment.get("speaker", "UNKNOWN")
                text = segment.get("text", "").strip()
                start = segment.get("start", 0)
                end = segment.get("end", start + 1)

                if text:
                    minutes = int(start // 60)
                    seconds = int(start % 60)
                    lines.append(f"[{minutes:02d}:{seconds:02d}] {speaker}: {text}")
                    self.segments_data.append({
                        "start": start,
                        "end": end,
                        "speaker": speaker,
                        "text": text
                    })
                    found_speakers.add(speaker)

            self.current_transcript = "\n".join(lines)
            
            # Apply D&D vocabulary corrections
            self.log("  → Applying vocabulary corrections...")
            self.current_transcript = self.apply_vocabulary_corrections(self.current_transcript)
            
            self.current_media_file = self.selected_file


            # ===== STEP 10: Save files =====
            self.log("")
            self.log("Saving output files...")
            txt_path = os.path.join(output_dir, f"{base_name}_notes.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(self.current_transcript)
            self.log(f"  → Saved: {os.path.basename(txt_path)}")

            json_path = os.path.join(output_dir, f"{base_name}_segments.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "media_file": self.selected_file,
                    "segments": self.segments_data,
                    "avatars": self.speaker_avatars
                }, f, indent=2)
            self.log(f"  → Saved: {os.path.basename(json_path)}")

            self.current_output_file = txt_path

            # Setup speakers
            self.speakers = {s: s for s in sorted(found_speakers)}

            # ===== STEP 11: Extract audio for playback =====
            self.log("")
            self.log("Extracting audio for playback...")
            self.extract_audio(self.selected_file)

            # ===== COMPLETE =====
            self.log("")
            self.log("=" * 50)
            self.log("TRANSCRIPTION COMPLETE!")
            self.log("=" * 50)
            self.log(f"  → Found {len(found_speakers)} speakers: {', '.join(sorted(found_speakers))}")
            self.log(f"  → Total segments: {len(self.segments_data)}")
            self.log(f"  → Output: {txt_path}")
            self.log("")
            self.log("Next: Go to SPEAKERS tab to assign names.")

            # Update UI
            self.root.after(0, self.transcription_complete)

        except Exception as e:
            error_msg = str(e)
            import traceback
            tb = traceback.format_exc()

            # Log to STATUS (user-friendly)
            self.log("")
            self.log("=" * 50)
            if "stopped by user" in error_msg.lower():
                self.log("TRANSCRIPTION STOPPED")
            else:
                self.log("TRANSCRIPTION FAILED")
            self.log("=" * 50)
            self.log(f"Error: {e}")
            self.log("")
            self.log("See ENGINE LOG below for full error details.")

            # Log full traceback to ENGINE LOG (copy-paste for debugging)
            self.tech_log("=" * 60)
            self.tech_log("EXCEPTION OCCURRED")
            self.tech_log("=" * 60)
            self.tech_log(f"Exception type: {type(e).__name__}")
            self.tech_log(f"Exception message: {e}")
            self.tech_log("-" * 60)
            self.tech_log("Full traceback:")
            for line in tb.strip().split('\n'):
                self.tech_log(line)
            self.tech_log("=" * 60)

            self.root.after(0, self.transcription_failed)

        finally:
            # Cleanup: Remove our logging handlers (if they were created)
            if gui_handler is not None:
                for logger_name in loggers_to_capture:
                    logger = logging.getLogger(logger_name)
                    try:
                        logger.removeHandler(gui_handler)
                    except:
                        pass
            # Restore original warning handler
            warnings.showwarning = original_showwarning

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


    # ==================== PLAYBACK FUNCTIONS ====================
    def start_playback(self, start_time=0):
        """Start or resume playback from a specific time"""
        if not self.temp_audio_file or not os.path.exists(self.temp_audio_file):
            messagebox.showwarning("No Audio", "No audio file available for playback")
            return

        # If paused, resume from where we left off
        if self.is_paused:
            start_time = self.playback_offset
            self.is_paused = False

        try:
            # Stop any existing playback
            if self.playback_process:
                self.playback_process.terminate()
                self.playback_process = None

            # Start ffplay with seek position
            cmd = ["ffplay", "-nodisp", "-autoexit", "-ss", str(start_time), self.temp_audio_file]
            self.playback_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.is_playing = True
            self.playback_start_time = time.time()
            self.playback_offset = start_time

            # Update button states
            self.play_btn.config(state='disabled')
            self.pause_btn.config(state='normal')
            self.update_playback()
        except Exception as e:
            self.log(f"Playback error: {e}")

    def pause_playback(self):
        """Pause playback and remember position"""
        if self.is_playing and self.playback_process:
            # Calculate current position
            elapsed = time.time() - self.playback_start_time + self.playback_offset
            self.playback_offset = elapsed

            # Stop the process
            self.playback_process.terminate()
            self.playback_process = None
            self.is_playing = False
            self.is_paused = True

            # Update button states
            self.play_btn.config(state='normal', text="▶ Resume")
            self.pause_btn.config(state='disabled')

    def stop_playback(self):
        """Stop playback completely"""
        if self.playback_process:
            self.playback_process.terminate()
            self.playback_process = None
        self.is_playing = False
        self.is_paused = False
        self.playback_offset = 0

        # Update button states
        self.play_btn.config(state='normal', text="▶ Play")
        self.pause_btn.config(state='disabled')
        self.reset_speaker_indicators()
        self.playback_time.config(text=f"00:00 / {self.format_time(self.audio_duration)}")

    def format_time(self, seconds):
        """Format seconds as MM:SS"""
        mins, secs = int(seconds // 60), int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def skip_playback(self, delta_seconds):
        """Skip forward or backward by delta_seconds"""
        if not self.temp_audio_file:
            return

        # Calculate new position
        new_pos = self.playback_offset + delta_seconds
        new_pos = max(0, min(new_pos, self.audio_duration))  # Clamp to valid range

        # If playing, restart from new position
        if self.is_playing and not self.is_paused:
            self.stop_playback()
            self.start_playback(new_pos)
        else:
            # Just update the offset for when play resumes
            self.playback_offset = new_pos
            self.playback_time.config(text=f"{self.format_time(new_pos)} / {self.format_time(self.audio_duration)}")
            self.scrub_var.set(new_pos)

    def on_scrub(self, value):
        """Handle scrub bar movement"""
        if not self.temp_audio_file or self.audio_duration <= 0:
            return

        new_pos = float(value)

        # If playing, restart from new position
        if self.is_playing and not self.is_paused:
            self.stop_playback()
            self.start_playback(new_pos)
        else:
            # Just update the offset for when play resumes
            self.playback_offset = new_pos
            self.playback_time.config(text=f"{self.format_time(new_pos)} / {self.format_time(self.audio_duration)}")

    def play_speaker_sample(self, speaker_id):
        """Play a sample clip of a specific speaker"""
        # Check for audio file
        if not self.temp_audio_file or not os.path.exists(self.temp_audio_file):
            # Try to extract from current media file if available
            if self.current_media_file and os.path.exists(self.current_media_file):
                self.log(f"Extracting audio for playback...")
                self.extract_audio(self.current_media_file)
            else:
                messagebox.showwarning("No Audio", "No audio file available for playback.\nLoad the original media file first.")
                return

        if not self.temp_audio_file or not os.path.exists(self.temp_audio_file):
            messagebox.showwarning("No Audio", "Could not extract audio for playback.")
            return

        # Find segments for this speaker
        speaker_segments = [s for s in self.segments_data if s.get("speaker") == speaker_id]

        # Debug: log what we're looking for
        if not speaker_segments:
            # Show what speakers we have
            all_speakers = set(s.get("speaker", "") for s in self.segments_data)
            self.log(f"No segments for '{speaker_id}'. Available: {all_speakers}")
            return

        # Pick a segment with reasonable length (not too short)
        best_segment = None
        for seg in speaker_segments:
            seg_duration = seg.get("end", 0) - seg.get("start", 0)
            if seg_duration >= 2:  # At least 2 seconds
                best_segment = seg
                break
        if not best_segment:
            best_segment = speaker_segments[0]

        start_time = max(0, best_segment.get("start", 0) - 0.5)  # Start slightly early
        end_time = best_segment.get("end", 0) + 0.5
        play_duration = min(10, end_time - start_time)  # Play up to 10 seconds

        self.log(f"Playing {speaker_id} @ {self.format_time(start_time)} ({play_duration:.1f}s)")
        self.log(f"  Text: \"{best_segment.get('text', '')[:50]}...\"")

        try:
            # Stop any existing playback
            if self.playback_process:
                self.playback_process.terminate()
                self.playback_process = None

            # Play just this segment
            cmd = ["ffplay", "-nodisp", "-autoexit", "-ss", str(start_time), "-t", str(play_duration), self.temp_audio_file]
            self.playback_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.is_playing = True
            self.is_paused = False
            self.playback_start_time = time.time()
            self.playback_offset = start_time

            self.play_btn.config(state='disabled')
            self.pause_btn.config(state='normal')
            self.update_playback()
        except Exception as e:
            self.log(f"Sample playback error: {e}")

    def update_playback(self):
        if not self.is_playing:
            return

        if self.playback_process and self.playback_process.poll() is not None:
            self.stop_playback()
            return

        elapsed = time.time() - self.playback_start_time + self.playback_offset
        current_time = self.format_time(elapsed)
        total_time = self.format_time(self.audio_duration) if self.audio_duration > 0 else "--:--"
        self.playback_time.config(text=f"{current_time} / {total_time}")

        # Update scrub bar position (without triggering callback)
        self.scrub_var.set(elapsed)

        # Update speaker indicators
        self.update_speaker_indicators(elapsed)

        self.root.after(100, self.update_playback)

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
        self.refresh_models()

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
