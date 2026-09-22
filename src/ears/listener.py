import os
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
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
SIMILARITY_THRESHOLD = 0.65

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


def listen(duration=DURATION, language="en"):
    global is_speaking
    if is_speaking:
        time.sleep(0.5)
        return ""

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