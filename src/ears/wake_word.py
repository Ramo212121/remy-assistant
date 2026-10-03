import openwakeword
from openwakeword.model import Model
import sounddevice as sd
import numpy as np

_model = None
THRESHOLD = 0.35


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

    def callback(indata, frames, time, status):
        nonlocal detected
        if detected:
            return

        audio = (indata[:, 0] * 32767).astype(np.int16)
        prediction = model.predict(audio)
        for name, score in prediction.items():
            if score > THRESHOLD:
                print(f"🎯 Wake word detected: {name} ({score:.2f})")
                detected = True

    try:
        stream = sd.InputStream(callback=callback, channels=1, samplerate=16000, device=0)
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