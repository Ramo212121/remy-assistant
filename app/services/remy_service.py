"""Remy voice backend integration with tool calling (streaming)."""
import sys
import threading
import subprocess
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

REMY_PATH = Path.home() / "Desktop" / "MyProjects" / "remy"
sys.path.insert(0, str(REMY_PATH))

load_dotenv(REMY_PATH / ".env")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

_listening = False

EXIT_COMMANDS = ["bye jarvis", "goodbye jarvis", "exit", "stop", "sleep", "goodbye"]


def handle_tool_calls(tool_calls, on_status=None):
    """Execute tool calls from Groq response."""
    from src.hands.tools import (
        get_time, get_date, calculate, set_reminder,
        open_app, read_pdf, web_search, read_email, analyze_screen,
        set_volume, mute, unmute, set_brightness, sleep_mac, lock_screen, set_alarm,
    )

    results = []

    for call in tool_calls:
        name = call.function.name
        try:
            args = json.loads(call.function.arguments or "{}")
        except:
            args = {}

        print(f"🛠️ Tool: {name} → {args}")

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

        print(f"🛠️ Result: {str(result)[:80]}")

        results.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": str(result)
        })

    return results


def stream_reply(messages, on_sentence=None):
    """Stream LLM response, speak sentence by sentence."""
    from src.mouth.speaker import speak

    stream = groq_client.chat.completions.create(
        model='openai/gpt-oss-120b',
        messages=messages,
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
                if on_sentence:
                    on_sentence(sentence)
                buffer = ""

    if buffer.strip():
        speak(buffer.strip())
        if on_sentence:
            on_sentence(buffer.strip())

    return full_reply


def chat_with_tools(user_text, messages_history, on_status=None, on_sentence=None):
    """Chat with LLM + tool calling + streaming."""
    from src.hands.tools import TOOLS

    if on_status:
        on_status("⏳ Thinking...")

    messages_history.append({'role': 'user', 'content': user_text})

    # İlk istek — stream=True
    stream = groq_client.chat.completions.create(
        model='openai/gpt-oss-120b',
        messages=messages_history,
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
            # İçerik geliyor ama tool call yok → streaming'e geç
            break

    # Tool call varsa
    if has_tool_call:
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

        tool_results = handle_tool_calls(
            [type('obj', (object,), {
                'id': tc['id'],
                'function': type('obj', (object,), {
                    'name': tc['function']['name'],
                    'arguments': tc['function']['arguments']
                })()
            })() for tc in tool_calls]
        )

        messages_history.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls
        })
        messages_history.extend(tool_results)

        # Şimdi streaming cevap
        reply = stream_reply(messages_history, on_sentence=on_sentence)
        return reply

    # Tool call yok → direkt streaming
    reply = stream_reply(messages_history, on_sentence=on_sentence)
    return reply


def start_wake_word_loop(on_result=None, on_status=None):
    """Start continuous wake word detection loop."""
    global _listening
    if _listening:
        return
    _listening = True

    def run():
        print("DEBUG: Wake word loop started")

        from src.ears.wake_word import wait_for_wake_word
        from src.ears.listener import listen, set_speaking, clear_buffer
        from src.mouth.speaker import speak, wait_until_done

        while _listening:
            try:
                if on_status:
                    on_status("💤 Say 'Hey Jarvis'...")

                detected = wait_for_wake_word(timeout=5)
                if not detected:
                    continue

                if on_status:
                    on_status("🎤 Conversation mode ON")

                speak("Yes, I'm listening")
                wait_until_done()
                set_speaking(False)
                clear_buffer()

                messages_history = [
                    {"role": "system", "content": "You are Remy, a helpful voice assistant. Keep answers short and friendly. Use tools when needed."}
                ]

                while _listening:
                    user_text = listen()
                    if not user_text:
                        continue

                    if any(cmd in user_text.lower() for cmd in EXIT_COMMANDS):
                        if on_status:
                            on_status("💤 Conversation mode OFF")
                        speak("Goodbye!")
                        wait_until_done()
                        set_speaking(False)
                        clear_buffer()
                        break

                    set_speaking(True)

                    if on_status:
                        on_status("⏳ Thinking...")

                    reply = chat_with_tools(
                        user_text, messages_history,
                        on_status=on_status,
                        on_sentence=lambda s: on_status(f"🔊 {s[:40]}...") if on_status else None
                    )

                    wait_until_done()
                    set_speaking(False)
                    clear_buffer()

                    if on_result:
                        on_result(user_text, reply)

                    if on_status:
                        on_status("🎤 Listening...")

            except Exception as e:
                print(f"DEBUG error: {e}")
                if on_status:
                    on_status(f"❌ Error: {e}")
                continue

        print("DEBUG: Wake word loop ended")

    threading.Thread(target=run, daemon=True).start()


def stop_wake_word_loop():
    global _listening
    _listening = False


def voice_chat(on_result=None, on_status=None):
    """One-shot voice chat with tool calling + streaming."""
    def run():
        try:
            from src.ears.listener import listen, set_speaking, clear_buffer
            from src.mouth.speaker import speak, wait_until_done

            if on_status:
                on_status("🎤 Listening...")

            user_text = listen()
            if not user_text:
                if on_status:
                    on_status("❌ No speech detected")
                return

            set_speaking(True)

            if on_status:
                on_status("⏳ Thinking...")

            messages_history = [
                {"role": "system", "content": "You are Remy, a helpful voice assistant. Keep answers short and friendly. Use tools when needed."}
            ]

            reply = chat_with_tools(
                user_text, messages_history,
                on_status=on_status,
                on_sentence=lambda s: on_status(f"🔊 {s[:40]}...") if on_status else None
            )

            wait_until_done()
            set_speaking(False)
            clear_buffer()

            if on_result:
                on_result(user_text, reply)

            if on_status:
                on_status("Ready")

        except Exception as e:
            if on_status:
                on_status(f"❌ Error: {e}")

    threading.Thread(target=run, daemon=True).start()


def run_tool(tool_name, on_result=None, on_status=None):
    """Run a specific tool via subprocess."""
    def run():
        try:
            if on_status:
                on_status(f"🛠️ Running {tool_name}...")

            tool_code = f"""
import sys
sys.path.insert(0, "{REMY_PATH}")
from src.hands.tools import {tool_name}
result = {tool_name}()
print("RESULT:" + str(result))
"""
            result = subprocess.run(
                [sys.executable, "-c", tool_code],
                capture_output=True, text=True, timeout=30
            )
            output = ""
            for line in result.stdout.split("\n"):
                if line.startswith("RESULT:"):
                    output = line[7:].strip()

            if on_result:
                on_result(tool_name, output)

            if on_status:
                on_status("Ready")

        except Exception as e:
            if on_status:
                on_status(f"❌ Error: {e}")

    threading.Thread(target=run, daemon=True).start()