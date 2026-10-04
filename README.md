
# 🤖 Remy — Local AI Voice Assistant

A fully local, privacy-first AI voice assistant for macOS.
Wake word, speech recognition, tool calling, and system control.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLM-orange)
![Piper](https://img.shields.io/badge/Piper-TTS-green)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Working-brightgreen)

---

## 📖 What is Remy?

Remy is a **voice-controlled AI assistant** for macOS. Unlike Alexa or Google Home, Remy runs **on your Mac** — no cloud dependency except for the free Groq API.

Say **"Hey Jarvis"** → Remy wakes up → speak your command → Remy responds with voice.

---

## ✨ Features

### 🎙️ Voice
- **Wake word:** "Hey Jarvis" (custom "Hey Remy" possible)
- **Speech-to-Text:** Groq Whisper (fast, free, 99 languages)
- **Text-to-Speech:** Piper neural voice (natural, offline)
- **Barge-in:** Interrupt Remy while speaking
- **Speaker recognition:** Only responds to your voice

### 🧠 Brain
- **LLM:** Groq `openai/gpt-oss-120b` (~1s response)
- **Memory:** SQLite — remembers conversations
- **Streaming:** Sentence-by-sentence TTS

### 🛠️ 16 Tools

| Tool              | What it does                       |
|-------------------|------------------------------------|
| `get_time`        | Current time                       |
| `get_date`        | Today's date                       |
| `calculate`       | Math expressions                   |
| `set_reminder`.   | Reminders with macOS notifications |
| `open_app`        | Launch macOS apps                  |
| `read_pdf`        | Read PDF files                     |
| `web_search`      | DuckDuckGo search                  |
| `read_email`      | Gmail unread emails                |
| `analyze_screen`  | Screenshot + vision analysis       |
| `set_volume`      | System volume                      |
| `mute` / `unmute` | Mute controls                      |
| `set_brightness`  | Screen brightness                  |
| `sleep_mac`       | Put Mac to sleep                   |
| `lock_screen`     | Lock screen                        |
| `set_alarm`       | Spoken alarm                       |
----------------------------------------------------------

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│              YOUR MAC                       │
│                                             │
│  ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │  EARS    │───▶│  BRAIN   │───▶│ MOUTH  | │
│  │          │    │          │    │        │ │
│  │ Groq     │    │ Groq     │    │ Piper  │ │
│  │ Whisper  │    │ LLM      │    │+ afplay│ │
│  └──────────┘    └────┬─────┘    └────────┘ │
│                       │                     │
│                  ┌────▼─────┐               │
│                  │  MEMORY  │               │
│                  │  SQLite  │               │
│                  └──────────┘               │
└─────────────────────────────────────────────┘
```

**Flow:**
1. 🎤 **Ears** — Wake word → record → Groq Whisper → text
2. 🧠 **Brain** — Groq LLM → tool calls → reply
3. 💾 **Memory** — Save to SQLite
4. 🔊 **Mouth** — Piper TTS → `afplay` → speaker

---

## 🚀 Quick Start

### Prerequisites
- **macOS** (Apple Silicon recommended)
- **Python 3.10+**
- **Homebrew**
- **Groq API key** — [get one free](https://console.groq.com/keys)

### 1. Clone

```bash
git clone https://github.com/Ramo212121/remy-assistant.git
cd remy-assistant
```

### 2. Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Piper TTS

```bash
brew install piper-tts

# Download voice model
curl -L -o en_US-ryan-high.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx"
curl -L -o en_US-ryan-high.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx.json"
```

### 5. Setup `.env`

```bash
cp .env.example .env
nano .env
```

Add:
```
GROQ_API_KEY=gsk_your_key_here
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 6. Enroll Your Voice (Optional)

```bash
python enroll.py
```

Speak for 30 seconds → `voice_profile.npy` created.

### 7. Run Remy

```bash
python remy.py
```

Say **"Hey Jarvis"** → speak your command.

---

## 🎮 Usage Examples

```
You: What time is it?
Remy: The current time is 16:51.

You: Set alarm for 07:00
Remy: Alarm set for 7 AM.

You: Open Safari
Remy: Safari is now open.

You: What's 25 times 4?
Remy: 100.

You: What's on my screen?
Remy: Your screen shows a terminal window with...

You: Read test.pdf
Remy: The PDF says: Hello, this is a test PDF...

You: Search for capital of Turkey
Remy: Ankara is the capital of Turkey.

You: Set volume to 30
Remy: Volume set to 30%.

You: quit
Remy: Goodbye!
```

---

## 📁 Project Structure

```
remy/
├── remy.py                     # Main loop
├── enroll.py                   # Voice enrollment
├── src/
│   ├── ears/
│   │   ├── listener.py         # Microphone + STT + speaker verification
│   │   └── wake_word.py        # Wake word detection
│   ├── mouth/
│   │   └── speaker.py          # Piper TTS + queue + barge-in
│   ├── memory/
│   │   └── database.py         # SQLite (messages, facts, reminders)
│   └── hands/
│       ├── tools.py            # 16 tools
│       └── reminder.py         # Background reminder checker
├── en_US-ryan-high.onnx        # Piper model (not in repo)
├── remy.db                     # Database (not in repo)
├── voice_profile.npy           # Voice profile (not in repo)
├── .env                        # API keys (not in repo)
├── .gitignore
├── NOTE.md                     # Daily learning log
├── README.md                   # This file
└── requirements.txt
```

---

## 🗺️ Roadmap

### ✅ Completed
- [x] Day 1-3: Ollama, Python, SQLite memory
- [x] Day 4-5: Speech recognition + TTS
- [x] Day 6-7: Streaming, echo fix, stability
- [x] Day 8: Speaker recognition
- [x] Day 9: Barge-in
- [x] Day 10-12: Tool calling (time, date, calc, reminder, app, PDF)
- [x] Day 13: Web search + email
- [x] Day 14: Vision (screen analysis)
- [x] Day 15: System control (volume, brightness, sleep, lock, alarm)
- [x] Day 16: Wake word ("Hey Jarvis")
- [x] Day 17: Groq LLM migration (1s responses)
- [x] Day 18: Final polish

### ⏳ Planned
- [ ] Day 19: Speed optimization
- [ ] Custom "Hey Remy" wake word model
- [ ] Mobile companion app

---

## 🐛 Known Issues

- **`PaMacCore Error -9986`** — CoreAudio lock. Fix: `sudo killall coreaudiod`
- **Wake word works best in quiet environment**
- **"Hey Remy" not yet available** — custom model requires Colab training

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **STT** | Groq Whisper `large-v3-turbo` |
| **LLM** | Groq `openai/gpt-oss-120b` |
| **TTS** | Piper `en_US-ryan-high` |
| **Playback** | macOS `afplay` |
| **Memory** | SQLite |
| **Wake word** | openWakeWord (TFLite) |
| **Speaker ID** | Resemblyzer |
| **Vision** | Ollama `moondream` |
| **Language** | Python 3.10+ |

---

## 📝 Learning Notes

Daily logs of what I learned building Remy are in [NOTE.md](NOTE.md).

**Read it if you want to:**
- Learn how to build an AI assistant
- Understand macOS audio quirks
- See real debugging stories

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Groq](https://groq.com) — free Whisper + LLM API
- [Piper](https://github.com/rhasspy/piper) — neural TTS
- [openWakeWord](https://github.com/dscripka/openWakeWord) — wake word
- [Resemblyzer](https://github.com/resemble-ai/Resemblyzer) — speaker recognition
- [Ollama](https://ollama.com) — local vision model

---

## 📧 Contact

- **GitHub:** [@Ramo212121](https://github.com/Ramo212121)
- **Project:** [remy-assistant](https://github.com/Ramo212121/remy-assistant)

---

⭐ **If you like this project, give it a star!**



