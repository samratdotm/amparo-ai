"""Set fake env vars before any agent module is imported.

Unit tests call tool methods directly — they never make real LLM or Moss
network calls. Setting placeholder credentials lets inference.LLM and
MossClient initialise without error; individual tests monkeypatch MossClient
to a recording fake so no Moss network traffic occurs.

Integration eval tests (test_agent.py) require real LiveKit inference
credentials. They are skipped automatically when only fake keys are present.
"""

import os

import pytest

os.environ.setdefault("LIVEKIT_API_KEY", "test-key")
os.environ.setdefault("LIVEKIT_API_SECRET", "test-secret")
os.environ.setdefault("LIVEKIT_URL", "wss://test.livekit.io")
os.environ.setdefault("MOSS_PROJECT_ID", "test-project")
os.environ.setdefault("MOSS_PROJECT_KEY", "test-key")

_FAKE_KEYS = {"test-key", "test-secret"}


@pytest.fixture
def requires_real_credentials():
    """Skip the test when only placeholder credentials are present."""
    key = os.environ.get("LIVEKIT_API_KEY", "")
    secret = os.environ.get("LIVEKIT_API_SECRET", "")
    if key in _FAKE_KEYS or secret in _FAKE_KEYS:
        pytest.skip("requires real LiveKit inference credentials")
