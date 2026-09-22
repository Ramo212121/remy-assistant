# Remy Development Notes

Daily log of what I learn, build, and debug while creating Remy — a fully local, privacy-first AI voice assistant for macOS.

---

## Day 1 — Ollama Setup and First Model

**Date:** 2025-01-XX
**Duration:** ~3 hours
**Difficulty:** 🟡 Medium

### Goal
Set up Ollama and run the first LLM locally.

### Concepts Learned
- **LLM:** Large Language Model — the brain of the AI
- **Ollama:** A runtime that runs LLMs locally on your machine
- **Model:** A trained AI file (qwen2.5:7b = 7 billion parameters)
- **brew vs pip:** brew installs applications, pip installs Python packages
- **Service:** A program that runs continuously in the background

### What I Did
- Installed Homebrew (`brew install`)
- Installed Ollama (`brew install ollama`)
- Started Ollama service (`brew services start ollama`)
- Pulled qwen2.5:7b model (`ollama pull qwen2.5:7b`)
- Tested the model from terminal

### Problems
- `brew` not recognized → added to PATH
- Mac froze (8GB RAM) → shortened `OLLAMA_KEEP_ALIVE`

### Results
- Turkish: Good
- English: Good
- Memory: Within session
- Speed: A bit slow on 8GB RAM

---

## Day 2 — Python + Ollama Integration

**Date:** 2025-01-XX
**Duration:** ~3 hours
**Difficulty:** 🟢 Easy

### Goal
Control Ollama from Python.

### Concepts Learned
- **venv:** Isolated Python environment
- **`ollama.chat()`:** Sends messages to the model
- **messages list:** Conversation history (memory)
- **system prompt:** Defines Remy's personality
- **role: system/user/assistant:** Who sent the message

### What I Built
- `~/Desktop/MyProjects/remy` project folder
- `venv` setup
- `pip install ollama`
- `remy.py` — chat loop with system prompt and memory

### Results
- Turkish: OK
- English: OK
- Same-session memory: OK
- Cross-session memory: Not yet (fixed in Day 3)

---

## Day 3 — Persistent Memory (SQLite)

**Date:** 2025-01-XX
**Duration:** ~5 hours
**Difficulty:** 🟡 Medium

### Goal
Make Remy remember conversations after restart.

### Concepts Learned

#### 1. What is SQLite?
- File-based, serverless database
- Single `.db` file
- Built into Python (`import sqlite3`)
- Perfect for small/medium projects

#### 2. Connection and Cursor
- `sqlite3.connect(DB_PATH)` → Opens/creates database
- `con.cursor()` → Creates cursor
- `con.commit()` → Saves changes
- `con.close()` → Closes connection

#### 3. Placeholders (`?`)
- Safe way to pass values into SQL
- Prevents SQL Injection
- Always tuple: `("value",)` not `("value")`

#### 4. SQL Commands Used
- `CREATE TABLE IF NOT EXISTS` → Creates table if not exists
- `INSERT INTO ... VALUES (?, ?)` → Adds row
- `INSERT OR REPLACE INTO ...` → Upsert
- `SELECT ... FROM ...` → Reads data
- `ORDER BY id DESC` → Newest first
- `LIMIT ?` → Limits results
- `WHERE key = ?` → Filters

#### 5. Fetch Methods
- `fetchone()` → One result
- `fetchall()` → All results
- `fetchmany(n)` → N results

#### 6. Upsert (`INSERT OR REPLACE`)
- Updates if exists, inserts if not

### What I Built

**File:** `src/memory/database.py`

**Tables:**
- `messages` → id, role, content, timestamp
- `facts` → id, key, value

**Functions:**
- `init_db()` → Creates both tables
- `save_message(role, content)` → Saves a message
- `get_messages(limit=10)` → Last N messages
- `save_fact(key, value)` → Saves/updates fact
- `get_fact(key)` → Returns value or None

**File:** `remy.py` (updated)
- Imports from `src.memory.database`
- Calls `init_db()` on startup
- Loads last 10 messages
- Saves every message

### Problems
1. **ImportError: cannot import name 'get_messages'**
   - Cause: Python cached `.pyc` files
   - Fix: `find . -type d -name "__pycache__" -exec rm -rf {} +`
2. **`tutorial.py` instead of `test_db.py`**
   - Fix: `mv tutorial.py test_db.py`
3. **`tutorial.db` leftover**
   - Fix: `rm tutorial.db`

### Results
- Save/load messages: OK
- Save/load facts: OK
- Remembers after restart: OK
- SQL injection protection: OK

### Key Takeaways
1. SQLite is perfect for local apps
2. Always use placeholders (`?`)
3. Always `commit()`
4. Always `close()`
5. `INSERT OR REPLACE` for upserts
6. Clear `__pycache__` when imports misbehave

---

## Day 4 — Speech Recognition (Ears)

**Date:** 2025-01-XX
**Duration:** ~5 hours
**Difficulty:** 🟠 Hard

### Goal
Make Remy hear the user via speech-to-text (STT).

### Concepts Learned

#### 1. What is STT?cat NOTE.md | grep "## Day"
- STT = Speech-to-Text
- Converts audio into text
- Pipeline: Microphone → Audio file → STT model → Text

#### 2. What is Whisper?
- OpenAI's STT model
- Trained on 680,000 hours of multilingual data
- Supports 99 languages (including Turkish)
- Model sizes: tiny, base, small, medium, large, turbo

#### 3. Groq Whisper API
- Free tier: 2,000 requests/day, 7,200 seconds/hour
- No credit card required
- 216x real-time speed
- No RAM usage (ideal for 8GB Mac)
- Model: `whisper-large-v3-turbo`

#### 4. VAD (Voice Activity Detection)
- Detects speech start/end
- Not used yet

#### 5. Audio Formats
- WAV: ~115 MB/hour, 100% quality
- FLAC: ~60 MB/hour, 100% quality (lossless)
- MP3 128k: ~57 MB/hour, ~75% quality
- OGG 128k: ~57 MB/hour, ~85% quality

Why FLAC? Lossless, ~50% smaller than WAV.

#### 6. Sample Rate and Channels
- Whisper wants: 16 kHz, mono
- Record at 16 kHz mono from the start

### What I Built

**File:** `test_stt.py` (temporary, root directory)

**Flow:**
1. Load `GROQ_API_KEY` from `.env`
2. Create Groq client
3. Record 5 seconds via `sounddevice`
4. Save as FLAC via `soundfile`
5. Send to Groq Whisper
6. Print text

### Libraries Used
- `groq` → Groq API client
- `sounddevice` → Microphone access
- `soundfile` → Write audio to FLAC
- `python-dotenv` → Load `.env`

Install: `pip install groq sounddevice soundfile python-dotenv`

### Problems
1. API key not visible → Groq keys shown once, create new
2. `GROQ_API_KEY` not found → create `.env`
3. `ModuleNotFoundError` → activate venv, install packages
4. Microphone permission → System Settings → Privacy → Microphone

### Results
- Recording (5 sec): OK
- FLAC save: OK
- Groq upload: OK
- Turkish transcription: OK
- English transcription: OK

Example output:
- Recording... (5 seconds)
- Recording finished
- Sending to Groq...
- Text: merhaba ben remy

### Key Takeaways
1. STT is the "ears" of Remy
2. Groq Whisper = free + fast + no RAM usage
3. FLAC is better than WAV
4. Record at 16 kHz mono
5. Always load API keys from `.env`
6. `.env` must be in `.gitignore`
7. Test files stay temporary; real code goes in `src/`

---

## Day 5 — Text-to-Speech (Mouth) + First Voice Conversation

**Date:** 2025-01-XX
**Duration:** ~6 hours
**Difficulty:** 🟠 Hard

### Goal
Make Remy speak the response. Today we add text-to-speech (TTS) so Remy talks back.

### Concepts Learned

#### 1. What is TTS?
- TTS = Text-to-Speech
- Converts text into audio
- Pipeline: Text → TTS model → Audio file → Speaker

#### 2. What is Piper?
- Piper = neural TTS engine by Rhasspy
- Runs locally (no cloud)
- Model sizes: low, medium, high
- high = best quality

#### 3. Piper vs macOS `say`
- Piper: Natural (neural), fast, needs model
- macOS `say`: Robotic, instant, built-in

#### 4. Audio Playback on macOS
- `afplay`: Native, but conflicts with `sounddevice`
- `say`: Stable, but robotic
- `sd.play()`: Python API, but crashes
- Solution: `afplay` + `time.sleep(0.5)`

#### 5. CoreAudio Conflict
- `sounddevice` (mic) + `afplay` (speaker) → conflict
- AirPods makes it worse
- Fix: `time.sleep(0.5)` or `sudo killall coreaudiod`

#### 6. Text Cleaning for TTS
- LLM output contains markdown
- Piper reads them letter by letter
- Fix: Regex to remove markdown

### What I Built

**File:** `src/mouth/speaker.py`

**Functions:**
- `clean_text_for_tts(text)` → Removes markdown, symbols
- `speak(text)` → TTS + playback

**File:** `remy.py` (updated)
- Full voice loop: listen → think → speak

### Libraries Used
- `piper-tts` → TTS engine
- `subprocess` → Call `piper` + `afplay`
- `re` → Text cleaning

### Problems
1. `afplay` + `sounddevice` conflict → `time.sleep(0.5)`
2. AirPods makes it worse → use Mac speakers
3. `sd.play()` crashes → use `afplay`
4. Piper reads markdown → `clean_text_for_tts()`
5. `KeyboardInterrupt` traceback → `try/except`

### Results
- Piper TTS: Natural voice
- `afplay`: OK
- Text cleaning: OK
- Full voice loop: OK
- No crash: OK

### Key Takeaways
1. Piper = natural, local, free TTS
2. `high` model > `low` model
3. `afplay` + `time.sleep` avoids conflict
4. Clean text before TTS
5. `try/except KeyboardInterrupt` for clean exit
6. Full voice loop = listen + think + speak

---

İşte kanka, **Gün 6 ve Gün 7 notları.** `NOTE.md`'nin en altına ekle. 🔥

---

```markdown
---

## Day 6 — Speed Optimization (Streaming)

**Date:** 2025-01-XX
**Duration:** ~5 hours
**Difficulty:** 🟠 Hard

### Goal
Make Remy respond faster. Until now, the user waited 5-10 seconds for a reply. Today we add **streaming** so the first words arrive in 1-2 seconds.

### Concepts Learned

#### 1. What is Streaming?
- LLM generates text **token by token** instead of all at once
- Each token is a word or word-piece
- **Without streaming:** Wait for full reply → 5-10 sec
- **With streaming:** First sentence ready → 1-2 sec

#### 2. Ollama Streaming
- `ollama.chat(..., stream=True)` returns a generator
- Each `chunk` contains one token
- `chunk['message']['content']` is the token

#### 3. Sentence Buffering
- Accumulate tokens in a `buffer`
- When a sentence-ending punctuation appears (`. `, `! `, `? `), send buffer to TTS
- **Minimum length check** (`len > 30`) prevents splitting short phrases like `"I'm"`

#### 4. Threading
- `threading.Thread` runs TTS in background
- LLM keeps generating while TTS plays
- `t.join()` waits for all threads to finish

### What I Built

**File:** `remy.py` (updated)

**Streaming logic:**
```python
stream = ollama.chat(model='qwen2.5:7b', messages=messages, stream=True)

buffer = ""
reply = ""

for chunk in stream:
    token = chunk['message']['content']
    buffer += token
    reply += token
    if len(buffer.strip()) > 30 and any(p in buffer for p in ['. ', '! ', '? ']):
        sentence = buffer.strip()
        speak(sentence)
        buffer = ""

if buffer.strip():
    speak(buffer.strip())
```

### Problems
1. **Sentences split incorrectly** (`"I'm"` → `"I"` + `"'m"`)
   - Cause: `len > 15` too short
   - Fix: `len > 30`
2. **`afplay` crashes** (`AudioQueueStart failed`)
   - Cause: Multiple `afplay` running at once
   - Fix: Speech queue (see Day 7)
3. **Remy hears itself** (echo)
   - Cause: Mic still active during TTS
   - Fix: `set_speaking()` flag (see Day 7)

### Results
- First sound: 1-2 seconds (was 5-10)
- Total response: 3-5 seconds
- Streaming: working
- Sentence splitting: fixed

### Key Takeaways
1. Streaming makes LLM feel instant
2. Sentence buffering groups tokens into speakable chunks
3. `len > 30` prevents splitting short phrases
4. Threading lets TTS run in background

---

## Day 7 — Echo, Sentence Splitting, and Crash Fixes

**Date:** 2025-01-XX
**Duration:** ~6 hours
**Difficulty:** 🟠 Hard

### Goal
Fix three stability issues:
1. **Echo** — Remy hears its own voice and replies to itself
2. **Sentence splitting** — short phrases broken mid-word
3. **`afplay` crash** — `AudioQueueStart failed`

### Concepts Learned

#### 1. Echo Problem
- Remy speaks → microphone picks up the sound → Whisper transcribes it → Remy replies to itself
- **Fix:** Pause microphone while Remy speaks

#### 2. `set_speaking` Flag (Better Than stop/start)
- **Old way:** `_stream.stop()` / `_stream.start()`
- **Problem:** macOS CoreAudio crashes (`PaMacCore Error -9986`) when restarting stream
- **New way:** Global flag `is_speaking`
  - `listen()` returns `""` if `is_speaking` is True
  - Stream never stops → no crash

#### 3. Buffer Clearing
- Even with `set_speaking`, stale audio stays in mic buffer
- **Fix:** `clear_buffer()` reads and discards 1 second of audio before resuming

#### 4. Speech Queue
- **Problem:** Multiple `afplay` processes conflict
- **Fix:** `queue.Queue` + worker thread
  - `speak()` adds text to queue
  - Worker pulls one at a time, plays it, waits
  - **Guarantees:** only one `afplay` at a time

#### 5. `wait_until_done()`
- `_speech_queue.join()` waits until queue is empty
- **Use:** After `speak()`, before `set_speaking(False)`
- **Ensures:** TTS fully finished before mic reopens

#### 6. Double Print Fix
- **Problem:** `remy.py` and `speaker.py` both printed `🔊 Remy: ...`
- **Fix:** Remove `print` from `remy.py`, keep only in `speaker.py`

### What I Built

**File:** `src/ears/listener.py` (updated)

**New functions:**
```python
is_speaking = False

def set_speaking(value):
    global is_speaking
    is_speaking = value

def clear_buffer():
    global _stream
    if _stream is not None:
        try:
            _stream.read(16000)
        except:
            pass

def listen(duration=DURATION, language="en"):
    global is_speaking
    if is_speaking:
        time.sleep(0.5)
        return ""
    filename = record_audio(duration=duration)
    text = transcribe(filename)
    return text
```

**File:** `src/mouth/speaker.py` (updated)

**Queue + worker:**
```python
_speech_queue = queue.Queue()

def _speech_worker():
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
        subprocess.run(["piper", "-m", MODEL_PATH, "-f", output_file],
                       input=text.encode("utf-8"), check=True)
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
    _speech_queue.put(text)

def wait_until_done():
    _speech_queue.join()
```

**File:** `remy.py` (updated)

**Main loop:**
```python
set_speaking(True)   # Remy is about to speak
response = ollama.chat(model='qwen2.5:7b', messages=messages)
reply = response['message']['content']
speak(reply)
wait_until_done()    # Wait for TTS to finish
clear_buffer()       # Clear mic buffer
set_speaking(False)  # Mic can listen again
```

### Problems Solved

| Problem | Cause | Fix |
|---------|-------|-----|
| Echo | Mic active during TTS | `set_speaking(True)` |
| Stream crash | `stop()` / `start()` loop | Never stop stream, use flag |
| Stale audio | Buffer holds old sound | `clear_buffer()` |
| `afplay` conflict | Multiple processes | Speech queue |
| Double print | Both files print | Remove from `remy.py` |

### Results
- Echo: **fixed**
- Sentence splitting: **fixed**
- `afplay` crash: **fixed**
- Stream crash: **fixed**
- Double print: **fixed**
- Program: **stable**

### Key Takeaways
1. Never `stop()` / `start()` a `sounddevice` stream on macOS
2. Use a **flag** to ignore microphone instead
3. **Speech queue** prevents `afplay` conflicts
4. **`wait_until_done()`** ensures TTS finishes before mic reopens
5. **`clear_buffer()`** removes stale audio
6. One `print` per message — pick a layer

---

---

## Day 8 — Speaker Recognition (Only My Voice)

**Date:** 2025-01-XX
**Duration:** ~6 hours
**Difficulty:** 🟠 Hard

### Goal
Make Remy respond **only to my voice**. Ignore other people, TV, background noise. This is called **Speaker Verification** — the assistant knows who is talking.

### Concepts Learned

#### 1. What is Speaker Recognition?
- **Speaker Recognition** = identifying who is speaking
- Two types:
  - **Identification:** Who is this? (1 of N speakers)
  - **Verification:** Is this the enrolled user? (yes/no)
- We use **Verification** — accept or reject

#### 2. Voice Embedding
- A **voice embedding** is a 256-dimensional vector
- It represents the **unique characteristics** of a voice
- Same speaker → similar embeddings
- Different speaker → different embeddings
- **Model:** Resemblyzer (`VoiceEncoder`)

#### 3. Enrollment
- **Enrollment** = recording the user's voice to create their profile
- Record 30-60 seconds of natural speech
- Extract embedding → save to `voice_profile.npy`
- Done **once** per user

#### 4. Verification (Similarity Check)
- For each new audio:
  1. Extract embedding
  2. Compare with stored embedding using **cosine similarity**
  3. If similarity > threshold → accept
  4. Else → reject
- **Cosine similarity** ranges from -1 to 1 (1 = identical)

#### 5. Threshold Tuning
- **Threshold** decides who is accepted
- Too high → rejects the real user (false negative)
- Too low → accepts others (false positive)
- **Test values:**
  - `0.75` → too strict (real user rejected)
  - `0.65` → good balance
  - `0.55` → too loose

#### 6. Resemblyzer
- Open-source speaker embedding model
- Runs locally (no cloud)
- **Requires:** `torch`, `librosa`, `webrtcvad`
- **Install issue:** `webrtcvad` uses deprecated `pkg_resources`
- **Fix:** `pip install "setuptools<82"`

### What I Built

**File:** `enroll.py` (new)

**Purpose:** Record voice once and save profile.

**Flow:**
1. Wait 3 seconds (prepare)
2. Record 30 seconds of voice
3. Extract embedding using `VoiceEncoder`
4. Save to `voice_profile.npy`

**Code:**
```python
import sounddevice as sd
import soundfile as sf
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path

DURATION = 30
SAMPLE_RATE = 16000
FILENAME = "my_voice.wav"
PROFILE = "voice_profile.npy"

def record_voice():
    print(f"🎤 Recording for {DURATION} seconds...")
    import time
    time.sleep(3)
    recording = sd.rec(int(DURATION * SAMPLE_RATE),
                       samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    sf.write(FILENAME, recording, SAMPLE_RATE)

def create_profile():
    wav = preprocess_wav(Path(FILENAME))
    encoder = VoiceEncoder()
    embedding = encoder.embed_utterance(wav)
    np.save(PROFILE, embedding)
```





