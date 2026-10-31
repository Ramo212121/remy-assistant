"""Exit / shutdown voice commands. The whole utterance must match, so 'that was quite good' is not 'quit'."""
import re

# Conversation mode'u kapatır, wake word bekleme moduna döner
# "sleep" burada yok: o komut sleep_mac tool'una gider
EXIT_COMMANDS = {
    "bye", "bye bye", "goodbye", "bye remy", "goodbye remy",
    "stop", "stop listening", "thats all", "im done", "i am done",
    "end conversation", "see you", "see ya",
    "talk to you later", "catch you later",
    "good night", "goodnight",
}

# Programı tamamen kapatır
SHUTDOWN_COMMANDS = {
    "shutdown remy", "shut down remy", "shut down",
    "shutdown", "quit remy", "quit", "exit remy", "exit",
    "power off remy", "turn off remy", "kill remy",
    "close remy", "terminate remy",
}


def _normalize(text):
    text = text.lower().replace("'", "").replace("’", "")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\bremi\b", "remy", text)
    return " ".join(text.split())


def is_exit_command(text):
    """Check if user wants to end the conversation."""
    return bool(text) and _normalize(text) in EXIT_COMMANDS


def is_shutdown_command(text):
    """Check if user wants to shut down the program."""
    return bool(text) and _normalize(text) in SHUTDOWN_COMMANDS
