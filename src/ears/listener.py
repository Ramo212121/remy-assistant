import os
import time
import sounddevice as sd
import soundfile as sf
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

DURATION = 5
SAMPLE_RATE = 16000
CHANNELS = 1

_stream = None
is_speaking = False


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
            _stream.read(16000)  # 1 saniyelik ses oku ve at
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
    text = transcribe(filename)
    return text


if __name__ == "__main__":
    text = listen()
    print(f"📝 Text: {text}")