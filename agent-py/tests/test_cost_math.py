"""Golden tests for the deterministic cost math module.

All dollar values are hand-verified. Changing a cost figure or plan fixture
MUST update the corresponding assertions here.

No Moss, no LLM, no network — pure deterministic math.
"""

from cost_math import (
    DrugCoverage,
    PlanData,
    ProviderCoverage,
    compute_annual_cost,
    rank_plans,
)

# ---------------------------------------------------------------------------
# Humira list price (specialty biologic, ~$50k/year before insurance)
# ---------------------------------------------------------------------------
HUMIRA_LIST_PRICE = 50_000.0

# ---------------------------------------------------------------------------
# 4-plan fixture set for Maria's demo scenario
#   Maria: pregnant, takes Humira, sees UCSF OB-GYN, family of 2
# ---------------------------------------------------------------------------

BRONZE_SAVER = PlanData(
    plan_id="bronze-2024",
    name="Bronze Saver",
    monthly_premium=150.0,
    deductible=6_000.0,
    oop_max=8_150.0,
    hsa_eligible=True,
    formulary={
        "Humira": DrugCoverage(
            name="Humira",
            covered=False,  # NOT on formulary — the trap
            list_price_per_year=HUMIRA_LIST_PRICE,
            source="Bronze Saver Formulary 2024, p. 12",
        ),
    },
    network={
        "UCSF Medical Center OB-GYN": ProviderCoverage(
            name="UCSF Medical Center OB-GYN",
            in_network=True,
            source="Bronze Saver Network Directory 2024",
        ),
    },
    sources=["Bronze Saver 2024 Summary of Benefits"],
)

SILVER_SELECT = PlanData(
    plan_id="silver-2024",
    name="Silver Select",
    monthly_premium=350.0,
    deductible=2_000.0,
    oop_max=4_000.0,
    hsa_eligible=False,
    formulary={
        "Humira": DrugCoverage(
            name="Humira",
            covered=True,
            coinsurance=0.30,
            list_price_per_year=HUMIRA_LIST_PRICE,
            source="Silver Select Formulary 2024, p. 18",
        ),
    },
    network={
        "UCSF Medical Center OB-GYN": ProviderCoverage(
            name="UCSF Medical Center OB-GYN",
            in_network=True,
            source="Silver Select Network Directory 2024",
        ),
    },
    sources=["Silver Select 2024 Summary of Benefits"],
)

GOLD_PLUS = PlanData(
    plan_id="gold-2024",
    name="Gold Plus",
    monthly_premium=500.0,
    deductible=1_000.0,
    oop_max=3_000.0,
    hsa_eligible=False,
    formulary={
        "Humira": DrugCoverage(
            name="Humira",
            covered=True,
            coinsurance=0.25,
            list_price_per_year=HUMIRA_LIST_PRICE,
            source="Gold Plus Formulary 2024, p. 22",
        ),
    },
    network={
        "UCSF Medical Center OB-GYN": ProviderCoverage(
            name="UCSF Medical Center OB-GYN",
            in_network=True,
            source="Gold Plus Network Directory 2024",
        ),
    },
    sources=["Gold Plus 2024 Summary of Benefits"],
)

PLATINUM_FULL = PlanData(
    plan_id="platinum-2024",
    name="Platinum Full",
    monthly_premium=700.0,
    deductible=0.0,
    oop_max=2_000.0,
    hsa_eligible=False,
    formulary={
        "Humira": DrugCoverage(
            name="Humira",
            covered=True,
            copay_per_fill=150.0,
            fills_per_year=12,
            list_price_per_year=HUMIRA_LIST_PRICE,
            source="Platinum Full Formulary 2024, p. 9",
        ),
    },
    network={
        "UCSF Medical Center OB-GYN": ProviderCoverage(
            name="UCSF Medical Center OB-GYN",
            in_network=True,
            source="Platinum Full Network Directory 2024",
        ),
    },
    sources=["Platinum Full 2024 Summary of Benefits"],
)

ALL_PLANS = [BRONZE_SAVER, SILVER_SELECT, GOLD_PLUS, PLATINUM_FULL]
MARIA_DRUGS = ["Humira"]
MARIA_PROVIDERS = ["UCSF Medical Center OB-GYN"]


# ---------------------------------------------------------------------------
# Bronze — the cheap-plan trap
# ---------------------------------------------------------------------------


def test_bronze_annual_total():
    # premium:          $150 * 12    = $1,800
    # covered_oop:      $0           (Humira not covered)
    # uncovered_costs:  $50,000      (Humira list price, NOT capped by OOP-max)
    # annual_total:                    $51,800
    result = compute_annual_cost(BRONZE_SAVER, MARIA_DRUGS, MARIA_PROVIDERS)
    assert result.annual_premium == 1_800.0
    assert result.covered_oop == 0.0
    assert result.capped_covered_oop == 0.0
    assert result.uncovered_costs == 50_000.0
    assert result.annual_total == 51_800.0


def test_bronze_trap_flagged():
    result = compute_annual_cost(BRONZE_SAVER, MARIA_DRUGS, MARIA_PROVIDERS)
    assert result.trap_flag is True
    assert "Humira" in result.uncovered_drugs


def test_bronze_uncovered_drug_exceeds_oop_max():
    # This is the core proof: $50,000 uncovered > $8,150 OOP-max.
    # The OOP-max does NOT protect against off-formulary drugs.
    result = compute_annual_cost(BRONZE_SAVER, MARIA_DRUGS, MARIA_PROVIDERS)
    assert result.uncovered_costs > BRONZE_SAVER.oop_max


# ---------------------------------------------------------------------------
# Silver — best plan for Maria despite mid-tier premium
# ---------------------------------------------------------------------------


def test_silver_annual_total():
    # premium:          $350 * 12     = $4,200
    # covered_oop raw:  $50,000 * 0.30 = $15,000
    # capped at oop_max $4,000:          $4,000
    # uncovered_costs:  $0
    # annual_total:                      $8,200
    result = compute_annual_cost(SILVER_SELECT, MARIA_DRUGS, MARIA_PROVIDERS)
    assert result.annual_premium == 4_200.0
    assert result.covered_oop == 15_000.0
    assert result.capped_covered_oop == 4_000.0
    assert result.uncovered_costs == 0.0
    assert result.annual_total == 8_200.0


def test_silver_no_trap():
    result = compute_annual_cost(SILVER_SELECT, MARIA_DRUGS, MARIA_PROVIDERS)
    assert result.trap_flag is False
    assert result.uncovered_drugs == []


# ---------------------------------------------------------------------------
# Gold — covered but higher premium than Silver
# ---------------------------------------------------------------------------


def test_gold_annual_total():
    # premium:          $500 * 12     = $6,000
    # covered_oop raw:  $50,000 * 0.25 = $12,500
    # capped at oop_max $3,000:          $3,000
    # uncovered_costs:  $0
    # annual_total:                      $9,000
    result = compute_annual_cost(GOLD_PLUS, MARIA_DRUGS, MARIA_PROVIDERS)
    assert result.annual_premium == 6_000.0
    assert result.covered_oop == 12_500.0
    assert result.capped_covered_oop == 3_000.0
    assert result.uncovered_costs == 0.0
    assert result.annual_total == 9_000.0


def test_gold_no_trap():
    result = compute_annual_cost(GOLD_PLUS, MARIA_DRUGS, MARIA_PROVIDERS)
    assert result.trap_flag is False


# ---------------------------------------------------------------------------
# Platinum — covered with flat copay; under OOP-max, not capped
# ---------------------------------------------------------------------------


def test_platinum_annual_total():
    # premium:          $700 * 12     = $8,400
    # covered_oop:      $150 * 12     = $1,800  (under $2,000 OOP-max, not capped)
    # uncovered_costs:  $0
    # annual_total:                     $10,200
    result = compute_annual_cost(PLATINUM_FULL, MARIA_DRUGS, MARIA_PROVIDERS)
    assert result.annual_premium == 8_400.0
    assert result.covered_oop == 1_800.0
    assert result.capped_covered_oop == 1_800.0
    assert result.uncovered_costs == 0.0
    assert result.annual_total == 10_200.0


def test_platinum_no_trap():
    result = compute_annual_cost(PLATINUM_FULL, MARIA_DRUGS, MARIA_PROVIDERS)
    assert result.trap_flag is False


# ---------------------------------------------------------------------------
# Ranking — the full Maria scenario
# ---------------------------------------------------------------------------


def test_rank_plans_maria_scenario():
    # Expected: Silver ($8,200) < Gold ($9,000) < Platinum ($10,200) < Bronze ($51,800)
    results = [compute_annual_cost(p, MARIA_DRUGS, MARIA_PROVIDERS) for p in ALL_PLANS]
    ranked = rank_plans(results)
    assert [r.plan_id for r in ranked] == [
        "silver-2024",
        "gold-2024",
        "platinum-2024",
        "bronze-2024",
    ]


def test_rank_plans_trap_is_last():
    results = [compute_annual_cost(p, MARIA_DRUGS, MARIA_PROVIDERS) for p in ALL_PLANS]
    ranked = rank_plans(results)
    assert ranked[-1].trap_flag is True
    assert ranked[-1].plan_id == "bronze-2024"


def test_rank_plans_annual_totals_ascending():
    results = [compute_annual_cost(p, MARIA_DRUGS, MARIA_PROVIDERS) for p in ALL_PLANS]
    ranked = rank_plans(results)
    totals = [r.annual_total for r in ranked]
    assert totals == sorted(totals)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_no_drugs_no_providers_only_premium():
    result = compute_annual_cost(BRONZE_SAVER, [], [])
    assert result.annual_total == BRONZE_SAVER.monthly_premium * 12
    assert result.uncovered_costs == 0.0
    assert result.covered_oop == 0.0
    assert result.trap_flag is False


def test_unknown_drug_not_in_formulary():
    # A drug not in the formulary at all: uncovered, $0 cost (no list price known).
    result = compute_annual_cost(BRONZE_SAVER, ["UnknownDrug"], [])
    assert "UnknownDrug" in result.uncovered_drugs
    assert result.uncovered_costs == 0.0  # no list price entry → $0, not fabricated


def test_out_of_network_provider_costs_uncapped():
    plan = PlanData(
        plan_id="oon-test",
        name="OON Test Plan",
        monthly_premium=300.0,
        deductible=2_000.0,
        oop_max=5_000.0,
        network={
            "UCSF Medical Center OB-GYN": ProviderCoverage(
                name="UCSF Medical Center OB-GYN",
                in_network=False,
                out_of_network_cost=8_000.0,
                source="OON Test Network Directory",
            ),
        },
    )
    result = compute_annual_cost(plan, [], ["UCSF Medical Center OB-GYN"])
    assert "UCSF Medical Center OB-GYN" in result.out_of_network_providers
    assert result.uncovered_costs == 8_000.0
    assert result.trap_flag is True
    # OON cost exceeds OOP-max — not capped
    assert result.uncovered_costs > plan.oop_max


def test_citations_in_result():
    result = compute_annual_cost(BRONZE_SAVER, MARIA_DRUGS, MARIA_PROVIDERS)
    assert any("Bronze Saver" in s for s in result.sources)
    assert any("Formulary" in s for s in result.sources)


def test_covered_oop_capped_not_uncovered():
    # Silver: raw covered OOP $15,000 is capped to $4,000.
    # uncovered remains $0 — the cap only applies to covered costs.
    result = compute_annual_cost(SILVER_SELECT, MARIA_DRUGS, MARIA_PROVIDERS)
    assert result.covered_oop == 15_000.0  # raw, before cap
    assert result.capped_covered_oop == 4_000.0  # after cap
    assert result.uncovered_costs == 0.0  # untouched
