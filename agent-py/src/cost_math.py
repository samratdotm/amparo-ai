"""Deterministic plan cost math — no LLM, no Moss, pure Python.

All dollar amounts are annual. The key trap: uncovered drug costs sit
outside the OOP-max and are NOT capped. A plan with a low premium can
still cost tens of thousands if a key drug is off-formulary.

Formula:
    annual_total = premium*12 + min(covered_oop, oop_max) + uncovered_costs
"""

from __future__ import annotations

from dataclasses import dataclass, field

TRAP_THRESHOLD = 5_000.0  # uncovered costs above this flag as a trap


@dataclass
class DrugCoverage:
    name: str
    covered: bool
    copay_per_fill: float | None = (
        None  # flat copay per fill (takes priority over coinsurance)
    )
    coinsurance: float | None = None  # 0.0-1.0, applied to list_price_per_year
    fills_per_year: int = 12
    list_price_per_year: float = 0.0  # used when uncovered (or as coinsurance base)
    source: str = ""


@dataclass
class ProviderCoverage:
    name: str
    in_network: bool
    out_of_network_cost: float = 0.0  # estimated annual OON cost if not in-network
    source: str = ""


@dataclass
class PlanData:
    plan_id: str
    name: str
    monthly_premium: float
    deductible: float
    oop_max: float
    hsa_eligible: bool = False
    formulary: dict[str, DrugCoverage] = field(default_factory=dict)
    network: dict[str, ProviderCoverage] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)


@dataclass
class CostResult:
    plan_id: str
    plan_name: str
    annual_premium: float
    covered_oop: float  # raw covered drug costs before OOP cap
    capped_covered_oop: float  # min(covered_oop, oop_max)
    uncovered_costs: float  # NOT capped — this is the trap
    annual_total: float  # annual_premium + capped_covered_oop + uncovered_costs
    trap_flag: bool  # True when uncovered_costs > TRAP_THRESHOLD
    uncovered_drugs: list[str]
    out_of_network_providers: list[str]
    sources: list[str]


def _drug_covered_annual_cost(drug: DrugCoverage) -> float:
    """Out-of-pocket cost for a single covered drug, per year."""
    if drug.copay_per_fill is not None:
        return drug.copay_per_fill * drug.fills_per_year
    if drug.coinsurance is not None:
        return drug.coinsurance * drug.list_price_per_year
    return 0.0


def compute_annual_cost(
    plan: PlanData,
    drug_names: list[str],
    provider_names: list[str],
) -> CostResult:
    """Compute the true annual cost for a plan given the user's constraints.

    Covered drug costs accumulate toward covered_oop, then get capped at oop_max.
    Uncovered drug costs and out-of-network provider costs are NOT capped.
    """
    covered_oop = 0.0
    uncovered_costs = 0.0
    uncovered_drugs: list[str] = []
    oon_providers: list[str] = []
    sources = list(plan.sources)

    for drug_name in drug_names:
        entry = plan.formulary.get(drug_name)
        if entry is None or not entry.covered:
            uncovered_drugs.append(drug_name)
            if entry is not None:
                uncovered_costs += entry.list_price_per_year
                if entry.source:
                    sources.append(entry.source)
        else:
            covered_oop += _drug_covered_annual_cost(entry)
            if entry.source:
                sources.append(entry.source)

    for provider_name in provider_names:
        entry = plan.network.get(provider_name)
        if entry is None or not entry.in_network:
            oon_providers.append(provider_name)
            if entry is not None:
                uncovered_costs += entry.out_of_network_cost
                if entry.source:
                    sources.append(entry.source)
        else:
            if entry.source:
                sources.append(entry.source)

    capped_covered_oop = min(covered_oop, plan.oop_max)
    annual_premium = plan.monthly_premium * 12
    annual_total = annual_premium + capped_covered_oop + uncovered_costs

    return CostResult(
        plan_id=plan.plan_id,
        plan_name=plan.name,
        annual_premium=annual_premium,
        covered_oop=covered_oop,
        capped_covered_oop=capped_covered_oop,
        uncovered_costs=uncovered_costs,
        annual_total=annual_total,
        trap_flag=uncovered_costs > TRAP_THRESHOLD,
        uncovered_drugs=uncovered_drugs,
        out_of_network_providers=oon_providers,
        sources=list(dict.fromkeys(sources)),  # deduplicate, preserve order
    )


def rank_plans(results: list[CostResult]) -> list[CostResult]:
    """Sort plans by annual_total, cheapest first."""
    return sorted(results, key=lambda r: r.annual_total)
