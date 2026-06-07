"""Clinical-handoff guardrail — Step 5.

Detects clinical questions (drug safety, dosing, diagnosis, medical advice)
and routes them to the handoff response. Amparo is a coverage navigator,
NOT a clinical advisor.

Design: keyword/regex-based, no LLM call — deterministic and instant.
The check runs in on_user_turn_completed before the LLM sees the message.
"""

from __future__ import annotations

import re

# The exact handoff line — keep it consistent across every entry point.
CLINICAL_HANDOFF = (
    "That's a question for your doctor or pharmacist. "
    "I can tell you what your plan covers, but medical advice isn't something I can give."
)

# Clinical patterns: phrases that signal a request for medical/clinical advice.
# Ordered from most specific to least to minimize false positives.
_CLINICAL_PATTERNS: list[str] = [
    # Drug safety & interactions
    r"\bis\s+\w+\s+safe\b",  # "is Humira safe"
    r"\bsafe\s+to\s+take\b",  # "safe to take"
    r"\bsafe\s+(during|while|for)\b",  # "safe during pregnancy"
    r"\bcan\s+i\s+take\b",  # "can I take X with Y"
    r"\bdrug\s+interact",  # "drug interaction"
    r"\binteract\s+with\b",  # "interact with my medication"
    r"\bside\s+effect",  # "side effects"
    r"\badverse\s+(effect|reaction|event)",  # "adverse effect/reaction"
    r"\ballerg(ic|y)\s+to\b",  # "allergic to"
    r"\boverdose\b",  # "overdose"
    # Dosing
    r"\bdos(e|age|ing)\b",  # "dose", "dosage", "dosing"
    r"\bhow\s+much\s+to\s+take\b",  # "how much to take"
    r"\bhow\s+many\s+(pills?|tablets?|mg)\b",
    r"\bwhen\s+to\s+take\b",  # "when to take"
    r"\btwice\s+a\s+day\b",  # "twice a day"
    # Switching / stopping medication
    r"\bshould\s+i\s+(take|switch|stop|start|use|try)\b",
    r"\bswitch\s+(from|to|medications?|drugs?)\b",
    r"\bstop\s+(taking|my\s+medication)\b",
    r"\bchange\s+my\s+(medication|prescription|drug)\b",
    # Diagnosis & symptoms
    r"\bdiagnos(e|is|ed)\b",  # "diagnose", "diagnosis"
    r"\bsymptom",  # "symptoms of"
    r"\bdo\s+i\s+have\b",  # "do I have"
    r"\bwhat\s+do\s+i\s+have\b",
    r"\bcondition\s+(i\s+have|to\s+treat)\b",
    # Treatment & prescriptions
    r"\btreatment\s+for\b",  # "treatment for my condition"
    r"\bprescri(be|ption|bed)\b",  # "prescribe", "prescription"
    r"\bmedical\s+advice\b",  # "medical advice"
    r"\bsee\s+a\s+doctor\b",  # "should I see a doctor"
    r"\bclinical\s+trial\b",
]

_CLINICAL_RE = re.compile(
    "|".join(_CLINICAL_PATTERNS),
    re.IGNORECASE,
)

# Phrases that look clinical but are actually coverage questions — exempted.
_COVERAGE_EXEMPTIONS: list[str] = [
    r"\bcovered\b",  # "is it covered", "is Humira covered"
    r"\bcopay\b",  # "what's my copay"
    r"\bformulary\b",  # "formulary tier"
    r"\bin.network\b",  # "in-network"
    r"\bout.of.network\b",  # "out-of-network"
    r"\bdeductible\b",  # "deductible"
    r"\bpremium\b",  # "premium"
    r"\bplan\s+(cover|pay)",  # "does my plan cover"
    r"\bcost\s+(under|with|for)\s+(my\s+)?plan\b",
    r"\binsurance\s+(cover|pay)\b",
]

_EXEMPTION_RE = re.compile(
    "|".join(_COVERAGE_EXEMPTIONS),
    re.IGNORECASE,
)


def is_clinical_question(text: str) -> bool:
    """Return True if text is a clinical/medical question that must be handed off.

    Checks for clinical patterns first, then exempts coverage-framed questions
    (e.g. "is Humira covered" is a coverage question, not clinical advice).
    """
    if not text or not text.strip():
        return False
    if not _CLINICAL_RE.search(text):
        return False
    # Exemption: if the sentence is clearly about coverage/cost, don't flag it.
    return not _EXEMPTION_RE.search(text)
