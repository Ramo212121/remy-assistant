import sqlite3

DB_PATH = "remy.db"

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (name TEXT, city TEXT, age INTEGER, job TEXT)")
    con.commit()
    con.close()

def add_user(name, city, age, job):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT INTO users (name, city, age, job) VALUES (?, ?, ?, ?)", 
                (name, city, age, job))
    con.commit()
    con.close()

def get_users():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    con.close()
    return users

if __name__ == "__main__":
    init_db()
    add_user("Ramazan", "İstanbul", 25, "Developer")    
    print(get_users())
