import ollama
from src.memory.database import init_db, save_message, get_messages

SYSTEM_PROMPT = """Sen Remy'sin. Kullanıcının kişisel yapay zeka asistanısın.
Türkçe konuşursun, samimi ve kısa cevap verirsin."""

# Veritabanını hazırla
init_db()

# Geçmişi yükle (son 10 mesaj)
history = get_messages(limit=10)
history.reverse()  # eskiden yeniye çevir

# messages listesini oluştur
messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
for role, content in history:
    messages.append({'role': role, 'content': content})

print("Remy hazır! (çıkmak için 'q' yaz)")
print("-" * 40)

while True:
    user_input = input("\nSen: ")
    
    if user_input.lower() == 'q':
        print("Remy: Görüşürüz kanka!")
        break
    
    # Kullanıcı mesajını kaydet
    save_message('user', user_input)
    messages.append({'role': 'user', 'content': user_input})
    
    # LLM'e gönder
    response = ollama.chat(model='qwen2.5:7b', messages=messages)
    reply = response['message']['content']
    
    # Cevabı kaydet
    save_message('assistant', reply)
    messages.append({'role': 'assistant', 'content': reply})
    
    print(f"Remy: {reply}")