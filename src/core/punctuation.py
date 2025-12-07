"""
THE KRAKEN DREAMS - Punctuation Improvements
Post-processing to improve sentence boundaries and punctuation in transcripts.

Whisper sometimes struggles with proper punctuation, especially for:
- Sentence endings
- Question detection
- Proper capitalization after periods
"""

import re


def improve_punctuation(text):
    """
    Improve punctuation and sentence boundaries in transcript text.
    
    Args:
        text (str): Raw transcript text
        
    Returns:
        str: Text with improved punctuation
    """
    result = text
    
    # Fix common run-on patterns
    result = fix_run_on_sentences(result)
    
    # Fix question marks
    result = fix_questions(result)
    
    # Fix capitalization after periods
    result = fix_capitalization(result)
    
    # Clean up spacing issues
    result = fix_spacing(result)
    
    return result


def fix_run_on_sentences(text):
    """
    Add periods to likely sentence boundaries.
    
    Looks for patterns like lowercase-to-uppercase transitions
    that suggest a missing period.
    """
    # Pattern: lowercase letter followed by space and uppercase letter (potential sentence break)
    # Only apply if there's no punctuation
    lines = []
    for line in text.split('\n'):
        # Skip timestamp lines - process the dialogue part only
        match = re.match(r'(\[\d+:\d+(?::\d+)?\]\s+[^:]+:\s*)(.*)', line)
        if match:
            prefix, dialogue = match.groups()
            
            # Find lowercase followed by space + uppercase (likely sentence break)
            # Don't match after common abbreviations
            fixed = re.sub(
                r'([a-z])\s+([A-Z][a-z])',
                r'\1. \2',
                dialogue
            )
            lines.append(prefix + fixed)
        else:
            lines.append(line)
    
    return '\n'.join(lines)


def fix_questions(text):
    """
    Convert likely questions to have question marks.
    
    Detects question patterns like "what", "why", "how", etc.
    """
    # Question starters
    question_words = [
        'what', 'why', 'how', 'where', 'when', 'who', 'which',
        'do you', 'can you', 'will you', 'would you', 'could you',
        'is it', 'is there', 'are you', 'are we', 'are they',
        'did you', 'have you', 'should we', 'shall we',
        'does anyone', 'does anyone', 'is anyone'
    ]
    
    lines = []
    for line in text.split('\n'):
        match = re.match(r'(\[\d+:\d+(?::\d+)?\]\s+[^:]+:\s*)(.*)', line)
        if match:
            prefix, dialogue = match.groups()
            
            # Split into sentences
            sentences = re.split(r'(?<=[.!?])\s+', dialogue)
            fixed_sentences = []
            
            for sentence in sentences:
                # Check if sentence starts with question word and ends with period
                lower = sentence.lower().strip()
                if any(lower.startswith(q) for q in question_words):
                    if sentence.rstrip().endswith('.'):
                        sentence = sentence.rstrip()[:-1] + '?'
                fixed_sentences.append(sentence)
            
            lines.append(prefix + ' '.join(fixed_sentences))
        else:
            lines.append(line)
    
    return '\n'.join(lines)


def fix_capitalization(text):
    """
    Fix capitalization after sentence-ending punctuation.
    """
    # Capitalize after . ! ?
    result = re.sub(r'([.!?])\s+([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
    
    return result


def fix_spacing(text):
    """
    Clean up common spacing issues.
    """
    # Remove multiple spaces
    result = re.sub(r'  +', ' ', text)
    
    # Fix space before punctuation
    result = re.sub(r'\s+([.!?,;:])', r'\1', result)
    
    # Ensure space after punctuation (except at end of line)
    result = re.sub(r'([.!?,;:])([A-Za-z])', r'\1 \2', result)
    
    return result


def fix_dnd_punctuation(text):
    """
    D&D-specific punctuation fixes.
    
    Handles common D&D speech patterns.
    """
    result = text
    
    # "I roll to..." often ends abruptly
    result = re.sub(r'I roll to ([a-z]+)\s+([A-Z])', r'I roll to \1. \2', result)
    
    # "Make a ... check/save"
    result = re.sub(r'(make a \w+ (?:check|save))\s+([A-Z])', r'\1. \2', result, flags=re.IGNORECASE)
    
    # "That's a hit/miss"  
    result = re.sub(r"(that's a (?:hit|miss|crit))\s+([A-Z])", r'\1! \2', result, flags=re.IGNORECASE)
    
    return result


def apply_all_improvements(text):
    """
    Apply all punctuation improvements.
    
    Args:
        text (str): Raw transcript text
        
    Returns:
        str: Improved text
    """
    result = text
    result = improve_punctuation(result)
    result = fix_dnd_punctuation(result)
    return result
