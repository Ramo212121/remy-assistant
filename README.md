# Remy

### An always-listening AI voice assistant for macOS, with on-device wake word and speech output

Natural voice interaction, real system control, and native tool calling — engineered for developers who value speed, privacy, and craft.

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![macOS](https://img.shields.io/badge/macOS-13+-000000?style=for-the-badge&logo=apple&logoColor=white)](https://www.apple.com/macos/)
[![Flet](https://img.shields.io/badge/Flet-UI-02569B?style=for-the-badge)](https://flet.dev/)
[![Groq](https://img.shields.io/badge/Groq-Inference-F55036?style=for-the-badge)](https://groq.com/)
[![License](https://img.shields.io/badge/License-MIT-34C759?style=for-the-badge)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=for-the-badge)](https://github.com/Ramo212121/remy-assistant/pulls)

<br />

**[Overview](#-overview)** · **[Features](#-features)** · **[Architecture](#-architecture)** · **[Quick Start](#-quick-start)** · **[Tools](#-built-in-tools)** · **[Configuration](#%EF%B8%8F-configuration)** · **[Roadmap](#-roadmap)** · **[License](#-license)**

---

## 📌 Overview

**Remy** is a voice-controlled AI assistant that runs natively on macOS. It listens for the wake word **"Hey Remy"**, answers without a button press while the app is open, understands natural language through a streaming LLM, and executes real tasks on your machine — launching applications, reading PDFs, searching the web, checking email, adjusting system settings, and more.

Remy was built around three engineering principles:

| Principle | Implementation |
| :--- | :--- |
| **Local where it can be** | The wake word, speaker check, speech output and screen analysis run on your Mac. Your commands and replies go to Groq for transcription and the LLM. |
| **Low latency** | Replies are spoken sentence by sentence, about 2 to 3.5 seconds after you stop talking. |
| **Extensible by design** | Every capability is a Python function with a JSON schema, registered in one file. |

---

## ✨ Features

### 🎙️ Voice Pipeline

- **Wake word detection** — "Hey Remy", transcribed on-device with `faster-whisper` (`tiny.en` first, `small.en` for unclear cases; about 535 MB in total, downloaded on first run)
- **Speaker verification** — `Resemblyzer`; only the enrolled voice is accepted
- **Voice Activity Detection** — `webrtcvad` (aggressiveness level 3)
- **Speech-to-text** — Groq Whisper Large v3 Turbo
- **Streaming TTS** — Piper + `afplay`, spoken sentence-by-sentence
- **Barge-in / interrupt** — speak while Remy talks to stop playback
- **Conversation mode** — one wake word, then continuous dialogue

### 🧠 Intelligence Layer

- **LLM** — Groq `openai/gpt-oss-120b` (streaming + native tool calling)
- **Memory** — SQLite (`messages`, `facts`, `reminders`)
- **Tool calling** — Parallel function calls with schema validation
- **System prompt** — Tuned for concise, natural, TTS-safe output
- **Multi-turn context** — Keeps the last 12 messages, restored from SQLite on restart

### 🎨 Interface

- **Flet desktop app** — Native macOS window
- **Sci-fi HUD** — Dark grid background (`scripts/generate_hud_bg.py`), monospace type, bracketed panels
- **Status waveform** — Animated bars with a color and motion for each state
- **Live log** — Terminal-style transcript that fills sentence by sentence
- **Always listening** — Voice mode starts with the app and keeps the Mac from idle sleep
- **Typed messages** — Chat with Remy without using the mic
- **Tools panel** — 10 tools on demand, with dialogs for the ones that need input
- **Stop control** — Stops playback and the running reply

### ⚙️ Reliability

- **Multi-tier exit** — Exit commands, shutdown commands, silence timeout
- **Graceful degradation** — Missing voice profile falls back to accept-all
- **Error recovery** — The voice loop restarts itself after a microphone error
- **Persistent memory** — Recent turns are restored across wake words and restarts
- **Resilient loop** — Network and API errors are spoken, not fatal
- **Rate-limit failover** — Switches to `gpt-oss-20b` instead of waiting out a limit

---

## 🏗️ Architecture

Remy is built as a **four-layer pipeline** — Ears, Brain, Hands, and Mouth — orchestrated around a SQLite memory store.

### Visual Overview

```mermaid
flowchart TD
    User([👤 User Voice]) --> Ears

    subgraph Ears[🎙️ EARS]
        WW[Local Whisper wake word] --> VAD[webrtcvad]
        VAD --> RS[Resemblyzer<br/>Speaker Verify]
        RS --> Whisper[Groq Whisper STT]
    end

    Whisper --> Brain

    subgraph Brain[🧠 BRAIN]
        LLM[Groq LLM<br/>gpt-oss-120b]
        LLM --> TC[Tool Calling]
        LLM --> TK[Text Tokens]
    end

    TC --> Hands
    TK --> Mouth

    subgraph Hands[🖐️ HANDS]
        T1[16 Python Tools]
        T2[subprocess / osascript]
        T3[PyMuPDF / IMAP / DDG]
    end

    subgraph Mouth[🔊 MOUTH]
        Piper[Piper TTS]
        Piper --> AF[afplay + interrupt]
    end

    Hands --> Memory
    Mouth --> Memory

    subgraph Memory[💾 MEMORY]
        DB[(SQLite<br/>messages · facts · reminders)]
    end

    style User fill:#007AFF,color:#fff
    style Ears fill:#34C759,color:#fff
    style Brain fill:#AF52DE,color:#fff
    style Hands fill:#FF9500,color:#fff
    style Mouth fill:#FF2D55,color:#fff
    style Memory fill:#8E8E93,color:#fff
```

### Terminal View

```text
┌─────────────────────────────────────────────────────────────┐
│                         USER (voice)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
       ┌───────────────────▼───────────────────┐
       │                EARS                    │
       │  Hey Remy → webrtcvad → Whisper        │
       │  Resemblyzer (speaker verification)    │
       └───────────────────┬───────────────────┘
                           │  transcribed text
       ┌───────────────────▼───────────────────┐
       │                BRAIN                   │
       │  Groq LLM (gpt-oss-120b)               │
       │  Streaming + Native Tool Calling       │
       └──────┬────────────────────────┬────────┘
              │                        │
      tool calls                        text tokens
              ▼                        ▼
       ┌──────────────┐         ┌──────────────┐
       │    HANDS     │         │    MOUTH     │
       │ 16 tools     │         │ Piper TTS    │
       │ subprocess   │         │ afplay       │
       │ osascript    │         │ interrupt    │
       └──────┬───────┘         └──────┬───────┘
              │                        │
              └────────────┬───────────┘
                           ▼
                ┌────────────────────┐
                │      MEMORY        │
                │ SQLite: messages,  │
                │ facts, reminders   │
                └────────────────────┘
```

### Data Flow

1. **Wake** — Local Whisper hears "Hey Remy"
2. **Listen** — `webrtcvad` captures the utterance, `Resemblyzer` verifies the speaker
3. **Transcribe** — Groq Whisper returns the text
4. **Reason** — Groq LLM streams tokens; if a tool is needed, it emits a `tool_call`
5. **Act** — The matching Python function runs (AppleScript, subprocess, PyMuPDF, etc.)
6. **Speak** — Piper synthesizes each completed sentence; `afplay` plays it with interrupt support
7. **Remember** — Both turns are persisted to SQLite

---

## 📁 Project Structure

```text
remy/
│
├── app/                              # Flet desktop application
│   ├── main.py                       # UI entry point (Apple-style)
│   └── services/
│       └── remy_service.py           # UI ↔ backend bridge
│
├── src/
│   ├── config.py                     # Absolute paths + settings
│   │
│   ├── brain/                        # Shared by terminal and desktop
│   │   ├── assistant.py              # LLM streaming + tool calling + memory
│   │   ├── commands.py               # Exit / shutdown phrases
│   │   └── voice_loop.py             # Wake word → conversation loop
│   │
│   ├── ears/                         # Input layer
│   │   ├── wake_word.py              # "Hey Remy" detection (local)
│   │   └── listener.py               # VAD + Whisper + speaker verify
│   │
│   ├── mouth/                        # Output layer
│   │   └── speaker.py                # Piper TTS + afplay + interrupt
│   │
│   ├── hands/                        # Action layer
│   │   ├── tools.py                  # 16 tool functions + JSON schemas
│   │   └── reminder.py               # Background reminder scheduler
│   │
│   └── memory/                       # Persistence
│       └── database.py               # SQLite schema + helpers
│
├── assets/
│   ├── hud_bg.png                    # App background
│   └── logo.png                      # App logo
│
├── scripts/
│   └── generate_hud_bg.py            # Regenerates the background
├── tests/                            # pytest suite (no mic or network needed)
├── remy.py                           # Terminal entry point
├── enroll.py                         # Voice enrollment CLI
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE                           # MIT
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Notes |
| :--- | :--- | :--- |
| **macOS** | 13 (Ventura) or later | Apple Silicon recommended |
| **Python** | 3.14 | Versions in `requirements.txt` are pinned and tested on 3.14 |
| **Groq API key** | — | Free tier: [console.groq.com](https://console.groq.com) |
| **Piper model** | `en_US-ryan-high.onnx` | [Download here](https://huggingface.co/rhasspy/piper-voices) |

### Installation

```bash
# 1. Clone
git clone https://github.com/Ramo212121/remy-assistant.git
cd remy-assistant

# 2. Virtual environment
python3.14 -m venv venv
source venv/bin/activate

# 3. Python dependencies (includes the piper command)
pip install -r requirements.txt

# 4. Piper voice model
#    Place en_US-ryan-high.onnx and en_US-ryan-high.onnx.json in the project root

# 5. Environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (and GMAIL_* for email tool)
```

### Voice Enrollment (optional, recommended)

```bash
python enroll.py
```

Speak a few sentences when prompted. This produces `voice_profile.npy`, which Remy uses to reject other speakers.

### Run

**Terminal interface:**

```bash
python remy.py
```

**Desktop interface:**

```bash
python app/main.py
```

**Tests:**

```bash
python -m pytest tests
```

---

## 🎤 Usage

### Basic Flow

```text
┌──────────────────────────────────────────────────────────────┐
│  1.  "Hey Remy"             →  Remy wakes:  "Yes?"           │
│  2.  "What time is it?"     →  "It's 4:32 PM."               │
│  3.  "Open Spotify"         →  Launches Spotify              │
│  4.  "Bye"                  →  "Goodbye!" (wake-word mode)   │
└──────────────────────────────────────────────────────────────┘
```

Keep the app open and the lid up. Voice mode starts with the app, and it stops the Mac from idle sleep while it listens. Use the `VOICE: ON` button to turn the microphone off. For better range, raise the input level in System Settings → Sound → Input.

### Conversation Mode

Once woken, Remy stays in **conversation mode** until one of:

| Trigger | Behavior |
| :--- | :--- |
| `"bye"`, `"goodbye"`, `"see you"`, `"that's all"`, `"i'm done"` | Exit conversation mode, return to wake-word standby. The whole sentence must be the command |
| `"shutdown remy"`, `"quit"`, `"exit"` | Fully terminate the program |
| **30 seconds of silence** | Auto-exit conversation mode |

### Example Commands

| You say | Remy does |
| :--- | :--- |
| *"What time is it?"* | Speaks the current time via `get_time` |
| *"Open Spotify"* | Launches Spotify via `open_app` |
| *"Read the PDF report.pdf"* | Extracts and summarizes via `read_pdf` |
| *"Search for the weather in Istanbul"* | DuckDuckGo search + summary |
| *"Read my last 5 emails"* | Gmail unread summary via `read_email` |
| *"What's on my screen?"* | Screenshot + vision analysis via `analyze_screen` |
| *"Set volume to 40"* | System volume via `set_volume` |
| *"Lock the screen"* | Locks macOS via `lock_screen` |
| *"Set an alarm for 7 AM"* | Spoken alarm at 07:00 via `set_alarm` |

---

## 🛠️ Built-in Tools

All tools are defined in `src/hands/tools.py` with JSON schemas for Groq's function calling.

| # | Tool | Category | Description |
| :-: | :--- | :--- | :--- |
| 1 | `get_time` | System | Current time (HH:MM) |
| 2 | `get_date` | System | Today's date |
| 3 | `calculate` | Utility | Evaluate a math expression |
| 4 | `set_reminder` | Productivity | Schedule a reminder (SQLite) |
| 5 | `open_app` | System | Launch any macOS app |
| 6 | `read_pdf` | Documents | Extract text from PDF (PyMuPDF) |
| 7 | `web_search` | Research | DuckDuckGo search + summary |
| 8 | `read_email` | Communication | Latest unread Gmail messages |
| 9 | `analyze_screen` | Vision | Screenshot + `moondream` analysis |
| 10 | `set_volume` | System | Set output volume (0–100) |
| 11 | `mute` | System | Mute output |
| 12 | `unmute` | System | Unmute output |
| 13 | `set_brightness` | System | Set screen brightness (0–100) |
| 14 | `sleep_mac` | System | Put Mac to sleep |
| 15 | `lock_screen` | System | Lock the screen |
| 16 | `set_alarm` | Productivity | Spoken alarm at HH:MM |

### Adding a New Tool

```python
# 1. Define the function in src/hands/tools.py
def my_tool(param: str) -> str:
    """Short description used by the LLM."""
    # ... implementation
    return f"Result: {param}"

# 2. Add the JSON schema to TOOLS
TOOLS.append({
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "What this tool does, when to use it.",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "..."}
            },
            "required": ["param"]
        }
    }
})

# 3. Register it in TOOL_FUNCTIONS in src/hands/tools.py
TOOL_FUNCTIONS["my_tool"] = my_tool
```

That's it — the LLM will route to it automatically.

---

## ⚙️ Configuration

### Environment Variables

`.env` (copy from `.env.example`):

```env
# Required
GROQ_API_KEY=gsk_...

# Optional — only for read_email tool
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx
```

> **Gmail App Password:** Regular passwords don't work with IMAP. Generate one at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

### System Prompt

Edit `SYSTEM_PROMPT` in `src/brain/assistant.py` to customize Remy's tone, tool-routing rules, and constraints.

### Wake Word

Edit `WAKE_PATTERN` in `src/ears/wake_word.py`. It is a regular expression over the locally transcribed text, so any phrase works.

### Speaker Verification

Edit `src/ears/listener.py`:

```python
SIMILARITY_THRESHOLD = 0.45   # Lower = more permissive
```

Delete `voice_profile.npy` to disable verification entirely.

### Fully Local Mode

Every cloud component has a local drop-in replacement:

| Layer | Cloud (default) | Local Alternative |
| :--- | :--- | :--- |
| **LLM** | Groq `gpt-oss-120b` | Ollama (`qwen2.5:7b`, `llama3.1:8b`) |
| **STT** | Groq Whisper Turbo | `faster-whisper` (small / medium) |
| **TTS** | Piper (already local) | Piper, Kokoro, MLX-Audio |
| **Vision** | Ollama `moondream` (already local) | `llava`, `bakllava` |

---

## 🧪 Technology Stack

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **UI** | [Flet](https://flet.dev/) | Cross-platform Python UI |
| **Wake Word** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | On-device wake phrase detection |
| **VAD** | [webrtcvad](https://github.com/wiseman/py-webrtcvad) | Voice activity detection |
| **STT** | Groq Whisper Large v3 Turbo | Speech-to-text (~216× real-time) |
| **Speaker ID** | [Resemblyzer](https://github.com/resemble-ai/Resemblyzer) | Voice embedding + cosine similarity |
| **LLM** | Groq `openai/gpt-oss-120b`, with `gpt-oss-20b` as fallback | Reasoning + tool calling |
| **TTS** | [Piper](https://github.com/rhasspy/piper) | Offline neural text-to-speech |
| **Audio I/O** | `sounddevice`, `soundfile` | Real-time mic + playback |
| **Persistence** | SQLite | Messages, facts, reminders |
| **PDF** | [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF text extraction |
| **Email** | [IMAPClient](https://imapclient.readthedocs.io/) | Gmail read access |
| **Web Search** | [ddgs](https://github.com/deedy5/ddgs) | DuckDuckGo search |
| **Vision** | Ollama `moondream` | Local screenshot analysis |

---

## 🛣️ Roadmap

- [x] Wake word + VAD + STT + TTS pipeline
- [x] 16 built-in tools with native function calling
- [x] Streaming LLM + streaming TTS
- [x] Conversation mode with multi-tier exit
- [x] Sci-fi HUD Flet desktop UI
- [x] Always-on "Hey Remy" with on-device detection
- [x] Speaker verification
- [x] **v1.0 release**
- [ ] Mobile companion app (Flet Android / iOS)
- [ ] Fully offline mode (Ollama + `faster-whisper` + Piper)
- [ ] Plugin system for user-defined tools
- [ ] Multi-language support (Turkish, English)
- [ ] Home automation (HomeKit, MQTT)
- [ ] Calendar integration (Google Calendar, Apple Calendar)

---

## 🤝 Contributing

Contributions are welcome and appreciated.

**Quick guide:**

```bash
# Fork the repo, then:
git checkout -b feature/your-feature
# Make changes
git commit -m "feat: add your feature"
git push origin feature/your-feature
# Open a Pull Request
```

**Guidelines:**

- Follow **PEP 8**
- Document all public functions with docstrings
- Keep PRs focused — one feature per PR
- Add tests for new tools when possible (`python -m pytest tests`)

---

## 📄 License

This project is released under the **MIT License**. See [LICENSE](LICENSE) for details.

You are free to use, modify, and distribute this software — including for commercial purposes.

---

## 🙏 Acknowledgments

Standing on the shoulders of excellent open-source work:

- **[Groq](https://groq.com/)** — Blazing-fast LLM and Whisper inference
- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** — On-device wake phrase detection
- **[Piper](https://github.com/rhasspy/piper)** — Offline neural TTS
- **[Resemblyzer](https://github.com/resemble-ai/Resemblyzer)** — Speaker verification
- **[Flet](https://flet.dev/)** — Beautiful cross-platform UI in pure Python
- **[Ollama](https://ollama.com/)** — Local vision model runtime

---

<div align="center">

### Remy

*A voice assistant that lives on your desk.*

**⭐ If you find this project useful, consider giving it a star.**

Made with ❤️ on macOS

</div>
