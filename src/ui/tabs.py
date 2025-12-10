
import tkinter as tk
from tkinter import ttk, filedialog
from tkinterdnd2 import DND_FILES
import os

from ..core.theme import KRAKEN
from ..core.narrative import get_narrative_styles
from ..core.llm_providers import GROQ_MODELS
from .widgets import create_button, create_section, create_styled_label
from ..core.config import AVATARS_DIR, WHISPER_MODELS, WHISPER_LANGUAGES

# Check for PIL
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def setup_record_tab(app):
    """Setup the Record tab which contains OBS instructions."""
    tab = app.record_tab
    
    # Main scrollable container
    canvas_container = tk.Frame(tab, bg=KRAKEN['bg_dark'])
    canvas_container.pack(fill=tk.BOTH, expand=True)
    
    canvas = tk.Canvas(canvas_container, bg=KRAKEN['bg_dark'], highlightthickness=0)
    scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=canvas.yview)
    
    container = tk.Frame(canvas, bg=KRAKEN['bg_dark'])
    canvas_window = canvas.create_window((0, 0), window=container, anchor='nw')
    
    def configure_scroll(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(canvas_window, width=event.width)
        
    container.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind('<Configure>', configure_scroll)
    
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Mousewheel scrolling
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    # Bind mousewheel only when hovering this canvas
    canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', on_mousewheel))
    canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

    # Add padding inside container
    content_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
    content_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

    # Header
    tk.Label(content_frame, text="🎬 Recording Your D&D Session", font=('Segoe UI', 18, 'bold'),
            bg=KRAKEN['bg_dark'], fg=KRAKEN['accent_glow']).pack(anchor='w', pady=(0, 5))
    tk.Label(content_frame, text="Use OBS Studio to capture both your microphone and Discord/system audio",
            font=('Segoe UI', 10), bg=KRAKEN['bg_dark'], fg=KRAKEN['text_dim']).pack(anchor='w', pady=(0, 20))

    # Download section
    download_frame = tk.Frame(content_frame, bg=KRAKEN['bg_mid'], padx=15, pady=15)
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
    setup_frame = tk.Frame(content_frame, bg=KRAKEN['bg_mid'], padx=15, pady=15)
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
    tips_frame = tk.Frame(content_frame, bg=KRAKEN['bg_mid'], padx=15, pady=15)
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

def setup_transcribe_tab(app):
    """Setup the Transcribe tab."""
    container = tk.Frame(app.transcribe_tab, bg=KRAKEN['bg_dark'])
    container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    # Top section - file selection (compact)
    top_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
    top_frame.pack(fill=tk.X, pady=(0, 10))

    # Drop zone - smaller, on the left
    app.drop_zone = tk.Label(top_frame,
        text="🐙\nDrop file or click",
        font=('Segoe UI', 11), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim'],
        relief='ridge', bd=2, cursor='hand2', justify='center', width=20)
    app.drop_zone.pack(side=tk.LEFT, padx=(0, 15), ipady=15)
    app.drop_zone.bind('<Button-1>', app.browse_media_file)

    # Setup drag and drop if available
    try:
        app.drop_zone.drop_target_register(DND_FILES)
        app.drop_zone.dnd_bind('<<Drop>>', app.on_file_drop)
    except:
        pass

    # Right side - file info and buttons
    right_frame = tk.Frame(top_frame, bg=KRAKEN['bg_dark'])
    right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # File info
    app.file_label = tk.Label(right_frame, text="No file selected", font=('Segoe UI', 12),
                              bg=KRAKEN['bg_dark'], fg=KRAKEN['text_dim'], anchor='w')
    app.file_label.pack(fill=tk.X, pady=(5, 10))

    # Button row
    btn_frame = tk.Frame(right_frame, bg=KRAKEN['bg_dark'])
    btn_frame.pack(fill=tk.X)

    # Transcribe button
    app.transcribe_btn = create_button(btn_frame, "🔮 BEGIN TRANSCRIPTION", app.start_transcription, large=True)
    app.transcribe_btn.pack(side=tk.LEFT, padx=(0, 10))

    # Stop button
    app.stop_transcribe_btn = create_button(btn_frame, "⏹ STOP", app.stop_transcription, large=True)
    app.stop_transcribe_btn.pack(side=tk.LEFT)
    app.stop_transcribe_btn.config(state='disabled')

    # Progress bar
    app.transcribe_progress = ttk.Progressbar(right_frame, mode='indeterminate', length=300)
    app.transcribe_progress.pack(fill=tk.X, pady=(10, 0))

    # ===== SPLIT LOG AREA =====
    paned = tk.PanedWindow(container, orient=tk.VERTICAL, bg=KRAKEN['tentacle'],
                           sashwidth=8, sashrelief='raised')
    paned.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

    # TOP: Status log
    status_frame = tk.Frame(paned, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
    status_header = tk.Label(status_frame, text="📜 STATUS - What's happening",
                            font=('Segoe UI', 10, 'bold'), bg=KRAKEN['tentacle'],
                            fg=KRAKEN['text_bright'], anchor='w', padx=10, pady=5)
    status_header.pack(fill=tk.X)
    app.log_text = tk.Text(status_frame, font=('Consolas', 11), bg=KRAKEN['bg_widget'],
                           fg=KRAKEN['biolum'], insertbackground=KRAKEN['text'], relief='flat',
                           wrap=tk.WORD, padx=10, pady=10)
    app.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    status_scroll = ttk.Scrollbar(app.log_text, command=app.log_text.yview)
    status_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    app.log_text.config(yscrollcommand=status_scroll.set)
    paned.add(status_frame, minsize=120)

    # BOTTOM: Technical/engine log
    tech_frame = tk.Frame(paned, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
    tech_header = tk.Label(tech_frame, text="🔧 ENGINE LOG - Copy this for debugging",
                          font=('Segoe UI', 10, 'bold'), bg='#1a1a2e',
                          fg='#888888', anchor='w', padx=10, pady=5)
    tech_header.pack(fill=tk.X)
    app.tech_log_text = tk.Text(tech_frame, font=('Consolas', 9), bg='#0d0d1a',
                                fg='#aaaaaa', insertbackground=KRAKEN['text'], relief='flat',
                                wrap=tk.NONE, padx=10, pady=10)
    app.tech_log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Horizontal scrollbar for long lines
    tech_hscroll = ttk.Scrollbar(tech_frame, orient=tk.HORIZONTAL, command=app.tech_log_text.xview)
    tech_hscroll.pack(side=tk.BOTTOM, fill=tk.X)
    tech_scroll = ttk.Scrollbar(app.tech_log_text, command=app.tech_log_text.yview)
    tech_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    app.tech_log_text.config(yscrollcommand=tech_scroll.set, xscrollcommand=tech_hscroll.set)
    paned.add(tech_frame, minsize=100)

    app.log("Ready. Select a file to transcribe.")
    app.tech_log("Engine log initialized.")

def setup_speakers_tab(app):
    """Setup the Speakers tab."""
    container = tk.Frame(app.speakers_tab, bg=KRAKEN['bg_dark'])
    container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    # Top controls
    top_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
    top_frame.pack(fill=tk.X, pady=(0, 10))

    create_button(top_frame, "📂 Load Transcript", app.load_transcript_file, small=True).pack(side=tk.LEFT, padx=5)
    create_button(top_frame, "📥 Load Mapping", app.load_mapping_file, small=True).pack(side=tk.LEFT, padx=5)
    create_button(top_frame, "💾 Save Mapping", app.save_mapping_file, small=True).pack(side=tk.LEFT, padx=5)

    # Current speaker display (large avatar during playback)
    current_speaker_frame = tk.Frame(top_frame, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
    current_speaker_frame.pack(side=tk.RIGHT, padx=(20, 0))

    avatar_container = tk.Frame(current_speaker_frame, bg=KRAKEN['bg_widget'], width=80, height=80)
    avatar_container.pack(side=tk.LEFT, padx=5, pady=5)
    avatar_container.pack_propagate(False)

    app.current_avatar_label = tk.Label(avatar_container, bg=KRAKEN['bg_widget'],
                                        text="👤", font=('Segoe UI', 28))
    app.current_avatar_label.pack(expand=True, fill=tk.BOTH)
    app.current_avatar_image = None

    current_info_frame = tk.Frame(current_speaker_frame, bg=KRAKEN['bg_mid'])
    current_info_frame.pack(side=tk.LEFT, padx=10, pady=5)

    tk.Label(current_info_frame, text="NOW SPEAKING", font=('Segoe UI', 8),
            bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(anchor='w')
    app.current_speaker_name = tk.Label(current_info_frame, text="—", font=('Segoe UI', 12, 'bold'),
                                        bg=KRAKEN['bg_mid'], fg=KRAKEN['biolum'])
    app.current_speaker_name.pack(anchor='w')

    # Playback controls frame
    playback_frame = tk.Frame(top_frame, bg=KRAKEN['bg_dark'])
    playback_frame.pack(side=tk.RIGHT, padx=(0, 10))

    # Row 1: Play/Pause/Stop and time
    controls_row = tk.Frame(playback_frame, bg=KRAKEN['bg_dark'])
    controls_row.pack(fill=tk.X)

    app.play_btn = create_button(controls_row, "▶ Play", app.start_playback, small=True)
    app.play_btn.pack(side=tk.LEFT, padx=2)

    app.pause_btn = create_button(controls_row, "⏸ Pause", app.pause_playback, small=True)
    app.pause_btn.pack(side=tk.LEFT, padx=2)
    app.pause_btn.config(state='disabled')

    app.stop_btn = create_button(controls_row, "⏹ Stop", app.stop_playback, small=True)
    app.stop_btn.pack(side=tk.LEFT, padx=2)

    # Skip buttons
    for label, secs in [("⏪-10s", -10), ("⏪-5s", -5), ("+5s⏩", 5), ("+10s⏩", 10)]:
        tk.Button(controls_row, text=label, font=('Segoe UI', 9), bg=KRAKEN['bg_widget'],
                 fg=KRAKEN['text'], activebackground=KRAKEN['accent'], bd=0, padx=6,
                 command=lambda s=secs: app.skip_playback(s)).pack(side=tk.LEFT, padx=2)

    app.playback_time = tk.Label(controls_row, text="00:00 / 00:00", font=('Consolas', 11),
                                 bg=KRAKEN['bg_dark'], fg=KRAKEN['accent_light'])
    app.playback_time.pack(side=tk.LEFT, padx=10)

    # Video Pop-out
    create_button(controls_row, "📺 Video", app.toggle_video_player, small=True).pack(side=tk.LEFT, padx=5)

    # Row 2: Scrub bar
    scrub_row = tk.Frame(playback_frame, bg=KRAKEN['bg_dark'])
    scrub_row.pack(fill=tk.X, pady=(5, 0))

    app.scrub_var = tk.DoubleVar(value=0)
    app.scrub_bar = tk.Scale(scrub_row, from_=0, to=100, orient=tk.HORIZONTAL,
                              variable=app.scrub_var, showvalue=False, length=300,
                              bg=KRAKEN['bg_widget'], fg=KRAKEN['accent'],
                              troughcolor=KRAKEN['bg_dark'], highlightthickness=0,
                              sliderrelief='flat', command=app.on_scrub)
    app.scrub_bar.pack(fill=tk.X, expand=True)

    # Bind events for smoother scrubbing
    app.scrub_bar.bind("<ButtonPress-1>", app.on_scrub_start)
    app.scrub_bar.bind("<ButtonRelease-1>", app.on_scrub_end)

    # Main content - speakers list with canvas scroll
    main_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
    main_frame.pack(fill=tk.BOTH, expand=True)

    app.speakers_canvas = tk.Canvas(main_frame, bg=KRAKEN['bg_dark'], highlightthickness=0)
    speakers_scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=app.speakers_canvas.yview)
    app.speakers_frame = tk.Frame(app.speakers_canvas, bg=KRAKEN['bg_dark'])

    app.speakers_frame.bind('<Configure>', lambda e: app.speakers_canvas.configure(scrollregion=app.speakers_canvas.bbox('all')))
    app.speakers_window = app.speakers_canvas.create_window((0, 0), window=app.speakers_frame, anchor='nw')
    app.speakers_canvas.configure(yscrollcommand=speakers_scrollbar.set)

    app.speakers_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    speakers_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    app.speakers_canvas.bind_all('<MouseWheel>', lambda e: app.speakers_canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))
    app.speakers_canvas.bind('<Configure>', app.on_speakers_canvas_resize)
    
    # Bottom controls
    bottom_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
    bottom_frame.pack(fill=tk.X, pady=(15, 0))

    app.apply_btn = create_button(bottom_frame, "✨ APPLY NAMES", app.apply_speaker_names, large=True)
    app.apply_btn.pack()

    app.speaker_entries = {}
    app.speaker_indicators = {}
    app.speaker_cards = []

def setup_preview_tab(app):
    """Setup the Preview tab."""
    container = tk.Frame(app.preview_tab, bg=KRAKEN['bg_dark'])
    container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

    top_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
    top_frame.pack(fill=tk.X, pady=(0, 10))

    create_button(top_frame, "💾 Save As...", app.save_transcript, small=True).pack(side=tk.LEFT, padx=5)
    create_button(top_frame, "📋 Copy All", app.copy_transcript, small=True).pack(side=tk.LEFT, padx=5)

    preview_frame = tk.Frame(container, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
    preview_frame.pack(fill=tk.BOTH, expand=True)

    app.preview_text = tk.Text(preview_frame, font=('Consolas', 10), bg=KRAKEN['bg_widget'],
                               fg=KRAKEN['text'], insertbackground=KRAKEN['text'], relief='flat',
                               wrap=tk.WORD, padx=15, pady=15)
    app.preview_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    preview_scroll = ttk.Scrollbar(preview_frame, command=app.preview_text.yview)
    preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    app.preview_text.config(yscrollcommand=preview_scroll.set)

def setup_bard_tab(app):
    """Setup the Bard's Tale tab."""
    container = tk.Frame(app.bard_tab, bg=KRAKEN['bg_dark'])
    container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

    # Header
    header_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
    header_frame.pack(fill=tk.X, pady=(0, 15))

    tk.Label(header_frame, text="🎭 The Bard's Tale", font=('Segoe UI', 16, 'bold'),
            bg=KRAKEN['bg_dark'], fg=KRAKEN['accent_glow']).pack(side=tk.LEFT)

    tk.Label(header_frame, text="Transform your session into a narrative story, as told by Zhree the Bard",
            font=('Segoe UI', 10, 'italic'), bg=KRAKEN['bg_dark'], fg=KRAKEN['text_dim']).pack(side=tk.LEFT, padx=(15, 0))

    # Settings section
    settings_frame = create_section(container, "⚙️ SETTINGS")
    settings_frame.pack(fill=tk.X, pady=(0, 15))

    # Provider selection
    provider_row = tk.Frame(settings_frame, bg=KRAKEN['bg_mid'])
    provider_row.pack(fill=tk.X, pady=5)
    tk.Label(provider_row, text="LLM Provider:", font=('Segoe UI', 10),
            bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], width=15, anchor='w').pack(side=tk.LEFT)
    app.llm_provider = tk.StringVar(value=app.config.get("llm_provider", "Ollama (Local)"))
    provider_combo = ttk.Combobox(provider_row, textvariable=app.llm_provider, width=22, state='normal',
                                  values=["Ollama (Local)", "Groq (Cloud)"])
    provider_combo.bind('<Key>', lambda e: "break")
    provider_combo.pack(side=tk.LEFT, padx=(10, 0))
    provider_combo.bind('<<ComboboxSelected>>', app.on_provider_change)

    # Model selection
    model_row = tk.Frame(settings_frame, bg=KRAKEN['bg_mid'])
    model_row.pack(fill=tk.X, pady=5)
    tk.Label(model_row, text="Model:", font=('Segoe UI', 10),
            bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], width=15, anchor='w').pack(side=tk.LEFT)
    app.ollama_model = tk.StringVar(value="")
    app.model_combo = ttk.Combobox(model_row, textvariable=app.ollama_model, width=30, state='normal')
    app.model_combo.bind('<Key>', lambda e: "break")
    app.model_combo.pack(side=tk.LEFT, padx=(10, 10))
    app.model_combo.bind('<<ComboboxSelected>>', app.on_model_change)
    app.refresh_models_btn = create_button(model_row, "🔄 Refresh", app.refresh_models, small=True)
    app.refresh_models_btn.pack(side=tk.LEFT, padx=5)

    # Bard name
    bard_row = tk.Frame(settings_frame, bg=KRAKEN['bg_mid'])
    bard_row.pack(fill=tk.X, pady=5)
    tk.Label(bard_row, text="Bard's Name:", font=('Segoe UI', 10),
            bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], width=15, anchor='w').pack(side=tk.LEFT)
    app.bard_name = tk.StringVar(value="Zhree")
    tk.Entry(bard_row, textvariable=app.bard_name, font=('Segoe UI', 10),
            bg=KRAKEN['bg_widget'], fg=KRAKEN['text'], insertbackground=KRAKEN['text'],
            relief='flat', width=25).pack(side=tk.LEFT, padx=(10, 0), ipady=4)

    # Style selection
    style_row = tk.Frame(settings_frame, bg=KRAKEN['bg_mid'])
    style_row.pack(fill=tk.X, pady=5)
    tk.Label(style_row, text="Narrative Style:", font=('Segoe UI', 10),
            bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], width=15, anchor='w').pack(side=tk.LEFT)
    app.narrative_style = tk.StringVar(value="Epic Fantasy")
    style_combo = ttk.Combobox(style_row, textvariable=app.narrative_style, width=22, state='normal',
                               values=get_narrative_styles())
    style_combo.bind('<Key>', lambda e: "break")
    style_combo.pack(side=tk.LEFT, padx=(10, 0))

    # Chunk size
    chunk_row = tk.Frame(settings_frame, bg=KRAKEN['bg_mid'])
    chunk_row.pack(fill=tk.X, pady=5)
    tk.Label(chunk_row, text="Process in chunks:", font=('Segoe UI', 10),
            bg=KRAKEN['bg_mid'], fg=KRAKEN['text'], width=15, anchor='w').pack(side=tk.LEFT)
    app.chunk_size = tk.StringVar(value="50")
    tk.Entry(chunk_row, textvariable=app.chunk_size, font=('Segoe UI', 10),
            bg=KRAKEN['bg_widget'], fg=KRAKEN['text'], insertbackground=KRAKEN['text'],
            relief='flat', width=10).pack(side=tk.LEFT, padx=(10, 0), ipady=4)
    tk.Label(chunk_row, text="lines at a time (smaller = more detail, larger = faster)",
            font=('Segoe UI', 9), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(side=tk.LEFT, padx=(10, 0))

    # Action buttons
    button_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
    button_frame.pack(fill=tk.X, pady=10)

    app.bard_btn = create_button(button_frame, "🎭 SPIN THE TALE", app.start_bard_tale, large=True)
    app.bard_btn.pack(side=tk.LEFT, padx=5)

    app.summary_btn = create_button(button_frame, "📜 Summarize", app.start_session_summary, large=True)
    app.summary_btn.pack(side=tk.LEFT, padx=5)

    app.stop_bard_btn = create_button(button_frame, "⏹ Stop", app.stop_bard_tale, small=True)
    app.stop_bard_btn.pack(side=tk.LEFT, padx=5)
    app.stop_bard_btn.config(state='disabled')
    
    app.discord_btn = create_button(button_frame, "💬 Post to Discord", app.post_to_discord, small=True)
    app.discord_btn.pack(side=tk.LEFT, padx=5)

    create_button(button_frame, "💾 Save Tale", app.save_bard_tale, small=True).pack(side=tk.RIGHT, padx=5)
    create_button(button_frame, "📋 Copy Tale", app.copy_bard_tale, small=True).pack(side=tk.RIGHT, padx=5)

    # Progress
    progress_frame = tk.Frame(container, bg=KRAKEN['bg_dark'])
    progress_frame.pack(fill=tk.X, pady=5)

    app.bard_progress = ttk.Progressbar(progress_frame, mode='determinate', length=400)
    app.bard_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

    app.bard_status = tk.Label(progress_frame, text="Ready to weave tales...", font=('Segoe UI', 9),
                               bg=KRAKEN['bg_dark'], fg=KRAKEN['text_dim'])
    app.bard_status.pack(side=tk.LEFT)

    # Party members with avatars
    party_frame = create_section(container, "🎭 THE PARTY")
    party_frame.pack(fill=tk.X, pady=(0, 10))

    app.party_avatars_frame = tk.Frame(party_frame, bg=KRAKEN['bg_mid'])
    app.party_avatars_frame.pack(fill=tk.X)

    app.party_placeholder = tk.Label(app.party_avatars_frame,
        text="Load a transcript with speakers to see the party members here",
        font=('Segoe UI', 10, 'italic'), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim'])
    app.party_placeholder.pack(pady=10)

    app.party_avatar_images = {}

    # Output area
    output_frame = tk.Frame(container, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
    output_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

    tale_header = tk.Frame(output_frame, bg=KRAKEN['tentacle'])
    tale_header.pack(fill=tk.X)
    tk.Label(tale_header, text="📜 THE TALE", font=('Segoe UI', 10, 'bold'),
            bg=KRAKEN['tentacle'], fg=KRAKEN['text_bright'], anchor='w', padx=10, pady=5).pack(fill=tk.X)

    app.bard_text = tk.Text(output_frame, font=('Georgia', 11), bg=KRAKEN['bg_widget'],
                            fg=KRAKEN['text'], insertbackground=KRAKEN['text'], relief='flat',
                            wrap=tk.WORD, padx=20, pady=15, spacing1=5, spacing2=3)
    app.bard_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    bard_scroll = ttk.Scrollbar(output_frame, command=app.bard_text.yview)
    bard_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    app.bard_text.config(yscrollcommand=bard_scroll.set)

    # Configure text tags for styling
    app.bard_text.tag_configure("title", font=('Georgia', 14, 'bold'), foreground=KRAKEN['accent_glow'],
                                 spacing1=10, spacing3=10, justify='center')
    app.bard_text.tag_configure("chapter", font=('Georgia', 12, 'bold italic'), foreground=KRAKEN['biolum'],
                                 spacing1=15, spacing3=5)
    app.bard_text.tag_configure("body", font=('Georgia', 11), foreground=KRAKEN['text'])
