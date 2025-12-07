"""
THE KRAKEN DREAMS - Text Formatting Utilities
Handles transcript formatting, timestamps, and text processing.

This module provides reusable formatting functions that can be
used across the application for consistent text output.
"""

import re
from datetime import timedelta


# =============================================================================
# TIMESTAMP FORMATTING
# =============================================================================

def format_timestamp(seconds, format_style="mm:ss"):
    """
    Format seconds into a human-readable timestamp.
    
    Args:
        seconds (float): Time in seconds
        format_style (str): "mm:ss" or "hh:mm:ss"
        
    Returns:
        str: Formatted timestamp string
    """
    if seconds is None or seconds < 0:
        return "00:00" if format_style == "mm:ss" else "00:00:00"
    
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if format_style == "hh:mm:ss" or hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def parse_timestamp(timestamp_str):
    """
    Parse a timestamp string back to seconds.
    
    Supports formats: "mm:ss", "hh:mm:ss", "h:mm:ss"
    
    Args:
        timestamp_str (str): Timestamp like "05:30" or "1:30:45"
        
    Returns:
        float: Time in seconds, or 0 if parsing fails
    """
    try:
        parts = timestamp_str.split(':')
        if len(parts) == 2:
            # mm:ss format
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            # hh:mm:ss format
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, IndexError):
        pass
    return 0


def format_duration(seconds):
    """
    Format a duration for display (e.g., "1h 30m 45s").
    
    Args:
        seconds (float): Duration in seconds
        
    Returns:
        str: Human-readable duration
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s" if secs > 0 else f"{mins}m"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"


# =============================================================================
# TRANSCRIPT FORMATTING
# =============================================================================

def convert_transcript_timestamps(transcript, to_format="hh:mm:ss"):
    """
    Convert all timestamps in a transcript to the specified format.
    
    Args:
        transcript (str): The transcript text with [mm:ss] timestamps
        to_format (str): Target format ("mm:ss" or "hh:mm:ss")
        
    Returns:
        str: Transcript with converted timestamps
    """
    def replace_timestamp(match):
        original = match.group(1)
        seconds = parse_timestamp(original)
        return f"[{format_timestamp(seconds, to_format)}]"
    
    # Match timestamps in [mm:ss] or [hh:mm:ss] format
    pattern = r'\[(\d+:\d+(?::\d+)?)\]'
    return re.sub(pattern, replace_timestamp, transcript)


def extract_speakers_from_transcript(transcript):
    """
    Extract unique speaker names from a transcript.
    
    Args:
        transcript (str): The transcript text
        
    Returns:
        list: Sorted list of unique speaker names
    """
    speakers = set()
    pattern = r'\[\d+:\d+(?::\d+)?\]\s+([^:]+):'
    
    for match in re.finditer(pattern, transcript):
        speaker = match.group(1).strip()
        if speaker:
            speakers.add(speaker)
    
    return sorted(speakers)


def clean_transcript_text(text):
    """
    Clean up transcript text by removing artifacts and normalizing whitespace.
    
    Args:
        text (str): Raw transcript text
        
    Returns:
        str: Cleaned transcript text
    """
    # Remove multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove trailing whitespace from lines
    text = '\n'.join(line.rstrip() for line in text.split('\n'))
    # Remove leading/trailing whitespace
    return text.strip()


# =============================================================================
# SPEAKER NAME FORMATTING
# =============================================================================

def format_speaker_line(timestamp_seconds, speaker, text, timestamp_format="mm:ss"):
    """
    Format a single transcript line with timestamp, speaker, and text.
    
    Args:
        timestamp_seconds (float): The timestamp in seconds
        speaker (str): Speaker name
        text (str): What they said
        timestamp_format (str): "mm:ss" or "hh:mm:ss"
        
    Returns:
        str: Formatted line like "[05:30] Speaker: Text"
    """
    ts = format_timestamp(timestamp_seconds, timestamp_format)
    return f"[{ts}] {speaker}: {text}"


# =============================================================================
# FILE NAMING
# =============================================================================

def sanitize_filename(name, max_length=50):
    """
    Sanitize a string for use as a filename.
    
    Args:
        name (str): The name to sanitize
        max_length (int): Maximum length for the filename
        
    Returns:
        str: Safe filename string
    """
    # Remove invalid characters
    safe = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace whitespace with underscores
    safe = re.sub(r'\s+', '_', safe)
    # Truncate if too long
    if len(safe) > max_length:
        safe = safe[:max_length]
    return safe.strip('_')
