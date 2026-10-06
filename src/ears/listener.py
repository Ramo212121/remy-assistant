import os
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
from resemblyzer import VoiceEncoder, preprocess_wav

# --- Config ---
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

DURATION = 5
SAMPLE_RATE = 16000
CHANNELS = 1
VOICE_PROFILE = "voice_profile.npy"
SIMILARITY_THRESHOLD = 0.45

# --- Globals ---
_stream = None
is_speaking = False
_encoder = None
_my_embedding = None


# --- Stream ---
def _get_stream():
    global _stream
    if _stream is None:
        _stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='float32'
        )
        _stream.start()
    return _stream


def set_speaking(value):
    """Set speaking flag to ignore microphone while Remy talks."""
    global is_speaking
    is_speaking = value


def clear_buffer():
    """Clear the microphone buffer to remove stale audio."""
    global _stream
    if _stream is not None:
        try:
            _stream.read(16000)
        except:
            pass


def record_audio(filename="temp.flac", duration=DURATION):
    print(f"🎤 Recording... ({duration}s)")
    stream = _get_stream()
    frames = int(duration * SAMPLE_RATE)
    recording, overflowed = stream.read(frames)
    if overflowed:
        print("⚠️ Overflow")
    sf.write(filename, recording, SAMPLE_RATE)
    print("✅ Recording finished")
    return filename


# --- VAD (Voice Activity Detection) ---
def listen_vad(language="en", max_duration=15, silence_duration=1.0, min_speech_frames=3):
    """    Record until silence detected (VAD) with strict noise filtering.
    
    Args:
        max_duration: maximum recording time
        silence_duration: silence after speech to stop
        min_speech_frames: minimum speech frames required (filters noise)
    """
    global is_speaking
    
    if is_speaking:
        print("🤐 Remy konuşuyor, mikrofon kapalı")
        time.sleep(0.5)
        return ""
    
    vad = webrtcvad.Vad(3)  # En agresif
    sample_rate = SAMPLE_RATE
    frame_duration_ms = 30
    frame_size = int(sample_rate * frame_duration_ms / 1000)

    stream = _get_stream()
    
    # Buffer temizle
    clear_buffer()
    
    print("🎤 Listening... (speak now)")

    recording = []
    silent_frames = 0
    speech_frames = 0
    max_silent_frames = int(silence_duration * 1000 / frame_duration_ms)
    max_frames = int(max_duration * 1000 / frame_duration_ms)
    speech_started = False

    for _ in range(max_frames):
        frame, overflowed = stream.read(frame_size)
        audio_bytes = (frame[:, 0] * 32767).astype(np.int16).tobytes()

        is_speech = vad.is_speech(audio_bytes, sample_rate)

        if is_speech:
            speech_started = True
            speech_frames += 1
            silent_frames = 0
        else:
            silent_frames += 1

        if speech_started:
            recording.append(frame)

        if speech_started and silent_frames > max_silent_frames:
            print("✅ Speech ended")
            break

    # Minimum konuşma kontrolü
    if speech_frames < min_speech_frames:
        print(f"❌ Too short ({speech_frames} frames) — ignoring")
        return ""

    if not recording:
        print("❌ No speech detected")
        return ""

    audio = np.concatenate(recording, axis=0)
    filename = "temp.flac"
    sf.write(filename, audio, sample_rate)

    # Speaker verification
    if not is_my_voice(filename):
        print("🤐 Not my voice, ignoring...")
        return ""

    text = transcribe(filename)
    return text

# --- Speaker Verification ---
def _load_encoder():
    global _encoder
    if _encoder is None:
        _encoder = VoiceEncoder()
    return _encoder


def _load_profile():
    global _my_embedding
    if _my_embedding is None:
        if Path(VOICE_PROFILE).exists():
            _my_embedding = np.load(VOICE_PROFILE)
        else:
            print("⚠️ voice_profile.npy not found! Run enroll.py first.")
    return _my_embedding


def is_my_voice(audio_file):
    """Check if the audio is from the enrolled user."""
    my_emb = _load_profile()
    if my_emb is None:
        return True  # No profile → accept everything

    encoder = _load_encoder()
    wav = preprocess_wav(Path(audio_file))
    new_emb = encoder.embed_utterance(wav)

    # Cosine similarity
    similarity = np.dot(my_emb, new_emb) / (
        np.linalg.norm(my_emb) * np.linalg.norm(new_emb)
    )
    print(f"🔍 Voice similarity: {similarity:.3f}")

    return similarity > SIMILARITY_THRESHOLD


# --- STT ---
def transcribe(filename, language="en"):
    print("📤 Sending to Groq...")
    with open(filename, "rb") as file:
        result = client.audio.transcriptions.create(
            file=file,
            model="whisper-large-v3-turbo",
            language=language,
            response_format="text"
        )
    return result


def listen(duration=DURATION, language="en", use_vad=True):
    """Listen with VAD — stops when silence detected."""
    global is_speaking
    if is_speaking:
        time.sleep(0.5)
        return ""

    if use_vad:
        return listen_vad(language=language)

    filename = record_audio(duration=duration)

    # Speaker verification
    if not is_my_voice(filename):
        print("🤐 Not my voice, ignoring...")
        return ""

    text = transcribe(filename)
    return text


if __name__ == "__main__":
    text = listen()
    print(f"📝 Text: {text}")