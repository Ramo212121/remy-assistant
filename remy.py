import ollama
from src.memory.database import init_db, save_message, get_messages
from src.ears.listener import listen, _stream, set_speaking, clear_buffer
from src.mouth.speaker import speak, wait_until_done
from src.hands.tools import (
    get_time, get_date, calculate, set_reminder,
    open_app, read_pdf, web_search, read_email, analyze_screen,
    set_volume, mute, unmute, set_brightness, sleep_mac, lock_screen, set_alarm,
    TOOLS
)
from src.hands.reminder import start_reminder_checker

SYSTEM_PROMPT = """You are Remy. You are the user's personal AI assistant.
You speak English, friendly and concise.

IMPORTANT RULES — follow these strictly:
- "read PDF" → use read_pdf with filename. Do NOT open Safari.
- "open <app>" → use open_app tool ONLY when user says "open" or "launch".
- time/date → get_time / get_date.
- math → calculate.
- reminder → set_reminder.
- "what's on my screen" → analyze_screen.
- volume/mute → set_volume / mute / unmute.
- brightness → set_brightness.
- sleep/lock → sleep_mac / lock_screen.
- "set alarm" / "wake me up" → use set_alarm tool. NEVER use open_app for alarm.
- If unsure, ASK the user instead of guessing."""

init_db()
start_reminder_checker()

history = get_messages(limit=10)
history.reverse()

messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
for role, content in history:
    messages.append({'role': role, 'content': content})

print("Remy is ready! (say 'quit' to exit)")
print("-" * 40)


def handle_tool_calls(response):
    """Execute tool calls and return results."""
    tool_calls = response['message'].get('tool_calls', [])
    results = []

    for call in tool_calls:
        name = call.function.name
        args = call.function.arguments

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

        print(f"🛠️ Tool: {name} → {result[:100]}")

        results.append({
            'role': 'tool',
            'content': result
        })

    return results


try:
    while True:
        user_input = listen()

        if not user_input or user_input.strip().lower() in ['quit', 'exit', 'q', 'stop', 'goodbye', 'bye']:
            speak("Goodbye!")
            wait_until_done()
            break

        print(f"\nYou: {user_input}")

        save_message('user', user_input)
        messages.append({'role': 'user', 'content': user_input})

        set_speaking(True)

        print("⏳ Thinking...")
        response = ollama.chat(model='qwen2.5:7b', messages=messages, tools=TOOLS)

        if response['message'].get('tool_calls'):
            tool_results = handle_tool_calls(response)
            messages.append(response['message'])
            messages.extend(tool_results)
            response = ollama.chat(model='qwen2.5:7b', messages=messages, tools=TOOLS)

        reply = response['message']['content']
        print(f"🔊 Remy: {reply}")
        speak(reply)

        wait_until_done()
        clear_buffer()
        set_speaking(False)

        save_message('assistant', reply)
        messages.append({'role': 'assistant', 'content': reply})

except KeyboardInterrupt:
    print("\n\n👋 Interrupted by user.")

finally:
    if _stream is not None:
        _stream.stop()
        _stream.close()
        print("\n🔇 Stream closed.")