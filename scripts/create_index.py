"""
Build the Moss fact-level index from plan JSON files.

One document per fact (benefit / formulary / provider) so each Moss query
resolves to exactly one precise fact — enabling ~40 parallel lookups per turn.

Metadata schema (must match compare_plans_engine.py exactly):
  Benefit doc : {plan, type:"benefit", field:"premium"|"deductible"|"oop_max"|"hsa_eligible",
                 value, plan_name, source}
  Drug doc    : {plan, type:"drug", covered:"true"|"false",
                 copay_per_fill, list_price_per_year, fills_per_year, source}
  Provider doc: {plan, type:"provider", in_network:"true"|"false",
                 out_of_network_cost, source}

Usage:
    python scripts/create_index.py
"""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

# Load credentials — check agent-py/.env.local then project root .env.local
_ROOT = Path(__file__).parent.parent
for _env_path in [_ROOT / "agent-py" / ".env.local", _ROOT / ".env.local"]:
    if _env_path.exists():
        load_dotenv(_env_path)
        break

try:
    from moss import DocumentInfo, MossClient, QueryOptions  # type: ignore
except ImportError:
    print("ERROR: 'moss' package not found. Run `pip install moss` first.")
    sys.exit(1)

DATA_DIR = _ROOT / "data" / "plans"
CITATIONS_DIR = _ROOT / "data" / "citations"
KNOWLEDGE_INDEX = os.getenv("MOSS_INDEX_NAME", "knowledge")
MEMORY_INDEX = os.getenv("MOSS_MEMORY_INDEX_NAME", "memory")

# Maps JSON plan_id → Moss plan_id expected by compare_plans_engine.PLAN_IDS
PLAN_ID_MAP: dict[str, str] = {
    "cchp_2024": "cchp-2024",    # cheapest premium, UCSF excluded — THE CHEAP PLAN TRAP
    "trio_2024": "trio-2024",    # narrow Trio network, UCSF excluded
    "kaiser_2024": "kaiser-2024", # 5-star closed system, UCSF 100% excluded — QUALITY TRAP
    "ppo_2024": "ppo-2024",      # highest premium, UCSF in-network — TRUE WINNER
}

DEFAULT_SPECIALTY_LIST_PRICE = 84_000.0


def _load_citations(plan_id: str) -> dict:
    """Load Unsiloed bbox citations for a plan, keyed by fact key. Returns {} if not found."""
    path = CITATIONS_DIR / f"{plan_id}_citations.json"
    if not path.exists():
        return {}
    with open(path) as f:
        data = json.load(f)
    return data.get("facts", {})


def _inject_citation(meta: dict, citations: dict, fact_key: str, plan_id: str) -> dict:
    """Add pdf_url + bbox_* fields to metadata if citation exists for this fact."""
    cit = citations.get(fact_key)
    if cit:
        meta["pdf_url"] = f"/pdfs/{plan_id}.pdf"
        meta["bbox_page"] = str(cit["page"])
        meta["bbox_left"] = str(round(cit["left"], 4))
        meta["bbox_top"] = str(round(cit["top"], 4))
        meta["bbox_width"] = str(round(cit["width"], 4))
        meta["bbox_height"] = str(round(cit["height"], 4))
    return meta


def _doc(text: str, metadata: dict) -> "DocumentInfo":
    return DocumentInfo(id=str(uuid.uuid4()), text=text, metadata=metadata)


def benefit_docs(plan: dict, moss_id: str, citations: dict, plan_id: str) -> list:
    plan_name = plan["plan_name"]
    source = plan["source"]
    docs = []

    premium = plan.get("premium_monthly_individual") or plan.get("premium_monthly_family", 0)
    docs.append(_doc(
        f"{plan_name} monthly premium individual is {premium} dollars",
        _inject_citation(
            {"plan": moss_id, "type": "benefit", "field": "premium",
             "value": str(premium), "plan_name": plan_name, "source": source},
            citations, "benefit:premium", plan_id,
        ),
    ))

    deductible = plan.get("deductible_individual") or plan.get("deductible_family", 0)
    docs.append(_doc(
        f"{plan_name} deductible individual is {deductible} dollars",
        _inject_citation(
            {"plan": moss_id, "type": "benefit", "field": "deductible",
             "value": str(deductible), "plan_name": plan_name, "source": source},
            citations, "benefit:deductible", plan_id,
        ),
    ))

    oop_max = plan.get("oop_max_individual") or plan.get("oop_max_family", 0)
    docs.append(_doc(
        f"{plan_name} out-of-pocket maximum individual is {oop_max} dollars",
        _inject_citation(
            {"plan": moss_id, "type": "benefit", "field": "oop_max",
             "value": str(oop_max), "plan_name": plan_name, "source": source},
            citations, "benefit:oop_max", plan_id,
        ),
    ))

    hsa = plan.get("hsa_eligible", False)
    docs.append(_doc(
        f"{plan_name} HSA eligible is {str(hsa).lower()}",
        _inject_citation(
            {"plan": moss_id, "type": "benefit", "field": "hsa_eligible",
             "value": str(hsa).lower(), "plan_name": plan_name, "source": source},
            citations, "benefit:hsa_eligible", plan_id,
        ),
    ))
    return docs


def formulary_docs(plan: dict, moss_id: str, citations: dict, plan_id: str) -> list:
    plan_name = plan["plan_name"]
    docs = []

    for drug in plan.get("formulary", []):
        drug_name = drug["drug_name"]
        generic = drug["generic_name"]
        drug_class = drug["drug_class"]
        covered: bool = drug["covered"]
        list_price = float(drug.get("annual_cost_if_uncovered") or DEFAULT_SPECIALTY_LIST_PRICE)

        if covered:
            copay = drug.get("member_cost_per_month")
            text = (
                f"{drug_name} ({generic}) {drug_class} covered on {plan_name} "
                f"tier {drug.get('tier')} member cost {copay} dollars per month"
            )
        else:
            text = (
                f"{drug_name} ({generic}) {drug_class} NOT covered on {plan_name}. "
                f"Full annual cost {list_price:.0f} dollars, not subject to OOP maximum."
            )

        meta: dict = {
            "plan": moss_id,
            "type": "drug",
            "drug_name": drug_name.lower(),
            "generic_name": generic.lower(),
            "drug_class": drug_class,
            "covered": "true" if covered else "false",
            "list_price_per_year": str(list_price),
            "fills_per_year": "12",
            "source": drug["source"],
        }
        if covered and drug.get("member_cost_per_month") is not None:
            meta["copay_per_fill"] = str(drug["member_cost_per_month"])
        if drug.get("note"):
            meta["note"] = drug["note"]

        _inject_citation(meta, citations, f"drug:{drug_name.lower()}", plan_id)
        docs.append(_doc(text, meta))
    return docs


def network_docs(plan: dict, moss_id: str, citations: dict, plan_id: str) -> list:
    plan_name = plan["plan_name"]
    docs = []

    for provider in plan.get("network", []):
        name = provider["provider_name"]
        specialty = provider["specialty"]
        in_network: bool = provider["in_network"]
        status = "in-network" if in_network else "OUT-OF-NETWORK"

        text = f"{name} {specialty} is {status} on {plan_name}"
        if not in_network:
            text += ". No out-of-network coverage except emergencies."

        oon_cost = provider.get("out_of_network_cost", 0) if not in_network else 0
        meta: dict = {
            "plan": moss_id,
            "type": "provider",
            "provider_name": name.lower(),
            "specialty": specialty,
            "in_network": "true" if in_network else "false",
            "out_of_network_cost": str(oon_cost),
            "source": provider["source"],
        }
        if provider.get("note"):
            meta["note"] = provider["note"]

        _inject_citation(meta, citations, f"provider:{name.lower()}", plan_id)
        docs.append(_doc(text, meta))
    return docs


async def main() -> None:
    project_id = os.getenv("MOSS_PROJECT_ID")
    project_key = os.getenv("MOSS_PROJECT_KEY")
    if not project_id or not project_key:
        print("ERROR: MOSS_PROJECT_ID and MOSS_PROJECT_KEY must be set in .env.local")
        sys.exit(1)

    client = MossClient(project_id, project_key)

    plan_paths = sorted(DATA_DIR.glob("*.json"))
    if not plan_paths:
        print(f"ERROR: No plan JSON files found in {DATA_DIR}")
        sys.exit(1)

    all_docs: list = []
    for path in plan_paths:
        with open(path) as f:
            plan = json.load(f)

        json_id = plan["plan_id"]
        moss_id = PLAN_ID_MAP.get(json_id, json_id)
        citations = _load_citations(json_id)
        has_cit = len(citations)
        print(f"  {json_id} -> {moss_id}: {has_cit} Unsiloed citations loaded")

        b = benefit_docs(plan, moss_id, citations, json_id)
        fd = formulary_docs(plan, moss_id, citations, json_id)
        n = network_docs(plan, moss_id, citations, json_id)
        print(f"  {json_id} -> {moss_id}: {len(b)} benefit + {len(fd)} formulary + {len(n)} network")
        all_docs.extend(b + fd + n)

    # List existing indexes so we can delete-and-recreate knowledge without
    # hitting the free-tier limit, and skip memory if it already exists.
    existing = await client.list_indexes()
    existing_names = {idx.name for idx in existing}
    print(f"Existing indexes: {sorted(existing_names)}")

    if KNOWLEDGE_INDEX in existing_names:
        print(f"Deleting stale '{KNOWLEDGE_INDEX}' index...")
        await client.delete_index(KNOWLEDGE_INDEX)

    print(f"\nCreating Moss index '{KNOWLEDGE_INDEX}' with {len(all_docs)} documents...")
    result = await client.create_index(KNOWLEDGE_INDEX, all_docs)
    print(f"Index created: {result}")

    print("Loading index into memory...")
    await client.load_index(KNOWLEDGE_INDEX)
    print("Knowledge index loaded.")

    # Create the memory index only if it doesn't exist yet.
    if MEMORY_INDEX in existing_names:
        print(f"\nMemory index '{MEMORY_INDEX}' already exists — skipping creation.")
        await client.load_index(MEMORY_INDEX)
        print("Memory index loaded.")
    else:
        print(f"\nCreating Moss memory index '{MEMORY_INDEX}'...")
        seed_doc = DocumentInfo(
            id=str(uuid.uuid4()),
            text="Amparo AI per-user memory store initialized",
            metadata={"type": "system", "note": "seed"},
        )
        await client.create_index(MEMORY_INDEX, [seed_doc])
        await client.load_index(MEMORY_INDEX)
        print("Memory index loaded.")

    # Smoke test — UCSF on cchp-2024 must be out-of-network (the network trap)
    print("\nSmoke test — UCSF network status on cchp-2024...")
    r = await client.query(
        KNOWLEDGE_INDEX,
        "UCSF Medical Center network",
        QueryOptions(top_k=1, alpha=0.6,
                     filter={"field": "plan", "condition": {"$eq": "cchp-2024"}}),
    )
    docs_out = getattr(r, "docs", [])
    if docs_out:
        meta = getattr(docs_out[0], "metadata", {})
        in_network = meta.get("in_network", "?")
        oon_cost = meta.get("out_of_network_cost", "?")
        latency = getattr(r, "time_taken_ms", "?")
        status = "PASS" if in_network == "false" and oon_cost != "0" else "FAIL"
        print(f"  in_network={in_network!r}  out_of_network_cost={oon_cost!r}  latency={latency}ms  [{status}]")
    else:
        print("  No results returned.")


if __name__ == "__main__":
    asyncio.run(main())
