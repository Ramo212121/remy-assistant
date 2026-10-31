"""Wake word → conversation mode loop, shared by the terminal and the desktop app."""
import threading

from src.brain.commands import is_exit_command, is_shutdown_command
from src.config import SILENCE_TIMEOUT
from src.ears import listener
from src.ears.listener import clear_buffer, listen, set_speaking
from src.ears.wake_word import load_model as load_wake_model, wait_for_wake_word
from src.mouth.speaker import load_voice, reset_interrupt, speak, wait_until_done, was_interrupted

# Yazılı mesaj ve sesli komut aynı anda konuşmasın
_turn_lock = threading.Lock()


def preload():
    """Load every local model up front, so the first reply is as fast as the rest."""
    load_voice()
    listener.preload()
    load_wake_model()


def _say(text):
    speak(text)
    _finish_speech()


def _finish_speech():
    wait_until_done()
    set_speaking(False)
    clear_buffer()


def run_turn(assistant, user_text, on_sentence=None, on_tool=None):
    """Answer one user message out loud. Returns the reply."""
    def handle_sentence(sentence):
        speak(sentence)
        if on_sentence:
            on_sentence(sentence)

    with _turn_lock:
        reset_interrupt()
        set_speaking(True)
        try:
            return assistant.respond(
                user_text, handle_sentence, should_stop=was_interrupted, on_tool=on_tool
            )
        finally:
            _finish_speech()


def run_voice_loop(assistant, is_active=lambda: True, on_state=None, on_user=None,
                   on_sentence=None, on_reply=None, on_tool=None):
    """Run until is_active() turns false or the user says a shutdown command. Returns True on shutdown."""
    def state(name):
        if on_state:
            on_state(name)

    preload()

    while is_active():
        # ─── DIŞ DÖNGÜ: Wake word bekle ───
        state("waiting")
        if not wait_for_wake_word(timeout=60, should_stop=lambda: not is_active()):
            continue

        print("\n🎤 Conversation mode ON")
        state("speaking")
        _say("Yes?")

        # ─── İÇ DÖNGÜ: Conversation mode ───
        while is_active():
            state("listening")
            user_input = listen(timeout=SILENCE_TIMEOUT, should_stop=lambda: not is_active())

            # None → sessizlik timeout'u, conversation mode kapanır
            if user_input is None:
                print("💤 Silence timeout — conversation mode OFF")
                state("speaking")
                _say("Going to sleep. Say Hey Remi when you need me.")
                break

            # Boş ses → tekrar dinle
            if not user_input.strip():
                continue

            if is_shutdown_command(user_input):
                print(f"\n🛑 Shutdown command: '{user_input}'")
                state("speaking")
                _say("Shutting down. Goodbye!")
                return True

            if is_exit_command(user_input):
                print(f"\n👋 Exit command: '{user_input}'")
                state("speaking")
                _say("Goodbye!")
                break

            print(f"\nYou: {user_input}")
            if on_user:
                on_user(user_input)

            state("thinking")
            reply = run_turn(assistant, user_input, on_sentence=on_sentence, on_tool=on_tool)
            if on_reply:
                on_reply(reply)

    return False
