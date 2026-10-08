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
_current_proc = None
_is_speaking = False

# Emoji pattern (tek yerde tanımlı)
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002700-\U000027BF"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U00002600-\U000026FF"  # misc symbols
    "\U0001FA00-\U0001FAFF"  # symbols extended
    "\U0001F000-\U0001F02F"  # mahjong
    "\U0001F0A0-\U0001F0FF"  # playing cards
    "\U00002190-\U000021FF"  # arrows
    "\U00002B00-\U00002BFF"  # misc symbols and arrows
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero width joiner
    "]+",
    flags=re.UNICODE
)


def clean_text_for_tts(text):
    """Remove markdown, emojis, symbols, and special characters."""
    # 1. Emoji temizle
    text = _EMOJI_PATTERN.sub(r'', text)

    # 2. Markdown temizle
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)          # **bold**
    text = re.sub(r'\*(.+?)\*', r'\1', text)              # *italic*
    text = re.sub(r'__(.+?)__', r'\1', text)              # __bold__
    text = re.sub(r'_(.+?)_', r'\1', text)                # _italic_
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)  # # headers
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # - bullets
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # 1. numbered
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # ```code```
    text = re.sub(r'`(.+?)`', r'\1', text)                # `inline code`
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)       # [link](url)
    text = re.sub(r'https?://\S+', '', text)              # URLs

    # 3. TTS için kötü karakterler
    text = re.sub(r'[#$@%^&*_=+<>|~]', '', text)
    text = re.sub(r'[()\[\]{}]', '', text)

    # 4. Fazla boşlukları temizle
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def is_speaking():
    """Check if speaker is currently playing."""
    return _is_speaking


def interrupt():
    """Interrupt current speech and clear queue."""
    global _current_proc, _is_speaking
    print("🛑 Interrupting speech...")

    # Queue'yu boşalt
    while not _speech_queue.empty():
        try:
            _speech_queue.get_nowait()
            _speech_queue.task_done()
        except queue.Empty:
            break

    # Çalan sesi kes
    if _current_proc is not None:
        try:
            _current_proc.terminate()
        except:
            pass

    _is_speaking = False


def _listen_for_interrupt(proc, threshold=INTERRUPT_THRESHOLD):
    """Listen to mic while afplay plays. Stop afplay if user speaks."""
    def callback(indata, frames, time_info, status):
        # Sadece gerçekten konuşurken dinle
        if not _is_speaking:
            raise sd.CallbackStop()

        volume = np.linalg.norm(indata) / len(indata)
        if volume > threshold:
            print(f"🛑 Interrupt detected (volume: {volume:.4f})")
            try:
                proc.terminate()
            except:
                pass
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
    global _current_proc, _is_speaking
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
        try:
            subprocess.run(
                ["piper", "-m", MODEL_PATH, "-f", output_file],
                input=text.encode("utf-8"),
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Piper error: {e}")
            _speech_queue.task_done()
            continue

        # afplay + interrupt listener
        _is_speaking = True
        try:
            _current_proc = subprocess.Popen(
                ["afplay", output_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            _listen_for_interrupt(_current_proc)
            _current_proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            print("⚠️ afplay timeout")
            if _current_proc:
                _current_proc.kill()
                _current_proc.wait()
        except Exception as e:
            print(f"⚠️ afplay error: {e}")
        finally:
            _current_proc = None
            _is_speaking = False

        # Wav dosyasını sil
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except:
                pass

        # Mikrofon buffer'ının temizlenmesi için kısa bekleme
        # (afplay bittikten hemen sonra listen() çağrılırsa çakışma olabilir)
        time.sleep(0.2)

        _speech_queue.task_done()


_worker_thread = threading.Thread(target=_speech_worker, daemon=True)
_worker_thread.start()


def speak(text):
    """Add text to speech queue."""
    _speech_queue.put(text)


def wait_until_done():
    """Wait until all speech is finished."""
    _speech_queue.join()


def stop_worker():
    """Stop the worker thread (for shutdown)."""
    _speech_queue.put(None)


if __name__ == "__main__":
    speak("Hello, **I am Remi**. How can I help you? #test $100 😊")
    wait_until_done()