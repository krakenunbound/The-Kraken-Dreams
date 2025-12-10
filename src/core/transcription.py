
import os
import sys
import logging
import warnings
import threading
import time
import gc
import json
import subprocess
import re
import traceback
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

from .config import APP_DIR
from .vocabulary import VocabularyManager, create_default_vocabulary

class TranscriptionManager:
    """
    Manages the transcription process using WhisperX and Pyannote.
    Moved from kraken_suite.py to reduce file size.
    """
    
    def __init__(self, app):
        """
        Initialize with reference to main app to access logger, config, etc.
        
        Args:
            app: The KrakenSuite application instance
        """
        self.app = app
        
    def log(self, message):
        self.app.log(message)
        
    def tech_log(self, message):
        self.app.tech_log(message)
        
    def set_status(self, message):
        self.app.set_status(message)

    def run_transcription(self):
        """
        Run transcription with detailed progress feedback.
        This is the worker thread function.
        """
        # Initialize variables for cleanup
        gui_handler = None
        loggers_to_capture = []
        original_showwarning = warnings.showwarning

        try:
            # Log immediately to confirm thread started
            self.log("Transcription thread started...")

            # Create a custom logging handler that sends messages to the TECH log
            class GUILogHandler(logging.Handler):
                def __init__(handler_self, tech_log_func):
                    super().__init__()
                    handler_self.tech_log_func = tech_log_func

                def emit(handler_self, record):
                    msg = handler_self.format(record)
                    if msg.strip():
                        handler_self.tech_log_func(f"[{record.name}] [{record.levelname}] {msg}")

            # Create handler for capturing library output -> goes to ENGINE LOG
            gui_handler = GUILogHandler(self.tech_log)
            gui_handler.setLevel(logging.INFO)
            gui_handler.setFormatter(logging.Formatter('%(message)s'))

            # Attach handler to relevant loggers
            loggers_to_capture = [
                'whisperx', 'whisperx.asr', 'whisperx.vads', 'whisperx.vads.pyannote',
                'pyannote', 'pyannote.audio', 'faster_whisper'
            ]
            for logger_name in loggers_to_capture:
                logger = logging.getLogger(logger_name)
                logger.addHandler(gui_handler)
                logger.setLevel(logging.INFO)

            # Also capture warnings -> goes to ENGINE LOG
            def custom_showwarning(message, category, filename, lineno, file=None, line=None):
                self.tech_log(f"[WARNING] {category.__name__}: {message}")
            warnings.showwarning = custom_showwarning

            # ===== STEP 1: Check prerequisites =====
            self.log("=" * 50)
            self.log("STARTING TRANSCRIPTION PIPELINE")
            self.log("=" * 50)

            if self.app.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # Check for HuggingFace token
            hf_token = self.app.config.get("hf_token", "").strip()
            if not hf_token:
                self.app.root.after(0, lambda: messagebox.showerror("Missing API Key",
                    "HuggingFace token is required for speaker diarization.\n\n"
                    "Click Settings (⚙️) to add your token.\n\n"
                    "Get a free token at:\nhttps://huggingface.co/settings/tokens"))
                self.app.root.after(0, self.app.transcription_failed)
                return

            # ===== STEP 2: Import libraries =====
            self.log("")
            self.log("[1/7] Loading libraries...")
            self.tech_log("Importing whisperx...")
            self.log("  → Importing WhisperX...")
            import whisperx
            self.tech_log("Importing DiarizationPipeline from whisperx.diarize...")
            self.log("  → Importing Diarization Pipeline...")
            from whisperx.diarize import DiarizationPipeline
            self.tech_log("Importing torch...")
            self.log("  → Importing PyTorch...")
            import torch
            self.tech_log(f"torch version: {torch.__version__}, CUDA available: {torch.cuda.is_available()}")
            self.log("  ✓ Libraries loaded successfully")

            if self.app.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 3: Setup device =====
            self.log("")
            self.log("[2/7] Setting up compute device...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cuda":
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
                self.log(f"  → GPU: {gpu_name}")
                self.log(f"  → VRAM: {gpu_memory:.1f} GB")
                self.log(f"  ✓ Using CUDA acceleration")
            else:
                self.log("  → No CUDA GPU detected")
                self.log("  ✓ Using CPU (slower)")

            if self.app.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 4: Load audio =====
            self.log("")
            self.log("[3/7] Loading audio file...")
            self.log(f"  → File: {os.path.basename(self.app.selected_file)}")
            file_size = os.path.getsize(self.app.selected_file) / (1024 * 1024)
            self.log(f"  → Size: {file_size:.1f} MB")
            self.log("  → Extracting audio (ffmpeg)...")
            self.tech_log(f"whisperx.load_audio('{self.app.selected_file}')")
            audio = whisperx.load_audio(self.app.selected_file)
            duration_seconds = len(audio) / 16000  # WhisperX uses 16kHz
            duration_minutes = duration_seconds / 60
            hours = int(duration_minutes // 60)
            mins = int(duration_minutes % 60)
            self.tech_log(f"Audio loaded: {len(audio)} samples, {duration_seconds:.1f}s")
            self.log(f"  → Duration: {hours}h {mins}m")
            self.log("  ✓ Audio loaded")

            if self.app.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 5: Transcribe with Whisper =====
            self.log("")
            self.log("[4/7] Loading Whisper model...")
            
            # Get model from config (default to large-v2 for best accuracy)
            whisper_model = self.app.config.get("whisper_model", "large-v2")
            whisper_language = self.app.config.get("whisper_language", "auto")
            self.log(f"  → Model: {whisper_model}")
            self.log(f"  → Language: {whisper_language}")
            compute_type = "float16" if device == "cuda" else "int8"
            self.log(f"  → Compute type: {compute_type}")
            self.log("  → Downloading/loading model weights...")
            self.tech_log(f"whisperx.load_model('{whisper_model}', device='{device}', compute_type='{compute_type}')")
            model = whisperx.load_model(whisper_model, device, compute_type=compute_type)
            self.tech_log("Whisper model loaded successfully")
            self.log("  ✓ Whisper model ready")


            self.log("")
            self.log("[5/7] Transcribing audio...")
            self.log("  → This is the longest step - please wait...")
            batch_size = 16 if device == "cuda" else 4
            self.log(f"  → Batch size: {batch_size}")
            
            # Use specified language or auto-detect
            if whisper_language and whisper_language != "auto":
                self.log(f"  → Using language: {whisper_language}")
                self.tech_log(f"model.transcribe(audio, batch_size={batch_size}, language='{whisper_language}') - STARTING")
                result = model.transcribe(audio, batch_size=batch_size, language=whisper_language)
            else:
                self.log("  → Detecting language...")
                self.tech_log(f"model.transcribe(audio, batch_size={batch_size}) - STARTING")
                result = model.transcribe(audio, batch_size=batch_size)
            
            self.tech_log("model.transcribe() - COMPLETED")
            detected_language = result.get("language", whisper_language if whisper_language != "auto" else "en")
            num_segments = len(result.get("segments", []))
            self.tech_log(f"Result: language={detected_language}, segments={num_segments}")

            self.log(f"  → Language: {detected_language}")
            self.log(f"  → Segments found: {num_segments}")
            self.log("  ✓ Transcription complete")

            if self.app.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # Free memory
            self.log("  → Releasing Whisper memory...")
            del model
            gc.collect()
            if device == "cuda":
                torch.cuda.empty_cache()
            self.log("  ✓ Memory released")

            # ===== STEP 6: Align words =====
            self.log("")
            self.log("[6/7] Aligning words to audio...")
            self.log(f"  → Loading alignment model ({detected_language})...")
            self.tech_log(f"whisperx.load_align_model(language_code='{detected_language}', device='{device}')")
            model_a, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
            self.tech_log("Alignment model loaded")
            self.log("  ✓ Alignment model loaded")
            self.log("  → Aligning transcript...")
            self.tech_log("whisperx.align() - STARTING")
            result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
            self.tech_log("whisperx.align() - COMPLETED")
            self.log("  ✓ Alignment complete")

            # Free memory
            self.log("  → Releasing alignment model...")
            del model_a
            gc.collect()
            self.tech_log("Alignment model released from memory")

            if self.app.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 7: Speaker diarization =====
            self.log("")
            self.log("[7/7] Identifying speakers...")
            self.log("  → Loading Pyannote diarization model...")
            self.log("  → Authenticating with HuggingFace...")
            self.tech_log(f"DiarizationPipeline(use_auth_token=hf_token, device='{device}')")
            diarize_model = DiarizationPipeline(use_auth_token=hf_token, device=device)
            self.tech_log("Pyannote diarization model loaded")
            self.log("  ✓ Diarization model loaded")
            self.log("  → Analyzing voices (this takes a while)...")
            self.log("  → Detecting who speaks when...")
            self.tech_log("diarize_model(audio) - STARTING speaker diarization")
            diarize_segments = diarize_model(audio)
            self.tech_log(f"diarize_model() - COMPLETED, got {type(diarize_segments)}")
            self.log("  ✓ Speaker diarization complete")

            if self.app.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 8: Assign speakers to segments =====
            self.log("")
            self.log("Assigning speakers to transcript...")
            self.tech_log("whisperx.assign_word_speakers() - STARTING")
            result = whisperx.assign_word_speakers(diarize_segments, result)
            self.tech_log("whisperx.assign_word_speakers() - COMPLETED")
            self.log("  ✓ Speakers assigned")

            if self.app.transcription_stop_requested:
                raise Exception("Transcription stopped by user")

            # ===== STEP 9: Build transcript =====
            self.log("")
            self.log("Building transcript...")
            base_name = os.path.splitext(os.path.basename(self.app.selected_file))[0]
            output_dir = os.path.dirname(self.app.selected_file)

            lines = ["D&D Session Transcription", "=" * 50, f"File: {base_name}", ""]
            self.app.segments_data = []
            found_speakers = set()

            for segment in result["segments"]:
                speaker = segment.get("speaker", "UNKNOWN")
                text = segment.get("text", "").strip()
                start = segment.get("start", 0)
                end = segment.get("end", start + 1)

                if text:
                    minutes = int(start // 60)
                    seconds = int(start % 60)
                    lines.append(f"[{minutes:02d}:{seconds:02d}] {speaker}: {text}")
                    self.app.segments_data.append({
                        "start": start,
                        "end": end,
                        "speaker": speaker,
                        "text": text
                    })
                    found_speakers.add(speaker)

            self.app.current_transcript = "\n".join(lines)
            
            # Apply D&D vocabulary corrections
            self.log("  → Applying vocabulary corrections...")
            self.app.current_transcript = self.app.apply_vocabulary_corrections(self.app.current_transcript)
            
            self.app.current_media_file = self.app.selected_file


            # ===== STEP 10: Save files =====
            self.log("")
            self.log("Saving output files...")
            
            # Save to source directory (next to video)
            source_txt_path = os.path.join(output_dir, f"{base_name}_notes.txt")
            with open(source_txt_path, "w", encoding="utf-8") as f:
                f.write(self.app.current_transcript)
                
            source_json_path = os.path.join(output_dir, f"{base_name}_segments.json")
            with open(source_json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "media_file": self.app.selected_file,
                    "segments": self.app.segments_data,
                    "avatars": self.app.speaker_avatars
                }, f, indent=2)

            # Save copies to dedicated Transcripts folder
            from .config import TRANSCRIPTS_DIR
            os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
            
            txt_path = os.path.join(TRANSCRIPTS_DIR, f"{base_name}_notes.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(self.app.current_transcript)
            self.log(f"  → Saved to Transcripts: {os.path.basename(txt_path)}")

            json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_name}_segments.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "media_file": self.app.selected_file,
                    "segments": self.app.segments_data,
                    "avatars": self.app.speaker_avatars
                }, f, indent=2)

            # Use the dedicated folder path as the "current" file for the app
            self.app.current_output_file = txt_path

            # Setup speakers
            self.app.speakers = {s: s for s in sorted(found_speakers)}

            # ===== STEP 11: Extract audio for playback =====
            self.log("")
            self.log("Extracting audio for playback...")
            self.app.extract_audio(self.app.selected_file)

            # ===== COMPLETE =====
            self.log("")
            self.log("=" * 50)
            self.log("TRANSCRIPTION COMPLETE!")
            self.log("=" * 50)
            self.log(f"  → Found {len(found_speakers)} speakers: {', '.join(sorted(found_speakers))}")
            self.log(f"  → Total segments: {len(self.app.segments_data)}")
            self.log(f"  → Output: {txt_path}")
            self.log("")
            self.log("Next: Go to SPEAKERS tab to assign names.")

            # Update UI
            self.app.root.after(0, self.app.transcription_complete)

        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()

            # Log to STATUS (user-friendly)
            self.log("")
            self.log("=" * 50)
            if "stopped by user" in error_msg.lower():
                self.log("TRANSCRIPTION STOPPED")
            else:
                self.log("TRANSCRIPTION FAILED")
            self.log("=" * 50)
            self.log(f"Error: {e}")
            self.log("")
            self.log("See ENGINE LOG below for full error details.")

            # Log full traceback to ENGINE LOG (copy-paste for debugging)
            self.tech_log("=" * 60)
            self.tech_log("EXCEPTION OCCURRED")
            self.tech_log("=" * 60)
            self.tech_log(f"Exception type: {type(e).__name__}")
            self.tech_log(f"Exception message: {e}")
            self.tech_log("-" * 60)
            self.tech_log("Full traceback:")
            for line in tb.strip().split('\n'):
                self.tech_log(line)
            self.tech_log("=" * 60)

            self.app.root.after(0, self.app.transcription_failed)

        finally:
            # Cleanup: Remove our logging handlers (if they were created)
            if gui_handler is not None:
                for logger_name in loggers_to_capture:
                    logger = logging.getLogger(logger_name)
                    try:
                        logger.removeHandler(gui_handler)
                    except:
                        pass
            # Restore original warning handler
            warnings.showwarning = original_showwarning

