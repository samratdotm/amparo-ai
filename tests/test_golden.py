"""
Golden tests — assert computed annual costs, rankings, and trap flags match
hand-verified values for real CA ACA plans.

Plans:
  cchp_2024   — CCHP Bronze 60 HMO   ($990/mo, UCSF excluded — cheap plan trap)
  trio_2024   — Blue Shield Trio HMO ($1,163/mo, narrow Trio network, UCSF excluded)
  kaiser_2024 — Kaiser Gold HMO      ($1,392/mo, 5-star closed system, UCSF excluded)
  ppo_2024    — Blue Shield HDHP PPO ($1,473/mo, UCSF in-network — TRUE WINNER)

The trap: 3 of 4 plans exclude UCSF. OON costs are NOT capped by OOP max.
The winner is the most expensive premium plan — it's the only one where Maria's
UCSF OB is in-network.

Run: python -m pytest tests/test_golden.py -v
"""

import json
from pathlib import Path
import pytest

DATA_DIR = Path(__file__).parent.parent / "data"
PLANS_DIR = DATA_DIR / "plans"
PERSONAS_DIR = DATA_DIR / "personas"

TRAP_THRESHOLD = 5_000.0  # matches cost_math.py


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def compute_annual_cost(plan: dict, persona: dict) -> dict:
    """
    Deterministic cost math — mirrors the agent's compare_plans tool.
    Covered drug costs accumulate toward covered_oop, capped at oop_max.
    Uncovered drug costs and OON provider costs are NOT capped — this is the trap.
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
            oon_cost = plan_provider.get("out_of_network_cost", 0)
            uncovered_costs += oon_cost
            if persona_provider["critical"]:
                hard_constraint_failures.append(
                    f"{persona_provider['provider_name']} out-of-network — ${oon_cost:,}/yr NOT covered"
                )

    # Flat estimate for other covered care (prenatal visits, labs, PCP) — $3,000 covered OOP
    covered_oop += 3_000

    capped_oop = min(covered_oop, oop_max)
    annual_total = annual_premium + capped_oop + uncovered_costs
    trap_flag = uncovered_costs > TRAP_THRESHOLD

    return {
        "annual_premium": round(annual_premium),
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


class TestCCHPTrap:
    """CCHP Bronze HMO — cheapest premium but UCSF excluded. Network trap."""

    def test_humira_covered(self, plans):
        cchp = plans["cchp_2024"]
        drug = next(d for d in cchp["formulary"] if d["drug_name"] == "Humira")
        assert drug["covered"] is True, "CCHP covers Humira"

    def test_humira_copay_per_fill(self, plans):
        cchp = plans["cchp_2024"]
        drug = next(d for d in cchp["formulary"] if d["drug_name"] == "Humira")
        assert drug["member_cost_per_month"] == 500, "CCHP Humira capped at $500/fill"

    def test_ucsf_out_of_network(self, plans):
        cchp = plans["cchp_2024"]
        ucsf = next(p for p in cchp["network"] if "UCSF" in p["provider_name"])
        assert ucsf["in_network"] is False

    def test_ucsf_oon_cost_substantial(self, plans):
        cchp = plans["cchp_2024"]
        ucsf = next(p for p in cchp["network"] if "UCSF" in p["provider_name"])
        assert ucsf["out_of_network_cost"] >= 20_000, "UCSF OON delivery cost should be substantial"

    def test_hsa_eligible(self, plans):
        assert plans["cchp_2024"]["hsa_eligible"] is True

    def test_trap_flag_set(self, plans, maria):
        result = compute_annual_cost(plans["cchp_2024"], maria)
        assert result["trap_flag"] is True, "CCHP should trigger trap (UCSF OON)"

    def test_ucsf_in_hard_constraints(self, plans, maria):
        result = compute_annual_cost(plans["cchp_2024"], maria)
        ucsf_failures = [f for f in result["hard_constraints_failed"] if "UCSF" in f]
        assert len(ucsf_failures) > 0, "UCSF OON should be a hard constraint failure"


class TestTrioTrap:
    """Blue Shield Trio HMO — narrow Trio network, UCSF excluded."""

    def test_humira_covered(self, plans):
        trio = plans["trio_2024"]
        drug = next(d for d in trio["formulary"] if d["drug_name"] == "Humira")
        assert drug["covered"] is True

    def test_humira_copay_per_fill(self, plans):
        trio = plans["trio_2024"]
        drug = next(d for d in trio["formulary"] if d["drug_name"] == "Humira")
        assert drug["member_cost_per_month"] == 250, "Trio Humira capped at $250/fill"

    def test_ucsf_out_of_network(self, plans):
        trio = plans["trio_2024"]
        ucsf = next(p for p in trio["network"] if "UCSF" in p["provider_name"])
        assert ucsf["in_network"] is False

    def test_trap_flag_set(self, plans, maria):
        result = compute_annual_cost(plans["trio_2024"], maria)
        assert result["trap_flag"] is True


class TestKaiserTrap:
    """Kaiser Gold HMO — 5-star quality, $0 deductible, but Kaiser-only closed system."""

    def test_humira_covered(self, plans):
        kaiser = plans["kaiser_2024"]
        drug = next(d for d in kaiser["formulary"] if d["drug_name"] == "Humira")
        assert drug["covered"] is True

    def test_zero_deductible(self, plans):
        assert plans["kaiser_2024"]["deductible_individual"] == 0, "Kaiser Gold has $0 deductible"

    def test_ucsf_out_of_network(self, plans):
        kaiser = plans["kaiser_2024"]
        ucsf = next(p for p in kaiser["network"] if "UCSF" in p["provider_name"])
        assert ucsf["in_network"] is False, "UCSF 100% excluded from Kaiser closed system"

    def test_ucsf_oon_cost_substantial(self, plans):
        kaiser = plans["kaiser_2024"]
        ucsf = next(p for p in kaiser["network"] if "UCSF" in p["provider_name"])
        assert ucsf["out_of_network_cost"] >= 20_000

    def test_trap_flag_set(self, plans, maria):
        result = compute_annual_cost(plans["kaiser_2024"], maria)
        assert result["trap_flag"] is True


class TestPPOWinner:
    """Blue Shield HDHP PPO — most expensive premium, but UCSF in-network. True winner."""

    def test_humira_covered(self, plans):
        ppo = plans["ppo_2024"]
        drug = next(d for d in ppo["formulary"] if d["drug_name"] == "Humira")
        assert drug["covered"] is True

    def test_ucsf_in_network(self, plans):
        ppo = plans["ppo_2024"]
        ucsf = next(p for p in ppo["network"] if "UCSF" in p["provider_name"])
        assert ucsf["in_network"] is True, "UCSF must be in-network on the PPO"

    def test_hsa_eligible(self, plans):
        assert plans["ppo_2024"]["hsa_eligible"] is True, "PPO is HSA-eligible HDHP"

    def test_no_trap_flag(self, plans, maria):
        result = compute_annual_cost(plans["ppo_2024"], maria)
        assert result["trap_flag"] is False

    def test_no_hard_constraints_failed(self, plans, maria):
        result = compute_annual_cost(plans["ppo_2024"], maria)
        assert result["hard_constraints_failed"] == []


class TestRankings:
    """PPO must be cheapest total for Maria despite highest premium — the key insight."""

    def test_ppo_cheapest_total_for_maria(self, plans, maria):
        results = {pid: compute_annual_cost(p, maria) for pid, p in plans.items()}
        ppo_total = results["ppo_2024"]["annual_total_estimated"]
        for pid, r in results.items():
            if pid != "ppo_2024":
                assert ppo_total < r["annual_total_estimated"], (
                    f"PPO ({ppo_total:,}) should be cheapest for Maria vs {pid} ({r['annual_total_estimated']:,})"
                )

    def test_cchp_cheapest_premium(self, plans):
        premiums = {pid: p["premium_monthly_individual"] for pid, p in plans.items()}
        assert premiums["cchp_2024"] == min(premiums.values()), (
            "CCHP must have cheapest premium — that's what makes it a trap"
        )

    def test_cchp_cheapest_premium_not_cheapest_total(self, plans, maria):
        results = {pid: compute_annual_cost(p, maria) for pid, p in plans.items()}
        premiums = {pid: p["premium_monthly_individual"] for pid, p in plans.items()}
        cheapest_premium = min(premiums, key=premiums.get)
        assert cheapest_premium == "cchp_2024"
        # But the cheapest-premium plan should cost MORE than the PPO
        cchp_total = results["cchp_2024"]["annual_total_estimated"]
        ppo_total = results["ppo_2024"]["annual_total_estimated"]
        assert cchp_total > ppo_total, (
            f"CCHP (cheapest premium) should cost more than PPO for Maria. "
            f"CCHP: ${cchp_total:,}  PPO: ${ppo_total:,}"
        )

    def test_ppo_saves_over_15k_vs_cchp(self, plans, maria):
        results = {pid: compute_annual_cost(p, maria) for pid, p in plans.items()}
        savings = results["cchp_2024"]["annual_total_estimated"] - results["ppo_2024"]["annual_total_estimated"]
        assert savings > 15_000, (
            f"PPO should save Maria >$15k vs CCHP (the demo moment). Got: ${savings:,}"
        )

    def test_three_plans_are_traps(self, plans, maria):
        results = {pid: compute_annual_cost(p, maria) for pid, p in plans.items()}
        trap_plans = [pid for pid, r in results.items() if r["trap_flag"]]
        assert len(trap_plans) == 3, f"Exactly 3 plans should be traps. Got: {trap_plans}"
        assert "ppo_2024" not in trap_plans, "PPO should NOT be a trap"

    def test_all_trap_plans_exclude_ucsf(self, plans, maria):
        results = {pid: compute_annual_cost(p, maria) for pid, p in plans.items()}
        for pid, r in results.items():
            if r["trap_flag"]:
                ucsf_fail = any("UCSF" in f for f in r["hard_constraints_failed"])
                assert ucsf_fail, f"{pid} is a trap but UCSF not in hard_constraints_failed"
