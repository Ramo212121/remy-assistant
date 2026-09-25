import sounddevice as sd
import numpy as np

def callback(indata, frames, time, status):
    volume = np.linalg.norm(indata) / len(indata)
    print(f"Volume: {volume:.4f}")

with sd.InputStream(callback=callback, channels=1, samplerate=16000, device=0):
    print("Listening for 10 seconds... SPEAK LOUDLY!")
    sd.sleep(10000)