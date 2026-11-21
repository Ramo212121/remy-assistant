"""The interrupt listener must never stop the audio stream from inside its callback."""
import threading

import numpy as np

from src.mouth import speaker


class FakeProc:
    def __init__(self):
        self.done = threading.Event()

    def poll(self):
        return 0 if self.done.is_set() else None

    def terminate(self):
        self.done.set()


class FakeStream:
    """Records the callback, and fails the test if the callback tries to stop the stream."""
    instances = []

    def __init__(self, callback, **kwargs):
        self.callback = callback
        self.stopped_from = []
        FakeStream.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stopped_from.append(threading.current_thread().name)


def run_listener(monkeypatch, feed):
    FakeStream.instances.clear()
    monkeypatch.setattr(speaker.sd, "InputStream", FakeStream)
    proc = FakeProc()
    interrupted = []
    monkeypatch.setattr(speaker, "interrupt", lambda: (interrupted.append(True), proc.terminate()))
    worker = threading.Thread(target=speaker._listen_for_interrupt, args=(proc,),
                              kwargs={"poll_seconds": 0.01}, daemon=True)
    worker.start()
    for _ in range(200):
        if FakeStream.instances:
            break
        threading.Event().wait(0.01)
    feed(FakeStream.instances[0].callback, proc)
    worker.join(timeout=2)
    if worker.is_alive():
        proc.terminate()
        worker.join(timeout=1)
        raise AssertionError("listener hung")
    return interrupted, FakeStream.instances[0]


def test_loud_sound_interrupts_and_stream_stops_on_the_worker(monkeypatch):
    def feed(callback, proc):
        loud = np.full((160, 1), 5.0, np.float32)   # volume ≈ 0.4, above the 0.25 threshold
        result = callback(loud, 160, None, None)
        assert result is None   # the callback never raises CallbackStop

    interrupted, stream = run_listener(monkeypatch, feed)
    assert interrupted == [True]
    assert stream.stopped_from and stream.stopped_from[0] != "Dummy"


def test_quiet_playback_ends_without_interrupt(monkeypatch):
    def feed(callback, proc):
        callback(np.zeros((160, 1), np.float32), 160, None, None)
        proc.terminate()   # afplay finished

    interrupted, _ = run_listener(monkeypatch, feed)
    assert interrupted == []
