import threading

import numpy as np
import pytest

from src.brain import voice_loop
from src.config import GESTURE_MODEL
from src.eyes.gestures import GestureFilter


# ─── GestureFilter ───
def feed(gesture_filter, frames):
    """frames: (name, score, time) → list of actions that fired."""
    return [a for a in (gesture_filter.update(n, s, t) for n, s, t in frames) if a]


def test_gesture_must_be_held():
    f = GestureFilter(hold_seconds=0.4, wake_hold_seconds=0.8)
    assert feed(f, [("Thumb_Up", 0.9, 0.0), ("Thumb_Up", 0.9, 0.2)]) == []
    assert feed(f, [("Thumb_Up", 0.9, 0.5)]) == ["done"]


def test_palm_needs_the_longer_hold_to_wake():
    f = GestureFilter(hold_seconds=0.4, wake_hold_seconds=0.8, cooldown_seconds=0)
    assert feed(f, [("Open_Palm", 0.9, 0.0), ("Open_Palm", 0.9, 0.5)]) == []
    assert feed(f, [("Open_Palm", 0.9, 0.9)]) == ["wake"]


def test_one_hold_fires_once():
    f = GestureFilter(hold_seconds=0.4, cooldown_seconds=0)
    frames = [("Closed_Fist", 0.9, t / 10) for t in range(30)]
    assert feed(f, frames) == ["stop"]


def test_low_confidence_and_unknown_gestures_are_ignored():
    f = GestureFilter(hold_seconds=0.1)
    assert feed(f, [("Open_Palm", 0.3, t / 10) for t in range(10)]) == []
    assert feed(f, [("Unknown_Gesture", 0.99, t / 10) for t in range(10)]) == []
    assert feed(f, [("None", 0.0, t / 10) for t in range(10)]) == []


def test_flicker_resets_the_hold():
    f = GestureFilter(hold_seconds=0.4)
    frames = [("Open_Palm", 0.9, 0.0), ("Open_Palm", 0.9, 0.3), ("None", 0, 0.35), ("Open_Palm", 0.9, 0.5)]
    assert feed(f, frames) == []


def test_cooldown_between_commands():
    f = GestureFilter(hold_seconds=0.2, wake_hold_seconds=0.2, cooldown_seconds=1.5)
    frames = [("Thumb_Up", 0.9, 0.0), ("Thumb_Up", 0.9, 0.3),       # fires at 0.3
              ("None", 0, 0.4),
              ("Open_Palm", 0.9, 0.5), ("Open_Palm", 0.9, 0.8),     # too soon
              ("None", 0, 0.9),
              ("Open_Palm", 0.9, 2.0), ("Open_Palm", 0.9, 2.3)]     # fires at 2.3
    assert feed(f, frames) == ["done", "wake"]


# ─── voice loop ───
def test_handle_gesture(monkeypatch):
    stopped = []
    monkeypatch.setattr(voice_loop, "interrupt", lambda: stopped.append(True))
    voice_loop._gesture_wake.clear()
    voice_loop._gesture_done.clear()
    voice_loop.handle_gesture("wake")
    voice_loop.handle_gesture("done")
    voice_loop.handle_gesture("stop")
    assert voice_loop._gesture_wake.is_set() and voice_loop._gesture_done.is_set() and stopped == [True]


def test_palm_wakes_and_thumb_up_ends_conversation(monkeypatch):
    said, states = [], []
    rounds = {"n": 0}

    def fake_wake(timeout, should_stop):
        rounds["n"] += 1
        if rounds["n"] == 1:
            voice_loop.handle_gesture("wake")    # ✋ while waiting
            assert should_stop()                 # the wait gives up right away
        return False

    def fake_listen(timeout, should_stop):
        voice_loop.handle_gesture("done")        # 👍 while listening
        assert should_stop()
        return ""

    active = {"on": True}

    def is_active():
        return active["on"] and rounds["n"] < 2

    monkeypatch.setattr(voice_loop, "preload", lambda: None)
    monkeypatch.setattr(voice_loop, "wait_for_wake_word", fake_wake)
    monkeypatch.setattr(voice_loop, "listen", fake_listen)
    monkeypatch.setattr(voice_loop, "_say", said.append)

    assert voice_loop.run_voice_loop(object(), is_active=is_active, on_state=states.append) is False
    assert said == ["Yes?", "Okay."]
    assert "listening" in states


# ─── the real model, on a frame with no hand ───
@pytest.mark.skipif(not GESTURE_MODEL.exists(), reason="gesture model not downloaded")
def test_model_sees_no_gesture_in_an_empty_frame():
    import mediapipe as mp
    from mediapipe.tasks import python as mp_tasks
    from mediapipe.tasks.python import vision

    recognizer = vision.GestureRecognizer.create_from_options(vision.GestureRecognizerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=str(GESTURE_MODEL)),
        running_mode=vision.RunningMode.VIDEO, num_hands=1,
    ))
    frame = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.zeros((240, 320, 3), np.uint8))
    assert recognizer.recognize_for_video(frame, 0).gestures == []
    recognizer.close()


# ─── extra gestures ───
def test_every_mediapipe_gesture_has_an_action_and_label():
    from src.eyes.gestures import ACTIONS, LABELS
    assert set(ACTIONS) == set(LABELS) == {
        "Open_Palm", "Closed_Fist", "Thumb_Up", "Pointing_Up", "Thumb_Down", "Victory", "ILoveYou"}


def test_volume_gestures_step_by_ten(monkeypatch):
    calls = []
    monkeypatch.setattr(voice_loop, "change_volume", lambda delta: calls.append(delta) or "ok")
    voice_loop.handle_gesture("volume_up")
    voice_loop.handle_gesture("volume_down")
    assert calls == [10, -10]


def test_change_volume_reads_then_sets(monkeypatch):
    from src.hands import tools
    commands = []

    class Done:
        stdout = "45\n"

    monkeypatch.setattr(tools.subprocess, "run", lambda cmd, **kw: commands.append(cmd[-1]) or Done())
    assert tools.change_volume(10) == "Volume set to 55%"
    assert commands == ["output volume of (get volume settings)", "set volume output volume 55"]
    commands.clear()
    Done.stdout = "95\n"
    assert tools.change_volume(10) == "Volume set to 100%"


def test_repeat_and_time_speak(monkeypatch):
    said = []
    monkeypatch.setattr(voice_loop, "_say_now", said.append)
    monkeypatch.setattr(voice_loop, "get_time", lambda: "14:30")
    voice_loop._last_reply["text"] = ""
    voice_loop.handle_gesture("repeat")
    voice_loop._last_reply["text"] = "It's sunny."
    voice_loop.handle_gesture("repeat")
    voice_loop.handle_gesture("time")
    assert said == ["I haven't said anything yet.", "It's sunny.", "It's 14:30."]


def test_run_turn_remembers_last_reply(monkeypatch):
    class Bot:
        def respond(self, text, on_sentence, should_stop, on_tool):
            return "Hello there."

    for name in ("reset_interrupt", "set_speaking", "_finish_speech"):
        monkeypatch.setattr(voice_loop, name, lambda *a: None)
    assert voice_loop.run_turn(Bot(), "hi") == "Hello there."
    assert voice_loop._last_reply["text"] == "Hello there."


# ─── open-close (✋ then ✊) ───
def frames(*parts):
    """parts: (name, start, end) at 15 fps."""
    out = []
    for name, start, end in parts:
        t = start
        while t <= end + 1e-9:
            out.append((name, 0.9, round(t, 3)))
            t += 1 / 15
    return out


def test_quick_open_close_opens_chrome_not_stop():
    f = GestureFilter()
    assert feed(f, frames(("Open_Palm", 0.0, 0.4), ("None", 0.47, 0.6), ("Closed_Fist", 0.67, 1.2))) == ["open_chrome"]


def test_long_palm_wakes_then_fist_just_stops():
    f = GestureFilter(cooldown_seconds=0)
    actions = feed(f, frames(("Open_Palm", 0.0, 1.0), ("Closed_Fist", 1.07, 1.6)))
    assert actions == ["wake", "stop"]


def test_fist_alone_stops():
    f = GestureFilter()
    assert feed(f, frames(("Closed_Fist", 0.0, 0.6))) == ["stop"]


def test_fist_long_after_a_short_palm_is_stop():
    f = GestureFilter()
    assert feed(f, frames(("Open_Palm", 0.0, 0.3), ("None", 0.37, 2.0), ("Closed_Fist", 2.07, 2.7))) == ["stop"]


def test_open_close_calls_chrome(monkeypatch):
    opened = []
    monkeypatch.setattr(voice_loop, "open_app", lambda name: opened.append(name) or "ok")
    voice_loop.handle_gesture("open_chrome")
    assert opened == ["Google Chrome"]


def test_progress_fills_towards_the_hold():
    f = GestureFilter(hold_seconds=0.4, wake_hold_seconds=0.8)
    f.update("Thumb_Up", 0.9, 0.0)
    assert f.progress(0.2) == pytest.approx(0.5)
    f.update("Open_Palm", 0.9, 1.0)
    assert f.progress(1.4) == pytest.approx(0.5)
    assert f.progress(5.0) == 1.0
    f.update("None", 0, 5.0)
    assert f.progress(5.1) == 0.0
