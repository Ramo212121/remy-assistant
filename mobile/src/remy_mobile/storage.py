"""Settings and conversation history in one JSON file, in the app's private storage."""
import json
import os
from pathlib import Path

DEFAULTS = {"api_key": "", "voice": "troy", "speak_replies": True}
MAX_HISTORY = 40


def data_dir():
    # Flet sets this inside the packaged Android app; the fallback is for running on a computer
    folder = os.environ.get("FLET_APP_STORAGE_DATA") or str(Path.home() / ".remy-mobile")
    Path(folder).mkdir(parents=True, exist_ok=True)
    return Path(folder)


def temp_dir():
    folder = os.environ.get("FLET_APP_STORAGE_TEMP") or str(data_dir() / "tmp")
    Path(folder).mkdir(parents=True, exist_ok=True)
    return Path(folder)


class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_dir() / "remy.json"
        self.settings = dict(DEFAULTS)
        self.history = []
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
                self.settings.update(saved.get("settings", {}))
                self.history = saved.get("history", [])
            except (ValueError, OSError) as e:
                print(f"Store unreadable, starting fresh: {e}")

    def save(self):
        self.history = self.history[-MAX_HISTORY:]
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"settings": self.settings, "history": self.history}), encoding="utf-8")
        # Yarım yazılmış dosya kalmasın diye önce geçici dosyaya yazıp değiştiriyoruz
        os.replace(temporary, self.path)

    def add_turn(self, user_text, reply):
        self.history += [{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}]
        self.save()

    def clear_history(self):
        self.history = []
        self.save()
