"""The conversation: same flow as the desktop Assistant, without the desktop's dependencies."""
import json
import re
from datetime import datetime

from remy_mobile import groq_api
from remy_mobile.tools import TOOLS, run_tool

LLM_MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b")  # ikincisinin ayrı dakikalık limiti var
MAX_MESSAGES = 12
MAX_TOOL_ROUNDS = 5
FIRST_CHUNK_CHARS = 60
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")

SYSTEM_PROMPT = """You are Remy, the user's personal AI assistant, running on their Android phone.
You speak English, friendly but not overly cheerful. Be concise.
The current date and time is {now}. Use it to resolve words like "today" or "tomorrow".

RULES:
1. NEVER use emojis, markdown or special symbols. Your replies are read aloud.
2. Do NOT start with filler like "Sure!" or "Great question!". Answer directly.
3. Keep answers SHORT: 1-3 sentences unless the user asks for detail.
4. Use "you", not "sir" or "ma'am".
5. You can only use the tools listed. You can't set alarms, send messages or control the phone. Say so when asked.

TOOLS:
- time → get_time. date or day → get_date. math → calculate.
- "open X" (a website) → open_website. "search for X" / "look up X" → search_web.

If unsure, ASK instead of guessing."""

ERROR_REPLIES = {
    "no_key": "Add your Groq API key in settings first.",
    "bad_key": "Your Groq API key was rejected. Check it in settings.",
    "busy": "I'm over my usage limit for the moment. Try again in a minute.",
    "network": "I couldn't reach the server. Check your connection.",
}


def error_reply(error):
    if error.status == 401:
        return ERROR_REPLIES["bad_key"]
    if error.status == 429:
        return ERROR_REPLIES["busy"]
    return ERROR_REPLIES["network"]


class Brain:
    def __init__(self, store, open_url, chat_stream=groq_api.chat_stream):
        self.store = store
        self.open_url = open_url
        self._chat_stream = chat_stream
        self.messages = [dict(m) for m in store.history if m.get("content")]
        self._trim()

    def respond(self, user_text, on_sentence, should_stop=lambda: False):
        """Stream the reply sentence by sentence to on_sentence and return the full text."""
        api_key = self.store.settings.get("api_key", "").strip()
        if not api_key:
            on_sentence(ERROR_REPLIES["no_key"])
            return ERROR_REPLIES["no_key"]

        checkpoint = len(self.messages)
        self.messages.append({"role": "user", "content": user_text})
        reply = ""
        try:
            for round_number in range(MAX_TOOL_ROUNDS):
                final_round = round_number == MAX_TOOL_ROUNDS - 1
                content, tool_calls = self._round(api_key, on_sentence, should_stop, final_round)
                reply = f"{reply} {content}".strip()
                if not tool_calls or should_stop():
                    break
                self.messages.append({"role": "assistant", "content": content or None, "tool_calls": tool_calls})
                for call in tool_calls:
                    self.messages.append(self._execute(call))
        except groq_api.GroqError as e:
            print(f"LLM error: {e} ({e.status})")
            del self.messages[checkpoint:]
            message = error_reply(e)
            on_sentence(message)
            return message

        if not reply:
            del self.messages[checkpoint:]
            return ""
        self.messages.append({"role": "assistant", "content": reply})
        self._trim()
        self.store.add_turn(user_text, reply)
        return reply

    def _open(self, api_key, final_round):
        """Switch model on a rate limit instead of waiting it out."""
        messages = [self._system_message()] + self.messages
        last_error = None
        for model in LLM_MODELS:
            try:
                stream = self._chat_stream(api_key, model, messages, TOOLS, "none" if final_round else "auto")
                first = next(stream, None)
                return first, stream
            except groq_api.GroqError as e:
                if not e.retryable:
                    raise
                print(f"{model} unavailable, trying next: {e}")
                last_error = e
        raise last_error

    def _round(self, api_key, on_sentence, should_stop, final_round):
        first, stream = self._open(api_key, final_round)
        buffer = ""
        content = ""
        calls = {}

        def chunks():
            if first is not None:
                yield first
            yield from stream

        for chunk in chunks():
            if should_stop():
                break
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}

            for tc in delta.get("tool_calls") or []:
                call = calls.setdefault(tc.get("index", 0), {"id": "", "name": "", "arguments": ""})
                call["id"] = tc.get("id") or call["id"]
                function = tc.get("function") or {}
                call["name"] = function.get("name") or call["name"]
                call["arguments"] += function.get("arguments") or ""

            text = delta.get("content")
            if text:
                buffer += text
                content += text
                *sentences, buffer = _SENTENCE_END.split(buffer)
                for sentence in sentences:
                    on_sentence(sentence)
                comma = buffer.rfind(", ")
                if comma >= FIRST_CHUNK_CHARS:
                    on_sentence(buffer[:comma + 1])
                    buffer = buffer[comma + 2:]

        if buffer.strip() and not should_stop():
            on_sentence(buffer.strip())

        tool_calls = [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
            for _, c in sorted(calls.items())
        ]
        return content, tool_calls

    def _execute(self, call):
        name = call["function"]["name"]
        try:
            args = json.loads(call["function"]["arguments"] or "{}")
        except ValueError:
            args = {}
        result = run_tool(name, args, self.open_url)
        print(f"Tool {name}: {result[:80]}")
        return {"role": "tool", "tool_call_id": call["id"], "content": result}

    def _system_message(self):
        now = datetime.now().strftime("%A, %B %d, %Y, %H:%M")
        return {"role": "system", "content": SYSTEM_PROMPT.format(now=now)}

    def _trim(self):
        if len(self.messages) > MAX_MESSAGES:
            self.messages = self.messages[-MAX_MESSAGES:]
        while self.messages and self.messages[0]["role"] != "user":
            self.messages.pop(0)

    def forget(self):
        self.messages = []
        self.store.clear_history()
