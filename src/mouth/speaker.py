import subprocess
import os
import time
import re
import queue
import threading

MODEL_PATH = "en_US-ryan-high.onnx"

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
        
        # Her cümle için ayrı dosya
        counter += 1
        output_file = f"temp_speech_{counter}.wav"
        
        # Piper ile sese çevir
        subprocess.run(
            ["piper", "-m", MODEL_PATH, "-f", output_file],
            input=text.encode("utf-8"),
            check=True
        )
        
        # afplay ile çal
        try:
            subprocess.run(["afplay", output_file], check=True, timeout=30)
        except subprocess.TimeoutExpired:
            print("⚠️ afplay timeout")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ afplay error: {e}")
        
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