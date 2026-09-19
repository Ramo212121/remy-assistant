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



Tamam kanka! 🔥 O zaman **ders notu gibi** detaylı yazalım. Her günün sonunda `NOTE.md`'ye hem **ne yaptığını** hem de **kavramları** detaylı yazacaksın. Sonra tekrar ederken bu notlar çok işine yarayacak.

İşte **Gün 3 için detaylı not taslağı:**

---

```markdown
## Day 3 — Persistent Memory (SQLite)

**Date:** 2025-01-15
**Duration:** ~5 hours
**Difficulty:** 🟡 Medium

---

### 🎯 Goal

Make Remy remember conversations even after restart. Until now, memory was only in RAM (`messages` list) and lost when the program closed. Now we save everything to a database.

---

### 📖 Concepts Learned

#### 1. What is SQLite?

- **Definition:** A file-based, serverless database engine.
- **Why SQLite?**
  - No server needed (unlike MySQL/PostgreSQL)
  - Single `.db` file
  - Built into Python (`import sqlite3`)
  - Perfect for small/medium projects
- **How it works:** Python code → `sqlite3` module → `remy.db` file

#### 2. Connection & Cursor

- **`sqlite3.connect(DB_PATH)`** → Opens (or creates) a database file. Returns a **connection object** (`con`).
- **`con.cursor()`** → Creates a **cursor**. Used to execute SQL and fetch results.
- **`con.commit()`** → Saves pending changes. Without it, changes are lost.
- **`con.close()`** → Closes the connection. Frees resources.

#### 3. Placeholders (`?`)

- **What:** A safe way to pass values into SQL queries.
- **Why:** Prevents **SQL Injection** attacks.
- **Example:**
  ```python
  cur.execute("INSERT INTO users (name) VALUES (?)", ("Ramazan",))
  ```
- **Note:** Single value must be a tuple with a trailing comma: `("Ramazan",)` not `("Ramazan")`.

#### 4. SQL Commands Used

| Command | Purpose |
|---------|---------|
| `CREATE TABLE IF NOT EXISTS` | Creates table if it doesn't exist |
| `INSERT INTO ... VALUES (?, ?)` | Adds new row |
| `INSERT OR REPLACE INTO ...` | Upsert (insert or update) |
| `SELECT ... FROM ...` | Reads data |
| `ORDER BY id DESC` | Sorts newest first |
| `LIMIT ?` | Limits number of results |
| `WHERE key = ?` | Filters results |

#### 5. Fetch Methods

- **`fetchone()`** → Returns one result (or `None`). Used for single queries.
- **`fetchall()`** → Returns all results as a list of tuples.
- **`fetchmany(n)`** → Returns n results.

#### 6. Upsert (`INSERT OR REPLACE`)

- If the row exists (same primary key or unique key), it updates.
- If not, it inserts.
- Useful for `facts` table (e.g., updating user's name).

---

### 🛠️ What I Built

#### File: `src/memory/database.py`

**Tables:**
- `messages` → `id`, `role`, `content`, `timestamp`
- `facts` → `id`, `key`, `value`

**Functions:**

| Function | Purpose |
|----------|---------|
| `init_db()` | Creates both tables if they don't exist |
| `save_message(role, content)` | Saves a message with timestamp |
| `get_messages(limit=10)` | Returns last N messages (newest first) |
| `save_fact(key, value)` | Saves/updates a fact |
| `get_fact(key)` | Returns fact value or `None` |

#### File: `remy.py` (updated)

- Imports from `src.memory.database`
- Calls `init_db()` on startup
- Loads last 10 messages into `messages` list
- Saves every user message and assistant reply
- Remy now remembers after restart

---

### 🐛 Problems I Hit

#### Problem 1: `ImportError: cannot import name 'get_messages'`

- **Cause:** Python cached the old `.pyc` files.
- **Fix:**
  ```bash
  find . -type d -name "__pycache__" -exec rm -rf {} +
  ```
- **Lesson:** Always clear `__pycache__` if imports don't update.

#### Problem 2: `tutorial.py` instead of `test_db.py`

- **Cause:** Typo when creating file with `nano`.
- **Fix:** `mv tutorial.py test_db.py`

#### Problem 3: `tutorial.db` leftover

- **Cause:** Old test database file.
- **Fix:** `rm tutorial.db`

---

### ✅ Test Results

| Test | Result |
|------|--------|
| Save and load messages | ✅ |
| Save and load facts | ✅ |
| Remy remembers after restart | ✅ |
| SQL injection protection (placeholder) | ✅ |

---

### 💡 Key Takeaways

1. **SQLite is perfect for local apps** — no server, single file.
2. **Always use placeholders (`?`)** — never f-strings in SQL.
3. **Always `commit()`** — otherwise changes are lost.
4. **Always `close()`** — free resources.
5. **`INSERT OR REPLACE`** is your friend for upserts.
6. **Clear `__pycache__`** when imports misbehave.
7. **Persistent memory** makes Remy feel alive.

---

### 🔜 Next Steps (Day 4)

- Speech recognition (STT) with Whisper
- Microphone input
- Voice Activity Detection (VAD)
- Convert speech to text
- Integrate into `remy.py`

---

### 📚 Resources Used

- Python docs: `docs.python.org/3/library/sqlite3.html`
- SQLite docs: `sqlite.org/docs.html`
- Stack Overflow (for `__pycache__` issue)
```






