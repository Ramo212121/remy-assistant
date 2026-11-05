# Remy for Android

A standalone Android version of Remy. Tap the mic, talk, tap again. Remy answers in text and, once voice is enabled, out loud.

It talks to Groq directly, so it works anywhere with internet and doesn't need the Mac. It doesn't share memory or tools with the desktop app.

## What it can do

| Tool | What it does |
| :--- | :--- |
| `get_time`, `get_date` | Time and date |
| `calculate` | Safe arithmetic (no `eval`) |
| `open_website` | Opens an `http`/`https` link in the browser |
| `search_web` | Opens a DuckDuckGo search in the browser |

There's no "Hey Remy" on the phone: Android limits always-on microphone use in the background.

## Setup on the phone

1. Install the APK.
2. Open **Settings** (top right) and paste a Groq API key from [console.groq.com/keys](https://console.groq.com/keys). It's stored only on the phone, never in the APK.
3. For spoken replies, accept the Orpheus model terms once: **Settings → ACCEPT VOICE TERMS**. Until then, replies are text only.

## Build

```bash
cd mobile
python3 -m venv .venv
.venv/bin/pip install "flet[all]==1.0.5" flet-audio==1.0.5 flet-audio-recorder==1.0.5 flet-permission-handler==1.0.5 pytest
.venv/bin/flet build apk --arch arm64-v8a
```

The first build downloads Flutter, the Android SDK, the NDK and a JDK (several GB). The APK lands in `build/apk/remy.apk`.

If the build says Flutter can't create `~/.config/flutter`, that folder is owned by another user. Point Flutter elsewhere with `XDG_CONFIG_HOME=$HOME/.flet/config` in front of the build command.

## Run on a computer

```bash
.venv/bin/flet run src/main.py
```

This is text only: the microphone and voice need the Android build.

## Tests

```bash
.venv/bin/python -m pytest
```

The tests use a fake network and need no API key.
