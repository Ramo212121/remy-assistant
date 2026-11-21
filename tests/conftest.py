"""Tests never open the real camera or send a photo anywhere."""
import pytest

from src.eyes import gestures, vision


@pytest.fixture(autouse=True)
def no_real_camera_or_vision(monkeypatch):
    def no_camera(*args, **kwargs):
        return None

    def no_network():
        raise RuntimeError("network is disabled in tests")

    monkeypatch.setattr(gestures, "capture_frame", no_camera)
    monkeypatch.setattr(vision, "get_groq_client", no_network)
