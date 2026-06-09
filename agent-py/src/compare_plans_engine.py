"""Step 4 — parallel Moss retrieval + plan comparison engine.

Per turn:
  1. asyncio.gather fires all Moss queries concurrently (~10 per plan x 4 plans ~= 40 queries)
  2. Results are parsed into PlanData objects
  3. compute_annual_cost (Step 3) ranks the plans and flags the trap

Moss metadata schema (Track C owns the index; must match exactly):
  Benefit doc : {plan, type:"benefit", field:"premium"|"deductible"|"oop_max"|"hsa_eligible", value, source}
  Drug doc    : {plan, type:"drug", covered:"true"|"false", copay_per_fill, coinsurance,
                 list_price_per_year, fills_per_year, source}
  Provider doc: {plan, type:"provider", in_network:"true"|"false", out_of_network_cost, source}
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging

from moss import MossClient, QueryOptions

from constraints import Constraints
from cost_math import (
    Citation,
    CostResult,
    DrugCoverage,
    PlanData,
    ProviderCoverage,
    compute_annual_cost,
    rank_plans,
)

logger = logging.getLogger(__name__)

# Plan IDs — must match the `plan` metadata field in Track C's Moss index
PLAN_IDS = ["cchp-2024", "trio-2024", "kaiser-2024", "ppo-2024"]

BENEFIT_FIELDS = ["premium", "deductible", "oop_max", "hsa_eligible"]

# Fallback list price for a specialty biologic (Humira retail ~$84k/year)
# used when Moss has no coverage doc for that drug.
_DEFAULT_SPECIALTY_LIST_PRICE = 84_000.0

# Fallback OOP-max when Moss has no benefit doc (ACA individual max 2024).
_DEFAULT_OOP_MAX = 9_450.0

# Fallback out-of-network cost when a plan has NO directory entry for a queried
# provider. A provider absent from a narrow-network HMO's directory is, in
# practice, out-of-network — so we fail toward the trap (same philosophy as the
# uncovered-drug fallback) rather than silently assuming in-network coverage.
_DEFAULT_OON_COST = 25_000.0

# Per-query timeout — keeps total retrieval well under 200ms even with 40 queries.
_QUERY_TIMEOUT = 2.0


def _citation_from_meta(meta: dict) -> Citation | None:
    """Build a Citation from Moss metadata if bbox fields are present."""
    if "pdf_url" not in meta or "bbox_page" not in meta:
        return None
    try:
        return Citation(
            pdf_url=meta["pdf_url"],
            page=int(meta["bbox_page"]),
            left=float(meta.get("bbox_left", 0)),
            top=float(meta.get("bbox_top", 0)),
            width=float(meta.get("bbox_width", 0)),
            height=float(meta.get("bbox_height", 0)),
            source_text=meta.get("source", ""),
        )
    except (ValueError, TypeError):
        return None


def _plan_filter(plan_id: str) -> dict:
    """Metadata filter that scopes Moss results to a single plan."""
    return {"field": "plan", "condition": {"$eq": plan_id}}


async def _moss_query(
    moss: MossClient,
    index: str,
    query: str,
    plan_id: str,
    timeout: float = _QUERY_TIMEOUT,
) -> object | None:
    """Single Moss query with per-query timeout and graceful fallback."""
    try:
        return await asyncio.wait_for(
            moss.query(
                index,
                query,
                QueryOptions(top_k=1, alpha=0.6, filter=_plan_filter(plan_id)),
            ),
            timeout=timeout,
        )
    except Exception as exc:
        logger.warning("Moss query failed plan=%s query=%r: %s", plan_id, query, exc)
        return None


def _first_meta(result: object | None) -> dict:
    """Extract metadata from the top Moss result doc, or {} on miss."""
    if result is None:
        return {}
    docs = getattr(result, "docs", None) or []
    return (getattr(docs[0], "metadata", {}) or {}) if docs else {}


def _provider_matches(doc_name: str, queried: str) -> bool:
    """True if a Moss provider doc actually corresponds to the queried provider.

    top_k=1 retrieval always returns the *nearest* doc, even when the plan has no
    entry for the provider. Without this check, querying "Stanford" against a plan
    whose directory only lists UCSF/Kaiser facilities returns a wrong doc — and a
    wrong in_network flag. We compare the provider's distinctive token (e.g.
    "stanford", "ucsf") against the stored, lowercased provider_name.
    """
    doc_name = (doc_name or "").lower().strip()
    queried = (queried or "").lower().strip()
    if not doc_name or not queried:
        return False
    # Distinctive keyword containment in either direction handles
    # "ucsf" ↔ "ucsf medical center" and "stanford" ↔ "stanford health care".
    return queried in doc_name or doc_name in queried


def _float(meta: dict, key: str, default: float) -> float:
    try:
        return float(meta[key])
    except (KeyError, TypeError, ValueError):
        return default


async def _fetch_plan_data(
    moss: MossClient,
    index: str,
    plan_id: str,
    constraints: Constraints,
    on_result=None,
) -> PlanData:
    """Fire all Moss queries for one plan concurrently and assemble PlanData.

    on_result: optional async callable(query: str, result: object) invoked for
    each successful Moss response — used by the agent to stream events to the
    frontend panel as queries complete.
    """
    queries = (
        [f"{plan_id} {field}" for field in BENEFIT_FIELDS]
        + list(constraints.drugs)
        + list(constraints.providers)
    )
    results = await asyncio.gather(
        *[_moss_query(moss, index, q, plan_id) for q in queries]
    )

    if on_result:
        for q, r in zip(queries, results):
            if r is not None:
                await on_result(q, r)

    nb = len(BENEFIT_FIELDS)
    nd = len(constraints.drugs)

    benefit_results = results[:nb]
    drug_results = results[nb : nb + nd]
    provider_results = results[nb + nd :]

    # --- Benefits ---
    premium = _float(_first_meta(benefit_results[0]), "value", 0.0)
    deductible = _float(_first_meta(benefit_results[1]), "value", 0.0)
    oop_max = _float(_first_meta(benefit_results[2]), "value", _DEFAULT_OOP_MAX)
    hsa_eligible = (
        _first_meta(benefit_results[3]).get("value", "false").lower() == "true"
    )

    # --- Drugs ---
    formulary: dict[str, DrugCoverage] = {}
    for drug, result in zip(constraints.drugs, drug_results):
        meta = _first_meta(result)
        if not meta:
            formulary[drug] = DrugCoverage(
                name=drug,
                covered=False,
                list_price_per_year=_DEFAULT_SPECIALTY_LIST_PRICE,
            )
            continue

        covered = meta.get("covered", "false").lower() == "true"
        list_price = _float(meta, "list_price_per_year", _DEFAULT_SPECIALTY_LIST_PRICE)
        citation = _citation_from_meta(meta)

        if covered:
            formulary[drug] = DrugCoverage(
                name=drug,
                covered=True,
                copay_per_fill=_float(meta, "copay_per_fill", None)
                if "copay_per_fill" in meta
                else None,
                coinsurance=_float(meta, "coinsurance", None)
                if "coinsurance" in meta
                else None,
                fills_per_year=int(_float(meta, "fills_per_year", 12)),
                list_price_per_year=list_price,
                source=meta.get("source", ""),
                citation=citation,
            )
        else:
            formulary[drug] = DrugCoverage(
                name=drug,
                covered=False,
                list_price_per_year=list_price,
                source=meta.get("source", ""),
                citation=citation,
            )

    # --- Providers ---
    network: dict[str, ProviderCoverage] = {}
    for provider, result in zip(constraints.providers, provider_results):
        meta = _first_meta(result)
        # Only trust the doc if it is a provider doc that actually names this
        # provider. top_k=1 returns the nearest doc even on a miss, so an absent
        # provider would otherwise read a wrong (often in-network) doc.
        matched = meta.get("type") == "provider" and _provider_matches(
            meta.get("provider_name", ""), provider
        )
        if not matched:
            # No directory entry for this provider on this plan → out-of-network.
            network[provider] = ProviderCoverage(
                name=provider,
                in_network=False,
                out_of_network_cost=_DEFAULT_OON_COST,
                source="",
                citation=None,
            )
            continue
        in_network = meta.get("in_network", "false").lower() == "true"
        network[provider] = ProviderCoverage(
            name=provider,
            in_network=in_network,
            out_of_network_cost=_float(meta, "out_of_network_cost", 0.0),
            source=meta.get("source", ""),
            citation=_citation_from_meta(meta),
        )

    plan_name = _first_meta(benefit_results[0]).get("plan_name", plan_id.upper())

    return PlanData(
        plan_id=plan_id,
        name=plan_name,
        monthly_premium=premium,
        deductible=deductible,
        oop_max=oop_max,
        hsa_eligible=hsa_eligible,
        formulary=formulary,
        network=network,
    )


async def run_comparison(
    moss: MossClient,
    index: str,
    constraints: Constraints,
    plan_ids: list[str] | None = None,
    on_result=None,
) -> list[CostResult]:
    """Fetch all 4 plans in parallel, compute costs, return ranked list.

    Total Moss queries = len(plan_ids) x (benefit_fields + drugs + providers).
    All queries fire concurrently via asyncio.gather.

    on_result: optional async callable forwarded to _fetch_plan_data so the
    caller can stream individual query results to the frontend panel live.
    """
    ids = plan_ids or PLAN_IDS

    all_plan_data = await asyncio.gather(
        *[_fetch_plan_data(moss, index, pid, constraints, on_result) for pid in ids]
    )

    cost_results = [
        compute_annual_cost(plan, constraints.drugs, constraints.providers)
        for plan in all_plan_data
    ]

    return rank_plans(cost_results)


def comparison_to_dict(
    results: list[CostResult], lookup_count: int | None = None
) -> dict:
    """Serialize ranked CostResults to a dict for JSON output.

    lookup_count: pass the actual query count from the caller (which knows
    constraints); falls back to a conservative estimate if omitted.
    """
    count = (
        lookup_count if lookup_count is not None else len(results) * len(BENEFIT_FIELDS)
    )
    return {
        "plans": [dataclasses.asdict(r) for r in results],
        "lookup_count": count,
    }
