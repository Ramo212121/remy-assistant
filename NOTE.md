# Remy Development Notes

Daily log of what I learn, build, and debug while creating Remy — a fully local, privacy-first AI voice assistant for macOS.

---

## Day 1 — Ollama Setup

**Difficulty:** 🟡 | **Duration:** ~3h

### What I Did
- Installed Homebrew + Ollama
- Started Ollama service
- Pulled `qwen2.5:7b` model
- Tested from terminal

### Learned
- **LLM** = brain, **Ollama** = local runtime, **Model** = trained file
- `brew` = apps, `pip` = Python packages

### Problems
- `brew` not in PATH → added
- Mac froze (8GB RAM) → shortened `OLLAMA_KEEP_ALIVE`

---

## Day 2 — Python + Ollama

**Difficulty:** 🟢 | **Duration:** ~3h

### What I Did
- Created project folder + `venv`
- `pip install ollama`
- Wrote `remy.py` (chat loop)

### Learned
- **venv** = isolated Python env
- **`ollama.chat()`** = send messages to model
- **messages list** = memory
- **system prompt** = personality

---

## Day 3 — Persistent Memory (SQLite)

**Difficulty:** 🟡 | **Duration:** ~5h

### What I Did
- Created `src/memory/database.py`
- Tables: `messages`, `facts`
- Functions: `init_db`, `save_message`, `get_messages`, `save_fact`, `get_fact`
- Integrated into `remy.py`

### Learned
- **SQLite** = file-based DB, built into Python
- **Cursor** = executes SQL
- **`?` placeholder** = prevents SQL injection
- **`commit()`** = saves changes
- **`INSERT OR REPLACE`** = upsert

### Problems
- `ImportError` → Python cache → `rm -rf __pycache__`
- `tutorial.py` typo → renamed

---

## Day 4 — Speech Recognition (Ears)

**Difficulty:** 🟠 | **Duration:** ~5h

### What I Did
- `pip install groq sounddevice soundfile`
- Created `test_stt.py`
- Record 5s → FLAC → Groq Whisper → text

### Learned
- **STT** = Speech-to-Text
- **Whisper** = OpenAI's STT model (99 languages)
- **Groq Whisper** = free, fast (216x), no RAM
- **FLAC** = lossless, ~50% smaller than WAV
- **16 kHz mono** = what Whisper wants

### Problems
- API key shown once → create new
- `.env` missing → created
- Mic permission → System Settings

---

## Day 5 — Text-to-Speech (Mouth)

**Difficulty:** 🟠 | **Duration:** ~6h

### What I Did
- Installed Piper TTS
- Downloaded `en_US-ryan-high.onnx`
- Created `src/mouth/speaker.py`
- `clean_text_for_tts()` + `speak()`
- First voice conversation!

### Learned
- **Piper** = neural TTS, local, free
- **`high` model** > `low` model (quality)
- **CoreAudio conflict:** `afplay` + `sounddevice` clash
- **Fix:** `time.sleep(0.5)` + `afplay`

### Problems
- AirPods made conflict worse → use Mac speakers
- `sd.play()` crashed → use `afplay`
- Piper read markdown → regex cleaning

---

## Day 6 — Speed Optimization (Streaming)

**Difficulty:** 🟠 | **Duration:** ~5h

### What I Did
- Added `stream=True` to `ollama.chat()`
- Sentence buffering (send to TTS per sentence)
- `len > 30` check to avoid splitting

### Learned
- **Streaming** = token by token (instant feel)
- **Sentence buffer** = group tokens into speakable chunks
- **Threading** = TTS in background

### Results
- First sound: 1-2s (was 5-10s)
- Sentence splitting fixed

---

## Day 7 — Echo + Crash Fixes

**Difficulty:** 🟠 | **Duration:** ~6h

### What I Did
- Added `set_speaking()` flag
- Added `clear_buffer()`
- Speech queue (`queue.Queue`)
- `wait_until_done()`

### Learned
- **Echo:** Remy hears itself → replies to itself
- **`set_speaking`** = pause mic without stopping stream
- **Never `stop()`/`start()`** stream on macOS (crashes)
- **Speech queue** = only one `afplay` at a time
- **`wait_until_done()`** = TTS finishes before mic reopens

### Results
- Echo: fixed
- `afplay` crash: fixed
- Double print: fixed
- Stable!

---

## Day 8 — Speaker Recognition

**Difficulty:** 🟠 | **Duration:** ~6h

### What I Did
- `pip install resemblyzer`
- Created `enroll.py` (record voice)
- `voice_profile.npy` saved
- `is_my_voice()` in `listener.py`

### Learned
- **Speaker Verification** = only my voice
- **Voice embedding** = 256-dim vector
- **Enrollment** = record once, verify forever
- **Cosine similarity** = compare voice match
- **Threshold** = 0.55 (tuned)
- **`setuptools<82`** needed for `webrtcvad`

### Results
- My voice: accepted (~0.68)
- Others: rejected (~0.60)
- Remy ignores non-user voices

---

## Day 9 — Barge-in (Interrupt)

**Difficulty:** 🔴 | **Duration:** ~6h

### What I Did
- Added `_listen_for_interrupt()` to `speaker.py`
- `INTERRUPT_THRESHOLD = 0.25`
- `proc.terminate()` to stop `afplay`

### Learned
- **Barge-in** = interrupt assistant while speaking
- **RMS volume** = `np.linalg.norm(indata) / len(indata)`
- **Threshold tuning:**
  - Silent: 0.001-0.005
  - Remy's own voice: 0.05-0.15
  - User speaking: 0.15-0.25
- **`sd.CallbackStop`** = exit stream cleanly

### Results
- Barge-in working
- Remy stops when user speaks
- Remy doesn't interrupt itself

---

## Day 10 — Tool Calling

**Difficulty:** 🟠 | **Duration:** ~6h

### What I Did
- Created `src/hands/tools.py`
- Functions: `get_time`, `get_date`, `calculate`
- `TOOLS` JSON schema
- Tool call loop in `remy.py`

### Learned
- **Tool Calling** = LLM calls Python functions
- **JSON schema** = describes each tool
- **`tools=TOOLS`** = enables tool calling
- **`tool_calls`** = model wants a function
- **Loop:** call → execute → append → re-call
- **`ToolCall` object** = use `.function.name`

### Results
- Time, date, calculate all work
- 3 tools total

---

## Day 11 — Reminder System

**Difficulty:** 🟡 | **Duration:** ~6h

### What I Did
- Added `reminders` table to `database.py`
- `save_reminder`, `get_pending_reminders`, `mark_done`
- Created `src/hands/reminder.py` (background checker)
- `set_reminder` tool
- macOS notifications via `osascript`

### Learned
- **3 parts:** SQLite + tool + background thread
- **ISO datetime** = `2025-09-26T14:00:00`
- **`threading.Thread(daemon=True)`** = background task
- **`time.sleep(30)`** = check every 30s
- **`osascript`** = macOS notifications

### Results
- 2-minute reminder works
- macOS notification appears
- 4 tools total

---

## Day 12 — App Control + PDF

**Difficulty:** 🟡 | **Duration:** ~6h

### What I Did
- `open_app()` via `subprocess.run(["open", "-a", ...])`
- `read_pdf()` via PyMuPDF
- Short path support (`PROJECT_DIR`)
- Tool descriptions + system prompt rules

### Learned
- **`open -a "App"`** = launch macOS app
- **PyMuPDF** = read PDFs (`fitz` / `pymupdf`)
- **Short path** = `"test.pdf"` → full path
- **Tool descriptions** = must be explicit
- **System prompt rules** = override LLM confusion
- **`cupsfilter`** = create test PDFs

### Results
- App control works
- PDF reading works
- 6 tools total

---

## Day 13 — Web Search + Email

**Difficulty:** 🟡 | **Duration:** ~6h

### What I Did
- `web_search()` via `ddgs` (renamed from `duckduckgo-search`)
- `read_email()` via IMAPClient
- Added Gmail credentials to `.env`

### Learned
- **`ddgs`** = new package name for DuckDuckGo
- **Free web search** = no API key
- **Gmail IMAP** = needs app password + 2FA
- **App password** = 16 chars, only shown once
- **IMAPClient** = simple IMAP library
- **ENVELOPE** = email headers
- **`load_dotenv()`** = must be in every file using `os.getenv()`

### Results
- Web search: working
- Email: code ready, `.env` pending
- 8 tools total

---

## Day 14 — Screen Vision (Eyes)

**Difficulty:** 🟠 | **Duration:** ~6h

### What I Did
- Pulled `moondream` vision model via Ollama
- Created `analyze_screen()` in `tools.py`
- Takes screenshot with `screencapture`
- Base64 encodes image
- Sends to `moondream` for description
- Added to `TOOLS` (9 tools total)

### Learned
- **Vision model** = LLM that understands images
- **Multimodal** = text + image input
- **`screencapture -x`** = silent screenshot on macOS
- **Base64 encode** = image → string for LLM
- **`images=[...]`** = Ollama vision parameter
- **`moondream`** = small vision model (~1.7GB), 8GB RAM friendly
- **`llava:7b`** = bigger (~4.5GB), better quality, but RAM-heavy

### Code
```python
import base64
import ollama

def analyze_screen():
    try:
        subprocess.run(["screencapture", "-x", "/tmp/screen.png"], check=True)
        with open("/tmp/screen.png", "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        response = ollama.chat(
            model="moondream",
            messages=[{
                "role": "user",
                "content": "What's on this screen? Describe it briefly.",
                "images": [image_data]
            }]
        )
        return response['message']['content']
    except Exception as e:
        return f"Error: {e}"

---

## Day 15 — System Control + Alarm

**Difficulty:** 🟡 | **Duration:** ~6h

### What I Did
- Added volume control (`set_volume`, `mute`, `unmute`)
- Added brightness control (`set_brightness`)
- Added system control (`sleep_mac`, `lock_screen`)
- Added alarm (`set_alarm`)
- Total tools: **16**

### Learned
- **`osascript -e`** = run AppleScript from terminal
- **Volume:** `set volume output volume 50`
- **Mute:** `set volume output muted true`
- **Sleep:** `tell application "System Events" to sleep`
- **Lock:** `CGSession -suspend` (native macOS binary)
- **Brightness:** `brightness` CLI (needs `brew install brightness`)
- **Alarm:** No native macOS alarm → use `threading` + `say`
- **Time check loop:** `while True: if now == alarm_time: say(); break`
- **`daemon=True`** = thread dies with main process

### Code
```python
def set_volume(level):
    subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)
    return f"Volume set to {level}%"

def mute():
    subprocess.run(["osascript", "-e", "set volume output muted true"], check=True)
    return "Muted"

def set_brightness(level):
    subprocess.run(["brightness", str(level / 100)], check=True)
    return f"Brightness set to {level}%"

def sleep_mac():
    subprocess.run(["osascript", "-e", 'tell application "System Events" to sleep'], check=True)
    return "Sleeping"

def lock_screen():
    subprocess.run([
        "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession",
        "-suspend"
    ], check=True)
    return "Screen locked"

def set_alarm(alarm_time, message="Wake up!"):
    def alarm_loop():
        while True:
            now = datetime.now().strftime("%H:%M")
            if now == alarm_time:
                subprocess.run(["say", message])
                break
            time.sleep(30)
    threading.Thread(target=alarm_loop, daemon=True).start()
    return f"Alarm set for {alarm_time}"


---

## Day 15 — System Control + Alarm + Performance

**Difficulty:** 🟡 | **Duration:** ~7h

### What I Did
- Added volume control (`set_volume`, `mute`, `unmute`)
- Added brightness (`set_brightness`)
- Added system control (`sleep_mac`, `lock_screen`)
- Added alarm (`set_alarm`)
- **Performance fix:** Switched from `qwen2.5:7b` to `qwen2.5:3b`
- Set `OLLAMA_KEEP_ALIVE=30s`
- Total tools: **16**

### Learned
- **`osascript -e`** = run AppleScript from terminal
- **Volume:** `set volume output volume 50`
- **Sleep:** `tell application "System Events" to sleep`
- **Lock:** `CGSession -suspend`
- **Brightness:** `brightness` CLI (`brew install brightness`)
- **Alarm:** `threading` + `say`
- **`daemon=True`** = thread dies with main process

### Performance Problem
- **8GB RAM not enough** for `qwen2.5:7b` (4.6GB)
- Mac froze due to swap
- **Fix 1:** `qwen2.5:3b` (~2GB) — saves ~2.6GB
- **Fix 2:** `OLLAMA_KEEP_ALIVE=30s` — model unloads after 30s
- **Result:** Mac no longer freezes

### Problems
- **Alarm → opened Safari** — LLM called `open_app`
  - Fix: Stronger tool descriptions + system prompt
- **`TOOLSfrom` syntax error** — two imports on one line
  - Fix: Split into two lines
- **`set_brightness` missing** from import + handler
  - Fix: Added both
- **`PaMacCore Error -9986`** — CoreAudio locked
  - Fix: `sudo killall coreaudiod`

### Results
- Volume/mute/brightness: OK
- Sleep/lock: OK
- Alarm: OK
- LLM picks correct tool: yes
- Mac no longer freezes: **yes**
- Total tools: **16**

### Key Takeaways
1. **8GB RAM is tight** — use 3b model, not 7b
2. **`OLLAMA_KEEP_ALIVE=30s`** frees RAM
3. **Tool descriptions must be explicit** — LLM follows literally
4. **System prompt rules** override confusion
5. **`sudo killall coreaudiod`** fixes audio lock
6. **`osascript`** controls macOS natively
7. **16 tools** — Remy is a full assistant



---

## Day 16 — Wake Word ("Hey Jarvis")

**Difficulty:** 🔴 | **Duration:** ~7h

### What I Did
- Installed `openwakeword` for wake word detection
- Created `src/ears/wake_word.py`
- Used TFLite backend (`ai-edge-litert`) instead of ONNX
- Integrated wake word into `remy.py`
- Fixed double response bug
- Total: 16 tools + wake word

### Learned
- **Wake word** = trigger phrase to activate assistant
- **openWakeWord** = free, open-source wake word engine
- **TFLite vs ONNX on macOS ARM64:**
  - ONNX → low scores (0.05-0.14), unreliable
  - TFLite (ai-edge-litert) → high scores (0.43-0.97), works
- **Threshold tuning:** 0.35 works well
- **Stream lifecycle:** `stream.start()` + `stream.stop()` manually
- **Circular import:** never import your own file

### Code
```python
# wake_word.py
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



