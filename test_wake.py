import openwakeword
from openwakeword.model import Model
import sounddevice as sd
import numpy as np

# Model yükle
model = Model(wakeword_models=["hey_jarvis"])
THRESHOLD = 0.5

print("💤 Listening for 'Hey Jarvis'... (Ctrl+C to stop)")

def callback(indata, frames, time, status):
    audio = (indata[:, 0] * 32767).astype(np.int16)
    prediction = model.predict(audio)
    for name, score in prediction.items():
        if score > THRESHOLD:
            print(f"🎯 Wake word detected: {name} ({score:.2f})")

with sd.InputStream(callback=callback, channels=1, samplerate=16000, device=0):
    sd.sleep(30000)