import subprocess
import os
import time
import re
import queue
import threading
import numpy as np
import sounddevice as sd

MODEL_PATH = "en_US-ryan-high.onnx"
INTERRUPT_THRESHOLD = 0.25

_speech_queue = queue.Queue()


def clean_text_for_tts(text):
    """Remove markdown, symbols, and special characters."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[#$@%^&*_=+<>|~]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _listen_for_interrupt(proc, threshold=INTERRUPT_THRESHOLD):
    """Listen to mic while afplay plays. Stop afplay if user speaks."""
    def callback(indata, frames, time_info, status):
        volume = np.linalg.norm(indata) / len(indata)
        if volume > threshold:
            print(f"🛑 Interrupt detected (volume: {volume:.4f})")
            proc.terminate()
            raise sd.CallbackStop()

    try:
        with sd.InputStream(callback=callback, channels=1, samplerate=16000, device=0):
            proc.wait()
    except sd.CallbackStop:
        pass
    except Exception as e:
        print(f"⚠️ Interrupt listener error: {e}")


def _speech_worker():
    """Pull sentences from queue, play one by one."""
    counter = 0
    while True:
        text = _speech_queue.get()
        if text is None:
            break

        text = text.replace("Remy", "Remi")
        text = clean_text_for_tts(text)
        if not text.strip():
            _speech_queue.task_done()
            continue

        print(f"🔊 Remy: {text}")

        counter += 1
        output_file = f"temp_speech_{counter}.wav"

        # Piper: text → wav
        subprocess.run(
            ["piper", "-m", MODEL_PATH, "-f", output_file],
            input=text.encode("utf-8"),
            check=True
        )

        # afplay + interrupt listener
        try:
            proc = subprocess.Popen(["afplay", output_file])
            _listen_for_interrupt(proc)
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            print("⚠️ afplay timeout")
            proc.kill()
            proc.wait()

        time.sleep(1.0)

        if os.path.exists(output_file):
            os.remove(output_file)

        _speech_queue.task_done()


_worker_thread = threading.Thread(target=_speech_worker, daemon=True)
_worker_thread.start()


def speak(text):
    """Add text to speech queue."""
    _speech_queue.put(text)


def wait_until_done():
    """Wait until all speech is finished."""
    _speech_queue.join()


if __name__ == "__main__":
    speak("Hello, **I am Remi**. How can I help you? #test $100")
    wait_until_done()