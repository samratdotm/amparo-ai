"""
Golden tests — assert computed annual costs, rankings, and trap flags match
hand-verified values in data/personas/maria.json.

Run: python -m pytest tests/test_golden.py -v
"""

import json
from pathlib import Path
import pytest

DATA_DIR = Path(__file__).parent.parent / "data"
PLANS_DIR = DATA_DIR / "plans"
PERSONAS_DIR = DATA_DIR / "personas"


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def compute_annual_cost(plan: dict, persona: dict) -> dict:
    """
    Deterministic cost math — same logic as the agent's compare_plans tool.
    Uncovered drugs are NOT capped by OOP max (the trap invariant).
    """
    tier = persona["coverage_tier"]
    premium_field = f"premium_monthly_{tier}"
    annual_premium = plan[premium_field] * 12

    oop_max_field = f"oop_max_{tier}"
    oop_max = plan[oop_max_field]

    covered_oop = 0.0
    uncovered_costs = 0.0
    hard_constraint_failures = []

    plan_drugs = {d["drug_name"].lower(): d for d in plan.get("formulary", [])}
    plan_providers = {p["provider_name"].lower(): p for p in plan.get("network", [])}

    for persona_drug in persona["drugs"]:
        key = persona_drug["drug_name"].lower()
        plan_drug = plan_drugs.get(key)
        if plan_drug is None:
            if persona_drug["critical"]:
                hard_constraint_failures.append(f"{persona_drug['drug_name']} not in formulary")
            continue

        if not plan_drug["covered"]:
            annual_uncovered = plan_drug.get("annual_cost_if_uncovered") or 0
            uncovered_costs += annual_uncovered
            if persona_drug["critical"]:
                hard_constraint_failures.append(
                    f"{persona_drug['drug_name']} not covered — ${annual_uncovered:,}/yr outside OOP"
                )
        else:
            monthly_cost = plan_drug.get("member_cost_per_month") or 0
            fills = persona_drug.get("monthly_fills", 1)
            covered_oop += monthly_cost * fills * 12

    for persona_provider in persona["providers"]:
        key = persona_provider["provider_name"].lower()
        plan_provider = plan_providers.get(key)
        if plan_provider is None:
            if persona_provider["critical"]:
                hard_constraint_failures.append(f"{persona_provider['provider_name']} not in directory")
            continue
        if not plan_provider["in_network"]:
            if persona_provider["critical"]:
                hard_constraint_failures.append(
                    f"{persona_provider['provider_name']} out-of-network"
                )

    # Add rough estimate for other care (maternity, PCP, etc.) — $3,000 covered OOP
    covered_oop += 3000

    capped_oop = min(covered_oop, oop_max)
    annual_total = annual_premium + capped_oop + uncovered_costs
    trap_flag = uncovered_costs > 0

    return {
        "annual_premium": annual_premium,
        "annual_total_estimated": round(annual_total),
        "uncovered_costs": uncovered_costs,
        "hard_constraints_failed": hard_constraint_failures,
        "trap_flag": trap_flag,
    }


@pytest.fixture
def maria():
    return load_json(PERSONAS_DIR / "maria.json")


@pytest.fixture
def plans():
    return {
        p.stem: load_json(p)
        for p in sorted(PLANS_DIR.glob("*.json"))
    }


class TestHMOTrap:
    def test_humira_not_covered(self, plans):
        hmo = plans["hmo_2024"]
        drug = next(d for d in hmo["formulary"] if d["drug_name"] == "Humira")
        assert drug["covered"] is False, "HMO must have Humira uncovered — this is the trap"

    def test_humira_uncovered_cost(self, plans):
        hmo = plans["hmo_2024"]
        drug = next(d for d in hmo["formulary"] if d["drug_name"] == "Humira")
        assert drug["annual_cost_if_uncovered"] == 38000

    def test_ucsf_out_of_network(self, plans):
        hmo = plans["hmo_2024"]
        ucsf = next(p for p in hmo["network"] if "UCSF Medical Center" in p["provider_name"])
        assert ucsf["in_network"] is False

    def test_trap_flag_set(self, plans, maria):
        result = compute_annual_cost(plans["hmo_2024"], maria)
        assert result["trap_flag"] is True

    def test_hmo_most_expensive_for_maria(self, plans, maria):
        results = {pid: compute_annual_cost(p, maria) for pid, p in plans.items()}
        hmo_total = results["hmo_2024"]["annual_total_estimated"]
        for pid, r in results.items():
            if pid != "hmo_2024":
                assert hmo_total > r["annual_total_estimated"], (
                    f"HMO ({hmo_total}) should be more expensive than {pid} ({r['annual_total_estimated']})"
                )


class TestPPOSafe:
    def test_humira_covered(self, plans):
        ppo = plans["ppo_2024"]
        drug = next(d for d in ppo["formulary"] if d["drug_name"] == "Humira")
        assert drug["covered"] is True

    def test_ucsf_in_network(self, plans):
        ppo = plans["ppo_2024"]
        ucsf = next(p for p in ppo["network"] if "UCSF Medical Center" in p["provider_name"])
        assert ucsf["in_network"] is True

    def test_no_trap_flag(self, plans, maria):
        result = compute_annual_cost(plans["ppo_2024"], maria)
        assert result["trap_flag"] is False

    def test_no_hard_constraints_failed(self, plans, maria):
        result = compute_annual_cost(plans["ppo_2024"], maria)
        assert result["hard_constraints_failed"] == []


class TestEPOPartialTrap:
    def test_humira_covered(self, plans):
        epo = plans["epo_2024"]
        drug = next(d for d in epo["formulary"] if d["drug_name"] == "Humira")
        assert drug["covered"] is True

    def test_ucsf_out_of_network(self, plans):
        epo = plans["epo_2024"]
        ucsf = next(p for p in epo["network"] if "UCSF Medical Center" in p["provider_name"])
        assert ucsf["in_network"] is False

    def test_ucsf_constraint_flagged(self, plans, maria):
        result = compute_annual_cost(plans["epo_2024"], maria)
        ucsf_failures = [f for f in result["hard_constraints_failed"] if "UCSF" in f]
        assert len(ucsf_failures) > 0


class TestHDHP:
    def test_humira_covered(self, plans):
        hdhp = plans["hdhp_2024"]
        drug = next(d for d in hdhp["formulary"] if d["drug_name"] == "Humira")
        assert drug["covered"] is True

    def test_hsa_eligible(self, plans):
        assert plans["hdhp_2024"]["hsa_eligible"] is True

    def test_ucsf_in_network(self, plans):
        hdhp = plans["hdhp_2024"]
        ucsf = next(p for p in hdhp["network"] if "UCSF Medical Center" in p["provider_name"])
        assert ucsf["in_network"] is True

    def test_no_trap_flag(self, plans, maria):
        result = compute_annual_cost(plans["hdhp_2024"], maria)
        assert result["trap_flag"] is False


class TestPremiumOrdering:
    """HMO must have the cheapest premium — that's what makes it look like a bargain."""

    def test_hmo_cheapest_family_premium(self, plans):
        premiums = {pid: p["premium_monthly_family"] for pid, p in plans.items()}
        assert premiums["hmo_2024"] == min(premiums.values()), (
            f"HMO must have lowest family premium for the trap to work. Got: {premiums}"
        )
