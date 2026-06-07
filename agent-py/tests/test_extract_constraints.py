"""Unit tests for extract_constraints @function_tool and the Constraints dataclass.

These are deterministic unit tests — no LLM or Moss credentials required.
The @function_tool is tested by calling the method directly with known inputs,
matching the pattern in test_moss.py.
"""

import json

import pytest

import agent as agent_module
from agent import Assistant
from constraints import Constraints

# ---------------------------------------------------------------------------
# Moss stub (same pattern as test_moss.py)
# ---------------------------------------------------------------------------


class _FakeMossClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def load_index(self, name, *args, **kwargs):
        pass

    async def query(self, index, query, options=None):
        return type("R", (), {"docs": [], "time_taken_ms": 0.0})()

    async def add_docs(self, index, docs, options=None):
        pass


@pytest.fixture
def stub_moss(monkeypatch):
    monkeypatch.setattr(agent_module, "MossClient", _FakeMossClient)


# ---------------------------------------------------------------------------
# Constraints dataclass — pure unit tests, no LLM
# ---------------------------------------------------------------------------


def test_constraints_defaults():
    c = Constraints()
    assert c.drugs == []
    assert c.providers == []
    assert c.events == []
    assert c.family_size == 1
    assert c.hsa_interest is False
    assert c.budget is None
    assert c.language == "en"


def test_constraints_from_dict_full():
    c = Constraints.from_dict(
        {
            "drugs": ["Humira", "metformin"],
            "providers": ["Dr. Chen at UCSF"],
            "events": ["pregnancy"],
            "family_size": 2,
            "hsa_interest": True,
            "budget": "$400/month",
            "language": "es",
        }
    )
    assert c.drugs == ["Humira", "metformin"]
    assert c.providers == ["Dr. Chen at UCSF"]
    assert c.events == ["pregnancy"]
    assert c.family_size == 2
    assert c.hsa_interest is True
    assert c.budget == "$400/month"
    assert c.language == "es"


def test_constraints_from_dict_missing_fields():
    c = Constraints.from_dict({})
    assert c.drugs == []
    assert c.family_size == 1
    assert c.hsa_interest is False
    assert c.budget is None
    assert c.language == "en"


def test_constraints_from_dict_family_size_min_1():
    c = Constraints.from_dict({"family_size": 0})
    assert c.family_size == 1


def test_constraints_roundtrip():
    original = Constraints(
        drugs=["Humira"],
        providers=["UCSF Medical Center"],
        events=["pregnancy"],
        family_size=2,
        hsa_interest=True,
        budget="$400/month",
        language="es",
    )
    restored = Constraints.from_dict(original.to_dict())
    assert restored.drugs == original.drugs
    assert restored.providers == original.providers
    assert restored.events == original.events
    assert restored.family_size == original.family_size
    assert restored.hsa_interest == original.hsa_interest
    assert restored.budget == original.budget
    assert restored.language == original.language


# ---------------------------------------------------------------------------
# extract_constraints @function_tool — direct method call tests
# ---------------------------------------------------------------------------


async def test_extract_constraints_returns_json(stub_moss) -> None:
    """Tool returns valid JSON with all expected keys."""
    assistant = Assistant()
    result = await assistant.extract_constraints(
        None,
        drugs=["Humira", "metformin"],
        providers=["Dr. Chen at UCSF"],
        events=["pregnancy"],
        family_size=2,
        hsa_interest=False,
        budget="$400/month",
        language="en",
    )
    data = json.loads(result)
    assert data["drugs"] == ["Humira", "metformin"]
    assert data["providers"] == ["Dr. Chen at UCSF"]
    assert data["events"] == ["pregnancy"]
    assert data["family_size"] == 2
    assert data["hsa_interest"] is False
    assert data["budget"] == "$400/month"
    assert data["language"] == "en"


async def test_extract_constraints_stores_on_assistant(stub_moss) -> None:
    """Tool persists the parsed Constraints on the assistant for downstream use."""
    assistant = Assistant()
    await assistant.extract_constraints(
        None,
        drugs=["Humira"],
        providers=["UCSF Medical Center"],
        events=["pregnancy"],
        family_size=2,
        hsa_interest=False,
        budget=None,
        language="en",
    )
    assert assistant._constraints is not None
    assert assistant._constraints.drugs == ["Humira"]
    assert assistant._constraints.family_size == 2


async def test_extract_constraints_family_size_clamped(stub_moss) -> None:
    """family_size is clamped to minimum 1."""
    assistant = Assistant()
    result = await assistant.extract_constraints(
        None,
        drugs=[],
        providers=[],
        events=[],
        family_size=0,
        hsa_interest=False,
        budget=None,
        language="en",
    )
    data = json.loads(result)
    assert data["family_size"] == 1


async def test_extract_constraints_null_budget(stub_moss) -> None:
    """budget=None is preserved as null in JSON output."""
    assistant = Assistant()
    result = await assistant.extract_constraints(
        None,
        drugs=[],
        providers=[],
        events=[],
        family_size=1,
        hsa_interest=False,
        budget=None,
        language="en",
    )
    data = json.loads(result)
    assert data["budget"] is None


async def test_extract_constraints_hsa_interest(stub_moss) -> None:
    """hsa_interest=True is captured."""
    assistant = Assistant()
    result = await assistant.extract_constraints(
        None,
        drugs=[],
        providers=[],
        events=[],
        family_size=1,
        hsa_interest=True,
        budget=None,
        language="en",
    )
    data = json.loads(result)
    assert data["hsa_interest"] is True


async def test_extract_constraints_maria_scenario(stub_moss) -> None:
    """Full Maria demo scenario: pregnancy, Humira, UCSF OB-GYN, family of 2."""
    assistant = Assistant()
    result = await assistant.extract_constraints(
        None,
        drugs=["Humira"],
        providers=["UCSF Medical Center OB-GYN"],
        events=["pregnancy"],
        family_size=2,
        hsa_interest=False,
        budget="$300/month",
        language="es",
    )
    data = json.loads(result)
    assert "Humira" in data["drugs"]
    assert any("UCSF" in p for p in data["providers"])
    assert "pregnancy" in data["events"]
    assert data["family_size"] == 2
    assert data["language"] == "es"
    assert assistant._constraints.events == ["pregnancy"]
