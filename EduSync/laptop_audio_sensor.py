import os
import wave
import threading
import sys
import json
import time
import audioop
import requests
import pygame
import pyaudio
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

DJANGO_API_BASE = "http://127.0.0.1:8000"

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
DECISION_FILENAME = "decision_recording.wav"

ALLOWED_SUBJECTS = [
    "Mathematics", "Biology", "Chemistry", "Physics", 
    "English", "Social Studies", "General Study"
]

def speak(text):
    print(f"\n🔊 Speaking: {text}")
    try:
        speech_file = "temp_speech.mp3"
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )
        with open(speech_file, "wb") as f:
            f.write(response.content)

        pygame.mixer.init()
        pygame.mixer.music.load(speech_file)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        pygame.mixer.music.unload()
        pygame.mixer.quit()

        if os.path.exists(speech_file):
            os.remove(speech_file)

    except Exception as e:
        print(f"⚠️ Speech playback error: {e}")

def transcribe_and_cleanup(filename):
    """Transcribes a single 30s chunk and immediately deletes the file."""
    if not os.path.exists(filename):
        return ""

    text = ""
    try:
        print(f"⚙️ Transcribing chunk ({filename})...")
        with open(filename, "rb") as audio_file:
            transcript_resp = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="en"
            )
        text = transcript_resp.text.strip()
    except Exception as e:
        print(f"❌ Chunk transcription error: {e}")
    finally:
        # Delete file immediately after transcription
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"🗑️ [Immediate Clean] Deleted {filename}")
            except Exception as e:
                print(f"⚠️ Deletion failed for {filename}: {e}")

    return text

def record_and_process_continuous_lesson():
    """
    Records in 30-second audio chunks, transcribing and deleting each 
    chunk until the user presses ENTER a second time.
    """
    p = pyaudio.PyAudio()
    
    stop_recording = False
    master_transcript = []
    chunk_index = 0

    def wait_for_stop():
        nonlocal stop_recording
        input("\n🔴 Recording active... Press [ENTER] to stop lesson and summarize.\n")
        stop_recording = True

    threading.Thread(target=wait_for_stop, daemon=True).start()

    print("🎤 Lesson recording started in 30s auto-transcribe loops...")

    while not stop_recording:
        chunk_filename = f"lesson_chunk_{chunk_index}.wav"
        chunk_index += 1

        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        frames = []

        # Record for 30 seconds or until stop signal
        start_time = time.time()
        while not stop_recording and (time.time() - start_time) < 30:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()

        if frames:
            wf = wave.open(chunk_filename, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()

            # Transcribe & delete immediately in sequence
            chunk_text = transcribe_and_cleanup(chunk_filename)
            if chunk_text:
                print(f"📝 Chunk Transcript: \"{chunk_text}\"")
                master_transcript.append(chunk_text)

    p.terminate()

    full_transcript = " ".join(master_transcript).strip()
    print(f"\n✅ Full Lesson Transcript: {full_transcript}\n")
    return full_transcript

def record_until_silence(filename=DECISION_FILENAME, silence_threshold=500, silence_duration=1.5):
    """Listens for user's voice decision, auto-stops after silence."""
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    frames = []
    silent_chunks = 0
    required_silent_chunks = int((RATE / CHUNK) * silence_duration)

    print("🎤 Listening for your voice decision...")
    recording_started = False
    
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

        rms = audioop.rms(data, 2)
        if rms > silence_threshold:
            recording_started = True
            silent_chunks = 0
        elif recording_started:
            silent_chunks += 1
            if silent_chunks >= required_silent_chunks:
                break

    print("⏹️ Decision audio captured.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    return filename

def semantically_determine_action(spoken_decision_text):
    prompt = f"""
    The user was asked: "Should I save this to dashboard, blast to parents via email, or discard it?"
    Transcribed response: "{spoken_decision_text}"

    Note: The input may contain audio mishearings (e.g. "send mail", "send mil", "blast", "mail it", "send").
    If the command indicates sending an email or blasting to parents, select BLAST_EMAIL.
    If it indicates saving, holding, or queueing, select SAVE_TO_DASHBOARD.
    Otherwise, select DISCARD.

    Return exactly ONE word: BLAST_EMAIL, SAVE_TO_DASHBOARD, or DISCARD.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You analyze teacher voice intent strictly."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip().upper()

def safe_post(url_endpoint, payload):
    try:
        res = requests.post(f"{DJANGO_API_BASE}{url_endpoint}", json=payload)
        print(f"📡 Backend Ingress ({url_endpoint}): Status {res.status_code}")
        return res
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def process_lesson():
    # 1. Continuously record 30s chunks until second ENTER
    raw_text = record_and_process_continuous_lesson()

    if not raw_text or len(raw_text) < 5:
        speak("No speech detected in the recording.")
        return

    # 2. Extract assignment details via GPT-4o-mini
    system_prompt = f"""You are an educational assistant speaking directly to a live classroom.
Analyze the transcribed lesson segment and extract key information.

1. SUBJECT NORMALIZATION:
   - Map 'subject' strictly to ONE of these values: {', '.join(ALLOWED_SUBJECTS)}.
   - If subtopics are specific, map to broader subjects (e.g. Biology, Mathematics, Social Studies).

2. TASK DETAILS & SUBTOPICS:
   - Provide rich, specific details. Highlight the specific subtopic taught and what students are asked to do.

3. SPOKEN SUMMARY (spoken_summary):
   - Speak directly to students in a warm teacher voice.
   - Summarize what was taught and what task needs to be completed.
   - NEVER use technical labels like "Parsed task" or "Due date is equal to".
   - IF A DUE DATE IS MENTIONED: Use phrasing like "We have [task] due on [day]".
   - IF NO DUE DATE IS MENTIONED: Omit due date mentions completely.

Return JSON with keys: subject, task_details, due_date, spoken_summary.
"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": raw_text}
        ],
        response_format={"type": "json_object"}
    )
    
    parsed = json.loads(completion.choices[0].message.content)
    subject = parsed.get("subject", "General Study")
    task_details = parsed.get("task_details", "No details provided.")
    due_date = parsed.get("due_date", None)
    spoken_summary = parsed.get("spoken_summary", "")

    if subject not in ALLOWED_SUBJECTS:
        subject = "General Study"

    # 3. Speak summary to class
    if spoken_summary:
        speak(spoken_summary)

    # 4. Prompt & record voice decision
    speak("Should I save this to the dashboard hold queue, blast it directly to parents via email, or discard it?")
    decision_audio_file = record_until_silence()

    # Transcribe and immediately delete decision audio
    decision_transcript = transcribe_and_cleanup(decision_audio_file)
    if not decision_transcript:
        decision_transcript = "SAVE"

    print(f"🗣️ You said: '{decision_transcript}'")
    action = semantically_determine_action(decision_transcript)

    payload = {
        "subject": subject,
        "task_details": task_details,
        "due_date": due_date
    }

    # 5. Route action
    if "BLAST_EMAIL" in action:
        speak("Blasting task directly to registered parents via email.")
        
        create_resp = safe_post("/api/create-assignment/", payload)
        assignment_id = None
        if create_resp and create_resp.status_code in [200, 201]:
            try:
                assignment_id = create_resp.json().get("assignment_id") or create_resp.json().get("id")
                print(f"🆔 Retrieved Assignment ID: {assignment_id}")
            except Exception as e:
                print(f"⚠️ Could not parse assignment_id: {e}")

        blast_payload = {
            "spoken_text": decision_transcript,
            "assignment_id": assignment_id
        }
        safe_post("/api/blast-assignment/", blast_payload)

    elif "SAVE_TO_DASHBOARD" in action:
        speak("Saving task to instructor dashboard hold queue.")
        safe_post("/api/create-assignment/", payload)

    else:
        speak("Task discarded.")

def main_loop():
    print("\n🚀 --- EduSync Interactive Voice Terminal ---")
    while True:
        user_input = input("\nPress [ENTER] to start recording (or type 'q' and press Enter to exit): ")
        if user_input.lower().strip() == 'q':
            speak("Exiting EduSync sensor.")
            sys.exit(0)

        process_lesson()

if __name__ == "__main__":
    main_loop()