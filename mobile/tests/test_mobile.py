import io
import json
import urllib.error

import pytest

from remy_mobile import brain as brain_module
from remy_mobile import groq_api, tools
from remy_mobile.brain import Brain
from remy_mobile.storage import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "remy.json")
    s.settings["api_key"] = "test-key"
    return s


def text(t):
    return {"choices": [{"delta": {"content": t}}]}


def tool_call(name, arguments):
    return {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {"name": name, "arguments": arguments}}]}}]}


class FakeChat:
    def __init__(self, *rounds):
        self.rounds = list(rounds)
        self.models = []

    def __call__(self, api_key, model, messages, tools_, tool_choice):
        self.models.append(model)
        self.last_messages = messages
        round_ = self.rounds.pop(0)
        if isinstance(round_, Exception):
            raise round_
        return iter(round_)


def make_brain(store, *rounds, opened=None):
    chat = FakeChat(*rounds)
    return Brain(store, (opened if opened is not None else []).append, chat_stream=chat), chat


# ─── brain ───
def test_reply_streams_sentences_and_is_remembered(store, tmp_path):
    bot, _ = make_brain(store, [text("Pi is 3."), text("14. "), text("Done.")])
    said = []
    assert bot.respond("hi", said.append) == "Pi is 3.14. Done."
    assert said == ["Pi is 3.14.", "Done."]
    assert Store(tmp_path / "remy.json").history[-1] == {"role": "assistant", "content": "Pi is 3.14. Done."}


def test_tool_round(store):
    bot, chat = make_brain(store, [tool_call("calculate", '{"expression": "6*7"}')], [text("It's 42.")])
    assert bot.respond("6 times 7?", lambda s: None) == "It's 42."
    assert chat.last_messages[-1]["content"] == "42"


def test_rate_limit_switches_model(store):
    bot, chat = make_brain(store, groq_api.GroqError("limit", status=429), [text("Ok.")])
    assert bot.respond("hi", lambda s: None) == "Ok."
    assert chat.models == list(brain_module.LLM_MODELS)


def test_bad_key_does_not_try_second_model(store):
    bot, chat = make_brain(store, groq_api.GroqError("nope", status=401))
    said = []
    assert bot.respond("hi", said.append) == brain_module.ERROR_REPLIES["bad_key"]
    assert said == [brain_module.ERROR_REPLIES["bad_key"]]
    assert len(chat.models) == 1
    assert bot.messages == []


def test_missing_key_never_calls_api(store):
    store.settings["api_key"] = ""
    bot, chat = make_brain(store)
    assert bot.respond("hi", lambda s: None) == brain_module.ERROR_REPLIES["no_key"]
    assert chat.models == []


def test_stop_ends_reply(store):
    flag = {"stop": False}

    def chunks():
        yield text("First. ")
        flag["stop"] = True
        yield text("Second.")

    bot, _ = make_brain(store, chunks())
    said = []
    bot.respond("hi", said.append, should_stop=lambda: flag["stop"])
    assert said == ["First."]


def test_open_website_tool_uses_browser(store):
    opened = []
    bot, _ = make_brain(store, [tool_call("open_website", '{"url": "youtube.com"}')], [text("Opened.")], opened=opened)
    bot.respond("open youtube", lambda s: None)
    assert opened == ["https://youtube.com"]


# ─── tools ───
@pytest.mark.parametrize("expression", ["__import__('os').system('x')", "9**9**9", "(1).__class__"])
def test_calculate_is_safe(expression):
    assert tools.calculate(expression).startswith("Error")


@pytest.mark.parametrize("url", ["tel:123", "sms:123", "intent://x", "javascript:alert(1)", "file:///etc/passwd"])
def test_only_web_links_open(url):
    opened = []
    assert tools.open_website(url, opened.append).startswith("Error")
    assert opened == []


def test_every_schema_has_a_function():
    assert {t["function"]["name"] for t in tools.TOOLS} == set(tools.TOOL_FUNCTIONS)


# ─── storage ───
def test_store_round_trip_and_history_cap(tmp_path):
    s = Store(tmp_path / "remy.json")
    for i in range(50):
        s.add_turn(f"q{i}", f"a{i}")
    again = Store(tmp_path / "remy.json")
    assert len(again.history) == 40
    assert again.history[-1]["content"] == "a49"


def test_corrupt_store_starts_fresh(tmp_path):
    (tmp_path / "remy.json").write_text("{not json")
    assert Store(tmp_path / "remy.json").history == []


# ─── groq_api over a fake network ───
class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def test_stream_parsing(monkeypatch):
    body = b'data: {"choices":[{"delta":{"content":"Hi"}}]}\n\n: keep-alive\n\ndata: [DONE]\n\n'
    monkeypatch.setattr(groq_api.urllib.request, "urlopen", lambda req, timeout: FakeResponse(body))
    assert list(groq_api.chat_stream("k", "m", [], [])) == [{"choices": [{"delta": {"content": "Hi"}}]}]


def test_http_error_becomes_groq_error(monkeypatch):
    def fail(req, timeout):
        payload = json.dumps({"error": {"message": "terms", "code": "model_terms_required"}}).encode()
        raise urllib.error.HTTPError(req.full_url, 400, "Bad", {}, io.BytesIO(payload))

    monkeypatch.setattr(groq_api.urllib.request, "urlopen", fail)
    with pytest.raises(groq_api.GroqError) as error:
        groq_api.speech("k", "hello", "troy")
    assert (error.value.status, error.value.code, error.value.retryable) == (400, "model_terms_required", False)


def test_transcribe_sends_multipart(monkeypatch):
    seen = {}

    def capture(req, timeout):
        seen["body"], seen["type"] = req.data, req.get_header("Content-type")
        return FakeResponse(b"what time is it\n")

    monkeypatch.setattr(groq_api.urllib.request, "urlopen", capture)
    assert groq_api.transcribe("k", b"RIFF....", "a.wav") == "what time is it"
    assert seen["type"].startswith("multipart/form-data; boundary=")
    assert b'name="file"; filename="a.wav"' in seen["body"] and b"RIFF...." in seen["body"]
