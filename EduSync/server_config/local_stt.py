import os
from faster_whisper import WhisperModel

# Initialize the lightweight inference engine locally on your laptop CPU
print("🧠 Loading local Faster-Whisper structural architecture into memory...")
stt_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
print("✅ Local speech parsing engine fully active.")

def transcribe_incoming_chunk(audio_file_path):
    """Accepts a localized wav file path and performs local CPU-based transcription."""
    if not os.path.exists(audio_file_path):
        return ""
    
    # beam_size=1 provides the fastest tracking speed for real-time speech
    segments, info = stt_model.transcribe(audio_file_path, beam_size=1, language="en")
    
    # Reassemble individual text frames into an integrated string statement
    compiled_transcript = "".join([segment.text for segment in segments]).strip()
    return compiled_transcript
