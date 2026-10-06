"""Remy voice backend integration with tool calling."""
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


def handle_tool_calls(response, on_status=None):
    """Execute tool calls from Groq response."""
    from src.hands.tools import (
        get_time, get_date, calculate, set_reminder,
        open_app, read_pdf, web_search, read_email, analyze_screen,
        set_volume, mute, unmute, set_brightness, sleep_mac, lock_screen, set_alarm,
    )
    
    tool_calls = response.choices[0].message.tool_calls
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
        
        print(f"🛠️ Result: {result[:80]}")
        
        results.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": str(result)
        })
    
    return results


def chat_with_tools(user_text, messages_history, on_status=None):
    """Chat with LLM + tool calling."""
    from src.hands.tools import TOOLS
    
    if on_status:
        on_status("⏳ Thinking...")
    
    # İlk çağrı
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages_history,
        tools=TOOLS,
        tool_choice="auto"
    )
    
    msg = response.choices[0].message
    
    # Tool call var mı?
    if msg.tool_calls:
        tool_results = handle_tool_calls(response, on_status)
        
        # Tool sonuçlarını geçmişe ekle
        messages_history.append({
            "role": "assistant",
            "content": None,
            "tool_calls": msg.tool_calls
        })
        messages_history.extend(tool_results)
        
        # Tekrar LLM'e gönder
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages_history,
            tools=TOOLS
        )
        msg = response.choices[0].message
    
    reply = msg.content or "Done."
    return reply


def start_wake_word_loop(on_result=None, on_status=None):
    """Start continuous wake word detection loop with conversation mode."""
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
                # 1. Wait for "Hey Jarvis"
                print("DEBUG: Waiting for 'Hey Jarvis'...")
                if on_status:
                    on_status("💤 Say 'Hey Jarvis'...")

                detected = wait_for_wake_word(timeout=5)
                if not detected:
                    continue

                # 2. Conversation mode ON
                print("DEBUG: Conversation mode ON")
                if on_status:
                    on_status("🎤 Conversation mode ON")

                speak("Yes, I'm listening")
                wait_until_done()
                set_speaking(False)
                clear_buffer()

                # Konuşma geçmişi
                messages_history = [
                    {"role": "system", "content": "You are Remy, a helpful voice assistant. Keep answers short and friendly. Use tools when needed."}
                ]

                # 3. Continuous listening
                while _listening:
                    user_text = listen()
                    if not user_text:
                        continue

                    print(f"DEBUG: user_text={user_text}")

                    # Exit command?
                    if any(cmd in user_text.lower() for cmd in EXIT_COMMANDS):
                        print("DEBUG: Exit command detected")
                        if on_status:
                            on_status("💤 Conversation mode OFF")
                        speak("Goodbye!")
                        wait_until_done()
                        set_speaking(False)
                        clear_buffer()
                        break

                    # Kullanıcı mesajını geçmişe ekle
                    messages_history.append({"role": "user", "content": user_text})

                    # LLM + tool calling
                    reply = chat_with_tools(user_text, messages_history, on_status)
                    print(f"DEBUG: reply={reply}")

                    # Cevabı geçmişe ekle
                    messages_history.append({"role": "assistant", "content": reply})

                    if on_status:
                        on_status("🔊 Speaking...")

                    # TTS
                    set_speaking(True)
                    speak(reply)
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
    """One-shot voice chat with tool calling."""
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

            if on_status:
                on_status("⏳ Thinking...")

            messages_history = [
                {"role": "system", "content": "You are Remy, a helpful voice assistant. Keep answers short and friendly. Use tools when needed."},
                {"role": "user", "content": user_text}
            ]

            reply = chat_with_tools(user_text, messages_history, on_status)

            if on_status:
                on_status("🔊 Speaking...")

            set_speaking(True)
            speak(reply)
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