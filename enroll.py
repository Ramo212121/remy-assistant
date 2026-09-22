import sounddevice as sd
import soundfile as sf
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path

DURATION = 60  # saniye
SAMPLE_RATE = 16000
FILENAME = "my_voice.wav"
PROFILE = "voice_profile.npy"

def record_voice():
    """Record 30 seconds of your voice."""
    print(f"🎤 Recording for {DURATION} seconds...")
    print("📢 Please speak naturally: introduce yourself, read something, etc.")
    print("⏳ Recording starts in 3 seconds...")
    
    import time
    time.sleep(3)
    
    print("🔴 RECORDING NOW!")
    recording = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    sf.write(FILENAME, recording, SAMPLE_RATE)
    print("✅ Recording finished")

def create_profile():
    """Create voice embedding and save it."""
    print("🧠 Creating voice profile...")
    
    wav = preprocess_wav(Path(FILENAME))
    encoder = VoiceEncoder()
    embedding = encoder.embed_utterance(wav)
    
    np.save(PROFILE, embedding)
    print(f"✅ Voice profile saved to {PROFILE}")
    print(f"📊 Embedding shape: {embedding.shape}")

if __name__ == "__main__":
    record_voice()
    create_profile()
    print("\n🎉 Enrollment complete! Now run remy.py")
