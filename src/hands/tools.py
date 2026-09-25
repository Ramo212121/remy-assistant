from datetime import datetime
import subprocess
from src.memory.database import save_reminder


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
    }
]