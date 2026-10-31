import sqlite3
from datetime import datetime
from types import SimpleNamespace as NS

import groq
import httpx
import pytest

from src.brain import assistant as assistant_module
from src.brain.assistant import MAX_MESSAGES, Assistant
from src.brain.commands import is_exit_command, is_shutdown_command
from src.config import LLM_FALLBACK_MODEL, LLM_MODEL
from src.ears import wake_word
from src.ears.wake_word import WAKE_PATTERN
from src.hands import reminder, tools
from src.memory import database


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "remy.db")
    database.init_db()


# ─── calculate ───
@pytest.mark.parametrize("expression,expected", [
    ("2 + 2", "4"), ("25 * 4", "100"), ("(1 + 2) ** 2", "9"), ("sqrt(16)", "4.0"), ("-3 % 2", "1"),
])
def test_calculate_math(expression, expected):
    assert tools.calculate(expression) == expected


@pytest.mark.parametrize("expression", [
    "__import__('os').system('touch /tmp/remy_pwned')",
    "open('/etc/passwd').read()",
    "(1).__class__",
    "9**9**9",
    "'a' * 5",
])
def test_calculate_rejects_everything_else(expression):
    assert tools.calculate(expression).startswith("Error")


# ─── commands ───
@pytest.mark.parametrize("text", ["that was quite good", "put my mac to sleep",
                                  "how do I stop a python loop", "maybe exit later"])
def test_normal_sentences_are_not_commands(text):
    assert not is_exit_command(text)
    assert not is_shutdown_command(text)


@pytest.mark.parametrize("text", ["Goodbye.", "Bye, Remy!", "That's all.", "stop"])
def test_exit_commands(text):
    assert is_exit_command(text)


@pytest.mark.parametrize("text", ["Quit.", "Shut down Remi.", "exit"])
def test_shutdown_commands(text):
    assert is_shutdown_command(text)


# ─── wake word ───
@pytest.mark.parametrize("text,expected", [
    ("hey remy", True), ("hey remi", True), ("oh hey remy", True), ("hi remy", True),
    ("hey jarvis", False), ("remy", False), ("hey jimmy", False), ("hey remember", False),
])
def test_wake_pattern(text, expected):
    assert bool(WAKE_PATTERN.search(text)) is expected


def transcripts(monkeypatch, fast, accurate):
    heard = {"fast": fast, "accurate": accurate}
    calls = []

    def fake(model, audio):
        calls.append(model)
        return heard[model]

    monkeypatch.setattr(wake_word, "load_model", lambda: None)
    monkeypatch.setattr(wake_word, "_transcribe", fake)
    monkeypatch.setattr(wake_word, "_fast_model", "fast")
    monkeypatch.setattr(wake_word, "_accurate_model", "accurate")
    return calls


def test_clear_wake_phrase_skips_slow_model(monkeypatch):
    calls = transcripts(monkeypatch, "hey remy", "unused")
    assert wake_word.is_wake_phrase(None) is True
    assert calls == ["fast"]


def test_unclear_hey_gets_second_pass(monkeypatch):
    calls = transcripts(monkeypatch, "hey ready", "hey remy")
    assert wake_word.is_wake_phrase(None) is True
    assert calls == ["fast", "accurate"]


def test_normal_speech_never_loads_slow_model(monkeypatch):
    calls = transcripts(monkeypatch, "what time is it", "hey remy")
    assert wake_word.is_wake_phrase(None) is False
    assert calls == ["fast"]


# ─── tools ───
def test_read_pdf_stays_in_project():
    assert "must be in the Remy project folder" in tools.read_pdf("../../secret.pdf")
    assert "must be in the Remy project folder" in tools.read_pdf("/etc/secret.pdf")


def test_run_tool_reports_bad_calls():
    assert tools.run_tool("nope").startswith("Error")
    assert tools.run_tool("web_search").startswith("Error")


def test_every_schema_has_a_function():
    assert {t["function"]["name"] for t in tools.TOOLS} == set(tools.TOOL_FUNCTIONS)


def test_alarm_time():
    now = datetime(2026, 1, 1, 8, 0)
    assert tools.next_alarm_time("7:00", now) == datetime(2026, 1, 2, 7, 0)
    assert tools.next_alarm_time("09:30", now) == datetime(2026, 1, 1, 9, 30)
    assert tools.next_alarm_time("soon", now) is None


def test_set_reminder_rejects_bad_date():
    assert tools.set_reminder("tomorrow", "x").startswith("Error")
    assert database.get_pending_reminders() == []


# ─── reminders ───
def test_notification_cannot_inject_applescript(monkeypatch):
    calls = []
    monkeypatch.setattr(reminder.subprocess, "run", lambda cmd: calls.append(cmd))
    evil = '" & (do shell script "touch /tmp/x") & "'
    reminder.send_notification("Title", evil)
    assert evil in calls[0]
    assert not any(evil in part for part in calls[0] if part.startswith("display"))


def test_due_reminder_fires_once_and_bad_rows_are_dropped(monkeypatch):
    sent = []
    monkeypatch.setattr(reminder, "send_notification", lambda t, m: sent.append(m))
    database.save_reminder("2026-01-01T10:00:00+03:00", "aware")
    database.save_reminder("not a date", "broken")
    database.save_reminder("2999-01-01T10:00:00", "future")
    reminder.check_once(datetime(2026, 6, 1))
    reminder.check_once(datetime(2026, 6, 1))
    assert sent == ["aware"]
    assert [row[2] for row in database.get_pending_reminders()] == ["future"]


def test_save_fact_overwrites():
    database.save_fact("name", "a")
    database.save_fact("name", "b")
    assert database.get_fact("name") == "b"
    with sqlite3.connect(database.DB_PATH) as con:
        assert con.execute("SELECT count(*) FROM facts").fetchone()[0] == 1


# ─── assistant ───
def text_chunk(text):
    return NS(choices=[NS(delta=NS(content=text, tool_calls=None))])


def tool_chunk(name, arguments, call_id="call_1"):
    tc = NS(index=0, id=call_id, function=NS(name=name, arguments=arguments))
    return NS(choices=[NS(delta=NS(content=None, tool_calls=[tc]))])


class FakeClient:
    def __init__(self, *rounds):
        self.rounds = list(rounds)
        self.requests = []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        round_ = self.rounds.pop(0)
        if isinstance(round_, Exception):
            raise round_
        return iter(round_)


def api_error():
    return groq.APIConnectionError(request=httpx.Request("POST", "http://x"))


def test_plain_reply_uses_one_request_and_splits_sentences():
    client = FakeClient([text_chunk("Pi is 3."), text_chunk("14 or so. "), text_chunk("Done.")])
    sentences = []
    reply = Assistant(client=client).respond("hi", sentences.append)
    assert reply == "Pi is 3.14 or so. Done."
    assert sentences == ["Pi is 3.14 or so.", "Done."]
    assert len(client.requests) == 1


def rate_limit_error():
    request = httpx.Request("POST", "http://x")
    return groq.RateLimitError("limit", response=httpx.Response(429, request=request), body=None)


def test_rate_limit_switches_model_without_waiting():
    client = FakeClient(rate_limit_error(), [text_chunk("Ok.")])
    assert Assistant(client=client).respond("hi", lambda s: None) == "Ok."
    assert [r["model"] for r in client.requests] == [LLM_MODEL, LLM_FALLBACK_MODEL]


def test_both_models_limited_gives_error_reply():
    client = FakeClient(rate_limit_error(), rate_limit_error())
    bot = Assistant(client=client)
    assert bot.respond("hi", lambda s: None) == assistant_module.ERROR_REPLY
    assert bot.messages == []


def test_long_sentence_splits_at_comma():
    long_clause = "The sky looks blue because the air scatters short wavelengths of light"
    client = FakeClient([text_chunk(long_clause + ", "), text_chunk("and red less. "), text_chunk("Done.")])
    spoken = []
    Assistant(client=client).respond("hi", spoken.append)
    assert spoken == [long_clause + ",", "and red less.", "Done."]


def test_tool_round_then_answer():
    client = FakeClient([tool_chunk("calculate", '{"expression": "2+2"}')], [text_chunk("It's 4.")])
    bot = Assistant(client=client)
    assert bot.respond("2+2?", lambda s: None) == "It's 4."
    tool_message = client.requests[1]["messages"][-1]
    assert (tool_message["role"], tool_message["content"]) == ("tool", "4")


def test_memory_survives_a_new_assistant():
    Assistant(client=FakeClient([text_chunk("Hello.")])).respond("hi", lambda s: None)
    assert Assistant(client=FakeClient()).messages == [
        {"role": "user", "content": "hi"}, {"role": "assistant", "content": "Hello."},
    ]


def test_api_error_is_spoken_and_leaves_history_clean():
    bot = Assistant(client=FakeClient(api_error(), api_error()))
    spoken = []
    assert bot.respond("hi", spoken.append) == assistant_module.ERROR_REPLY
    assert spoken == [assistant_module.ERROR_REPLY]
    assert bot.messages == []


def test_trim_never_starts_on_a_tool_result():
    bot = Assistant(client=FakeClient())
    bot.messages = [{"role": "tool", "content": "x", "tool_call_id": "1"}] * (MAX_MESSAGES + 5)
    bot.messages[-3] = {"role": "user", "content": "q"}
    bot._trim()
    assert bot.messages[0]["role"] == "user"


def test_system_prompt_has_todays_date():
    bot = Assistant(client=FakeClient([text_chunk("Ok.")]))
    bot.respond("hi", lambda s: None)
    assert str(datetime.now().year) in bot._system_message()["content"]


def test_stop_ends_stream():
    stop = {"now": False}

    def chunks():
        yield text_chunk("First. ")
        stop["now"] = True
        yield text_chunk("Second. ")
        yield text_chunk("Third.")

    spoken = []
    client = FakeClient(chunks())
    Assistant(client=client).respond("hi", spoken.append, should_stop=lambda: stop["now"])
    assert spoken == ["First."]
