import ollama

SYSTEM_PROMPT = """Sen remy'sin. Kullanıcının kişisel yapay zeka asistanısın.
Türkçe konuşursun, samimi ve kısa cevap verirsin."""

messages = [
    {'role': 'system', 'content': SYSTEM_PROMPT}
]

print("Remy hazır! (çıkmak için 'q' yaz)")
print("-" * 40)

while True:
    user_input = input("\nSen: ")
    
    if user_input.lower() == 'q':
        print("Remy: Görüşürüz kanka!")
        break
    
    messages.append({'role': 'user', 'content': user_input})
    
    response = ollama.chat(
        model='qwen2.5:7b',
        messages=messages
    )
    
    reply = response['message']['content']
    messages.append({'role': 'assistant', 'content': reply})
    
    print(f"Remy: {reply}")

