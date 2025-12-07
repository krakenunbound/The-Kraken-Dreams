"""
THE KRAKEN DREAMS - Audio Recording Module
Handles dual-channel audio recording (microphone + system audio).

This module manages simultaneous recording from two audio devices,
typically a microphone and system audio (Stereo Mix or WASAPI loopback).
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import time
import os
from datetime import datetime


class AudioRecorder:
    """
    Dual-channel audio recorder for capturing mic and system audio.
    
    Records from two audio devices simultaneously and mixes them
    into a single stereo output file.
    """
    
    def __init__(self, sample_rate=44100):
        """
        Initialize the audio recorder.
        
        Args:
            sample_rate (int): The sample rate for recording (default 44100 Hz)
        """
        self.sample_rate = sample_rate
        self.is_recording = False
        self.mic_data = []
        self.system_data = []
        self.recording_thread_mic = None
        self.recording_thread_system = None
        self.start_time = None
        self.level_callback = None  # Callback for level meters
    
    @staticmethod
    def get_input_devices():
        """
        Get list of available input devices (microphones).
        
        Returns:
            list: List of tuples (device_id, device_name)
        """
        devices = sd.query_devices()
        return [
            (i, d['name']) 
            for i, d in enumerate(devices) 
            if d['max_input_channels'] > 0
        ]
    
    @staticmethod
    def get_output_devices():
        """
        Get list of available output devices (for WASAPI loopback).
        
        Returns:
            list: List of tuples (device_id, device_name)
        """
        devices = sd.query_devices()
        return [
            (i, d['name']) 
            for i, d in enumerate(devices) 
            if d['max_output_channels'] > 0
        ]
    
    @staticmethod
    def get_all_devices_for_system_audio():
        """
        Get all devices suitable for system audio capture.
        
        Includes both input devices (like Stereo Mix) and output devices
        (for WASAPI loopback capture).
        
        Returns:
            list: List of tuples (device_id, display_name, is_output)
        """
        devices = sd.query_devices()
        result = []
        input_names = set()
        
        # First add input devices
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                result.append((i, d['name'], False))
                input_names.add(d['name'])
        
        # Then add output devices (marked as [OUTPUT])
        for i, d in enumerate(devices):
            if d['max_output_channels'] > 0 and d['name'] not in input_names:
                result.append((i, f"[OUTPUT] {d['name']}", True))
        
        return result
    
    def set_level_callback(self, callback):
        """
        Set a callback function for audio level updates.
        
        The callback receives (mic_level, system_level) as 0-100 values.
        
        Args:
            callback: Function to call with level updates
        """
        self.level_callback = callback
    
    def _record_device(self, device_id, data_list, channels):
        """
        Record from a single device in a background thread.
        
        Args:
            device_id (int): The sounddevice device ID
            data_list (list): List to append audio chunks to
            channels (int): Number of channels to record
        """
        def callback(indata, frames, time_info, status):
            if self.is_recording:
                # Store the audio data
                data_list.append(indata.copy())
                
                # Calculate level for meters (RMS converted to 0-100)
                if self.level_callback:
                    level = np.sqrt(np.mean(indata**2)) * 500
                    level = min(100, level)
                    # Call the callback from main thread
                    # (handled by the caller)
        
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                device=device_id,
                channels=channels,
                callback=callback,
                blocksize=2048
            ):
                while self.is_recording:
                    time.sleep(0.1)
        except Exception as e:
            print(f"Recording error on device {device_id}: {e}")
    
    def start_recording(self, mic_device_id, system_device_id):
        """
        Start recording from both devices.
        
        Args:
            mic_device_id (int): The microphone device ID
            system_device_id (int): The system audio device ID
        """
        if self.is_recording:
            return
        
        self.mic_data = []
        self.system_data = []
        self.is_recording = True
        self.start_time = time.time()
        
        # Start recording threads
        self.recording_thread_mic = threading.Thread(
            target=self._record_device,
            args=(mic_device_id, self.mic_data, 1)
        )
        self.recording_thread_system = threading.Thread(
            target=self._record_device,
            args=(system_device_id, self.system_data, 2)
        )
        
        self.recording_thread_mic.start()
        self.recording_thread_system.start()
    
    def stop_recording(self, output_dir):
        """
        Stop recording and save the audio file.
        
        Args:
            output_dir (str): Directory to save the recording
            
        Returns:
            str: Path to the saved file, or None on error
        """
        if not self.is_recording:
            return None
        
        self.is_recording = False
        
        # Wait for threads to finish
        if self.recording_thread_mic:
            self.recording_thread_mic.join(timeout=2.0)
        if self.recording_thread_system:
            self.recording_thread_system.join(timeout=2.0)
        
        # Combine and save audio
        try:
            if self.mic_data and self.system_data:
                mic_audio = np.concatenate(self.mic_data)
                sys_audio = np.concatenate(self.system_data)
                
                # Ensure same length
                min_len = min(len(mic_audio), len(sys_audio))
                mic_audio = mic_audio[:min_len]
                sys_audio = sys_audio[:min_len]
                
                # Convert to mono if stereo, then create stereo output
                if len(mic_audio.shape) > 1:
                    mic_audio = mic_audio.mean(axis=1)
                if len(sys_audio.shape) > 1:
                    sys_audio = sys_audio.mean(axis=1)
                
                # Combine into stereo (mic left, system right)
                stereo = np.column_stack([mic_audio, sys_audio])
                
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"dnd_session_{timestamp}.wav"
                filepath = os.path.join(output_dir, filename)
                
                # Save file
                sf.write(filepath, stereo, self.sample_rate)
                
                return filepath
                
        except Exception as e:
            print(f"Error saving recording: {e}")
        
        return None
    
    def get_elapsed_time(self):
        """
        Get the elapsed recording time.
        
        Returns:
            float: Elapsed time in seconds, or 0 if not recording
        """
        if self.start_time and self.is_recording:
            return time.time() - self.start_time
        return 0
    
    @staticmethod
    def format_time(seconds):
        """
        Format seconds as HH:MM:SS string.
        
        Args:
            seconds (float): Time in seconds
            
        Returns:
            str: Formatted time string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
