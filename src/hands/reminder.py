import threading
import time
import subprocess
from datetime import datetime
from src.memory.database import get_pending_reminders, mark_done


def send_notification(title, message):
    """Send macOS notification."""
    subprocess.run([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}"'
    ])


def check_loop():
    """Check reminders every 30 seconds."""
    while True:
        now = datetime.now()
        for rid, remind_at, content in get_pending_reminders():
            try:
                if datetime.fromisoformat(remind_at) <= now:
                    print(f"🔔 Reminder: {content}")
                    send_notification("Remy Reminder", content)
                    mark_done(rid)
            except Exception as e:
                print(f"⚠️ Reminder error: {e}")
        time.sleep(30)


def start_reminder_checker():
    """Start background reminder thread."""
    threading.Thread(target=check_loop, daemon=True).start()
    print("⏰ Reminder checker started")


if __name__ == "__main__":
    start_reminder_checker()
    time.sleep(60)