"""Terminal entry point: python remy.py"""
from src.brain.assistant import Assistant
from src.brain.voice_loop import run_voice_loop
from src.ears.listener import close_stream
from src.hands.reminder import start_reminder_checker
from src.memory.database import init_db


def main():
    init_db()
    start_reminder_checker()
    assistant = Assistant()

    print("Remy is ready!")
    print("Say 'Hey Remy' to start. Say 'bye' to end. Say 'shutdown remy' to quit.")
    print("-" * 40)

    try:
        run_voice_loop(assistant)
        print("👋 Remy shutting down...")
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user.")
    finally:
        close_stream()
        print("\n🔇 Stream closed.")


if __name__ == "__main__":
    main()
