"""
THE KRAKEN DREAMS - Core Module
Contains configuration, constants, and shared utilities.
"""

from .config import (
    load_config, 
    save_config, 
    DEFAULT_CONFIG,
    APP_DIR,
    RECORDINGS_DIR,
    TRANSCRIPTS_DIR,
    AVATARS_DIR,
    CONFIG_FILE,
    ensure_directories
)
from .theme import KRAKEN, FONT_FAMILY, FONTS, apply_theme, get_style_config

from .llm_providers import (
    OllamaProvider, 
    GroqProvider, 
    GROQ_MODELS, 
    create_provider
)
from .narrative import (
    NARRATIVE_STYLES,
    get_narrative_styles,
    build_narrative_prompt,
    build_summary_prompt
)
from .recording import AudioRecorder
from .playback import AudioPlayer, get_current_speaker
from .formatters import (
    format_timestamp,
    parse_timestamp,
    format_duration,
    convert_transcript_timestamps,
    extract_speakers_from_transcript
)
from .search import TranscriptSearcher, SearchResult, quick_search
from .vocabulary import VocabularyManager, apply_dnd_corrections, create_default_vocabulary
from .exporters import export_to_obsidian, export_to_markdown, export_to_html, get_export_formats
from .database import SessionDatabase, get_database
from .punctuation import improve_punctuation, apply_all_improvements
