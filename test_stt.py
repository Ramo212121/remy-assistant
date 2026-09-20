import os
import sounddevice as sd
import soundfile as sf
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

DURATION = 5
SAMPLE_RATE = 16000
CHANNELS = 1
FILENAME = "test.flac"
#-----------------------------------------------------------
def record_audio():
    print(f"🎤 Recording... ({DURATION} seconds)")
    recording = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS)
    sd.wait()
    sf.write(FILENAME, recording, SAMPLE_RATE)
    print("✅ Recording finished")
#-----------------------------------------------------------
def transcribe(filename):
    print("📤 Sending to Groq...")
    with open(filename, "rb") as file:
        result = client.audio.transcriptions.create(
            file=file,
            model="whisper-large-v3-turbo",
            language="tr",
            response_format="text"
        )
    return result
#-----------------------------------------------------------
def main():
    record_audio()
    text = transcribe(FILENAME)
    print(f"📝 Text: {text}")
#-----------------------------------------------------------
if __name__ == "__main__":
    main()