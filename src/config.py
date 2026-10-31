"""Shared paths and settings. Every path is absolute so the working directory never matters."""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DB_PATH = PROJECT_ROOT / "remy.db"
VOICE_PROFILE = PROJECT_ROOT / "voice_profile.npy"
VOICE_SAMPLE = PROJECT_ROOT / "my_voice.wav"
TEMP_AUDIO = PROJECT_ROOT / "temp.flac"
TTS_MODEL = PROJECT_ROOT / "en_US-ryan-high.onnx"
ASSETS_DIR = PROJECT_ROOT / "assets"

LLM_MODEL = "openai/gpt-oss-120b"
LLM_FALLBACK_MODEL = "openai/gpt-oss-20b"  # ayrı dakikalık limiti var
STT_MODEL = "whisper-large-v3-turbo"
SILENCE_TIMEOUT = 30  # conversation mode ends after this many silent seconds

_groq_client = None


def get_groq_client():
    """Create the Groq client on first use, so a missing key is a clear error and not an import crash."""
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(f"GROQ_API_KEY is not set. Add it to {PROJECT_ROOT / '.env'}")
        _groq_client = Groq(api_key=api_key)
    return _groq_client
