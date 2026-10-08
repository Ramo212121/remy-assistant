import os
import json
import sys
import time
from groq import Groq
from dotenv import load_dotenv
from src.memory.database import init_db, save_message, get_messages
from src.ears.listener import listen, _stream, set_speaking, clear_buffer
from src.ears.wake_word import wait_for_wake_word
from src.mouth.speaker import speak, wait_until_done, interrupt, is_speaking
from src.hands.tools import (
    get_time, get_date, calculate, set_reminder,
    open_app, read_pdf, web_search, read_email, analyze_screen,
    set_volume, mute, unmute, set_brightness, sleep_mac, lock_screen, set_alarm,
    TOOLS
)
from src.hands.reminder import start_reminder_checker

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are Remy, the user's personal AI assistant.
You speak English, friendly but not overly cheerful. Be concise.

CRITICAL RULES — follow these strictly:

1. NEVER use emojis, emoticons, or special symbols. They break text-to-speech.
2. Do NOT start responses with "Sure!", "Of course!", "Absolutely!", "Great question!" or similar filler. Just answer directly.
3. Keep answers SHORT. 1-3 sentences unless the user asks for detail.
4. Do NOT be overly polite or formal. Be natural and direct.
5. Use "you", not "sir" or "ma'am".

TOOL ROUTING — follow exactly:
- time / "what time" → get_time ONLY.
- date / "what day" → get_date ONLY.
- math / calculation → calculate.
- "remind me" → set_reminder.
- "open X" / "launch X" → open_app (ONLY when user says "open" or "launch").
- "read PDF X" → read_pdf with filename.
- "search for X" / "look up X" → web_search.
- "read my email" → read_email.
- "what's on my screen" → analyze_screen.
- "volume X" / "set volume" → set_volume (ONLY if user says "volume").
- "mute" → mute. "unmute" → unmute.
- "brightness X" → set_brightness.
- "sleep" → sleep_mac. "lock" → lock_screen.
- "set alarm" / "wake me up" → set_alarm (NEVER use open_app for alarm).

If unsure, ASK the user instead of guessing."""

# ─────────────────────────────────────────
# KOMUT LİSTELERİ
# ─────────────────────────────────────────

# Conversation mode'u kapatır, wake word bekleme moduna döner
EXIT_COMMANDS = [
    "bye", "goodbye", "bye jarvis", "goodbye jarvis",
    "stop", "stop listening", "that's all", "thats all",
    "i'm done", "im done", "i am done",
    "end conversation", "see you", "see ya",
    "talk to you later", "catch you later",
    "sleep", "good night", "goodnight",
]

# Programı tamamen kapatır (Ctrl+C gibi)
SHUTDOWN_COMMANDS = [
    "shutdown remy", "shut down remy", "shut down",
    "shutdown", "quit remy", "quit", "exit remy", "exit",
    "power off remy", "turn off remy", "kill remy",
    "close remy", "terminate remy",
]

# Sessizlik timeout'u (saniye) — conversation mode'da bu süre sessiz kalırsan kapanır
SILENCE_TIMEOUT = 30


init_db()
start_reminder_checker()

history = get_messages(limit=10)
history.reverse()

messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
for role, content in history:
    messages.append({'role': role, 'content': content})

print("Remy is ready!")
print("Say 'Hey Jarvis' to start. Say 'bye' to end. Say 'shutdown remy' to quit.")
print("-" * 40)


def is_exit_command(text):
    """Check if user wants to end conversation."""
    if not text:
        return False
    text_lower = text.lower().strip()
    for cmd in EXIT_COMMANDS:
        if cmd in text_lower:
            return True
    return False


def is_shutdown_command(text):
    """Check if user wants to shut down the program."""
    if not text:
        return False
    text_lower = text.lower().strip()
    for cmd in SHUTDOWN_COMMANDS:
        if cmd in text_lower:
            return True
    return False


def handle_tool_calls(tool_calls_raw):
    """Execute tool calls and return results (Groq format)."""
    results = []

    for call in tool_calls_raw:
        name = call.function.name
        try:
            args = json.loads(call.function.arguments or "{}")
        except:
            args = {}

        if name == 'get_time':
            result = get_time()
        elif name == 'get_date':
            result = get_date()
        elif name == 'calculate':
            result = calculate(args.get('expression', ''))
        elif name == 'set_reminder':
            result = set_reminder(args.get('remind_at', ''), args.get('content', ''))
        elif name == 'open_app':
            result = open_app(args.get('app_name', ''))
        elif name == 'read_pdf':
            result = read_pdf(args.get('file_path', ''))
        elif name == 'web_search':
            result = web_search(args.get('query', ''))
        elif name == 'read_email':
            result = read_email(args.get('count', 5))
        elif name == 'analyze_screen':
            result = analyze_screen()
        elif name == 'set_volume':
            result = set_volume(args.get('level', 50))
        elif name == 'mute':
            result = mute()
        elif name == 'unmute':
            result = unmute()
        elif name == 'set_brightness':
            result = set_brightness(args.get('level', 50))
        elif name == 'sleep_mac':
            result = sleep_mac()
        elif name == 'lock_screen':
            result = lock_screen()
        elif name == 'set_alarm':
            result = set_alarm(args.get('alarm_time', ''), args.get('message', 'Wake up!'))
        else:
            result = "Unknown tool"

        print(f"🛠️ Tool: {name} → {str(result)[:100]}")

        results.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": str(result)
        })

    return results


def stream_reply(msgs):
    """Stream LLM response, speak sentence by sentence."""
    stream = groq_client.chat.completions.create(
        model='openai/gpt-oss-120b',
        messages=msgs,
        stream=True
    )

    buffer = ""
    full_reply = ""

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        token = delta.content or ""

        if not token:
            continue

        buffer += token
        full_reply += token

        if buffer.rstrip().endswith((".", "!", "?", "…")):
            sentence = buffer.strip()
            if sentence:
                speak(sentence)
                buffer = ""

    if buffer.strip():
        speak(buffer.strip())

    return full_reply


def get_reply(user_text):
    """Get reply with tool calling + streaming."""
    messages.append({'role': 'user', 'content': user_text})

    stream = groq_client.chat.completions.create(
        model='openai/gpt-oss-120b',
        messages=messages,
        tools=TOOLS,
        stream=True
    )

    tool_calls_buffer = {}
    has_tool_call = False

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        if delta.tool_calls:
            has_tool_call = True
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_buffer:
                    tool_calls_buffer[idx] = {
                        "id": tc.id or "",
                        "name": "",
                        "arguments": ""
                    }
                if tc.function:
                    if tc.function.name:
                        tool_calls_buffer[idx]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls_buffer[idx]["arguments"] += tc.function.arguments

        if delta.content and not has_tool_call:
            break

    if has_tool_call:
        print("🛠️ Tool call detected")

        tool_calls = []
        for idx in sorted(tool_calls_buffer.keys()):
            tc = tool_calls_buffer[idx]
            tool_calls.append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"]
                }
            })

        class FakeCall:
            def __init__(self, id, name, arguments):
                self.id = id
                self.function = type('obj', (object,), {
                    'name': name,
                    'arguments': arguments
                })()

        fake_calls = [FakeCall(tc['id'], tc['function']['name'], tc['function']['arguments'])
                      for tc in tool_calls]

        tool_results = handle_tool_calls(fake_calls)

        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls
        })
        messages.extend(tool_results)

        return stream_reply(messages)

    return stream_reply(messages)


def listen_with_timeout(timeout=SILENCE_TIMEOUT):
    """
    Listen with VAD but also track total silence time.
    Returns (user_text, silence_duration).
    If no speech for `timeout` seconds, returns ("", silence_duration).
    """
    import numpy as np
    import soundfile as sf
    import webrtcvad
    from src.ears.listener import (
        _get_stream, _load_profile, _load_encoder, is_my_voice,
        transcribe, SAMPLE_RATE, clear_buffer
    )
    from resemblyzer import preprocess_wav
    from pathlib import Path

    vad = webrtcvad.Vad(3)
    frame_duration_ms = 30
    frame_size = int(SAMPLE_RATE * frame_duration_ms / 1000)

    stream = _get_stream()
    clear_buffer()

    print("🎤 Listening... (speak now)")

    recording = []
    silent_frames = 0
    speech_frames = 0
    max_silent_frames = int(1.0 * 1000 / frame_duration_ms)  # 1 sn sessizlik sonrası dur
    speech_started = False

    # Toplam sessizlik takibi
    total_silent_frames = 0
    max_total_silent_frames = int(timeout * 1000 / frame_duration_ms)

    while True:
        frame, overflowed = stream.read(frame_size)
        audio_bytes = (frame[:, 0] * 32767).astype(np.int16).tobytes()

        is_speech = vad.is_speech(audio_bytes, SAMPLE_RATE)

        if is_speech:
            speech_started = True
            speech_frames += 1
            silent_frames = 0
            total_silent_frames = 0
        else:
            silent_frames += 1
            if not speech_started:
                total_silent_frames += 1

        if speech_started:
            recording.append(frame)

        # Konuşma başladıktan sonra 1 sn sessizlik → dur
        if speech_started and silent_frames > max_silent_frames:
            print("✅ Speech ended")
            break

        # Hiç konuşma başlamadıysa ve timeout dolduysa → çık
        if not speech_started and total_silent_frames > max_total_silent_frames:
            print(f"⏰ Silence timeout ({timeout}s) — exiting conversation mode")
            return "", timeout

    # Minimum konuşma kontrolü
    if speech_frames < 3:
        print(f"❌ Too short ({speech_frames} frames) — ignoring")
        return "", 0

    if not recording:
        return "", 0

    audio = np.concatenate(recording, axis=0)
    filename = "temp.flac"
    sf.write(filename, audio, SAMPLE_RATE)

    if not is_my_voice(filename):
        print("🤐 Not my voice, ignoring...")
        return "", 0

    text = transcribe(filename)
    return text, 0


# ═══════════════════════════════════════════════
# ANA DÖNGÜ
# ═══════════════════════════════════════════════

try:
    while True:
        # ─── DIŞ DÖNGÜ: Wake word bekle ───
        if not wait_for_wake_word(timeout=60):
            continue

        print("\n🎤 Conversation mode ON")
        speak("Yes?")
        wait_until_done()
        set_speaking(False)
        clear_buffer()

        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]

        # ─── İÇ DÖNGÜ: Conversation mode ───
        while True:
            user_input, silence_time = listen_with_timeout(timeout=SILENCE_TIMEOUT)

            # Sessizlik timeout'u → conversation mode kapan
            if silence_time >= SILENCE_TIMEOUT:
                print("💤 Silence timeout — conversation mode OFF")
                speak("Going to sleep. Say Hey Jarvis when you need me.")
                wait_until_done()
                set_speaking(False)
                clear_buffer()
                break

            # Boş ses → tekrar dinle
            if not user_input or not user_input.strip():
                continue

            # Shutdown komutu mu? → programı tamamen kapat
            if is_shutdown_command(user_input):
                print(f"\n🛑 Shutdown command: '{user_input}'")
                speak("Shutting down. Goodbye!")
                wait_until_done()
                set_speaking(False)
                clear_buffer()
                print("👋 Remy shutting down...")
                sys.exit(0)

            # Exit komutu mu? → sadece conversation mode kapan
            if is_exit_command(user_input):
                print(f"\n👋 Exit command: '{user_input}'")
                speak("Goodbye!")
                wait_until_done()
                set_speaking(False)
                clear_buffer()
                print("💤 Conversation mode OFF")
                break

            print(f"\nYou: {user_input}")

            save_message('user', user_input)
            set_speaking(True)

            print("⏳ Thinking...")
            reply = get_reply(user_input)

            wait_until_done()
            clear_buffer()
            set_speaking(False)

            save_message('assistant', reply)
            messages.append({'role': 'assistant', 'content': reply})

            # Oturum geçmişi çok uzarsa kırp
            if len(messages) > 22:
                messages = [messages[0]] + messages[-20:]

except KeyboardInterrupt:
    print("\n\n👋 Interrupted by user.")

finally:
    if _stream is not None:
        _stream.stop()
        _stream.close()
        print("\n🔇 Stream closed.")