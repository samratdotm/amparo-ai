"""Structured health insurance constraints extracted from a user's voice utterance."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Constraints:
    """Typed struct for what a user needs from a health plan."""

    drugs: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    family_size: int = 1
    hsa_interest: bool = False
    budget: str | None = None
    language: str = "en"

    def to_dict(self) -> dict:
        return {
            "drugs": self.drugs,
            "providers": self.providers,
            "events": self.events,
            "family_size": self.family_size,
            "hsa_interest": self.hsa_interest,
            "budget": self.budget,
            "language": self.language,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Constraints:
        return cls(
            drugs=list(data.get("drugs") or []),
            providers=list(data.get("providers") or []),
            events=list(data.get("events") or []),
            family_size=max(1, int(data.get("family_size") or 1)),
            hsa_interest=bool(data.get("hsa_interest")),
            budget=str(data["budget"]) if data.get("budget") else None,
            language=str(data.get("language") or "en"),
        )
