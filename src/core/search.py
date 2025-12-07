"""
THE KRAKEN DREAMS - Search Module
Provides full-text search across transcript files.

This module enables searching through all saved transcripts
for specific text, speakers, or keywords.
"""

import os
import re
import json
from datetime import datetime


class TranscriptSearcher:
    """
    Search engine for transcript files.
    
    Indexes and searches through transcript files in the transcripts directory.
    """
    
    def __init__(self, transcripts_dir):
        """
        Initialize the searcher.
        
        Args:
            transcripts_dir (str): Path to the transcripts directory
        """
        self.transcripts_dir = transcripts_dir
        self.index = {}  # filename -> content cache
    
    def scan_transcripts(self):
        """
        Scan the transcripts directory and build an index.
        
        Returns:
            int: Number of files indexed
        """
        self.index = {}
        
        if not os.path.exists(self.transcripts_dir):
            return 0
        
        for filename in os.listdir(self.transcripts_dir):
            if filename.endswith('.txt'):
                filepath = os.path.join(self.transcripts_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Store metadata
                    stat = os.stat(filepath)
                    self.index[filename] = {
                        'path': filepath,
                        'content': content.lower(),  # For case-insensitive search
                        'content_original': content,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'lines': content.count('\n') + 1
                    }
                except (IOError, UnicodeDecodeError):
                    continue
        
        return len(self.index)
    
    def search(self, query, case_sensitive=False, whole_word=False):
        """
        Search all indexed transcripts for a query.
        
        Args:
            query (str): The search text
            case_sensitive (bool): Whether to match case
            whole_word (bool): Whether to match whole words only
            
        Returns:
            list: List of SearchResult objects with matches
        """
        results = []
        
        if not query:
            return results
        
        search_query = query if case_sensitive else query.lower()
        
        if whole_word:
            pattern = r'\b' + re.escape(search_query) + r'\b'
            flags = 0 if case_sensitive else re.IGNORECASE
        
        for filename, data in self.index.items():
            content = data['content_original'] if case_sensitive else data['content']
            
            matches = []
            
            if whole_word:
                for match in re.finditer(pattern, data['content_original'], flags):
                    matches.append(self._extract_context(data['content_original'], match.start()))
            else:
                start = 0
                while True:
                    pos = content.find(search_query, start)
                    if pos == -1:
                        break
                    matches.append(self._extract_context(data['content_original'], pos))
                    start = pos + 1
            
            if matches:
                results.append(SearchResult(
                    filename=filename,
                    path=data['path'],
                    matches=matches,
                    match_count=len(matches),
                    modified=data['modified']
                ))
        
        # Sort by match count (most matches first)
        results.sort(key=lambda r: r.match_count, reverse=True)
        return results
    
    def _extract_context(self, content, position, context_chars=50):
        """
        Extract context around a match position.
        
        Args:
            content (str): The full content
            position (int): Position of the match
            context_chars (int): Characters of context on each side
            
        Returns:
            dict: Context with line number and snippet
        """
        # Find line number
        line_num = content[:position].count('\n') + 1
        
        # Find the line containing the match
        line_start = content.rfind('\n', 0, position) + 1
        line_end = content.find('\n', position)
        if line_end == -1:
            line_end = len(content)
        
        line = content[line_start:line_end].strip()
        
        return {
            'line_number': line_num,
            'line': line,
            'position': position - line_start
        }
    
    def search_by_speaker(self, speaker_name):
        """
        Find all lines spoken by a specific speaker.
        
        Args:
            speaker_name (str): The speaker to search for
            
        Returns:
            list: SearchResult objects with speaker's lines
        """
        results = []
        pattern = re.compile(
            r'\[\d+:\d+(?::\d+)?\]\s+' + re.escape(speaker_name) + r':\s*(.+)',
            re.IGNORECASE
        )
        
        for filename, data in self.index.items():
            matches = []
            for line_num, line in enumerate(data['content_original'].split('\n'), 1):
                if pattern.match(line):
                    matches.append({
                        'line_number': line_num,
                        'line': line.strip(),
                        'position': 0
                    })
            
            if matches:
                results.append(SearchResult(
                    filename=filename,
                    path=data['path'],
                    matches=matches,
                    match_count=len(matches),
                    modified=data['modified']
                ))
        
        results.sort(key=lambda r: r.match_count, reverse=True)
        return results
    
    def get_all_speakers(self):
        """
        Get all unique speakers across all transcripts.
        
        Returns:
            dict: Speaker name -> count of lines
        """
        speakers = {}
        pattern = r'\[\d+:\d+(?::\d+)?\]\s+([^:]+):'
        
        for data in self.index.values():
            for match in re.finditer(pattern, data['content_original']):
                speaker = match.group(1).strip()
                speakers[speaker] = speakers.get(speaker, 0) + 1
        
        return dict(sorted(speakers.items(), key=lambda x: x[1], reverse=True))


class SearchResult:
    """
    Represents a search result from a single file.
    """
    
    def __init__(self, filename, path, matches, match_count, modified):
        self.filename = filename
        self.path = path
        self.matches = matches
        self.match_count = match_count
        self.modified = modified
    
    def __repr__(self):
        return f"SearchResult({self.filename}, {self.match_count} matches)"


def quick_search(transcripts_dir, query):
    """
    Convenience function for quick searching.
    
    Args:
        transcripts_dir (str): Path to transcripts directory
        query (str): Search text
        
    Returns:
        list: SearchResult objects
    """
    searcher = TranscriptSearcher(transcripts_dir)
    searcher.scan_transcripts()
    return searcher.search(query)
