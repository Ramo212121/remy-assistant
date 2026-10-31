"""Bridge between the Flet UI and the Remy backend. Every call runs off the UI thread."""
import os
import subprocess
import threading
import time

from src.memory.database import get_messages, init_db


RESTART_DELAY_SECONDS = 2


class RemyService:
    def __init__(self, on_state, on_message, on_sentence):
        """
        on_state(name): idle | waiting | listening | thinking | speaking | error text
        on_message(role, text): a finished chat message (role: user | remy | tool)
        on_sentence(text): one sentence of the reply that is being spoken
        """
        self._on_state = on_state
        self._on_message = on_message
        self._on_sentence = on_sentence
        self._assistant = None
        self._voice_active = False
        self._voice_thread = None
        self._caffeinate = None
        self._init_lock = threading.Lock()
        init_db()

    # ─── Yavaş import'lar (torch, resemblyzer) pencere açıldıktan sonra yüklenir ───
    def _get_assistant(self):
        with self._init_lock:
            if self._assistant is None:
                from src.brain.voice_loop import preload
                from src.brain.assistant import Assistant
                from src.hands.reminder import start_reminder_checker
                start_reminder_checker()
                preload()
                self._assistant = Assistant()
            return self._assistant

    def start_background(self):
        """Start the reminder checker and load the backend as soon as the window is up."""
        threading.Thread(target=self._get_assistant, daemon=True).start()

    def history(self, limit=10):
        """Recent messages, oldest first, for the transcript."""
        return list(reversed(get_messages(limit=limit)))

    @property
    def voice_active(self):
        return self._voice_active

    def _after_turn(self):
        self._on_state("waiting" if self._voice_active else "idle")

    def send_text(self, text):
        """Answer a typed message."""
        def run():
            try:
                self._on_message("user", text)
                self._on_state("thinking")
                assistant = self._get_assistant()
                from src.brain.voice_loop import run_turn
                reply = run_turn(
                    assistant, text,
                    on_sentence=self._sentence, on_tool=self._tool,
                )
                self._on_message("remy", reply)
                self._after_turn()
            except Exception as e:
                self._on_state(f"Error: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _sentence(self, sentence):
        self._on_state("speaking")
        self._on_sentence(sentence)

    def _tool(self, name, result):
        print(f"🛠️ {name}: {result[:80]}")

    def start_voice(self):
        """Start wake word + conversation mode."""
        if self._voice_active:
            return
        self._voice_active = True
        # Hızlı kapat-aç: eski döngü henüz bitmediyse ikinci bir döngü başlatma
        if self._voice_thread is not None and self._voice_thread.is_alive():
            return

        self._keep_awake()

        def run():
            # Mikrofon hatası hep-dinle modunu sessizce kapatmasın
            while self._voice_active:
                try:
                    from src.brain.voice_loop import run_voice_loop
                    from src.ears.listener import close_stream
                    try:
                        shutdown = run_voice_loop(
                            self._get_assistant(),
                            is_active=lambda: self._voice_active,
                            on_state=self._on_state,
                            on_user=lambda text: self._on_message("user", text),
                            on_sentence=self._sentence,
                            on_reply=lambda reply: self._on_message("remy", reply),
                            on_tool=self._tool,
                        )
                    finally:
                        close_stream()
                    if shutdown:
                        self._voice_active = False
                except Exception as e:
                    print(f"⚠️ Voice loop error: {e}")
                    self._on_state(f"Error: {e}")
                    time.sleep(RESTART_DELAY_SECONDS)
            self._release_awake()
            self._on_state("idle")

        self._voice_thread = threading.Thread(target=run, daemon=True)
        self._voice_thread.start()

    def _keep_awake(self):
        """A sleeping Mac can't hear anything. caffeinate exits with this process."""
        if self._caffeinate is None:
            self._caffeinate = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])

    def _release_awake(self):
        if self._caffeinate is not None:
            self._caffeinate.terminate()
            self._caffeinate = None

    def stop_voice(self):
        self._voice_active = False
        self.stop_speaking()

    def stop_speaking(self):
        from src.mouth.speaker import interrupt
        interrupt()

    def run_tool(self, label, name, args=None):
        """Run a quick action and show the result as a chat message."""
        def run():
            from src.hands.tools import run_tool
            self._on_state("thinking")
            self._on_message("tool", f"{label}: {run_tool(name, args)}")
            self._after_turn()

        threading.Thread(target=run, daemon=True).start()
