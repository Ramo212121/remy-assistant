import subprocess
import os
import time
import re
import queue
import threading
import numpy as np
import sounddevice as sd
import wave

from piper import PiperVoice

from src.config import TTS_MODEL

MODEL_PATH = str(TTS_MODEL)
INTERRUPT_THRESHOLD = 0.25

_speech_queue = queue.Queue()  # metin → sentez
_play_queue = queue.Queue()    # hazır wav → çalma, sıradaki cümle önceden hazırlanır
_voice = None
_voice_lock = threading.Lock()
_current_proc = None
_is_speaking = False
_interrupted = threading.Event()
_generation = 0  # interrupt() ile artar, kuyruktan çıkmış eski cümleler çalmasın

# Emoji pattern — TTS emojileri yanlış okur
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "\U00002600-\U000026FF"
    "\U0001FA00-\U0001FAFF"
    "\U0001F000-\U0001F02F"
    "\U0001F0A0-\U0001F0FF"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE
)


def clean_text_for_tts(text):
    """Remove markdown, emojis, symbols, and special characters."""
    text = _EMOJI_PATTERN.sub(r'', text)

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
    text = re.sub(r'[()\[\]{}]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def is_speaking():
    """Check if speaker is currently playing."""
    return _is_speaking


def was_interrupted():
    """True after interrupt(), until reset_interrupt()."""
    return _interrupted.is_set()


def reset_interrupt():
    _interrupted.clear()


def load_voice():
    """Keep the voice model in memory. Loading it for every sentence costs over half a second."""
    global _voice
    with _voice_lock:
        if _voice is None:
            _voice = PiperVoice.load(MODEL_PATH)
        return _voice


def _drain(target, on_item=None):
    while True:
        try:
            item = target.get_nowait()
        except queue.Empty:
            return
        if on_item and item is not None:
            on_item(item)
        target.task_done()


def _remove(path):
    if os.path.exists(path):
        os.remove(path)


def interrupt():
    """Interrupt current speech and clear both queues."""
    global _current_proc, _is_speaking, _generation
    print("🛑 Interrupting speech...")
    _generation += 1
    _interrupted.set()

    _drain(_speech_queue)
    _drain(_play_queue, lambda item: _remove(item[0]))

    if _current_proc is not None:
        try:
            _current_proc.terminate()
        except:
            pass

    _is_speaking = False


def _listen_for_interrupt(proc, threshold=INTERRUPT_THRESHOLD):
    """Listen to mic while afplay plays. Stop afplay if user speaks."""
    def callback(indata, frames, time_info, status):
        if not _is_speaking:
            raise sd.CallbackStop()

        volume = np.linalg.norm(indata) / len(indata)
        if volume > threshold:
            print(f"🛑 Interrupt detected (volume: {volume:.4f})")
            interrupt()
            raise sd.CallbackStop()

    try:
        with sd.InputStream(callback=callback, channels=1, samplerate=16000):
            proc.wait()
    except sd.CallbackStop:
        pass
    except Exception as e:
        print(f"⚠️ Interrupt listener error: {e}")


def _synthesize(text, counter):
    """Turn one sentence into a wav and queue it for playback."""
    generation = _generation

    text = text.replace("Remy", "Remi")
    text = clean_text_for_tts(text)

    if not text.strip():
        return

    output_file = str(TTS_MODEL.parent / f"temp_speech_{counter}.wav")
    with wave.open(output_file, "wb") as wav_file:
        load_voice().synthesize_wav(text, wav_file)

    # Sentez sırasında Stop'a basıldıysa çalma
    if generation != _generation:
        _remove(output_file)
        return

    print(f"🔊 Remy: {text}")
    _play_queue.put((output_file, generation))


def _play(output_file, generation):
    """afplay + interrupt listener."""
    global _current_proc, _is_speaking
    try:
        if generation != _generation:
            return
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
        finally:
            _current_proc = None
            _is_speaking = False
    finally:
        _remove(output_file)


def _synth_worker():
    """Pull sentences from the queue and prepare audio ahead of playback."""
    counter = 0
    while True:
        text = _speech_queue.get()
        if text is None:
            _speech_queue.task_done()
            break

        counter += 1
        # Worker ne olursa olsun ölmemeli, yoksa wait_until_done() sonsuza kadar bekler
        try:
            _synthesize(text, counter)
        except Exception as e:
            print(f"⚠️ Speech error: {e}")
            print(f"⚠️ Model path: {MODEL_PATH}, exists: {os.path.exists(MODEL_PATH)}")
        finally:
            _speech_queue.task_done()


def _play_worker():
    while True:
        item = _play_queue.get()
        if item is None:
            _play_queue.task_done()
            break
        try:
            _play(*item)
        except Exception as e:
            print(f"⚠️ Playback error: {e}")
        finally:
            _play_queue.task_done()


threading.Thread(target=_synth_worker, daemon=True).start()
threading.Thread(target=_play_worker, daemon=True).start()


def speak(text):
    """Add text to speech queue."""
    _speech_queue.put(text)


def wait_until_done():
    """Wait until all speech is finished."""
    _speech_queue.join()
    _play_queue.join()


def stop_worker():
    """Stop the worker threads (for shutdown)."""
    _speech_queue.put(None)
    _play_queue.put(None)


if __name__ == "__main__":
    print(f"Model path: {MODEL_PATH}")
    print(f"Model exists: {os.path.exists(MODEL_PATH)}")
    speak("Hello, this is a test. **Bold** text and emoji 😊 should work.")
    wait_until_done()