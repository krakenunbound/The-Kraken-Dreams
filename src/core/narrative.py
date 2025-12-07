"""
THE KRAKEN DREAMS - Narrative Generation Module
Handles story generation using LLM providers (Bard's Tale functionality).

This module contains the prompt templates and narrative styles for
transforming D&D session transcripts into engaging stories.
"""

# =============================================================================
# NARRATIVE STYLE PROMPTS
# =============================================================================
# Each style has a distinct voice and approach to storytelling.
# The bard_name is replaced with the configured narrator name (default: Zhree).
# =============================================================================

NARRATIVE_STYLES = {
    "Epic Fantasy": {
        "description": "Grand, sweeping narrative with dramatic prose",
        "prompt_prefix": """You are {bard_name}, a legendary bard of great renown. 
        Write in the style of classic high fantasy epics like Tolkien or Jordan. 
        Use vivid imagery, dramatic tension, and epic scope. 
        Include rich descriptions of settings and character emotions."""
    },
    
    "Humorous Tavern Tale": {
        "description": "Light-hearted, funny retelling with witty observations",
        "prompt_prefix": """You are {bard_name}, a witty bard known for comedic tales.
        Write in a humorous, self-aware style reminiscent of Terry Pratchett.
        Find the funny moments, add comedic observations, and don't take things too seriously.
        Break the fourth wall occasionally and poke fun at typical fantasy tropes."""
    },
    
    "Dramatic Chronicle": {
        "description": "Serious, historical-feeling account of events",
        "prompt_prefix": """You are {bard_name}, a scholarly chronicler of great deeds.
        Write as if recording official history, with gravitas and importance.
        Use formal language and treat even small events as historically significant.
        Include "historical" context and foreshadowing."""
    },
    
    "Bardic Ballad": {
        "description": "Poetic, song-like narrative with rhythm and rhyme",
        "prompt_prefix": """You are {bard_name}, a master of verse and song.
        Write in a style that could be sung - use rhythm, occasional rhyme, and lyrical language.
        Structure the narrative like a ballad with refrains and memorable phrases.
        Make it feel like an oral tradition being passed down."""
    },
    
    "Mysterious Legend": {
        "description": "Dark, atmospheric tale with foreboding undertones",
        "prompt_prefix": """You are {bard_name}, a mysterious storyteller of dark tales.
        Write in a gothic, atmospheric style with hints of cosmic horror.
        Emphasize shadows, uncertainty, and the unknown lurking beyond perception.
        Create an unsettling mood while still celebrating the heroes."""
    },
    
    "Heroic Saga": {
        "description": "Action-focused narrative celebrating brave deeds",
        "prompt_prefix": """You are {bard_name}, a bard who celebrates warriors and heroes.
        Write in the style of Norse sagas - direct, action-focused, and heroic.
        Emphasize combat, bravery, and bold decisions.
        Character dialogue should feel powerful and quotable."""
    }
}


def get_narrative_styles():
    """
    Get list of available narrative style names.
    
    Returns:
        list: List of style names
    """
    return list(NARRATIVE_STYLES.keys())


def get_style_description(style_name):
    """
    Get the description for a narrative style.
    
    Args:
        style_name (str): The style name
        
    Returns:
        str: The style description, or empty string if not found
    """
    return NARRATIVE_STYLES.get(style_name, {}).get("description", "")


def build_narrative_prompt(style_name, bard_name, transcript_chunk, chunk_number, total_chunks, speaker_info=None):
    """
    Build a complete prompt for narrative generation.
    
    Args:
        style_name (str): The narrative style to use
        bard_name (str): The name of the narrator bard
        transcript_chunk (str): The transcript text to transform
        chunk_number (int): Current chunk number (1-based)
        total_chunks (int): Total number of chunks
        speaker_info (dict): Optional speaker gender/name information
        
    Returns:
        str: The complete prompt for the LLM
    """
    style = NARRATIVE_STYLES.get(style_name, NARRATIVE_STYLES["Epic Fantasy"])
    prefix = style["prompt_prefix"].format(bard_name=bard_name)
    
    # Build speaker context if provided
    speaker_context = ""
    if speaker_info:
        speaker_context = "\n\nSpeaker Information:\n"
        for speaker_id, info in speaker_info.items():
            name = info.get('name', speaker_id)
            gender = info.get('gender', 'Unknown')
            speaker_context += f"- {name}: {gender}\n"
        speaker_context += "\nUse appropriate pronouns based on the speaker genders above.\n"
    
    # Build the full prompt
    prompt = f"""{prefix}

Transform the following D&D session transcript into an engaging narrative story.
This is chunk {chunk_number} of {total_chunks}. {"Continue the story naturally." if chunk_number > 1 else "Begin the tale."}
{speaker_context}
Keep dialogue where it makes sense but weave it into descriptive prose.
Don't just transcribe - transform it into a story others would want to read.

TRANSCRIPT:
{transcript_chunk}

Write the narrative now:"""

    return prompt


def build_summary_prompt(bard_name, transcript, speaker_info=None):
    """
    Build a prompt for session summary generation.
    
    Args:
        bard_name (str): The name of the narrator bard  
        transcript (str): The full transcript to summarize
        speaker_info (dict): Optional speaker gender/name information
        
    Returns:
        str: The complete prompt for summary generation
    """
    # Build speaker context if provided
    speaker_context = ""
    if speaker_info:
        speaker_context = "\n\nParty Members:\n"
        for speaker_id, info in speaker_info.items():
            name = info.get('name', speaker_id)
            gender = info.get('gender', 'Unknown')
            speaker_context += f"- {name} ({gender})\n"
    
    prompt = f"""You are {bard_name}, a wise bard summarizing a D&D session for the party.
    
Create a brief, engaging summary of this session that could be posted to Discord.
Include:
- Key events and decisions
- Notable combat encounters or challenges
- Character moments and roleplay highlights  
- Any important discoveries or plot developments

Keep it concise (2-4 paragraphs) but capture the essence of what happened.
Use present tense for immediacy and excitement.
{speaker_context}
TRANSCRIPT:
{transcript}

Write the summary now:"""

    return prompt


def get_title_prompt(bard_name, narrative_preview):
    """
    Build a prompt for generating a story title.
    
    Args:
        bard_name (str): The name of the narrator bard
        narrative_preview (str): First portion of the narrative
        
    Returns:
        str: The prompt for title generation
    """
    return f"""You are {bard_name} the bard. Based on this story excerpt, create a single evocative title.
Return ONLY the title, no explanation or quotes.

Story excerpt:
{narrative_preview[:1000]}

Title:"""


def get_closing_prompt(bard_name, style_name):
    """
    Build a prompt for the bardic closing line.
    
    Args:
        bard_name (str): The name of the narrator bard
        style_name (str): The narrative style being used
        
    Returns:
        str: The prompt for the closing line
    """
    return f"""You are {bard_name} the bard, finishing a tale in the {style_name} style.
Write a single closing line that a bard would use to end their performance.
Something like "And so the tale is told..." but fitting your style.
Return ONLY the closing line, no explanation."""
