import numpy as np
import sounddevice as sd
import soundfile as sf
import time
import webrtcvad
from resemblyzer import VoiceEncoder, preprocess_wav

from src.config import (
    SILENCE_TIMEOUT, STT_MODEL, TEMP_AUDIO, VOICE_PROFILE, get_groq_client,
)

# --- Config ---
SAMPLE_RATE = 16000
CHANNELS = 1
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


def close_stream():
    """Release the microphone."""
    global _stream
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None


def set_speaking(value):
    """Set speaking flag to ignore microphone while Remy talks."""
    global is_speaking
    is_speaking = value


def clear_buffer():
    """Drop audio that is already buffered, without waiting for new audio."""
    if _stream is not None:
        try:
            available = _stream.read_available
            if available:
                _stream.read(available)
        except sd.PortAudioError:
            pass


# --- VAD (Voice Activity Detection) ---
def listen(timeout=SILENCE_TIMEOUT, max_duration=15, silence_duration=0.7,
           min_speech_frames=3, should_stop=lambda: False, language="en"):
    """Record one utterance and transcribe it.

    Returns the text, "" if nothing usable was heard, or None if no speech
    started within `timeout` seconds.
    """
    if is_speaking:
        time.sleep(0.5)
        return ""

    vad = webrtcvad.Vad(2)  # 3, odanın öbür ucundaki sesi kaçırıyor
    frame_duration_ms = 30
    frame_size = int(SAMPLE_RATE * frame_duration_ms / 1000)

    stream = _get_stream()
    clear_buffer()

    print("🎤 Listening... (speak now)")

    recording = []
    silent_frames = 0
    speech_frames = 0
    waited_frames = 0
    max_silent_frames = int(silence_duration * 1000 / frame_duration_ms)
    max_wait_frames = int(timeout * 1000 / frame_duration_ms)
    max_frames = int(max_duration * 1000 / frame_duration_ms)

    while True:
        # Yazılı mesaja cevap verilirken veya GUI'den kapatılınca bırak
        if is_speaking or should_stop():
            return ""

        frame, overflowed = stream.read(frame_size)
        audio_bytes = (frame[:, 0] * 32767).astype(np.int16).tobytes()

        if vad.is_speech(audio_bytes, SAMPLE_RATE):
            speech_frames += 1
            silent_frames = 0
        else:
            silent_frames += 1

        if speech_frames:
            recording.append(frame)
            if silent_frames > max_silent_frames or len(recording) >= max_frames:
                print("✅ Speech ended")
                break
        else:
            waited_frames += 1
            if waited_frames > max_wait_frames:
                print(f"⏰ Silence timeout ({timeout}s)")
                return None

    # Minimum konuşma kontrolü
    if speech_frames < min_speech_frames:
        print(f"❌ Too short ({speech_frames} frames) — ignoring")
        return ""

    sf.write(TEMP_AUDIO, np.concatenate(recording, axis=0), SAMPLE_RATE)

    try:
        if not is_my_voice(TEMP_AUDIO):
            print("🤐 Not my voice, ignoring...")
            return ""
        return transcribe(TEMP_AUDIO, language=language)
    except Exception as e:
        # Ağ hatası konuşma döngüsünü düşürmesin
        print(f"⚠️ Transcription error: {e}")
        return ""


# --- Speaker Verification ---
def preload():
    """Load the voice check now so the first command doesn't pay for it."""
    _load_encoder()
    _load_profile()


def _load_encoder():
    global _encoder
    if _encoder is None:
        _encoder = VoiceEncoder()
    return _encoder


def _load_profile():
    global _my_embedding
    if _my_embedding is None:
        if VOICE_PROFILE.exists():
            _my_embedding = np.load(VOICE_PROFILE)
        else:
            print(f"⚠️ {VOICE_PROFILE} not found! Run enroll.py first. Accepting every voice.")
    return _my_embedding


def is_my_voice(audio_file):
    """Check if the audio is from the enrolled user."""
    my_emb = _load_profile()
    if my_emb is None:
        return True  # No profile → accept everything

    encoder = _load_encoder()
    wav = preprocess_wav(audio_file)
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
        result = get_groq_client().audio.transcriptions.create(
            file=file,
            model=STT_MODEL,
            language=language,
            response_format="text"
        )
    return result


if __name__ == "__main__":
    text = listen()
    print(f"📝 Text: {text}")
