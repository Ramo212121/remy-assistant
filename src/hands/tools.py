import ast
import email.header
import math
import operator
import os
from datetime import datetime, timedelta
import subprocess
import tempfile
import pymupdf as fitz
from src.config import PROJECT_ROOT
from src.memory.database import save_reminder
from ddgs import DDGS
from imapclient import IMAPClient
import base64
import threading
import time
import ollama


PROJECT_DIR = str(PROJECT_ROOT)


# ─────────────────────────────────────────
# Time / Date / Math
# ─────────────────────────────────────────

def get_time():
    """Get the current time."""
    now = datetime.now()
    return now.strftime("%H:%M")


def get_date():
    """Get today's date."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y")


_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "sqrt": math.sqrt, "abs": abs, "round": round,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "exp": math.exp,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}
MAX_POWER = 1000


def _evaluate(node):
    """Only numbers, arithmetic and whitelisted math functions. Anything else is rejected."""
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        # 9**9**9 gibi ifadeler işlemciyi kilitlemesin
        if isinstance(node.op, ast.Pow) and (abs(right) > MAX_POWER or abs(left) > 10 ** 6):
            raise ValueError("number too large")
        return _BINARY_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_evaluate(node.operand))
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCTIONS and not node.keywords):
        return _FUNCTIONS[node.func.id](*[_evaluate(arg) for arg in node.args])
    raise ValueError("only arithmetic is allowed")


def calculate(expression):
    """Calculate a math expression."""
    try:
        return str(_evaluate(ast.parse(str(expression), mode="eval")))
    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────
# Reminders
# ─────────────────────────────────────────

def set_reminder(remind_at, content):
    """Set a reminder."""
    try:
        datetime.fromisoformat(remind_at)
    except (TypeError, ValueError):
        return f"Error: '{remind_at}' is not an ISO datetime like 2026-09-26T14:00:00"
    save_reminder(remind_at, content)
    return f"Reminder set for {remind_at}: {content}"


# ─────────────────────────────────────────
# App Control
# ─────────────────────────────────────────

def open_app(app_name):
    """Open a macOS application by name."""
    try:
        subprocess.run(["open", "-a", app_name], check=True)
        return f"Opened {app_name}"
    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────
# PDF
# ─────────────────────────────────────────

def read_pdf(file_path):
    """Read text from a PDF file in the project folder."""
    file_path = os.path.realpath(os.path.join(PROJECT_DIR, file_path))
    if os.path.commonpath([file_path, os.path.realpath(PROJECT_DIR)]) != os.path.realpath(PROJECT_DIR):
        return "Error: the PDF must be in the Remy project folder"

    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text[:2000]
    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────
# Web Search
# ─────────────────────────────────────────

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


# ─────────────────────────────────────────
# Email
# ─────────────────────────────────────────

def _decode_subject(raw):
    """IMAP returns encoded words (=?UTF-8?...), so Turkish subjects need decoding."""
    if not raw:
        return "(no subject)"
    return str(email.header.make_header(email.header.decode_header(raw.decode(errors="replace"))))


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
            messages = messages[-max(1, min(int(count), 20)):]

            output = f"Latest {len(messages)} unread emails:\n\n"
            for uid, data in client.fetch(messages, ["ENVELOPE"]).items():
                env = data[b"ENVELOPE"]
                subject = _decode_subject(env.subject)
                from_addr = env.from_[0].mailbox.decode() + "@" + env.from_[0].host.decode()
                output += f"From: {from_addr}\nSubject: {subject}\n\n"

            return output[:2000]
    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────
# Vision (Screen)
# ─────────────────────────────────────────

def analyze_screen():
    """Take a screenshot and analyze it with vision model."""
    try:
        # Sabit /tmp yolu başka kullanıcılar tarafından okunabilir
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "screen.png")
            subprocess.run(["screencapture", "-x", path], check=True)
            with open(path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()

        response = ollama.chat(
            model="moondream",
            messages=[{
                "role": "user",
                "content": "What's on this screen? Describe it briefly.",
                "images": [image_data]
            }]
        )

        return response['message']['content']
    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────
# Volume
# ─────────────────────────────────────────

def _percent(level):
    """Clamp a model-supplied level to an int between 0 and 100."""
    return max(0, min(100, int(float(level))))


def set_volume(level):
    """Set system volume (0-100)."""
    try:
        level = _percent(level)
        subprocess.run(
            ["osascript", "-e", f"set volume output volume {level}"],
            check=True
        )
        return f"Volume set to {level}%"
    except Exception as e:
        return f"Error: {e}"


def mute():
    """Mute system volume."""
    try:
        subprocess.run(
            ["osascript", "-e", "set volume output muted true"],
            check=True
        )
        return "Muted"
    except Exception as e:
        return f"Error: {e}"


def unmute():
    """Unmute system volume."""
    try:
        subprocess.run(
            ["osascript", "-e", "set volume output muted false"],
            check=True
        )
        return "Unmuted"
    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────
# Brightness
# ─────────────────────────────────────────

def set_brightness(level):
    """Set screen brightness (0-100)."""
    try:
        level = _percent(level)
        brightness = level / 100
        subprocess.run(["brightness", str(brightness)], check=True)
        return f"Brightness set to {level}%"
    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────
# System Control
# ─────────────────────────────────────────

def sleep_mac():
    """Put Mac to sleep."""
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to sleep'],
            check=True
        )
        return "Sleeping"
    except Exception as e:
        return f"Error: {e}"


def lock_screen():
    """Lock the screen."""
    try:
        # CGSession yeni macOS'ta yok; bu, sistemin Ctrl+Cmd+Q kısayolu
        # (uygulamanın Erişilebilirlik izni olmalı)
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to keystroke "q" using {control down, command down}'
        ], check=True, capture_output=True)
        return "Screen locked"
    except subprocess.CalledProcessError:
        # İzin yoksa ekranı kapat; parola ayarı açıksa bu da kilitler
        subprocess.run(["pmset", "displaysleepnow"], check=True)
        return "Display turned off. Grant Accessibility permission for a guaranteed lock."
    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────
# Alarm
# ─────────────────────────────────────────

def set_alarm(alarm_time, message="Wake up!"):
    """Set an alarm at the next occurrence of HH:MM."""
    target = next_alarm_time(alarm_time)
    if target is None:
        return f"Error: '{alarm_time}' is not a time in HH:MM format"

    def alarm_loop():
        while datetime.now() < target:
            time.sleep(5)
        subprocess.run(["say", message])

    threading.Thread(target=alarm_loop, daemon=True).start()
    return f"Alarm set for {target.strftime('%A %H:%M')}"


def next_alarm_time(alarm_time, now=None):
    """Next datetime matching HH:MM, or None if the format is wrong."""
    now = now or datetime.now()
    try:
        parsed = datetime.strptime(str(alarm_time).strip(), "%H:%M")
    except ValueError:
        return None
    target = now.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


# ─────────────────────────────────────────
# TOOLS (JSON schema for Groq)
# ─────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time. Use when user asks 'what time is it'.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": "Get today's date. Use when user asks 'what's today's date'.",
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
            "description": "Set a reminder at a specific time in ISO format. Use when user says 'remind me'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "remind_at": {
                        "type": "string",
                        "description": "ISO datetime in local time, e.g. '2026-09-26T14:00:00'"
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
            "description": "ONLY use this when the user explicitly says 'open <app>' or 'launch <app>'. Do NOT use for alarm, reminder, time, date, math, or any other request.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_screen",
            "description": "Take a screenshot and describe what's on the screen",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set system volume (0-100)",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Volume level 0-100"
                    }
                },
                "required": ["level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mute",
            "description": "Mute system volume",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "unmute",
            "description": "Unmute system volume",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_brightness",
            "description": "Set screen brightness (0-100)",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Brightness level 0-100"
                    }
                },
                "required": ["level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sleep_mac",
            "description": "Put Mac to sleep",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_screen",
            "description": "Lock the screen",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_alarm",
            "description": "Use this when the user says 'set alarm', 'wake me up at', or 'alarm for'. This sets a spoken alarm within the next 24 hours. Do NOT use it for 'remind me'. Do NOT open any app.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alarm_time": {
                        "type": "string",
                        "description": "Time in HH:MM format, e.g. '07:00'"
                    },
                    "message": {
                        "type": "string",
                        "description": "Alarm message (default: Wake up!)"
                    }
                },
                "required": ["alarm_time"]
            }
        }
    }
]


TOOL_FUNCTIONS = {
    "get_time": get_time,
    "get_date": get_date,
    "calculate": calculate,
    "set_reminder": set_reminder,
    "open_app": open_app,
    "read_pdf": read_pdf,
    "web_search": web_search,
    "read_email": read_email,
    "analyze_screen": analyze_screen,
    "set_volume": set_volume,
    "mute": mute,
    "unmute": unmute,
    "set_brightness": set_brightness,
    "sleep_mac": sleep_mac,
    "lock_screen": lock_screen,
    "set_alarm": set_alarm,
}


def run_tool(name, args=None):
    """Run a tool by name. Failures come back as text the model can explain to the user."""
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return f"Error: unknown tool {name}"
    try:
        return str(function(**(args or {})))
    except Exception as e:
        return f"Error: {e}"
