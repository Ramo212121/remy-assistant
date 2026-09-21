import ollama
from src.memory.database import init_db, save_message, get_messages
from src.ears.listener import listen, _stream, set_speaking, clear_buffer
from src.mouth.speaker import speak, wait_until_done

SYSTEM_PROMPT = """You are Remy. You are the user's personal AI assistant.
You speak English, friendly and concise."""

init_db()

history = get_messages(limit=10)
history.reverse()

messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
for role, content in history:
    messages.append({'role': role, 'content': content})

print("Remy is ready! (say 'quit' to exit)")
print("-" * 40)

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
        
        # Remy konuşmaya başlıyor → mikrofonu yoksay
        set_speaking(True)
        
        # Tam cevap al (streaming yok)
        print("⏳ Thinking...")
        response = ollama.chat(model='qwen2.5:7b', messages=messages)
        reply = response['message']['content']
        
        
        speak(reply)
        
        # TTS bitene kadar bekle
        wait_until_done()
        
        # Buffer'ı temizle
        clear_buffer()
        
        # Remy sustu → mikrofonu tekrar dinle
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