"""
THE KRAKEN DREAMS - Theme Configuration
Dark underwater Kraken theme colors and styles for the application.

This module defines the complete color palette used throughout the app,
inspired by deep sea bioluminescence and tentacle aesthetics.
"""

# =============================================================================
# KRAKEN THEME COLOR PALETTE
# =============================================================================
# The color scheme is designed to evoke a deep underwater atmosphere:
# - Dark purples and blues for backgrounds
# - Bioluminescent teal for highlights and accents
# - Coral reds for warnings and recording states
# =============================================================================

KRAKEN = {
    # Background Colors (darkest to lightest)
    'bg_dark': '#0a0a0f',      # Deepest abyss - main background
    'bg_mid': '#12121a',        # Deep sea - section backgrounds
    'bg_light': '#1a1a24',      # Twilight zone - lighter sections
    'bg_widget': '#22222e',     # Widget backgrounds (inputs, buttons)
    
    # Accent Colors (purple tentacle tones)
    'accent': '#6b5b95',        # Deep purple - primary accent
    'accent_light': '#8b7bb5',  # Lighter purple - hover states
    'accent_glow': '#9d8dc7',   # Glowing purple - highlights
    'tentacle': '#4a3f6b',      # Dark purple - section headers
    
    # Feature Colors
    'deep_sea': '#1e3a5f',      # Deep blue - secondary accent
    'biolum': '#00d4aa',        # Bioluminescent teal - success/active
    'warning': '#ff6b6b',       # Coral red - warnings/recording
    'success': '#50c878',       # Emerald green - success states
    'recording': '#ff4444',     # Bright red - recording indicator
    
    # Text Colors
    'text': '#e0e0e8',          # Main text - soft white
    'text_dim': '#8888a0',      # Dim text - labels, hints
    'text_bright': '#ffffff',   # Bright text - headings, emphasis
}


# =============================================================================
# CROSS-PLATFORM FONT CONFIGURATION
# =============================================================================
# Font family stack that works on Windows, Linux, and macOS.
# Falls back gracefully if primary font is not available.
# =============================================================================

import sys

def get_font_family():
    """Get the best available font family for the current platform."""
    if sys.platform == 'win32':
        return 'Segoe UI'
    elif sys.platform == 'darwin':  # macOS
        return 'SF Pro Display'
    else:  # Linux and others
        return 'DejaVu Sans'

# Primary UI font - cross-platform
FONT_FAMILY = get_font_family()

# Font presets for common uses
FONTS = {
    'heading': (FONT_FAMILY, 16, 'bold'),
    'subheading': (FONT_FAMILY, 12, 'bold'),
    'section': (FONT_FAMILY, 10, 'bold'),
    'body': (FONT_FAMILY, 10),
    'small': (FONT_FAMILY, 9),
    'tiny': (FONT_FAMILY, 8),
    'button': (FONT_FAMILY, 10),
    'button_large': (FONT_FAMILY, 11, 'bold'),
    'entry': (FONT_FAMILY, 10),
    'mono': ('Consolas' if sys.platform == 'win32' else 'DejaVu Sans Mono', 10),
}


# =============================================================================
# SPEAKER COLOR PALETTE
# =============================================================================
# Distinct colors for differentiating speakers in transcripts.
# Designed to be readable on dark backgrounds while being visually distinct.
# Colors are inspired by D&D character archetypes and fantasy themes.
# =============================================================================

SPEAKER_COLORS = [
    '#ff7b7b',  # Coral Red - Warrior/Fighter
    '#7bffb5',  # Emerald Green - Ranger/Druid
    '#7bb5ff',  # Sky Blue - Wizard/Mage
    '#ffdf7b',  # Gold - Cleric/Paladin
    '#d87bff',  # Violet - Warlock/Sorcerer
    '#7bfff5',  # Cyan - Rogue/Bard
    '#ffb57b',  # Orange - Barbarian
    '#b5ff7b',  # Lime - Monk
    '#ff7bdf',  # Pink - Artificer
    '#7bdfff',  # Light Blue - DM/Narrator
    '#c4a5ff',  # Lavender - NPC 1
    '#a5ffc4',  # Mint - NPC 2
]


def get_speaker_color(index):
    """
    Get a speaker color by index.
    Cycles through the palette if more speakers than colors.
    
    Args:
        index (int): The speaker index (0-based)
        
    Returns:
        str: Hex color code
    """
    return SPEAKER_COLORS[index % len(SPEAKER_COLORS)]


def assign_speaker_colors(speaker_ids):
    """
    Assign colors to a list of speaker IDs.
    
    Args:
        speaker_ids (list): List of speaker ID strings
        
    Returns:
        dict: Mapping of speaker_id -> hex color
    """
    return {
        speaker_id: get_speaker_color(i) 
        for i, speaker_id in enumerate(speaker_ids)
    }




def get_style_config():
    """
    Returns a dictionary of ttk style configurations for the Kraken theme.
    Use this to configure ttk.Style() in the application.
    
    Returns:
        dict: Style configuration dictionary
    """
    return {
        'TFrame': {
            'configure': {'background': KRAKEN['bg_dark']}
        },
        'TLabel': {
            'configure': {
                'background': KRAKEN['bg_dark'],
                'foreground': KRAKEN['text'],
                'font': ('Segoe UI', 10)
            }
        },
        'TButton': {
            'configure': {
                'background': KRAKEN['bg_widget'],
                'foreground': KRAKEN['text'],
                'font': ('Segoe UI', 10),
                'padding': 8,
                'borderwidth': 0
            },
            'map': {
                'background': [('active', KRAKEN['accent']), ('pressed', KRAKEN['tentacle'])]
            }
        },
        'TNotebook': {
            'configure': {'background': KRAKEN['bg_dark'], 'borderwidth': 0}
        },
        'TNotebook.Tab': {
            'configure': {
                'background': KRAKEN['bg_mid'],
                'foreground': KRAKEN['text_dim'],
                'font': ('Segoe UI', 11, 'bold'),
                'padding': [20, 10]
            },
            'map': {
                'background': [('selected', KRAKEN['accent']), ('active', KRAKEN['tentacle'])],
                'foreground': [('selected', KRAKEN['text_bright']), ('active', KRAKEN['text'])]
            }
        },
        'TCombobox': {
            'configure': {
                'fieldbackground': KRAKEN['bg_widget'],
                'foreground': KRAKEN['text'],
                'background': KRAKEN['bg_widget'],
                'arrowcolor': KRAKEN['accent'],
                'selectbackground': KRAKEN['accent'],
                'selectforeground': KRAKEN['text_bright']
            },
            'map': {
                'fieldbackground': [
                    ('readonly', KRAKEN['bg_widget']),
                    ('disabled', KRAKEN['bg_dark'])
                ],
                'foreground': [
                    ('readonly', KRAKEN['text']),
                    ('disabled', KRAKEN['text_dim'])
                ]
            }
        },
        'TLabelframe': {
            'configure': {
                'background': KRAKEN['bg_dark'],
                'foreground': KRAKEN['accent_light']
            }
        },
        'TLabelframe.Label': {
            'configure': {
                'background': KRAKEN['bg_dark'],
                'foreground': KRAKEN['accent_light'],
                'font': ('Segoe UI', 11, 'bold')
            }
        },
        'Horizontal.TProgressbar': {
            'configure': {
                'background': KRAKEN['biolum'],
                'troughcolor': KRAKEN['bg_widget'],
                'borderwidth': 0,
                'thickness': 8
            }
        },
        'TEntry': {
            'configure': {
                'fieldbackground': KRAKEN['bg_widget'],
                'foreground': KRAKEN['text']
            }
        }
    }


def apply_theme(style):
    """
    Apply the Kraken theme to a ttk.Style instance.
    
    Args:
        style: A ttk.Style() instance to configure
    """
    style.theme_use('clam')
    config = get_style_config()
    
    for style_name, settings in config.items():
        if 'configure' in settings:
            style.configure(style_name, **settings['configure'])
        if 'map' in settings:
            style.map(style_name, **settings['map'])
