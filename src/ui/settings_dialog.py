"""
THE KRAKEN DREAMS - Settings Dialog
The settings dialog window for configuring audio devices, API keys, and LLM providers.

This module contains the SettingsDialog class which creates and manages
the application settings configuration window.
"""

import tkinter as tk
from tkinter import ttk
import sounddevice as sd
import requests

from ..core.theme import KRAKEN
from ..core.config import save_config, WHISPER_MODELS, WHISPER_LANGUAGES
from ..core.llm_providers import GROQ_MODELS




class SettingsDialog:
    """
    Settings dialog for The Kraken Dreams application.
    
    Provides configuration for:
    - Audio devices (microphone and system audio)
    - HuggingFace API token for transcription
    - Ollama local LLM settings
    - Groq cloud LLM settings
    """
    
    def __init__(self, parent, config, on_save_callback=None):
        """
        Create the settings dialog.
        
        Args:
            parent: The parent tkinter window
            config: The current configuration dictionary
            on_save_callback: Optional callback function called after saving settings
        """
        self.parent = parent
        self.config = config
        self.on_save_callback = on_save_callback
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings - The Kraken Dreams")
        self.dialog.geometry("550x950")
        self.dialog.configure(bg=KRAKEN['bg_dark'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 550) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 950) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        # Create the UI
        self._create_ui()
        
        # Auto-refresh Ollama models when dialog opens
        self.dialog.after(100, self._refresh_ollama)
    
    def _create_ui(self):
        """Create all UI elements for the settings dialog."""
        # Create a canvas with scrollbar for scrollable content
        canvas_container = tk.Frame(self.dialog, bg=KRAKEN['bg_dark'])
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(canvas_container, bg=KRAKEN['bg_dark'], 
                               highlightthickness=0, bd=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL, 
                                  command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Main frame inside canvas
        main_frame = tk.Frame(self.canvas, bg=KRAKEN['bg_dark'])
        self.canvas_window = self.canvas.create_window((0, 0), window=main_frame, anchor='nw')
        
        # Configure canvas scrolling
        def configure_scroll(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # Make the inner frame as wide as the canvas
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        
        main_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind('<Configure>', configure_scroll)
        
        # Enable mouse wheel scrolling
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.canvas.bind_all("<MouseWheel>", on_mousewheel)
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: self._on_close())
        
        # Add padding inside the scrollable frame
        inner_frame = tk.Frame(main_frame, bg=KRAKEN['bg_dark'])
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        tk.Label(inner_frame, text="⚙️ Settings", font=('Segoe UI', 16, 'bold'),
                bg=KRAKEN['bg_dark'], fg=KRAKEN['accent_glow']).pack(anchor='w', pady=(0, 15))

        
        # Create StringVars for all settings fields
        self.hf_token_var = tk.StringVar(value=self.config.get("hf_token", ""))
        self.ollama_url_var = tk.StringVar(value=self.config.get("ollama_url", "http://localhost:11434"))
        self.ollama_model_var = tk.StringVar(value=self.config.get("ollama_model", ""))
        self.groq_key_var = tk.StringVar(value=self.config.get("groq_api_key", ""))
        self.groq_url_var = tk.StringVar(value=self.config.get("groq_url", "https://api.groq.com/openai/v1/chat/completions"))
        self.groq_model_var = tk.StringVar(value=self.config.get("groq_model", ""))
        self.mic_device_var = tk.StringVar(value=self.config.get("mic_device", ""))
        self.system_device_var = tk.StringVar(value=self.config.get("system_device", ""))
        
        # Transcription settings
        self.whisper_model_var = tk.StringVar(value=self.config.get("whisper_model", "large-v2"))
        self.whisper_language_var = tk.StringVar(value=self.config.get("whisper_language", "auto"))
        self.auto_transcribe_var = tk.BooleanVar(value=self.config.get("auto_transcribe", False))
        self.apply_vocabulary_var = tk.BooleanVar(value=self.config.get("apply_vocabulary", True))
        
        # Discord integration
        self.discord_webhook_var = tk.StringVar(value=self.config.get("discord_webhook", ""))

        
        # Audio Devices Section
        self._create_audio_section(inner_frame)
        
        # Transcription Section (NEW)
        self._create_transcription_section(inner_frame)
        
        # HuggingFace Section
        self._create_huggingface_section(inner_frame)
        
        # Ollama Section
        self._create_ollama_section(inner_frame)
        
        # Groq Section
        self._create_groq_section(inner_frame)
        
        # Discord Section
        self._create_discord_section(inner_frame)
        
        # Buttons
        self._create_buttons(inner_frame)



    
    def _create_audio_section(self, parent):
        """Create the audio devices configuration section."""
        audio_frame = tk.LabelFrame(parent, text="🎙️ Audio Devices (Recording)", 
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=KRAKEN['bg_mid'], fg=KRAKEN['accent_light'], 
                                   padx=10, pady=10)
        audio_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Get available audio devices
        try:
            devices = sd.query_devices()
            input_devices = [(i, d['name']) for i, d in enumerate(devices) if d['max_input_channels'] > 0]
            input_names = [name for i, name in input_devices]
            output_devices = [(i, d['name']) for i, d in enumerate(devices) if d['max_output_channels'] > 0]
            output_names = [name for i, name in output_devices]
            system_device_names = input_names + [f"[OUTPUT] {name}" for name in output_names if name not in input_names]
        except:
            input_names = []
            system_device_names = []
        
        # Microphone selector
        tk.Label(audio_frame, text="Microphone:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text']).pack(anchor='w')
        mic_combo = ttk.Combobox(audio_frame, textvariable=self.mic_device_var, 
                                width=45, values=input_names)
        mic_combo.pack(fill=tk.X, pady=(2, 8), ipady=2)
        
        # System audio selector
        tk.Label(audio_frame, text="System Audio (what you hear):", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text']).pack(anchor='w')
        system_combo = ttk.Combobox(audio_frame, textvariable=self.system_device_var, 
                                   width=45, values=system_device_names)
        system_combo.pack(fill=tk.X, pady=(2, 5), ipady=2)
        
        # Tip
        tk.Label(audio_frame, 
                text="Tip: Look for 'Stereo Mix', 'What U Hear', or [OUTPUT] device for loopback",
                font=('Segoe UI', 8), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(anchor='w')
    
    def _create_transcription_section(self, parent):
        """Create the transcription settings section."""
        trans_frame = tk.LabelFrame(parent, text="📝 Transcription Settings", 
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=KRAKEN['bg_mid'], fg=KRAKEN['accent_light'], 
                                   padx=10, pady=10)
        trans_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Whisper model selector
        tk.Label(trans_frame, text="Whisper Model:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text']).pack(anchor='w')
        
        model_combo = ttk.Combobox(trans_frame, textvariable=self.whisper_model_var, 
                                  width=30, state='readonly', values=WHISPER_MODELS)
        model_combo.pack(fill=tk.X, pady=(2, 5), ipady=2)
        
        # Model descriptions
        tk.Label(trans_frame, 
                text="tiny/base: Fast, less accurate | medium: Balanced | large-v2: Best accuracy",
                font=('Segoe UI', 8), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(anchor='w')
        
        # Language selector
        tk.Label(trans_frame, text="Language:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text']).pack(anchor='w', pady=(10, 0))
        
        # Create display names for combobox
        lang_display = [f"{code} - {name}" for code, name in WHISPER_LANGUAGES]
        lang_codes = [code for code, name in WHISPER_LANGUAGES]
        
        lang_combo = ttk.Combobox(trans_frame, textvariable=self.whisper_language_var, 
                                 width=30, state='readonly', values=lang_codes)
        lang_combo.pack(fill=tk.X, pady=(2, 5), ipady=2)
        
        tk.Label(trans_frame, 
                text="'auto' detects language automatically (recommended for English)",
                font=('Segoe UI', 8), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(anchor='w')
        
        # Auto-transcribe checkbox
        auto_check = tk.Checkbutton(trans_frame, text="Auto-transcribe after recording", 
                                   variable=self.auto_transcribe_var,
                                   font=('Segoe UI', 10), bg=KRAKEN['bg_mid'], fg=KRAKEN['text'],
                                   activebackground=KRAKEN['bg_mid'], activeforeground=KRAKEN['text'],
                                   selectcolor=KRAKEN['bg_widget'], cursor='hand2')
        auto_check.pack(anchor='w', pady=(10, 0))
        
        tk.Label(trans_frame, 
                text="When enabled, transcription starts automatically when recording stops",
                font=('Segoe UI', 8), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(anchor='w')
        
        # Vocabulary corrections checkbox
        vocab_check = tk.Checkbutton(trans_frame, text="Apply D&D vocabulary corrections", 
                                    variable=self.apply_vocabulary_var,
                                    font=('Segoe UI', 10), bg=KRAKEN['bg_mid'], fg=KRAKEN['text'],
                                    activebackground=KRAKEN['bg_mid'], activeforeground=KRAKEN['text'],
                                    selectcolor=KRAKEN['bg_widget'], cursor='hand2')
        vocab_check.pack(anchor='w', pady=(5, 0))
        
        tk.Label(trans_frame, 
                text="Fix common D&D terms + custom vocabulary from custom_vocabulary.txt",
                font=('Segoe UI', 8), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(anchor='w')


    def _create_huggingface_section(self, parent):

        """Create the HuggingFace token configuration section."""
        hf_frame = tk.LabelFrame(parent, text="🤗 HuggingFace (Transcription)", 
                                font=('Segoe UI', 10, 'bold'),
                                bg=KRAKEN['bg_mid'], fg=KRAKEN['accent_light'], 
                                padx=10, pady=10)
        hf_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(hf_frame, text="API Token:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text']).pack(anchor='w')
        
        hf_entry = tk.Entry(hf_frame, textvariable=self.hf_token_var, font=('Segoe UI', 10),
                           bg=KRAKEN['bg_widget'], fg=KRAKEN['text'], 
                           insertbackground=KRAKEN['text'],
                           relief='flat', width=50, show="*")
        hf_entry.pack(fill=tk.X, pady=(2, 5), ipady=4)
        
        tk.Label(hf_frame, text="Get free token at: https://huggingface.co/settings/tokens",
                font=('Segoe UI', 8), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(anchor='w')
    
    def _create_ollama_section(self, parent):
        """Create the Ollama configuration section."""
        ollama_frame = tk.LabelFrame(parent, text="🦙 Ollama (Local LLM)", 
                                    font=('Segoe UI', 10, 'bold'),
                                    bg=KRAKEN['bg_mid'], fg=KRAKEN['accent_light'], 
                                    padx=10, pady=10)
        ollama_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Server URL
        tk.Label(ollama_frame, text="Server URL:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text']).pack(anchor='w')
        tk.Entry(ollama_frame, textvariable=self.ollama_url_var, font=('Segoe UI', 10),
                bg=KRAKEN['bg_widget'], fg=KRAKEN['text'], insertbackground=KRAKEN['text'],
                relief='flat', width=50).pack(fill=tk.X, pady=(2, 5), ipady=4)
        
        # Model selection
        tk.Label(ollama_frame, text="Default Model:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text']).pack(anchor='w')
        
        model_row = tk.Frame(ollama_frame, bg=KRAKEN['bg_mid'])
        model_row.pack(fill=tk.X, pady=(2, 5))
        
        self.ollama_model_combo = ttk.Combobox(model_row, textvariable=self.ollama_model_var, 
                                               width=35, state='readonly')
        self.ollama_model_combo.pack(side=tk.LEFT, ipady=2)
        
        refresh_btn = tk.Button(model_row, text="🔄 Refresh", font=('Segoe UI', 9),
                               bg=KRAKEN['bg_widget'], fg=KRAKEN['text'],
                               activebackground=KRAKEN['tentacle'], bd=0, padx=10, pady=2,
                               cursor='hand2', command=self._refresh_ollama)
        refresh_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status label
        self.ollama_status = tk.Label(ollama_frame, text="", font=('Segoe UI', 8),
                                     bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim'])
        self.ollama_status.pack(anchor='w')
    
    def _create_groq_section(self, parent):
        """Create the Groq configuration section."""
        groq_frame = tk.LabelFrame(parent, text="⚡ Groq (Cloud LLM)", 
                                  font=('Segoe UI', 10, 'bold'),
                                  bg=KRAKEN['bg_mid'], fg=KRAKEN['accent_light'], 
                                  padx=10, pady=10)
        groq_frame.pack(fill=tk.X, pady=(0, 15))
        
        # API Key
        tk.Label(groq_frame, text="API Key:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text']).pack(anchor='w')
        groq_key_entry = tk.Entry(groq_frame, textvariable=self.groq_key_var, 
                                 font=('Segoe UI', 10),
                                 bg=KRAKEN['bg_widget'], fg=KRAKEN['text'], 
                                 insertbackground=KRAKEN['text'],
                                 relief='flat', width=50, show="*")
        groq_key_entry.pack(fill=tk.X, pady=(2, 5), ipady=4)
        
        tk.Label(groq_frame, text="Get free key at: https://console.groq.com",
                font=('Segoe UI', 8), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(anchor='w')
        
        # API URL
        tk.Label(groq_frame, text="API URL:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text']).pack(anchor='w', pady=(5, 0))
        tk.Entry(groq_frame, textvariable=self.groq_url_var, font=('Segoe UI', 10),
                bg=KRAKEN['bg_widget'], fg=KRAKEN['text'], insertbackground=KRAKEN['text'],
                relief='flat', width=50).pack(fill=tk.X, pady=(2, 5), ipady=4)
        
        # Model selection (using GROQ_MODELS from llm_providers module)
        tk.Label(groq_frame, text="Default Model:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text']).pack(anchor='w')
        
        groq_model_combo = ttk.Combobox(groq_frame, textvariable=self.groq_model_var, 
                                       width=40, state='readonly', values=GROQ_MODELS)
        groq_model_combo.pack(fill=tk.X, pady=(2, 5), ipady=2)
        
        if not self.groq_model_var.get():
            self.groq_model_var.set(GROQ_MODELS[0])
    
    def _create_discord_section(self, parent):
        """Create the Discord webhook configuration section."""
        discord_frame = tk.LabelFrame(parent, text="💬 Discord Integration", 
                                     font=('Segoe UI', 10, 'bold'),
                                     bg=KRAKEN['bg_mid'], fg=KRAKEN['accent_light'], 
                                     padx=10, pady=10)
        discord_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Webhook URL
        tk.Label(discord_frame, text="Webhook URL:", font=('Segoe UI', 10),
                bg=KRAKEN['bg_mid'], fg=KRAKEN['text']).pack(anchor='w')
        tk.Entry(discord_frame, textvariable=self.discord_webhook_var, font=('Segoe UI', 10),
                bg=KRAKEN['bg_widget'], fg=KRAKEN['text'], insertbackground=KRAKEN['text'],
                relief='flat', width=50).pack(fill=tk.X, pady=(2, 5), ipady=4)
        
        tk.Label(discord_frame, 
                text="Create webhook in Discord: Server Settings → Integrations → Webhooks",
                font=('Segoe UI', 8), bg=KRAKEN['bg_mid'], fg=KRAKEN['text_dim']).pack(anchor='w')

    def _create_buttons(self, parent):

        """Create the Save and Cancel buttons."""
        btn_frame = tk.Frame(parent, bg=KRAKEN['bg_dark'])
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        # Save button
        save_btn = tk.Button(btn_frame, text="💾 Save Settings", font=('Segoe UI', 11, 'bold'),
                            bg=KRAKEN['accent'], fg=KRAKEN['text_bright'],
                            activebackground=KRAKEN['accent_light'], bd=0, padx=20, pady=8,
                            cursor='hand2', command=self._save_and_close)
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_btn = tk.Button(btn_frame, text="Cancel", font=('Segoe UI', 10),
                              bg=KRAKEN['bg_widget'], fg=KRAKEN['text'],
                              activebackground=KRAKEN['tentacle'], bd=0, padx=15, pady=6,
                              cursor='hand2', command=self.dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
    
    def _refresh_ollama(self):
        """Fetch available models from Ollama server."""
        url = self.ollama_url_var.get().strip()
        self.ollama_status.config(text="Connecting...", fg=KRAKEN['text_dim'])
        self.dialog.update()
        
        try:
            response = requests.get(f"{url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                if model_names:
                    self.ollama_model_combo['values'] = model_names
                    current = self.ollama_model_var.get()
                    if not current or current not in model_names:
                        self.ollama_model_var.set(model_names[0])
                    self.ollama_status.config(text=f"✓ Found {len(model_names)} models", 
                                             fg=KRAKEN['success'])
                else:
                    self.ollama_model_combo['values'] = []
                    self.ollama_status.config(text="No models. Run: ollama pull <model>", 
                                             fg=KRAKEN['warning'])
            else:
                self.ollama_status.config(text=f"Error: {response.status_code}", 
                                         fg=KRAKEN['warning'])
        except requests.exceptions.ConnectionError:
            self.ollama_model_combo['values'] = []
            self.ollama_status.config(text=f"Cannot connect to {url}", fg=KRAKEN['warning'])
        except Exception as e:
            self.ollama_status.config(text=f"Error: {str(e)[:40]}", fg=KRAKEN['warning'])
    
    def _save_and_close(self):
        """Save all settings to config and close the dialog."""
        # Update config with all values
        self.config["hf_token"] = self.hf_token_var.get().strip()
        self.config["ollama_url"] = self.ollama_url_var.get().strip()
        self.config["ollama_model"] = self.ollama_model_var.get().strip()
        self.config["groq_api_key"] = self.groq_key_var.get().strip()
        self.config["groq_url"] = self.groq_url_var.get().strip()
        self.config["groq_model"] = self.groq_model_var.get().strip()
        self.config["mic_device"] = self.mic_device_var.get().strip()
        self.config["system_device"] = self.system_device_var.get().strip()
        
        # Transcription settings
        self.config["whisper_model"] = self.whisper_model_var.get()
        self.config["whisper_language"] = self.whisper_language_var.get()
        self.config["auto_transcribe"] = self.auto_transcribe_var.get()
        self.config["apply_vocabulary"] = self.apply_vocabulary_var.get()
        
        # Discord integration
        self.config["discord_webhook"] = self.discord_webhook_var.get().strip()

        
        # Save to file
        save_config(self.config)
        
        # Call the callback if provided
        if self.on_save_callback:
            self.on_save_callback()
        
        # Close dialog
        self._on_close()

    def _on_close(self):
        """Clean up and close the dialog."""
        # Unbind mousewheel to prevent issues after dialog closes
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except:
            pass
        self.dialog.destroy()


def show_settings_dialog(parent, config, on_save_callback=None):
    """
    Convenience function to show the settings dialog.
    
    Args:
        parent: The parent tkinter window
        config: The current configuration dictionary  
        on_save_callback: Optional callback function called after saving settings
        
    Returns:
        SettingsDialog: The dialog instance
    """
    return SettingsDialog(parent, config, on_save_callback)
