"""Remy voice backend integration."""
import sys
import threading
import subprocess
import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

REMY_PATH = Path.home() / "Desktop" / "MyProjects" / "remy"
sys.path.insert(0, str(REMY_PATH))

load_dotenv(REMY_PATH / ".env")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

_listening = False

# Exit commands
EXIT_COMMANDS = ["bye jarvis", "goodbye jarvis", "exit", "stop", "sleep", "goodbye"]


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

                # 3. Continuous listening
                while _listening:
                    user_text = listen()
                    if not user_text:
                        continue

                    print(f"DEBUG: user_text={user_text}")

                    # "Bye Jarvis" said?
                    if any(cmd in user_text.lower() for cmd in EXIT_COMMANDS):
                        print("DEBUG: Exit command detected")
                        if on_status:
                            on_status("💤 Conversation mode OFF")
                        speak("Goodbye!")
                        wait_until_done()
                        set_speaking(False)
                        clear_buffer()
                        break  # Exit conversation mode

                    if on_status:
                        on_status("⏳ Thinking...")

                    # LLM
                    response = groq_client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[
                            {"role": "system", "content": "You are Remy, a helpful voice assistant. Keep answers short and friendly."},
                            {"role": "user", "content": user_text}
                        ]
                    )
                    reply = response.choices[0].message.content
                    print(f"DEBUG: reply={reply}")

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
    """One-shot voice chat (manual button)."""
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

            response = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You are Remy, a helpful voice assistant. Keep answers short and friendly."},
                    {"role": "user", "content": user_text}
                ]
            )
            reply = response.choices[0].message.content

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