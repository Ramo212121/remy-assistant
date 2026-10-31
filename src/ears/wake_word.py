"""'Hey Remy' detection. Short bursts of speech are transcribed on this machine, nothing leaves it."""
import collections
import re

import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_MS / 1000)
PRE_ROLL_FRAMES = 10         # kelimenin başı kırpılmasın
END_SILENCE_FRAMES = 13      # ~0.4 sn sessizlik parçayı bitirir
MIN_SPEECH_FRAMES = 8        # ~0.25 sn'den kısası gürültüdür
MAX_PHRASE_FRAMES = 100      # ~3 sn'den uzunu uyandırma cümlesi değildir
MAX_NO_SPEECH_PROB = 0.6

# Whisper "Remy" adını farklı yazabiliyor
WAKE_PATTERN = re.compile(
    r"\b(hey|hay|hi|heh)\s+(remy|remi|remmy|remmi|remie|reme|rémy|ramy|rami|romy|remy's)\b"
)

# Hızlı model "hey ..." duyup adı seçemezse büyük model bir daha dinler
MAYBE_WAKE_PATTERN = re.compile(r"\b(hey|hay|hi|heh)\b")

_fast_model = None
_accurate_model = None


def load_model():
    """Load the local speech models (downloaded once, about 75 MB and 460 MB)."""
    global _fast_model, _accurate_model
    if _fast_model is None:
        _fast_model = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=4)
    if _accurate_model is None:
        _accurate_model = WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=4)


def _transcribe(model, audio):
    segments, _ = model.transcribe(
        audio,
        language="en",
        beam_size=1,
        without_timestamps=True,
        condition_on_previous_text=False,
        hotwords="Remy",
    )
    text = " ".join(s.text for s in segments if s.no_speech_prob < MAX_NO_SPEECH_PROB)
    return " ".join(re.sub(r"[^\w\s']", " ", text.lower()).split())


def is_wake_phrase(audio):
    """audio: mono float32 at 16 kHz. True if it contains 'hey remy'."""
    load_model()
    text = _transcribe(_fast_model, audio)
    print(f"👂 Heard: {text}")
    if WAKE_PATTERN.search(text):
        return True
    if not MAYBE_WAKE_PATTERN.search(text):
        return False

    text = _transcribe(_accurate_model, audio)
    print(f"👂 Heard (second pass): {text}")
    return WAKE_PATTERN.search(text) is not None


def wait_for_wake_word(timeout=30, should_stop=lambda: False):
    """Block until 'hey remy' is heard, timeout passes, or should_stop() is true."""
    load_model()
    vad = webrtcvad.Vad(2)
    print("💤 Waiting for wake word...")

    pre_roll = collections.deque(maxlen=PRE_ROLL_FRAMES)
    phrase = []
    speech_frames = 0
    silent_frames = 0
    max_frames = int(timeout * 1000 / FRAME_MS)

    with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, dtype="float32", blocksize=FRAME_SIZE) as stream:
        for _ in range(max_frames):
            if should_stop():
                return False

            frame, overflowed = stream.read(FRAME_SIZE)
            samples = frame[:, 0].copy()
            is_speech = vad.is_speech((samples * 32767).astype(np.int16).tobytes(), SAMPLE_RATE)

            if not phrase:
                if is_speech:
                    phrase = list(pre_roll) + [samples]
                    speech_frames, silent_frames = 1, 0
                else:
                    pre_roll.append(samples)
                continue

            phrase.append(samples)
            speech_frames += is_speech
            silent_frames = 0 if is_speech else silent_frames + 1

            if silent_frames < END_SILENCE_FRAMES and len(phrase) < MAX_PHRASE_FRAMES:
                continue

            # Uzun konuşmayı boşuna çözümleme, sadece kısa parçalar aday
            if speech_frames >= MIN_SPEECH_FRAMES and len(phrase) < MAX_PHRASE_FRAMES:
                # Ses doğrulaması burada yok: 1 sn'lik klipte sahibini de reddediyor.
                # Asıl kapı, uyandıktan sonraki komutta listen() içinde.
                if is_wake_phrase(np.concatenate(phrase)):
                    print("✅ Wake word confirmed")
                    return True

            phrase = []
            pre_roll.clear()

    return False


if __name__ == "__main__":
    result = wait_for_wake_word(timeout=30)
    print(f"Detected: {result}")
