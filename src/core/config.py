"""
THE KRAKEN DREAMS - Configuration Management
Handles loading, saving, and accessing application configuration.

Configuration is stored in kraken_config.json in the application directory.
Sensitive data (API keys) is excluded from version control via .gitignore.
"""

import os
import json

# =============================================================================
# APPLICATION DIRECTORY STRUCTURE
# =============================================================================
# These paths define where all application data is stored.
# The structure keeps recordings, transcripts, and avatars organized.
# =============================================================================

# Get the directory containing the main application file
# This ensures paths work correctly regardless of where the app is launched from
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Subdirectories for organized file storage
RECORDINGS_DIR = os.path.join(APP_DIR, "recordings")    # Audio recordings
TRANSCRIPTS_DIR = os.path.join(APP_DIR, "transcripts")  # Transcript files
AVATARS_DIR = os.path.join(APP_DIR, "avatars")          # Character avatars
CONFIG_FILE = os.path.join(APP_DIR, "kraken_config.json")  # User settings


# =============================================================================
# DEFAULT CONFIGURATION
# =============================================================================
# These are the default values for all configuration options.
# They are used when no config file exists or when a key is missing.
# =============================================================================

DEFAULT_CONFIG = {
    # HuggingFace token for Pyannote speaker diarization
    # Required for transcription - get from huggingface.co/settings/tokens
    "hf_token": "",
    
    # Ollama settings for local LLM inference
    # Ollama must be running locally for this to work
    "ollama_url": "http://localhost:11434",
    "ollama_model": "",  # Will be populated from Ollama API
    
    # Groq settings for cloud LLM inference
    # Free tier available - get API key from console.groq.com
    "groq_api_key": "",
    "groq_url": "https://api.groq.com/openai/v1/chat/completions",
    "groq_model": "",  # Will be populated from model list
    
    # Bard's Tale settings
    "bard_name": "Zhree",  # The name of the in-universe bard narrator
    "chunk_size": 50,      # Lines to process at a time for narrative
    
    # Audio device preferences (saved device names)
    "mic_device": "",      # Preferred microphone device name
    "system_device": "",   # Preferred system audio device name
    
    # Transcription settings
    "whisper_model": "large-v2",  # Whisper model size (tiny, base, small, medium, large-v2)
    "whisper_language": "auto",   # Language for transcription (auto, en, es, fr, de, etc.)
    "auto_transcribe": False,     # Auto-transcribe after recording finishes
    "timestamp_format": "mm:ss",  # Timestamp format: "mm:ss" or "hh:mm:ss"
    "apply_vocabulary": True,     # Apply D&D vocabulary corrections after transcription
    "vocabulary_file": "custom_vocabulary.txt",  # Custom vocabulary file name
    
    # Window position and size (for remembering layout)
    "window_x": None,      # Window X position (None = center)
    "window_y": None,      # Window Y position (None = center)
    "window_width": 950,   # Window width in pixels
    "window_height": 750,  # Window height in pixels
    
    # Discord webhook for posting summaries
    "discord_webhook": "",  # Discord webhook URL for posting summaries
    
    # Speaker colors for transcript display (speaker_id -> hex color)
    "speaker_colors": {}   # Will be populated as speakers are assigned
}



# Available Whisper model sizes
# Smaller = faster but less accurate, Larger = slower but more accurate
WHISPER_MODELS = [
    "tiny",      # Fastest, lowest accuracy (~39 MB)
    "base",      # Fast, basic accuracy (~74 MB)
    "small",     # Balanced speed/accuracy (~244 MB)
    "medium",    # Good accuracy, slower (~769 MB)
    "large-v2",  # Best accuracy, slowest (~1.5 GB) - RECOMMENDED
]

# Supported languages for Whisper transcription
WHISPER_LANGUAGES = [
    ("auto", "Auto-Detect"),
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("zh", "Chinese"),
    ("ru", "Russian"),
    ("ar", "Arabic"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("sv", "Swedish"),
]



def ensure_directories():
    """
    Create application directories if they don't exist.
    Should be called at application startup.
    """
    for directory in [RECORDINGS_DIR, TRANSCRIPTS_DIR, AVATARS_DIR]:
        os.makedirs(directory, exist_ok=True)


def load_config():
    """
    Load configuration from the config file.
    
    If the config file doesn't exist or is corrupted, returns default config.
    Missing keys in an existing config are filled with defaults.
    
    Returns:
        dict: The merged configuration dictionary
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                # Merge with defaults for any missing keys
                # This ensures new config options work with old config files
                config = DEFAULT_CONFIG.copy()
                config.update(saved)
                return config
        except (json.JSONDecodeError, IOError):
            # Config file is corrupted or unreadable
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """
    Save configuration to the config file.
    
    Args:
        config (dict): The configuration dictionary to save
    """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_config_value(key, default=None):
    """
    Get a single configuration value by key.
    
    Args:
        key (str): The configuration key to retrieve
        default: The value to return if key doesn't exist
        
    Returns:
        The configuration value, or default if not found
    """
    config = load_config()
    return config.get(key, default)


def set_config_value(key, value):
    """
    Set a single configuration value and save.
    
    Args:
        key (str): The configuration key to set
        value: The value to store
    """
    config = load_config()
    config[key] = value
    save_config(config)
