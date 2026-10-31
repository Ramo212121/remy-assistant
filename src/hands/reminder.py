import threading
import time
import subprocess
from datetime import datetime
from src.memory.database import get_pending_reminders, mark_done

_started = False


def send_notification(title, message):
    """Send macOS notification. Text goes in as arguments, so it can never run as AppleScript."""
    subprocess.run([
        "osascript",
        "-e", "on run argv",
        "-e", "display notification (item 1 of argv) with title (item 2 of argv)",
        "-e", "end run",
        message, title,
    ])


def is_due(remind_at, now):
    """Compare in local time. Raises ValueError for a malformed date."""
    when = datetime.fromisoformat(remind_at)
    if when.tzinfo is not None:
        when = when.astimezone().replace(tzinfo=None)
    return when <= now


def check_once(now=None):
    now = now or datetime.now()
    for rid, remind_at, content in get_pending_reminders():
        try:
            if is_due(remind_at, now):
                print(f"🔔 Reminder: {content}")
                send_notification("Remy Reminder", content)
                mark_done(rid)
        except ValueError as e:
            # Bozuk kayıt her 30 saniyede bir hata basmasın
            print(f"⚠️ Dropping invalid reminder {rid}: {e}")
            mark_done(rid)


def check_loop():
    """Check reminders every 30 seconds."""
    while True:
        try:
            check_once()
        except Exception as e:
            print(f"⚠️ Reminder error: {e}")
        time.sleep(30)


def start_reminder_checker():
    """Start background reminder thread (only once per process)."""
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=check_loop, daemon=True).start()
    print("⏰ Reminder checker started")


if __name__ == "__main__":
    start_reminder_checker()
    time.sleep(60)
