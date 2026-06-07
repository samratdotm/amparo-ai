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

    def merge(self, new: "Constraints") -> "Constraints":
        """Return a new Constraints that accumulates this turn's additions into prior state.

        Lists (drugs, providers, events) are unioned — existing items are never dropped.
        Scalars are updated only when the new value signals the user actually said something:
          - family_size: updated only if new > 1 (1 is the LLM default for "not mentioned")
          - hsa_interest: latches True (once the user mentions it, it stays)
          - budget: updated only if new is not None
          - language: always takes the latest value (reflects the current turn's language)
        """

        def _union(old: list[str], incoming: list[str]) -> list[str]:
            seen = {item.lower() for item in old}
            merged = list(old)
            for item in incoming:
                if item.lower() not in seen:
                    seen.add(item.lower())
                    merged.append(item)
            return merged

        return Constraints(
            drugs=_union(self.drugs, new.drugs),
            providers=_union(self.providers, new.providers),
            events=_union(self.events, new.events),
            family_size=new.family_size if new.family_size > 1 else self.family_size,
            hsa_interest=self.hsa_interest or new.hsa_interest,
            budget=new.budget if new.budget is not None else self.budget,
            language=new.language,
        )

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
