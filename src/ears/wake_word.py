import openwakeword
from openwakeword.model import Model
import sounddevice as sd
import numpy as np

_model = None
THRESHOLD = 0.5


def _load_model():
    global _model
    if _model is None:
        _model = Model(
            wakeword_models=["hey_jarvis"],
            inference_framework="tflite"
        )
    return _model


def wait_for_wake_word(timeout=30):
    """Block until wake word is detected or timeout."""
    model = _load_model()
    print("💤 Waiting for wake word...")
    detected = False
    stream = None
    consecutive_hits = 0

    def callback(indata, frames, time, status):
        nonlocal detected, consecutive_hits
        if detected:
            return
        audio = (indata[:, 0] * 32767).astype(np.int16)
        prediction = model.predict(audio)
        for name, score in prediction.items():
            if score > THRESHOLD:
                consecutive_hits += 1
                print(f"🎯 Hit {consecutive_hits}/3: {name} ({score:.2f})")
                if consecutive_hits >= 3:
                    print(f"✅ Wake word confirmed: {name}")
                    detected = True
            else:
                consecutive_hits = 0

    try:
        stream = sd.InputStream(
            callback=callback,
            channels=1,
            samplerate=16000,
            device=0
        )
        stream.start()

        elapsed = 0
        while not detected and elapsed < timeout * 10:
            sd.sleep(100)
            elapsed += 1
    finally:
        if stream is not None:
            stream.stop()
            stream.close()

    return detected


if __name__ == "__main__":
    result = wait_for_wake_word(timeout=30)
    print(f"Detected: {result}")