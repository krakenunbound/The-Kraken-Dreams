"""
THE KRAKEN DREAMS - Custom Vocabulary Module
Manages custom words, character names, and D&D terminology for better transcription.

This module provides:
- Loading/saving custom vocabulary from a simple text file
- Built-in D&D common terms
- Post-processing to fix common transcription errors
"""

import os
import re

# =============================================================================
# BUILT-IN D&D VOCABULARY
# =============================================================================
# Common D&D terms that Whisper often mishears.
# Format: (wrong_spelling, correct_spelling)

DND_CORRECTIONS = [
    # Races
    ("teefling", "tiefling"),
    ("tifling", "tiefling"),
    ("dragonborne", "dragonborn"),
    ("half orc", "half-orc"),
    ("half elf", "half-elf"),
    ("aasamar", "aasimar"),
    ("assimar", "aasimar"),
    ("genassi", "genasi"),
    ("golioth", "goliath"),
    ("kenku", "kenku"),
    ("tabaxy", "tabaxi"),
    ("tortle", "tortle"),
    ("yuan ti", "yuan-ti"),
    
    # Classes
    ("barbarian", "barbarian"),
    ("artifcer", "artificer"),
    ("blood hunter", "blood hunter"),
    
    # Common terms
    ("dungeon master", "Dungeon Master"),
    ("game master", "Game Master"),
    ("non player character", "NPC"),
    ("player character", "PC"),
    ("armor class", "AC"),
    ("hit points", "HP"),
    ("dungens and dragons", "Dungeons & Dragons"),
    ("d and d", "D&D"),
    ("dnd", "D&D"),
    ("dee and dee", "D&D"),
    ("nat 20", "nat 20"),
    ("natural 20", "nat 20"),
    ("nat 1", "nat 1"),
    ("natural 1", "nat 1"),
    ("critical hit", "crit"),
    ("critical miss", "crit fail"),
    
    # Dice
    ("d4", "d4"),
    ("d6", "d6"),
    ("d8", "d8"),
    ("d10", "d10"),
    ("d12", "d12"),
    ("d20", "d20"),
    ("d100", "d100"),
    ("percentile", "percentile"),
    
    # Spells (commonly misheard)
    ("fireball", "Fireball"),
    ("magic missile", "Magic Missile"),
    ("eldritch blast", "Eldritch Blast"),
    ("cure wounds", "Cure Wounds"),
    ("healing word", "Healing Word"),
    ("thunder wave", "Thunderwave"),
    ("shield", "Shield"),
    ("counter spell", "Counterspell"),
    ("dispel magic", "Dispel Magic"),
    
    # Actions
    ("attack of opportunity", "opportunity attack"),
    ("bonus action", "bonus action"),
    ("reaction", "reaction"),
    ("concentration", "concentration"),
    ("advantage", "advantage"),
    ("disadvantage", "disadvantage"),
    ("saving throw", "saving throw"),
    ("ability check", "ability check"),
    ("skill check", "skill check"),
    ("death save", "death save"),
    ("death saving throw", "death save"),
]


class VocabularyManager:
    """
    Manages custom vocabulary for transcript post-processing.
    
    Stores character names, places, and custom terms that should be
    corrected in transcripts after Whisper processing.
    """
    
    def __init__(self, vocab_file=None):
        """
        Initialize the vocabulary manager.
        
        Args:
            vocab_file (str): Path to custom vocabulary file
        """
        self.vocab_file = vocab_file
        self.custom_corrections = []  # List of (wrong, correct) tuples
        self.character_names = []     # List of character names
        self.place_names = []         # List of place/location names
        
        if vocab_file and os.path.exists(vocab_file):
            self.load_vocabulary()
    
    def load_vocabulary(self):
        """Load vocabulary from the file."""
        if not self.vocab_file or not os.path.exists(self.vocab_file):
            return
        
        try:
            with open(self.vocab_file, 'r', encoding='utf-8') as f:
                section = None
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Section headers
                    if line.startswith('[') and line.endswith(']'):
                        section = line[1:-1].lower()
                        continue
                    
                    # Parse based on section
                    if section == 'characters':
                        self.character_names.append(line)
                    elif section == 'places':
                        self.place_names.append(line)
                    elif section == 'corrections':
                        if '->' in line:
                            wrong, correct = line.split('->', 1)
                            self.custom_corrections.append(
                                (wrong.strip().lower(), correct.strip())
                            )
        except IOError:
            pass
    
    def save_vocabulary(self):
        """Save vocabulary to the file."""
        if not self.vocab_file:
            return
        
        try:
            with open(self.vocab_file, 'w', encoding='utf-8') as f:
                f.write("# Custom Vocabulary for The Kraken Dreams\n")
                f.write("# Add your campaign-specific terms below\n\n")
                
                f.write("[Characters]\n")
                f.write("# Character names (one per line)\n")
                for name in self.character_names:
                    f.write(f"{name}\n")
                f.write("\n")
                
                f.write("[Places]\n")
                f.write("# Location names (one per line)\n")
                for name in self.place_names:
                    f.write(f"{name}\n")
                f.write("\n")
                
                f.write("[Corrections]\n")
                f.write("# Format: wrong_text -> correct_text\n")
                for wrong, correct in self.custom_corrections:
                    f.write(f"{wrong} -> {correct}\n")
        except IOError:
            pass
    
    def add_character(self, name):
        """Add a character name to vocabulary."""
        if name and name not in self.character_names:
            self.character_names.append(name)
    
    def add_place(self, name):
        """Add a place name to vocabulary."""
        if name and name not in self.place_names:
            self.place_names.append(name)
    
    def add_correction(self, wrong, correct):
        """Add a custom correction."""
        self.custom_corrections.append((wrong.lower(), correct))
    
    def apply_corrections(self, text, use_dnd_terms=True):
        """
        Apply all vocabulary corrections to text.
        
        Args:
            text (str): The transcript text to correct
            use_dnd_terms (bool): Whether to apply built-in D&D corrections
            
        Returns:
            str: Corrected text
        """
        result = text
        
        # First apply custom corrections (higher priority)
        for wrong, correct in self.custom_corrections:
            # Case-insensitive replacement preserving boundaries
            pattern = r'\b' + re.escape(wrong) + r'\b'
            result = re.sub(pattern, correct, result, flags=re.IGNORECASE)
        
        # Apply character name capitalization
        for name in self.character_names:
            pattern = r'\b' + re.escape(name.lower()) + r'\b'
            result = re.sub(pattern, name, result, flags=re.IGNORECASE)
        
        # Apply place name capitalization
        for name in self.place_names:
            pattern = r'\b' + re.escape(name.lower()) + r'\b'
            result = re.sub(pattern, name, result, flags=re.IGNORECASE)
        
        # Apply D&D corrections if enabled
        if use_dnd_terms:
            for wrong, correct in DND_CORRECTIONS:
                pattern = r'\b' + re.escape(wrong) + r'\b'
                result = re.sub(pattern, correct, result, flags=re.IGNORECASE)
        
        return result
    
    def get_all_terms(self):
        """Get all vocabulary terms as a list (for display)."""
        terms = []
        terms.extend([('Character', n) for n in self.character_names])
        terms.extend([('Place', n) for n in self.place_names])
        terms.extend([('Correction', f"{w} → {c}") for w, c in self.custom_corrections])
        return terms


def create_default_vocabulary(filepath):
    """
    Create a default vocabulary file with examples.
    
    Args:
        filepath (str): Path to create the file at
    """
    content = """# Custom Vocabulary for The Kraken Dreams
# Add your campaign-specific terms below
# Lines starting with # are comments

[Characters]
# Add your party member and NPC names here (one per line)
# These will be properly capitalized in transcripts
# Example:
# Thalindra
# Grimjaw
# Zephyros the Wise

[Places]
# Add locations, cities, realms (one per line)
# Example:
# Waterdeep
# Baldur's Gate
# Neverwinter
# The Sword Coast

[Corrections]
# Format: wrong_text -> correct_text
# Use this to fix consistent transcription errors
# Example:
# barovia -> Barovia
# van richten -> Van Richten
# strahd -> Strahd
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


# Convenience function for quick correction
def apply_dnd_corrections(text):
    """
    Apply built-in D&D corrections to text.
    
    Args:
        text (str): Text to correct
        
    Returns:
        str: Corrected text
    """
    manager = VocabularyManager()
    return manager.apply_corrections(text, use_dnd_terms=True)
