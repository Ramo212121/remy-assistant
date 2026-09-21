import sqlite3
from datetime import datetime

DB_PATH = "remy.db"

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, role TEXT, content TEXT, timestamp TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY, key TEXT, value TEXT)")
    con.commit()
    con.close()

def save_message(role, content):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    timestamp = datetime.now().isoformat()
    cur.execute("INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)", 
                (role, content, timestamp))
    con.commit()
    con.close()

def get_messages(limit=10):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    messages = cur.fetchall()
    con.close()
    return messages

def save_fact(key, value):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO facts (key, value) VALUES (?, ?)", (key, value))
    con.commit()
    con.close()

def get_fact(key):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT value FROM facts WHERE key = ?", (key,))
    result = cur.fetchone()
    con.close()
    return result[0] if result else None