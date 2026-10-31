import time

import numpy as np
import sounddevice as sd
import soundfile as sf
from resemblyzer import VoiceEncoder, preprocess_wav

from src.config import VOICE_PROFILE, VOICE_SAMPLE

DURATION = 60  # saniye
SAMPLE_RATE = 16000


def record_voice():
    """Record a sample of your voice."""
    print(f"🎤 Recording for {DURATION} seconds...")
    print("📢 Please speak naturally: introduce yourself, read something, etc.")
    print("⏳ Recording starts in 3 seconds...")

    time.sleep(3)

    print("🔴 RECORDING NOW!")
    recording = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    sf.write(VOICE_SAMPLE, recording, SAMPLE_RATE)
    print("✅ Recording finished")


def create_profile():
    """Create voice embedding and save it."""
    print("🧠 Creating voice profile...")

    wav = preprocess_wav(VOICE_SAMPLE)
    encoder = VoiceEncoder()
    embedding = encoder.embed_utterance(wav)

    np.save(VOICE_PROFILE, embedding)
    print(f"✅ Voice profile saved to {VOICE_PROFILE}")
    print(f"📊 Embedding shape: {embedding.shape}")


if __name__ == "__main__":
    record_voice()
    create_profile()
    print("\n🎉 Enrollment complete! Now run remy.py")
