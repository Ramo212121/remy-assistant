import os
from datetime import datetime
import subprocess
import pymupdf as fitz
from src.memory.database import save_reminder
from ddgs import DDGS
from imapclient import IMAPClient


PROJECT_DIR = os.path.expanduser("~/Desktop/MyProjects/remy")


def get_time():
    """Get the current time."""
    now = datetime.now()
    return now.strftime("%H:%M")


def get_date():
    """Get today's date."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y")


def calculate(expression):
    """Calculate a math expression."""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def set_reminder(remind_at, content):
    """Set a reminder."""
    save_reminder(remind_at, content)
    return f"Reminder set for {remind_at}: {content}"


def open_app(app_name):
    """Open a macOS application by name."""
    try:
        subprocess.run(["open", "-a", app_name], check=True)
        return f"Opened {app_name}"
    except Exception as e:
        return f"Error: {e}"


def read_pdf(file_path):
    """Read text from a PDF file."""
    if not file_path.startswith("/"):
        file_path = os.path.join(PROJECT_DIR, file_path)

    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text[:2000]
    except Exception as e:
        return f"Error: {e}"


def web_search(query):
    """Search the web using DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))

        if not results:
            return "No results found"

        output = f"Search results for '{query}':\n\n"
        for i, r in enumerate(results, 1):
            output += f"{i}. {r['title']}\n{r['body']}\n\n"

        return output[:2000]
    except Exception as e:
        return f"Error: {e}"


def read_email(count=5):
    """Read latest unread emails from Gmail."""
    user = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not user or not password:
        return "Gmail credentials not set in .env"

    try:
        with IMAPClient("imap.gmail.com", ssl=True) as client:
            client.login(user, password)
            client.select_folder("INBOX")

            messages = client.search(["UNSEEN"])
            messages = messages[-count:]

            output = f"Latest {len(messages)} unread emails:\n\n"
            for uid, data in client.fetch(messages, ["ENVELOPE"]).items():
                env = data[b"ENVELOPE"]
                subject = env.subject.decode() if env.subject else "(no subject)"
                from_addr = env.from_[0].mailbox.decode() + "@" + env.from_[0].host.decode()
                output += f"From: {from_addr}\nSubject: {subject}\n\n"

            return output[:2000]
    except Exception as e:
        return f"Error: {e}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": "Get today's date",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Calculate a math expression like '2 + 2' or '25 * 4'",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression to calculate"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a reminder at a specific time in ISO format",
            "parameters": {
                "type": "object",
                "properties": {
                    "remind_at": {
                        "type": "string",
                        "description": "ISO datetime, e.g. '2025-09-26T14:00:00'"
                    },
                    "content": {
                        "type": "string",
                        "description": "What to remind about"
                    }
                },
                "required": ["remind_at", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open a macOS application by name",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "App name, e.g. 'Spotify', 'Safari', 'Visual Studio Code'"
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_pdf",
            "description": "Read text from a PDF file. Use only the filename (e.g. 'test.pdf'), not a full path. The PDF must be in the Remy project folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "PDF filename, e.g. 'test.pdf'"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo. Use for questions about current events, facts, or anything that needs up-to-date information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'capital of Turkey'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_email",
            "description": "Read the latest unread emails from Gmail",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of emails to read (default 5)"
                    }
                }
            }
        }
    }
]