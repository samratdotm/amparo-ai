"""Tests for the clinical-handoff guardrail.

All tests are deterministic — no LLM, no Moss, no network.
Golden rule: 5 clinical questions must trigger, 5 coverage questions must not.
"""

import pytest
from livekit.agents import llm

import agent as agent_module
from agent import Assistant
from guardrail import CLINICAL_HANDOFF, is_clinical_question

# ---------------------------------------------------------------------------
# Clinical questions — MUST return True (these must always be handed off)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Should I switch from Humira to a biosimilar?",
        "Is it safe to take metformin while pregnant?",
        "What dose of Humira should I be taking?",
        "What are the side effects of adalimumab?",
        "Can I take ibuprofen with my current medications?",
        "Is Humira safe for long-term use?",
        "What's the dosage for a biologic injection?",
        "Do I need a prescription for adalimumab?",
        "Can I stop taking my medication if I feel better?",
        "What are the symptoms of a Humira drug interaction?",
    ],
)
def test_clinical_questions_trigger(text):
    assert is_clinical_question(text) is True, f"Should have triggered: {text!r}"


# ---------------------------------------------------------------------------
# Coverage questions — MUST return False (these are Amparo's domain)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Is Humira covered by the Silver plan?",
        "How much does Humira cost under my plan?",
        "What's my copay for specialty drugs?",
        "Which plan covers my OB-GYN at UCSF?",
        "What's my deductible for the Gold plan?",
        "Is UCSF Medical Center in network for Bronze?",
        "Compare the four plans for my pregnancy",
        "What does my plan cover for prenatal care?",
        "How much is the monthly premium for Platinum?",
        "Does the HDHP have an HSA option?",
    ],
)
def test_coverage_questions_do_not_trigger(text):
    assert is_clinical_question(text) is False, f"Should NOT have triggered: {text!r}"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_string_is_not_clinical():
    assert is_clinical_question("") is False


def test_whitespace_only_is_not_clinical():
    assert is_clinical_question("   ") is False


def test_none_like_empty_is_not_clinical():
    assert is_clinical_question("") is False


def test_clinical_handoff_constant_is_non_empty():
    assert len(CLINICAL_HANDOFF) > 20


def test_coverage_framed_dose_question_not_clinical():
    # "dose" appears but it's about plan coverage, not medical advice
    assert is_clinical_question("Is the dose covered by my plan?") is False


# ---------------------------------------------------------------------------
# on_user_turn_completed integration — verify guardrail injects system message
# ---------------------------------------------------------------------------


class _FakeMossClient:
    def __init__(self, *args, **kwargs):
        pass

    async def load_index(self, *args, **kwargs):
        pass

    async def query(self, *args, **kwargs):
        return type("R", (), {"docs": [], "time_taken_ms": 0.0})()

    async def add_docs(self, *args, **kwargs):
        pass


@pytest.fixture
def stub_moss(monkeypatch):
    monkeypatch.setattr(agent_module, "MossClient", _FakeMossClient)


def _make_message(text: str) -> llm.ChatMessage:
    return llm.ChatMessage(role="user", content=[text])


async def test_guardrail_injects_system_message_for_clinical(stub_moss):
    """on_user_turn_completed adds a system message when clinical question detected."""
    assistant = Assistant()
    ctx = llm.ChatContext()
    msg = _make_message("Should I switch from Humira to a biosimilar?")

    await assistant.on_user_turn_completed(ctx, msg)

    system_messages = [m for m in ctx.messages() if m.role == "system"]
    assert len(system_messages) == 1
    assert CLINICAL_HANDOFF in (system_messages[0].text_content or "")


async def test_guardrail_no_injection_for_coverage_question(stub_moss):
    """on_user_turn_completed does NOT add a system message for coverage questions."""
    assistant = Assistant()
    ctx = llm.ChatContext()
    msg = _make_message("Is Humira covered by the Silver plan?")

    await assistant.on_user_turn_completed(ctx, msg)

    system_messages = [m for m in ctx.messages() if m.role == "system"]
    assert len(system_messages) == 0


async def test_guardrail_fires_for_all_five_demo_probes(stub_moss):
    """The 5 clinical probes judges will ask must ALL trigger the guardrail."""
    demo_probes = [
        "Should I switch drugs?",
        "Is this safe to take?",
        "What dose should I take?",
        "What are the side effects?",
        "Can I take this with my other medications?",
    ]
    assistant = Assistant()
    for probe in demo_probes:
        ctx = llm.ChatContext()
        msg = _make_message(probe)
        await assistant.on_user_turn_completed(ctx, msg)
        system_msgs = [m for m in ctx.messages() if m.role == "system"]
        assert len(system_msgs) == 1, f"Guardrail did not fire for: {probe!r}"
