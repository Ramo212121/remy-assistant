"""Groq over plain urllib, so the Android build needs no compiled dependencies."""
import json
import urllib.error
import urllib.request
import uuid

API_URL = "https://api.groq.com/openai/v1"
USER_AGENT = "remy-mobile/1.0"


class GroqError(Exception):
    def __init__(self, message, status=None, code=None):
        super().__init__(message)
        self.status = status
        self.code = code

    @property
    def retryable(self):
        """Rate limits, server errors and network failures are worth another model."""
        return self.status is None or self.status == 429 or self.status >= 500


def _open(path, api_key, body, content_type, timeout):
    request = urllib.request.Request(
        f"{API_URL}/{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": content_type,
            "User-Agent": USER_AGENT,
        },
    )
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as e:
        try:
            error = json.loads(e.read().decode("utf-8", "replace")).get("error", {})
        except ValueError:
            error = {}
        raise GroqError(error.get("message", f"HTTP {e.code}"), status=e.code, code=error.get("code")) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise GroqError(f"Network error: {e}") from e


def chat_stream(api_key, model, messages, tools, tool_choice="auto", timeout=60):
    """Yield streamed chat chunks as dicts."""
    body = json.dumps({
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": tool_choice,
        "stream": True,
    }).encode("utf-8")
    with _open("chat/completions", api_key, body, "application/json", timeout) as response:
        for raw in response:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                return
            yield json.loads(data)


def transcribe(api_key, audio, filename, model="whisper-large-v3-turbo", language="en", timeout=60):
    """Send recorded audio and return the text."""
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in (("model", model), ("language", language), ("response_format", "text")):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode() + audio + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    with _open("audio/transcriptions", api_key, b"".join(parts), f"multipart/form-data; boundary={boundary}", timeout) as response:
        return response.read().decode("utf-8", "replace").strip()


def speech(api_key, text, voice, model="canopylabs/orpheus-v1-english", timeout=60):
    """Return WAV bytes for one sentence."""
    body = json.dumps({"model": model, "input": text, "voice": voice, "response_format": "wav"}).encode("utf-8")
    with _open("audio/speech", api_key, body, "application/json", timeout) as response:
        return response.read()
