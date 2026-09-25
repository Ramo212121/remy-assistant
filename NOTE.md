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






```markdown
---

## Day 9 — Barge-in (Interrupt While Speaking)

**Date:** 2025-01-XX
**Duration:** ~6 hours
**Difficulty:** 🔴 Hard

### Goal
When Remy is speaking and the user starts talking, Remy should **stop immediately** and listen. Just like Alexa/Google Home.

### Concepts Learned

#### 1. What is Barge-in?
- **Barge-in** = interrupting the assistant while it speaks
- Without it: user waits for Remy to finish
- With it: Remy stops instantly when user speaks
- Real assistants (Alexa, Siri) support this

#### 2. Volume Detection
- Read mic volume continuously via `sounddevice.InputStream`
- **RMS formula:** `volume = np.linalg.norm(indata) / len(indata)`
- Result is a small float (0.001 – 0.2)
- `callback()` fires every ~0.1 seconds

#### 3. Threshold Tuning
- **Interrupt threshold** decides when to stop `afplay`
- Values observed:
  - Silent room: `0.001 – 0.005`
  - Remy's own voice (from speaker to mic): `0.05 – 0.15`
  - User speaking directly: `0.15 – 0.25`
- **Problem:** Remy's own voice and user's voice overlap
- **Fix:** Set threshold to `0.25` so only loud user speech interrupts

#### 4. Stopping `afplay`
- `afplay` runs as a subprocess (`Popen`)
- `proc.terminate()` sends SIGTERM to stop playback
- `sd.CallbackStop` exits the mic stream cleanly
- `proc.wait(timeout=30)` prevents hangs

#### 5. Speaker Recognition Threshold
- Voice similarity between user and enrolled profile
- Values observed:
  - User speaking clearly: `0.65 – 0.85`
  - User speaking short words: `0.55 – 0.65`
  - Other people: `0.45 – 0.60`
- **Problem:** Short utterances give low similarity
- **Fix:** Lower threshold from `0.65` to `0.55`

#### 6. Echo Problem During Barge-in
- Remy's own voice reaches the microphone
- Causes false interrupts (Remy interrupts itself)
- Causes Remy to transcribe its own speech and reply to itself
- **Fix:** Raise `INTERRUPT_THRESHOLD` to `0.25` so only real user speech triggers

### What I Built

**File:** `src/mouth/speaker.py` (updated)

**New constant:**
```python
INTERRUPT_THRESHOLD = 0.25
```

**New imports:**
```python
import numpy as np
import sounddevice as sd
```

**New function:**
```python
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
```

**Updated `_speech_worker`:**
```python
try:
    proc = subprocess.Popen(["afplay", output_file])
    _listen_for_interrupt(proc)
    proc.wait(timeout=30)
except subprocess.TimeoutExpired:
    print("⚠️ afplay timeout")
    proc.kill()
    proc.wait()
```

**File:** `src/ears/listener.py` (updated)

**Threshold changed:**
```python
SIMILARITY_THRESHOLD = 0.55   # was 0.65
```

### Problems Solved

| Problem | Cause | Fix |
|---------|-------|-----|
| Remy interrupts itself | Own voice reaches mic | Threshold `0.25` |
| "Voice ignoring" errors | Short utterances give low similarity | Threshold `0.55` |
| `afplay` hangs | No timeout | `proc.wait(timeout=30)` |
| Mic stream stays open | Callback doesn't stop | `sd.CallbackStop` |

### Results
- Barge-in: **working**
- Remy stops when user speaks: **yes**
- Remy interrupts itself: **no**
- Speaker recognition: **stable** (0.68 typical)
- Threshold values: interrupt `0.25`, similarity `0.55`

### Key Takeaways
1. **Barge-in** makes the assistant feel responsive
2. **Volume threshold** must separate user voice from own voice
3. **RMS** is a simple, effective volume metric
4. **`proc.terminate()`** stops `afplay` cleanly
5. **`sd.CallbackStop`** exits the stream gracefully
6. **Speaker recognition threshold** needs tuning for short phrases
7. **Echo** is the main enemy of barge-in

---
```

---



```
---

## Day 10 — Tool Calling (Time, Date, Calculate)

**Date:** 2025-01-XX
**Duration:** ~6 hours
**Difficulty:** 🟠 Hard

### Goal
Make Remy use real tools. Until now, Remy only talked. Now it can call Python functions to get real data.

### Concepts Learned

#### 1. What is Tool Calling?
- LLM decides **when** to call a function
- Python **executes** the function
- LLM **explains** the result
- Flow:
  1. User: "What time is it?"
  2. LLM: "I should call `get_time()`"
  3. Python: `get_time()` → `"23:55"`
  4. LLM: "It's 23:55."

#### 2. JSON Schema for Tools
- Each tool described as JSON
- Fields:
  - `type`: "function"
  - `function.name`: function name
  - `function.description`: what it does
  - `function.parameters`: input schema
- Model reads this to decide which tool to call

#### 3. Ollama `tools` Parameter
- `ollama.chat(..., tools=TOOLS)` enables tool calling
- Response contains `tool_calls` if model wants to call a tool
- `tool_calls` = list of `ToolCall` objects
- Each has `function.name` and `function.arguments`

#### 4. Tool Call Loop
1. Send user message + tools to LLM
2. If `tool_calls` present:
   - Execute each tool
   - Append `{'role': 'tool', 'content': result}` to messages
   - Send again to LLM
3. LLM produces final text response

#### 5. Arguments Handling
- Arguments come as a dict: `{'expression': '25 * 4'}`
- Access with `args.get('expression', '')`
- Empty arguments for no-param tools like `get_time`

### What I Built

**File:** `src/hands/tools.py` (new)

**Functions:**
```python
from datetime import datetime

def get_time():
    now = datetime.now()
    return now.strftime("%H:%M")

def get_date():
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y")

def calculate(expression):
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"
```

**Tool definitions:**
```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": "Get today's date",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Calculate a math expression like '2 + 2'",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]
```

**File:** `remy.py` (updated)

**Handler:**
```python
def handle_tool_calls(response):
    tool_calls = response['message'].get('tool_calls', [])
    results = []
    for call in tool_calls:
        name = call.function.name
        args = call.function.arguments
        if name == 'get_time':
            result = get_time()
        elif name == 'get_date':
            result = get_date()
        elif name == 'calculate':
            result = calculate(args.get('expression', ''))
        else:
            result = "Unknown tool"
        print(f"🛠️ Tool: {name} → {result}")
        results.append({'role': 'tool', 'content': result})
    return results
```

**Main loop:**
```python
response = ollama.chat(model='qwen2.5:7b', messages=messages, tools=TOOLS)

if response['message'].get('tool_calls'):
    tool_results = handle_tool_calls(response)
    messages.append(response['message'])
    messages.extend(tool_results)
    response = ollama.chat(model='qwen2.5:7b', messages=messages, tools=TOOLS)

reply = response['message']['content']
```

### Problems
1. **`ToolCall` object, not dict**
   - Cause: Ollama returns objects, not raw dicts
   - Fix: Use `.function.name` and `.function.arguments`
2. **Empty `content` when tool called**
   - Normal: model returns only `tool_calls`, no text
   - Fix: After tool execution, send back to get final text

### Results
- `get_time()`: OK (`23:55`)
- `get_date()`: OK (`Friday, September 25, 2026`)
- `calculate('25 * 4')`: OK (`100`)
- Ollama `tool_calls`: OK
- Full loop (tool → result → reply): OK

### Key Takeaways
1. **Tool calling** lets LLM use real functions
2. **JSON schema** describes each tool
3. **`tools=TOOLS`** enables tool calling in Ollama
4. **`tool_calls`** in response means model wants a function
5. **Loop:** call → execute → append → re-call
6. **`ToolCall`** object uses `.function.name`, not dict keys
7. **Empty content** with tool call is normal
```

---











İşte kanka, **Gün 11 notları.** `NOTE.md`'nin en altına ekle. 🔥

```markdown
---

## Day 11 — Reminder System (SQLite + macOS Notifications)

**Date:** 2025-01-XX
**Duration:** ~6 hours
**Difficulty:** 🟡 Medium

### Goal
Make Remy set reminders. User says "remind me in 2 minutes to drink water" and gets a macOS notification at the right time.

### Concepts Learned

#### 1. Reminder Architecture
- **3 parts:**
  1. SQLite table (`reminders`) — stores reminders
  2. Tool (`set_reminder`) — LLM calls it to add reminders
  3. Background thread — checks every 30 seconds, sends notifications

#### 2. SQLite `reminders` Table
- Columns: `id`, `remind_at`, `content`, `done`
- `remind_at` = ISO datetime string (`2025-09-26T14:00:00`)
- `done` = 0 (pending) or 1 (done)
- `init_db()` creates it with `CREATE TABLE IF NOT EXISTS`

#### 3. Reminder Functions
- `save_reminder(remind_at, content)` — inserts new reminder
- `get_pending_reminders()` — returns `WHERE done = 0`
- `mark_done(id)` — sets `done = 1`

#### 4. Tool Calling for Reminders
- Tool definition in `TOOLS` list (JSON schema)
- Parameters: `remind_at` (ISO string), `content` (string)
- Both required
- LLM decides when to call it

#### 5. Background Check Loop
- `threading.Thread(daemon=True)` — runs in background
- `while True:` — infinite loop
- Every 30 seconds:
  - Get pending reminders
  - Compare `remind_at` with `now`
  - If due → notify + mark done
- `time.sleep(30)` — wait before next check

#### 6. macOS Notifications via `osascript`
- Command: `osascript -e 'display notification "..." with title "..."'`
- `subprocess.run()` runs it
- Notification appears in macOS Notification Center
- Works with default notification settings

#### 7. ISO Datetime Format
- `datetime.now().isoformat()` → `'2025-09-26T23:55:12.345678'`
- `datetime.fromisoformat(str)` → parses it back
- **Why ISO?** Sortable, standard, human-readable

### What I Built

**File:** `src/memory/database.py` (updated)

**New table:**
```python
cur.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY,
        remind_at TEXT,
        content TEXT,
        done INTEGER DEFAULT 0
    )
""")
```

**New functions:**
```python
def save_reminder(remind_at, content):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO reminders (remind_at, content) VALUES (?, ?)",
        (remind_at, content)
    )
    con.commit()
    con.close()

def get_pending_reminders():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id, remind_at, content FROM reminders WHERE done = 0")
    rows = cur.fetchall()
    con.close()
    return rows

def mark_done(reminder_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))
    con.commit()
    con.close()
```

**File:** `src/hands/reminder.py` (new)

```python
import threading
import time
import subprocess
from datetime import datetime
from src.memory.database import get_pending_reminders, mark_done


def send_notification(title, message):
    subprocess.run([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}"'
    ])


def check_loop():
    while True:
        now = datetime.now()
        for rid, remind_at, content in get_pending_reminders():
            try:
                if datetime.fromisoformat(remind_at) <= now:
                    print(f"🔔 Reminder: {content}")
                    send_notification("Remy Reminder", content)
                    mark_done(rid)
            except Exception as e:
                print(f"⚠️ Reminder error: {e}")
        time.sleep(30)


def start_reminder_checker():
    threading.Thread(target=check_loop, daemon=True).start()
    print("⏰ Reminder checker started")
```

**File:** `src/hands/tools.py` (updated)

**New tool:**
```python
def set_reminder(remind_at, content):
    save_reminder(remind_at, content)
    return f"Reminder set for {remind_at}: {content}"
```

**JSON schema:**
```python
{
    "type": "function",
    "function": {
        "name": "set_reminder",
        "description": "Set a reminder at a specific time in ISO format",
        "parameters": {
            "type": "object",
            "properties": {
                "remind_at": {"type": "string", "description": "ISO datetime"},
                "content": {"type": "string", "description": "What to remind about"}
            },
            "required": ["remind_at", "content"]
        }
    }
}
```

**File:** `remy.py` (updated)

- Imports `set_reminder`, `start_reminder_checker`
- Calls `start_reminder_checker()` after `init_db()`
- Tool handler handles `set_reminder`

### Problems
1. **`datetime.fromisoformat` fails on invalid strings**
   - Cause: LLM may send wrong format
   - Fix: `try/except` around parsing
2. **Thread crashes silently**
   - Cause: `daemon=True` threads die with main process
   - OK: That's what we want
3. **Notification doesn't appear**
   - Cause: macOS notification settings / Do Not Disturb
   - Fix: Check System Settings → Notifications

### Results
- `set_reminder` tool: OK
- SQLite save: OK
- Background checker: OK (every 30 sec)
- macOS notification: OK
- 2-minute reminder: **works**
- No crashes: OK

### Key Takeaways
1. **Reminders need 3 parts:** storage + tool + background loop
2. **SQLite + ISO datetime** works well
3. **`threading.Thread(daemon=True)`** for background tasks
4. **`osascript`** sends macOS notifications
5. **`time.sleep(30)`** keeps CPU usage low
6. **`try/except`** prevents crashes from bad data
7. **Tool calling** makes reminders voice-controlled


İşte kanka, **Gün 12 notları.** `NOTE.md`'nin en altına ekle. 🔥

```markdown
---

## Day 12 — App Control + PDF Reading

**Date:** 2025-01-XX
**Duration:** ~6 hours
**Difficulty:** 🟡 Medium

### Goal
Make Remy open apps and read PDFs via voice commands:
- "Open Safari" → Safari launches
- "Read test.pdf" → Remy reads the PDF content

### Concepts Learned

#### 1. macOS App Control via `subprocess`
- `subprocess.run(["open", "-a", "AppName"])` launches an app
- `-a` flag = "application by name"
- Works for any installed app: Safari, Spotify, VS Code
- `check=True` raises error if launch fails

#### 2. PDF Reading with PyMuPDF
- `pip install pymupdf`
- Import: `import fitz` (or `import pymupdf` in newer versions)
- `fitz.open(path)` opens a PDF
- `page.get_text()` extracts text from one page
- Loop over pages → concatenate text
- `doc.close()` releases the file

#### 3. Short Path Support
- **Problem:** LLM shouldn't guess full paths
- **Fix:** If input doesn't start with `/`, prepend `PROJECT_DIR`
- Example: `"test.pdf"` → `~/Desktop/MyProjects/remy/test.pdf`
- **Benefit:** User says "read test.pdf", no full path needed

#### 4. Tool Description Tuning
- LLM chooses tools based on `description`
- Vague description → wrong tool calls (e.g., "Read test PDF" → `open_app("Safari")`)
- **Fix:** Add explicit examples and constraints
  - `"Use only the filename (e.g. 'test.pdf'), not a full path"`
  - `"The PDF must be in the Remy project folder"`

#### 5. System Prompt Rules
- Even better than tool descriptions for edge cases
- Add numbered rules:
  - `"read PDF" → use read_pdf with filename. Do NOT open Safari.`
  - `"open <app>" → use open_app`
- LLM follows rules more reliably

#### 6. Creating Test PDFs on macOS
- `cupsfilter input.txt > output.pdf` converts text to PDF
- Built into macOS, no extra install
- Useful for testing

#### 7. `fitz` Deprecation Warning
- `fitz` API is deprecated in newer PyMuPDF versions
- Use `import pymupdf` instead
- Same functions, new name

### What I Built

**File:** `src/hands/tools.py` (updated)

**New imports:**
```python
import os
import fitz
PROJECT_DIR = os.path.expanduser("~/Desktop/MyProjects/remy")
```

**New functions:**
```python
def open_app(app_name):
    try:
        subprocess.run(["open", "-a", app_name], check=True)
        return f"Opened {app_name}"
    except Exception as e:
        return f"Error: {e}"

def read_pdf(file_path):
    if not file_path.startswith("/"):
        file_path = os.path.join(PROJECT_DIR, file_path)
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text[:2000]
    except Exception as e:
        return f"Error: {e}"
```

**New tool definitions:**
```python
{
    "type": "function",
    "function": {
        "name": "open_app",
        "description": "Open a macOS application by name",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "App name"}
            },
            "required": ["app_name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "read_pdf",
        "description": "Read text from a PDF file. Use only the filename (e.g. 'test.pdf'), not a full path. The PDF must be in the Remy project folder.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "PDF filename"}
            },
            "required": ["file_path"]
        }
    }
}
```

**File:** `remy.py` (updated)

- Imported `open_app`, `read_pdf`
- Added rules to `SYSTEM_PROMPT`:
```
IMPORTANT RULES:
- "read PDF" → use read_pdf with filename (e.g. "test.pdf"). Do NOT open Safari.
- "open <app>" → use open_app tool.
- time/date → get_time / get_date.
- math → calculate.
- reminder → set_reminder.
```
- Added tool handler cases:
```python
elif name == 'open_app':
    result = open_app(args.get('app_name', ''))
elif name == 'read_pdf':
    result = read_pdf(args.get('file_path', ''))
```

### Problems
1. **Wrong tool called** ("Read test PDF" → `open_app("Safari")`)
   - Cause: Vague `read_pdf` description
   - Fix: Explicit description + system prompt rules
2. **PDF not found** (`/path/to/your/test.pdf`)
   - Cause: LLM guessed a fake path
   - Fix: Short path support + description says "filename only"
3. **Multiple tool calls with wrong names** (`test.pdf`, `text.pdf`)
   - Cause: LLM unsure, tries variations
   - Fix: PDF file actually exists → success
4. **`fitz` deprecation warning**
   - Cause: PyMuPDF renamed `fitz` to `pymupdf`
   - Fix: Ignore warning (works fine) or use `import pymupdf`

### Results
- `open_app("Safari")`: OK
- `open_app("Spotify")`: OK
- `read_pdf("test.pdf")`: OK (after creating the file)
- Short path resolution: OK
- Tool description tuning: OK
- System prompt rules: OK
- Total tools: **6**

### Key Takeaways
1. **`subprocess.run(["open", "-a", "App"])`** opens macOS apps
2. **PyMuPDF** reads PDFs in 5 lines of code
3. **Short path support** lets user say "test.pdf" not full path
4. **Tool descriptions** must be explicit — LLM follows them literally
5. **System prompt rules** override LLM confusion
6. **`cupsfilter`** creates test PDFs on macOS
7. **`fitz` vs `pymupdf`** — same library, new name

---
```

---










