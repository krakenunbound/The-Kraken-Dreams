"""
THE KRAKEN DREAMS - Playback Module
Handles audio playback with speaker indicator synchronization.

This module manages audio playback for reviewing transcripts,
including seeking, pausing, and tracking the current speaker.
"""

import subprocess
import threading
import time


class AudioPlayer:
    """
    Audio player with seeking and speaker tracking support.
    
    Uses ffplay for cross-platform audio playback with precise seeking.
    """
    
    def __init__(self):
        """Initialize the audio player."""
        self.process = None
        self.is_playing = False
        self.is_paused = False
        self.start_time = None
        self.playback_offset = 0
        self.audio_duration = 0
        self.current_file = None
        self.update_callback = None
    
    def set_update_callback(self, callback):
        """
        Set a callback for playback position updates.
        
        The callback receives the current position in seconds.
        
        Args:
            callback: Function to call with position updates
        """
        self.update_callback = callback
    
    def load_file(self, filepath):
        """
        Load an audio file for playback.
        
        Args:
            filepath (str): Path to the audio file
            
        Returns:
            float: Duration in seconds, or 0 on error
        """
        self.current_file = filepath
        self.audio_duration = self._get_duration(filepath)
        return self.audio_duration
    
    def _get_duration(self, filepath):
        """
        Get the duration of an audio file using ffprobe.
        
        Args:
            filepath (str): Path to the audio file
            
        Returns:
            float: Duration in seconds, or 0 on error
        """
        try:
            result = subprocess.run(
                [
                    'ffprobe', '-v', 'quiet', '-show_entries', 
                    'format=duration', '-of', 
                    'default=noprint_wrappers=1:nokey=1', filepath
                ],
                capture_output=True, text=True, timeout=10
            )
            return float(result.stdout.strip())
        except Exception:
            return 0
    
    def play(self, start_time=0):
        """
        Start or resume playback from a specific time.
        
        Args:
            start_time (float): Position to start from in seconds
        """
        if not self.current_file:
            return
        
        self.stop()
        
        self.playback_offset = start_time
        self.is_playing = True
        self.is_paused = False
        self.start_time = time.time()
        
        # Start ffplay in background
        try:
            self.process = subprocess.Popen(
                [
                    'ffplay', '-nodisp', '-autoexit',
                    '-ss', str(start_time),
                    '-loglevel', 'quiet',
                    self.current_file
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"Playback error: {e}")
            self.is_playing = False
    
    def pause(self):
        """Pause playback and remember position."""
        if self.is_playing and not self.is_paused:
            self.playback_offset = self.get_current_position()
            self.stop_process()
            self.is_paused = True
    
    def resume(self):
        """Resume playback from paused position."""
        if self.is_paused:
            self.play(self.playback_offset)
    
    def stop(self):
        """Stop playback completely."""
        self.stop_process()
        self.is_playing = False
        self.is_paused = False
        self.playback_offset = 0
    
    def stop_process(self):
        """Kill the ffplay process if running."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=1)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
    
    def seek(self, position):
        """
        Seek to a specific position.
        
        Args:
            position (float): Position in seconds
        """
        if self.is_playing:
            was_paused = self.is_paused
            self.stop()
            self.play(position)
            if was_paused:
                self.pause()
        else:
            self.playback_offset = position
    
    def skip(self, delta_seconds):
        """
        Skip forward or backward by a number of seconds.
        
        Args:
            delta_seconds (float): Seconds to skip (negative for backward)
        """
        current = self.get_current_position()
        new_pos = max(0, min(self.audio_duration, current + delta_seconds))
        self.seek(new_pos)
    
    def get_current_position(self):
        """
        Get the current playback position.
        
        Returns:
            float: Current position in seconds
        """
        if self.is_playing and not self.is_paused and self.start_time:
            return self.playback_offset + (time.time() - self.start_time)
        return self.playback_offset
    
    def is_finished(self):
        """
        Check if playback has finished.
        
        Returns:
            bool: True if playback is complete
        """
        if self.process:
            return self.process.poll() is not None
        return not self.is_playing
    
    @staticmethod
    def format_time(seconds):
        """
        Format seconds as MM:SS string.
        
        Args:
            seconds (float): Time in seconds
            
        Returns:
            str: Formatted time string
        """
        if seconds < 0:
            seconds = 0
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"


def get_current_speaker(segments, current_time, linger_duration=1.5):
    """
    Determine which speaker is active at a given time.
    
    Includes a "linger" effect where a speaker stays active briefly
    after they finish speaking for visual continuity.
    
    Args:
        segments (list): List of segment dictionaries with start/end/speaker
        current_time (float): Current playback time in seconds
        linger_duration (float): How long to "linger" after speaking
        
    Returns:
        str: The speaker ID, or None if no speaker is active
    """
    active_speaker = None
    latest_end = -1
    
    for seg in segments:
        start = seg.get('start', 0)
        end = seg.get('end', 0)
        speaker = seg.get('speaker', '')
        
        # Check if this segment is currently active (with linger)
        if start <= current_time <= end + linger_duration:
            # Prefer the most recently started segment
            if end > latest_end:
                active_speaker = speaker
                latest_end = end
    
    return active_speaker
