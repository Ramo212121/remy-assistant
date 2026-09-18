# Remy Development Notes

Daily log of what I learn, build, and debug while creating Remy — a fully local, privacy-first AI voice assistant for macOS.

---

## Day 1 — Ollama Setup and First Model

**Date:** (today's date)

### What I did
- Installed Homebrew (package manager for macOS)
- Installed Ollama (`brew install ollama`)
- Started Ollama service (`brew services start ollama`)
- Pulled the qwen2.5:7b model (`ollama pull qwen2.5:7b`)
- Tested the model from the terminal

### What I learned
- **LLM:** Large Language Model — the brain of the AI
- **Ollama:** A runtime that runs LLMs locally on your machine
- **Model:** A trained AI file (qwen2.5:7b = 7 billion parameters)
- **brew vs pip:** brew installs applications, pip installs Python packages
- **Service:** A program that runs continuously in the background

### Problems I hit
- `brew` command was not recognized at first → added it to PATH
- Mac froze when the model loaded (8GB RAM limit)
- Fix: shortened `OLLAMA_KEEP_ALIVE` so the model unloads from RAM automatically

### Test results
- Turkish: ✅ Good
- English: ✅ Good
- Memory: ✅ Works within a session
- Speed: ⚠️ A bit slow on 8GB RAM

---

## Day 2 — Python + Ollama Integration

**Date:** (today's date)

### What I did
- Created the `remy` project folder on Desktop
- Set up a Python virtual environment (venv)
- Installed the `ollama` Python package
- Wrote `remy.py` — a chat loop with system prompt and memory

### What I learned
- **venv:** An isolated Python environment for the project
- **ollama.chat():** Function that sends messages to the model
- **messages list:** Conversation history (memory)
- **system prompt:** Defines the model's personality and rules
- **role: system/user/assistant:** Who sent the message

### Code structure
```python
import ollama

SYSTEM_PROMPT = "You are Remy..."
messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]

while True:
    user_input = input("You: ")
    if user_input == 'q': break
    messages.append({'role': 'user', 'content': user_input})
    response = ollama.chat(model='qwen2.5:7b', messages=messages)
    reply = response['message']['content']
    messages.append({'role': 'assistant', 'content': reply})
    print(f"Remy: {reply}")
