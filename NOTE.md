# Remy Development Notes

Daily log of what I learn, build, and debug while creating Remy — a fully local, privacy-first AI voice assistant for macOS.

---

## Day 1 — Ollama Setup and First Model

**Date:** 2025-01-XX
**Duration:** ~3 hours
**Difficulty:** 🟡 Medium

### 🎯 Goal
Set up Ollama and run the first LLM locally.

### 📖 Concepts Learned
- **LLM:** Large Language Model — the brain of the AI
- **Ollama:** A runtime that runs LLMs locally on your machine
- **Model:** A trained AI file (qwen2.5:7b = 7 billion parameters)
- **brew vs pip:** brew installs applications, pip installs Python packages
- **Service:** A program that runs continuously in the background

### 🛠️ What I Did
- Installed Homebrew (`brew install`)
- Installed Ollama (`brew install ollama`)
- Started Ollama service (`brew services start ollama`)
- Pulled qwen2.5:7b model (`ollama pull qwen2.5:7b`)
- Tested the model from terminal

### 🐛 Problems
- `brew` not recognized → added to PATH
- Mac froze (8GB RAM) → shortened `OLLAMA_KEEP_ALIVE`

### ✅ Results
- Turkish: ✅ Good
- English: ✅ Good
- Memory: ✅ Within session
- Speed: ⚠️ A bit slow on 8GB RAM

---

## Day 2 — Python + Ollama Integration

**Date:** 2025-01-XX
**Duration:** ~3 hours
**Difficulty:** 🟢 Easy

### 🎯 Goal
Control Ollama from Python.

### 📖 Concepts Learned
- **venv:** Isolated Python environment
- **`ollama.chat()`:** Sends messages to the model
- **messages list:** Conversation history (memory)
- **system prompt:** Defines Remy's personality
- **role: system/user/assistant:** Who sent the message

### 🛠️ What I Built
- `~/Desktop/MyProjects/remy` project folder
- `venv` setup
- `pip install ollama`
- `remy.py` — chat loop with system prompt and memory

### ✅ Results
- Turkish: ✅
- English: ✅
- Same-session memory: ✅
- Cross-session memory: ❌ (fixed in Day 3)

---

## Day 3 — Persistent Memory (SQLite)

**Date:** 2025-01-XX
**Duration:** ~5 hours
**Difficulty:** 🟡 Medium

### 🎯 Goal
Make Remy remember conversations after restart.

### 📖 Concepts Learned

#### 1. What is SQLite?
- File-based, serverless database
- Single `.db` file
- Built into Python (`import sqlite3`)
- Perfect for small/medium projects

#### 2. Connection & Cursor
- `sqlite3.connect(DB_PATH)` → Opens/creates database
- `con.cursor()` → Creates cursor
- `con.commit()` → Saves changes
- `con.close()` → Closes connection

#### 3. Placeholders (`?`)
- Safe way to pass values into SQL
- Prevents **SQL Injection**
- Always tuple: `("value",)` not `("value")`

#### 4. SQL Commands Used
| Command | Purpose |
|---------|---------|
| `CREATE TABLE IF NOT EXISTS` | Creates table if not exists |
| `INSERT INTO ... VALUES (?, ?)` | Adds row |
| `INSERT OR REPLACE INTO ...` | Upsert |
| `SELECT ... FROM ...` | Reads data |
| `ORDER BY id DESC` | Newest first |
| `LIMIT ?` | Limits results |
| `WHERE key = ?` | Filters |

#### 5. Fetch Methods
- `fetchone()` → One result
- `fetchall()` → All results
- `fetchmany(n)` → N results

#### 6. Upsert (`INSERT OR REPLACE`)
- Updates if exists, inserts if not

### 🛠️ What I Built

**File:** `src/memory/database.py`

**Tables:**
- `messages` → id, role, content, timestamp
- `facts` → id, key, value

**Functions:**
| Function | Purpose |
|----------|---------|
| `init_db()` | Creates both tables |
| `save_message(role, content)` | Saves a message |
| `get_messages(limit=10)` | Last N messages |
| `save_fact(key, value)` | Saves/updates fact |
| `get_fact(key)` | Returns value or None |

**File:** `remy.py` (updated)
- Imports from `src.memory.database`
- Calls `init_db()` on startup
- Loads last 10 messages
- Saves every message

### 🐛 Problems
1. **`ImportError: cannot import name 'get_messages'`**
   - Cause: Python cached `.pyc` files
   - Fix: `find . -type d -name "__pycache__" -exec rm -rf {} +`
2. **`tutorial.py` instead of `test_db.py`**
   - Fix: `mv tutorial.py test_db.py`
3. **`tutorial.db` leftover**
   - Fix: `rm tutorial.db`

### ✅ Results
- Save/load messages: ✅
- Save/load facts: ✅
- Remembers after restart: ✅
- SQL injection protection: ✅

### 💡 Key Takeaways
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

### 🎯 Goal
Make Remy hear the user via speech-to-text (STT).

### 📖 Concepts Learned

#### 1. What is STT?
- **STT = Speech-to-Text**
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
- Not used yet (Day 5)

#### 5. Audio Formats
| Format | Size (1 hour) | Quality |
|--------|---------------|---------|
| WAV | ~115 MB | 100% |
| FLAC | ~60 MB | 100% (lossless) |
| MP3 128k | ~57 MB | ~75% |
| OGG 128k | ~57 MB | ~85% |

**Why FLAC?** Lossless, ~50% smaller than WAV.

#### 6. Sample Rate & Channels
- Whisper wants: 16 kHz, mono
- Record at 16 kHz mono from the start

### 🛠️ What I Built

**File:** `test_stt.py` (temporary, root directory)

**Flow:**
1. Load `GROQ_API_KEY` from `.env`
2. Create Groq client
3. Record 5 seconds via `sounddevice`
4. Save as FLAC via `soundfile`
5. Send to Groq Whisper
6. Print text

**Code:**
```python
import os
import sounddevice as sd
import soundfile as sf
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

DURATION = 5
SAMPLE_RATE = 16000
CHANNELS = 1
FILENAME = "test.flac"

def record_audio():
    print(f"🎤 Recording... ({DURATION} seconds)")
    recording = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS)
    sd.wait()
    sf.write(FILENAME, recording, SAMPLE_RATE)
    print("✅ Recording finished")

def transcribe(filename):
    print("📤 Sending to Groq...")
    with open(filename, "rb") as file:
        result = client.audio.transcriptions.create(
            file=file,
            model="whisper-large-v3-turbo",
            language="tr",
            response_format="text"
        )
    return result

def main():
    record_audio()
    text = transcribe(FILENAME)
    print(f"📝 Text: {text}")

if __name__ == "__main__":
    main()


### 📦 Libraries Used
| Library | Purpose |
|---------|---------|
| `groq` | Groq API client |
| `sounddevice` | Microphone access |
| `soundfile` | Write audio to FLAC |
| `python-dotenv` | Load `.env` |

**Install:**
```bash
pip install groq sounddevice soundfile python-dotenv

**Yani:** Üç tane backtick (` ``` `) ekle. Bu, kod bloğunu **kapatır.**

**Sonra Day 5 başlar:**

```markdown
---

## Day 5 — Text-to-Speech (Mouth) + First Voice Conversation
...
