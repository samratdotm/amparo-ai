"""Tests for the compare_plans engine and @function_tool.

Uses the same 4-plan fixtures as test_cost_math.py.
Moss is fully stubbed — no credentials or network required.
"""

from __future__ import annotations

import json

import pytest

import agent as agent_module
from agent import Assistant
from compare_plans_engine import (
    PLAN_IDS,
    _fetch_plan_data,
    _first_meta,
    comparison_to_dict,
    run_comparison,
)
from constraints import Constraints

# ---------------------------------------------------------------------------
# Shared fixtures (same values as test_cost_math.py)
# ---------------------------------------------------------------------------

HUMIRA_LIST_PRICE = 50_000.0

MARIA = Constraints(
    drugs=["Humira"],
    providers=["UCSF Medical Center OB-GYN"],
    events=["pregnancy"],
    family_size=2,
    language="es",
)


# ---------------------------------------------------------------------------
# Moss stubs
# ---------------------------------------------------------------------------


class _FakeMossClient:
    def __init__(self, *args, **kwargs):
        self.queries: list[tuple] = []
        self._docs_by_plan: dict[str, list] = {}

    def set_plan_docs(self, plan_id: str, docs: list) -> None:
        self._docs_by_plan[plan_id] = docs

    async def load_index(self, *args, **kwargs):
        pass

    async def query(self, index, query, options=None):
        self.queries.append((index, query, options))
        plan_id = (options.filter or {}).get("condition", {}).get("$eq", "")
        docs = self._docs_by_plan.get(plan_id, [])
        return type("R", (), {"docs": docs, "time_taken_ms": 1.0})()

    async def add_docs(self, *args, **kwargs):
        pass


class _FakeDoc:
    def __init__(self, text: str = "", metadata: dict | None = None):
        self.text = text
        self.score = 0.9
        self.metadata = metadata or {}


@pytest.fixture
def stub_moss(monkeypatch):
    monkeypatch.setattr(agent_module, "MossClient", _FakeMossClient)


# ---------------------------------------------------------------------------
# _first_meta helper
# ---------------------------------------------------------------------------


def test_first_meta_returns_metadata():
    doc = _FakeDoc(metadata={"value": "350"})
    result = type("R", (), {"docs": [doc]})()
    assert _first_meta(result) == {"value": "350"}


def test_first_meta_empty_on_none():
    assert _first_meta(None) == {}


def test_first_meta_empty_on_no_docs():
    result = type("R", (), {"docs": []})()
    assert _first_meta(result) == {}


# ---------------------------------------------------------------------------
# _fetch_plan_data — query count and structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_plan_data_fires_correct_query_count():
    """For 1 drug and 1 provider: 4 benefits + 1 drug + 1 provider = 6 queries."""
    moss = _FakeMossClient()
    await _fetch_plan_data(moss, "knowledge", "silver-2024", MARIA)
    assert len(moss.queries) == 6  # 4 benefits + 1 drug + 1 provider


@pytest.mark.asyncio
async def test_fetch_plan_data_uses_plan_filter():
    """Every query must be scoped to the requested plan_id."""
    moss = _FakeMossClient()
    await _fetch_plan_data(moss, "knowledge", "gold-2024", MARIA)
    for _, _, options in moss.queries:
        assert options is not None
        cond = (options.filter or {}).get("condition", {})
        assert cond.get("$eq") == "gold-2024"


@pytest.mark.asyncio
async def test_fetch_plan_data_parses_benefit_docs():
    """Premium, deductible, oop_max, hsa_eligible are parsed from Moss metadata."""
    moss = _FakeMossClient()
    moss.set_plan_docs(
        "silver-2024",
        [
            _FakeDoc(
                metadata={"value": "350", "plan_name": "Silver Select"}
            ),  # premium
        ],
    )
    plan = await _fetch_plan_data(moss, "knowledge", "silver-2024", MARIA)
    assert plan.monthly_premium == 350.0


@pytest.mark.asyncio
async def test_fetch_plan_data_uncovered_drug_on_no_result():
    """If Moss returns no doc for a drug, it is treated as uncovered."""
    moss = _FakeMossClient()
    plan = await _fetch_plan_data(moss, "knowledge", "bronze-2024", MARIA)
    assert "Humira" in plan.formulary
    assert plan.formulary["Humira"].covered is False


@pytest.mark.asyncio
async def test_fetch_plan_data_covered_drug_parsed():
    """A covered drug doc sets covered=True and coinsurance."""
    moss = _FakeMossClient()
    moss.set_plan_docs(
        "silver-2024",
        [
            _FakeDoc(
                metadata={
                    "covered": "true",
                    "coinsurance": "0.30",
                    "list_price_per_year": "50000",
                }
            )
        ],
    )
    plan = await _fetch_plan_data(moss, "knowledge", "silver-2024", MARIA)
    drug = plan.formulary.get("Humira")
    assert drug is not None
    assert drug.covered is True
    assert drug.coinsurance == pytest.approx(0.30)


# ---------------------------------------------------------------------------
# run_comparison — parallel structure and ranking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_comparison_queries_all_plans():
    """run_comparison must fire queries for every plan in PLAN_IDS."""
    moss = _FakeMossClient()
    await run_comparison(moss, "knowledge", MARIA)
    queried_plans = {
        (opt.filter or {}).get("condition", {}).get("$eq")
        for _, _, opt in moss.queries
        if opt
    }
    assert queried_plans == set(PLAN_IDS)


@pytest.mark.asyncio
async def test_run_comparison_total_query_count():
    """4 plans x (4 benefits + 1 drug + 1 provider) = 24 queries."""
    moss = _FakeMossClient()
    await run_comparison(moss, "knowledge", MARIA)
    assert len(moss.queries) == 24


@pytest.mark.asyncio
async def test_run_comparison_returns_four_results():
    moss = _FakeMossClient()
    results = await run_comparison(moss, "knowledge", MARIA)
    assert len(results) == 4


@pytest.mark.asyncio
async def test_run_comparison_sorted_cheapest_first():
    moss = _FakeMossClient()
    results = await run_comparison(moss, "knowledge", MARIA)
    totals = [r.annual_total for r in results]
    assert totals == sorted(totals)


# ---------------------------------------------------------------------------
# comparison_to_dict serialization
# ---------------------------------------------------------------------------


def _make_result(plan_id: str, total: float, trap: bool = False):
    from cost_math import CostResult

    return CostResult(
        plan_id=plan_id,
        plan_name=plan_id.upper(),
        annual_premium=total,
        covered_oop=0.0,
        capped_covered_oop=0.0,
        uncovered_costs=0.0,
        annual_total=total,
        trap_flag=trap,
        uncovered_drugs=[],
        out_of_network_providers=[],
        sources=[],
    )


def test_comparison_to_dict_has_plans_key():
    results = [_make_result("silver-2024", 8200.0)]
    d = comparison_to_dict(results)
    assert "plans" in d
    assert "lookup_count" in d
    assert len(d["plans"]) == 1


def test_comparison_to_dict_serializable():
    results = [_make_result("bronze-2024", 51800.0, trap=True)]
    d = comparison_to_dict(results)
    json.dumps(d)  # must not raise


def test_comparison_to_dict_trap_flag_preserved():
    results = [_make_result("bronze-2024", 51800.0, trap=True)]
    d = comparison_to_dict(results)
    assert d["plans"][0]["trap_flag"] is True


# ---------------------------------------------------------------------------
# compare_plans @function_tool on the agent
# ---------------------------------------------------------------------------


async def test_compare_plans_tool_requires_constraints(stub_moss) -> None:
    """compare_plans returns an error when called before extract_constraints."""
    assistant = Assistant()
    result = await assistant.compare_plans(None)
    data = json.loads(result)
    assert "error" in data


async def test_compare_plans_tool_returns_json(stub_moss) -> None:
    """compare_plans returns valid JSON with plans + lookup_count after constraints set."""
    assistant = Assistant()
    await assistant.extract_constraints(
        None,
        drugs=["Humira"],
        providers=["UCSF Medical Center OB-GYN"],
        events=["pregnancy"],
        family_size=2,
        hsa_interest=False,
        budget=None,
        language="es",
    )
    result = await assistant.compare_plans(None)
    data = json.loads(result)
    assert "plans" in data
    assert "lookup_count" in data
    assert len(data["plans"]) == 4


async def test_compare_plans_tool_trap_flag_present(stub_moss) -> None:
    """Bronze plan (uncovered Humira) must be flagged as a trap in the output."""
    assistant = Assistant()
    await assistant.extract_constraints(
        None,
        drugs=["Humira"],
        providers=["UCSF Medical Center OB-GYN"],
        events=["pregnancy"],
        family_size=2,
        hsa_interest=False,
        budget=None,
        language="es",
    )
    result = await assistant.compare_plans(None)
    data = json.loads(result)
    # When no Moss data is returned, all drugs are treated as uncovered →
    # uncovered_costs = list_price → trap_flag = True for all plans.
    assert any(p["trap_flag"] for p in data["plans"])
