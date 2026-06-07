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
KNOWLEDGE_INDEX = os.getenv("MOSS_INDEX_NAME", "knowledge")
MEMORY_INDEX = os.getenv("MOSS_MEMORY_INDEX_NAME", "memory")

# Maps JSON plan_id → Moss plan_id expected by compare_plans_engine.PLAN_IDS
PLAN_ID_MAP: dict[str, str] = {
    "hmo_2024": "bronze-2024",    # lowest premium, Humira uncovered — THE TRAP
    "ppo_2024": "silver-2024",    # Humira covered + UCSF in-network — best for Maria
    "hdhp_2024": "gold-2024",     # HSA-eligible, Humira covered, high deductible
    "epo_2024": "platinum-2024",  # Humira covered, UCSF out-of-network
}

DEFAULT_SPECIALTY_LIST_PRICE = 84_000.0


def _doc(text: str, metadata: dict) -> "DocumentInfo":
    return DocumentInfo(id=str(uuid.uuid4()), text=text, metadata=metadata)


def benefit_docs(plan: dict, moss_id: str) -> list:
    plan_name = plan["plan_name"]
    source = plan["source"]
    docs = []

    family_premium = plan.get("premium_monthly_family", plan.get("premium_monthly_individual", 0))
    docs.append(_doc(
        f"{plan_name} monthly premium family is {family_premium} dollars",
        {"plan": moss_id, "type": "benefit", "field": "premium",
         "value": str(family_premium), "plan_name": plan_name, "source": source},
    ))

    family_ded = plan.get("deductible_family", plan.get("deductible_individual", 0))
    docs.append(_doc(
        f"{plan_name} deductible family is {family_ded} dollars",
        {"plan": moss_id, "type": "benefit", "field": "deductible",
         "value": str(family_ded), "plan_name": plan_name, "source": source},
    ))

    family_oop = plan.get("oop_max_family", plan.get("oop_max_individual", 0))
    docs.append(_doc(
        f"{plan_name} out-of-pocket maximum family is {family_oop} dollars",
        {"plan": moss_id, "type": "benefit", "field": "oop_max",
         "value": str(family_oop), "plan_name": plan_name, "source": source},
    ))

    hsa = plan.get("hsa_eligible", False)
    docs.append(_doc(
        f"{plan_name} HSA eligible is {str(hsa).lower()}",
        {"plan": moss_id, "type": "benefit", "field": "hsa_eligible",
         "value": str(hsa).lower(), "plan_name": plan_name, "source": source},
    ))
    return docs


def formulary_docs(plan: dict, moss_id: str) -> list:
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

        docs.append(_doc(text, meta))
    return docs


def network_docs(plan: dict, moss_id: str) -> list:
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

        meta: dict = {
            "plan": moss_id,
            "type": "provider",
            "provider_name": name.lower(),
            "specialty": specialty,
            "in_network": "true" if in_network else "false",
            "out_of_network_cost": "0",
            "source": provider["source"],
        }
        if provider.get("note"):
            meta["note"] = provider["note"]

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

        b = benefit_docs(plan, moss_id)
        fd = formulary_docs(plan, moss_id)
        n = network_docs(plan, moss_id)
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

    # Smoke test — Humira on bronze must be covered=false
    print("\nSmoke test — Humira coverage on bronze-2024...")
    r = await client.query(
        KNOWLEDGE_INDEX,
        "is Humira covered",
        QueryOptions(top_k=1, alpha=0.6,
                     filter={"field": "plan", "condition": {"$eq": "bronze-2024"}}),
    )
    docs_out = getattr(r, "docs", [])
    if docs_out:
        meta = getattr(docs_out[0], "metadata", {})
        covered = meta.get("covered", "?")
        latency = getattr(r, "time_taken_ms", "?")
        status = "PASS" if covered == "false" else "FAIL"
        print(f"  covered={covered!r}  latency={latency}ms  [{status}]")
    else:
        print("  No results returned.")


if __name__ == "__main__":
    asyncio.run(main())
