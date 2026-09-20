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

#### 1. What is STT?
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

## Day 6 — (Coming Soon)

### Planned
- Speed optimization (faster model, Groq, streaming)
- Barge-in (interrupt Remy while speaking)
- Tool calling