# NOTE.md

> **Developer Notes** — internal architecture, technical decisions, known issues, and roadmap.
>
> This file is more candid and technical than the README. It's a behind-the-scenes guide for contributors.

---

## 📌 Project Goal

Remy is an always-listening voice assistant for macOS.

**Why it exists:**
- An assistant you own and can change, instead of Alexa, Siri or Google
- As much as possible runs on the Mac: wake word, speaker check, TTS, screen analysis
- Natural, fast interaction

**What leaves the machine:** Commands after the wake word go to Groq for transcription, and the conversation goes to Groq's LLM. Tool results, such as email subjects, go with it.

**Target user:** macOS developers who like Python.

---

## 🧠 Design Decisions

### Why Groq?

| Criteria | Groq | OpenAI | Local (Ollama) |
|---|---|---|---|
| **Speed** | ⚡ ~800 tok/s | 🐢 ~100 tok/s | 🐌 ~20–50 tok/s |
| **Free tier** | ✅ Yes | ❌ No | ✅ Yes |
| **Tool calling** | ✅ Excellent | ✅ Excellent | ⚠️ Model-dependent |
| **Privacy** | ⚠️ Cloud | ❌ Cloud | ✅ Local |

**Decision:** Groq for speed + free tier + reliable tool calling. Local mode is planned (Roadmap).

**Free-tier limit:** 8,000 tokens per minute per model, and each request costs at least ~1,135 tokens, so 5-6 quick requests hit it. The SDK's silent retries froze replies for up to 9 s, so retries are off and a 429 switches to `gpt-oss-20b`, which has its own limit.

### Why Local Whisper for the Wake Word?

openWakeWord has no "hey remy" model, so short bursts of speech are transcribed on-device and matched against a pattern.

- `tiny.en` handles everything first (~0.17 s).
- `small.en` re-checks only when `tiny.en` heard "hey ..." without the name (~1.5 s), which helps at a distance.
- `base.en` is skipped: it heard "hey ready" or "hey randy" nearly every time.

Simulated range with `say` voices, added reverb and the measured room noise: 12/12 close, 11/12 at ~2 m, 8/12 at ~4 m.


### Why `gpt-oss-120b`?

- Fast (MoE — only ~3.6B active params)
- Stable tool calling (small 7B models hallucinate arguments)
- Good in English and Turkish
- Free on Groq

**Alternatives tested:**
- `llama-3.3-70b-versatile` — slower, weaker tool calling
- `qwen2.5:7b` (Ollama) — fast but unreliable tool calls
- `gemma3` — no tool calling support

### Why Streaming TTS?

**Blocking (old):**
```
User asks → LLM produces full reply (2–3s) → TTS starts (1s)
Total: 3–4s delay
```

**Streaming (current):**
```
User asks → LLM produces first sentence (0.5s) → TTS starts
Total: 0.5–1s delay
```

**Key trick:** Flush the buffer to TTS at a sentence end followed by whitespace, or at a comma once a clause passes 60 characters. The voice model stays in memory (~0.85 s per sentence, vs 1.4 s for the `piper` CLI), and the next sentence is synthesized while the current one plays.

### Why Piper?

- Offline — no internet needed
- Fast — real-time even on CPU
- Free — no license issues
- Quality — `en_US-ryan-high` sounds natural

**Alternatives:**
- `edge-tts` → natural but requires internet
- macOS `say` → free but very robotic
- Kokoro → natural but heavier

### Why Flet?

- Write in Python — no new language
- Desktop + mobile + web from one codebase
- Modern UI (Flutter-based, smooth)
- Hot reload for fast iteration

**Alternatives:**
- PyQt → great desktop, no mobile
- Kivy → good mobile, dated UI
- BeeWare → native but hard to set up

---

## 🏗️ Architecture Choices

### Layered: Ears → Brain → Hands → Mouth

```
User voice → Ears (STT) → Brain (LLM) → Hands (tools) → Mouth (TTS) → User
```

**Why:**
- Each layer is independently testable
- `remy.py` and the desktop app share `src/brain`, so a fix lands in both
- Swapping one layer (e.g., Groq → Ollama) doesn't affect others
- Readable code

### Why SQLite?

- No dependency — built into Python
- Lightweight — single file (`remy.db`)
- Good enough — messages, reminders, facts
- Easy backup — copy the `.db` file

### Why Tool Calling?

**Regex approach:** "what time" → `get_time()`
- ❌ Fragile, breaks with phrasing changes
- ❌ Can't handle complex commands

**Intent classification:** Separate model for intent
- ❌ Extra model, extra latency
- ❌ Hard to maintain

**Tool calling (current):** The LLM decides
- ✅ Natural language flexible
- ✅ Easy to add tools
- ✅ Supports multi-step tasks

---

## ⚠️ Known Issues

### 1. STT Mishears Words

**Example:**
```
User: "Tell me a joke"
Whisper: "a joke tell me a joke"
```

**Cause:** Turkish-accented English + Whisper's language model.

**Workaround:**
```python
result = client.audio.transcriptions.create(
    file=file,
    model="whisper-large-v3-turbo",
    language="en",
    prompt="Remy voice assistant. Common phrases: tell me a joke, what time is it, open Spotify."
)
```

### 2. Voice Similarity Threshold Is Tight

**Problem:** `SIMILARITY_THRESHOLD = 0.45` sometimes scores 0.48–0.50 → Remy rejects the user.

**Measured:** On clips of the enrollment recording, over half of 1 s clips score below 0.45, and synthetic voices land in the same range. That's why the check runs on the command and not on the wake phrase, so anyone can get a "Yes?". At a simulated distance, ~10-30% of commands are rejected.

**Fix:** Re-run `enroll.py` with a louder sample, or lower to `0.40`.

### 3. TTS Cuts Itself Off

**Problem:** `_listen_for_interrupt()` monitors the mic while `afplay` plays. Remy's own voice can trigger it.

**Workaround:** Raise `INTERRUPT_THRESHOLD` (`0.25` → `0.40`).

**Real fix:** Echo cancellation (WebRTC AEC) or mute mic during playback.

### 4. Similar Names Can Wake Remy

**Problem:** "Hey Randy" woke Remy in 7 of 9 simulated tries. The other test phrases didn't.

### 5. Piper Model Files Are Large

**Problem:** `en_US-ryan-high.onnx` ~110 MB — too big for GitHub.

**Fix:** Add to `.gitignore`, link to download in README.

### 6. `pkg_resources` Deprecation Warning

**Problem:** `webrtcvad` uses legacy `pkg_resources` → warning on Python 3.14.

**Workaround:** Ignore (warning, not error).

**Real fix:** Switch to `webrtcvad-wheels` or `silero-vad`.

---

## 🧪 Testing

### Automated

```bash
python -m pytest tests
```

Covers the calculator, commands, reminders, wake phrase logic and the assistant loop, with no mic or network.

### Manual Test Checklist

After any major change:

1. **Wake word:** Open the app, press nothing, say "Hey Remy" → Remy says "Yes?"
2. **Simple question:** "What time is it?" → correct time
3. **Tool call:** "Open Spotify" → Spotify launches
4. **Streaming TTS:** "Tell me a long story" → first sentence in < 1s
5. **Conversation mode:** "What time?" + "Tell me a joke" → no wake word needed
6. **Exit:** "Bye" → conversation mode ends
7. **Shutdown:** "Shutdown remy" → program exits
8. **Silence timeout:** Stay quiet for 30s → auto-exit
9. **Interrupt:** Say "Stop" while Remy talks → TTS stops

### Performance Targets (M2, 8GB RAM)

| Stage | Target |
|---|---|
| Wake word detection (clear) | < 0.5s |
| STT | < 0.5s |
| LLM first token | < 0.8s |
| TTS first audio | < 0.3s |
| **Total first audio** | **< 2s** |

---

## 🛠️ Dev Environment

### Recommended VS Code Extensions

- **Python** (Microsoft)
- **Pylance** — type checking
- **Black Formatter** — auto-format
- **Ruff** — fast linter
- **GitLens** — git history

### Coding Standards

- **PEP 8**
- **Type hints** on function signatures
- **Docstrings** on all public functions
- **Max line length:** 100
- **Commit prefixes:** `feat:`, `fix:`, `docs:`, `refactor:`

### Branch Strategy

- `main` → stable, releasable
- `dev` → development
- `feature/xxx` → new feature
- `fix/xxx` → bug fix

---

## 📋 TODO

### Short-term (v1.1)

- [x] Wire real `interrupt()` into `remy_service.py`
- [ ] STT improvement (Whisper `prompt` param)
- [ ] Warn in the UI if `voice_profile.npy` is missing
- [ ] Echo cancellation, so Remy can't interrupt itself
- [x] User-friendly error messages
- [x] Pin `requirements.txt`

### Mid-term (v1.2)

- [ ] Mobile companion app (Flet Android)
- [ ] Fully local mode (Ollama + `faster-whisper`)
- [ ] Multi-language support (TR, EN)
- [ ] Plugin system for custom tools
- [ ] System tray icon (run in background)

### Long-term (v2.0)

- [ ] HomeKit integration
- [ ] Google Calendar / Apple Calendar
- [ ] WhatsApp message reading
- [ ] Home automation (MQTT)
- [ ] Voice cloning (Chatterbox TTS)
- [ ] Windows and Linux support

---

## 🐛 Troubleshooting

### `module 'flet.controls.padding' has no attribute 'symmetric'`

**Cause:** Flet 0.85+ API change.

**Fix:** `ft.padding.symmetric()` → `ft.Padding.symmetric()` (capital P)

### Remy doesn't wake from across the room

**Cause:** Low input level. Check the `👂 Heard:` lines in the log.

**Fix:** Raise the input level in System Settings → Sound → Input (it was 27% when range was measured). Add a recurring spelling of the name to `WAKE_PATTERN` in `wake_word.py`.

### `afplay timeout`

**Cause:** A single audio file exceeded 60s.

**Fix:** Increase timeout in `speaker.py` or split text.

---

## 🎓 Lessons Learned

1. **Streaming is everything.** Users won't wait 2 seconds. Streaming STT + LLM + TTS = seamless UX.

2. **Prompt engineering matters.** The line `WAKE WORD: ...` confused the LLM into telling the user to say "Hey Jarvis". Simplify prompts; remove irrelevant info.

3. **Error tolerance is essential.** Mic fails, Groq returns 429. Handle both without stopping the loop.

4. **Tool calling is magic.** 16 tools, no hardcoded intent routing. Adding a new tool = 10 lines.

5. **Measure before fixing.** The "sometimes slow" replies were a rate limit, not a slow model. A guess would have changed the wrong thing.

6. **Commit discipline.** Commit daily with meaningful messages — recruiters look at your history.

7. **Docs = finishing the job.** Code is 50%. Documentation is the other 50%.

---

## 📚 References

- [Groq API Docs](https://console.groq.com/docs)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Piper TTS](https://github.com/rhasspy/piper)
- [Flet Docs](https://flet.dev/docs/)
- [Resemblyzer](https://github.com/resemble-ai/Resemblyzer)
- [Groq Function Calling](https://console.groq.com/docs/tool-use)
- [SoundDevice](https://python-sounddevice.readthedocs.io/)
- [PyMuPDF](https://pymupdf.readthedocs.io/)

---

## 📝 Changelog

### v1.1.0 (Oct 2026)

- Wake word changed to "Hey Remy", detected on-device
- Voice mode starts with the app, and the Mac stays awake from idle
- Desktop app rebuilt as a sci-fi HUD: typed messages, tools panel, working Stop
- Conversation memory now survives wake words and restarts
- Rate-limit failover and faster TTS
- Security: `eval` removed from `calculate`, AppleScript injection closed, PDFs limited to the project folder
- Terminal and desktop apps share `src/brain`; pytest suite added

### v1.0.0 (Oct 2025)

- First stable release
- Wake word + VAD + STT + TTS pipeline
- 16 tools + native tool calling
- Streaming LLM + streaming TTS
- Conversation mode + multi-tier exit
- Apple-style Flet UI
- Speaker verification
- SQLite memory

### v0.5.0 (Sep 2025)

- Streaming TTS integration
- Conversation mode
- First Flet UI
- 16 tools added

### v0.1.0 (Aug 2025)

- Project start
- Wake word + STT + LLM core loop
- First 5 tools

---

<div align="center">

*This is a living document. Updated after every major change.*

*Last updated: Oct 2026*

</div>
