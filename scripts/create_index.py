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

import json
import sys
from pathlib import Path

try:
    from moss import MossClient, QueryOptions  # type: ignore
except ImportError:
    print("ERROR: 'moss' package not found. Run `pip install moss` or `pnpm setup` first.")
    sys.exit(1)

DATA_DIR = Path(__file__).parent.parent / "data" / "plans"

# Maps JSON plan_id → Moss plan_id expected by compare_plans_engine.PLAN_IDS.
# Ordering: cheapest-premium first so bronze is the trap plan.
PLAN_ID_MAP: dict[str, str] = {
    "hmo_2024": "bronze-2024",    # lowest premium, Humira uncovered — THE TRAP
    "ppo_2024": "silver-2024",    # Humira covered + UCSF in-network — best for Maria
    "hdhp_2024": "gold-2024",     # HSA-eligible, Humira covered, high deductible
    "epo_2024": "platinum-2024",  # Humira covered, but UCSF out-of-network
}

# Fallback list price for specialty biologic used when not specified in JSON.
DEFAULT_SPECIALTY_LIST_PRICE = 50_000.0


def load_plans() -> list[dict]:
    plans = []
    for path in sorted(DATA_DIR.glob("*.json")):
        with open(path) as f:
            plans.append(json.load(f))
    if not plans:
        print(f"ERROR: No plan JSON files found in {DATA_DIR}")
        sys.exit(1)
    print(f"Loaded {len(plans)} plans: {[p['plan_id'] for p in plans]}")
    return plans


def index_benefit_facts(client: "MossClient", plan: dict, moss_id: str) -> int:
    """
    Emit 4 benefit docs per plan with field names matching BENEFIT_FIELDS in
    compare_plans_engine.py: "premium", "deductible", "oop_max", "hsa_eligible".

    Family figures are used for premium/deductible/oop_max since the demo scenario
    (Maria, family_size=2) needs family-tier numbers. Individual figures are also
    indexed with explicit "individual" in the text so year-round Q&A still works.
    """
    plan_name = plan["plan_name"]
    source = plan["source"]
    count = 0

    # --- premium (family — used by the engine for Maria's comparison) ---
    family_premium = plan.get("premium_monthly_family", plan.get("premium_monthly_individual", 0))
    client.add_document(
        text=f"{plan_name} monthly premium family is {family_premium} dollars",
        metadata={
            "plan": moss_id,
            "type": "benefit",
            "field": "premium",
            "value": str(family_premium),
            "plan_name": plan_name,
            "source": source,
        },
    )
    count += 1

    # --- deductible (family) ---
    family_ded = plan.get("deductible_family", plan.get("deductible_individual", 0))
    client.add_document(
        text=f"{plan_name} deductible family is {family_ded} dollars",
        metadata={
            "plan": moss_id,
            "type": "benefit",
            "field": "deductible",
            "value": str(family_ded),
            "plan_name": plan_name,
            "source": source,
        },
    )
    count += 1

    # --- oop_max (family) ---
    family_oop = plan.get("oop_max_family", plan.get("oop_max_individual", 0))
    client.add_document(
        text=f"{plan_name} out-of-pocket maximum family is {family_oop} dollars",
        metadata={
            "plan": moss_id,
            "type": "benefit",
            "field": "oop_max",
            "value": str(family_oop),
            "plan_name": plan_name,
            "source": source,
        },
    )
    count += 1

    # --- hsa_eligible ---
    hsa = plan.get("hsa_eligible", False)
    client.add_document(
        text=f"{plan_name} HSA eligible is {str(hsa).lower()}",
        metadata={
            "plan": moss_id,
            "type": "benefit",
            "field": "hsa_eligible",
            "value": str(hsa).lower(),   # "true" / "false"
            "plan_name": plan_name,
            "source": source,
        },
    )
    count += 1

    return count


def index_formulary(client: "MossClient", plan: dict, moss_id: str) -> int:
    """
    Emit one doc per drug with field names matching _fetch_plan_data:
      covered        → "true" / "false"  (string, NOT bool — engine calls .lower())
      copay_per_fill → monthly member cost (flat copay path in DrugCoverage)
      list_price_per_year → annual retail price (used for uncovered cost + coinsurance base)
      fills_per_year → 12 (default; engine uses this with copay_per_fill)
    """
    plan_name = plan["plan_name"]
    count = 0

    for drug in plan.get("formulary", []):
        drug_name = drug["drug_name"]
        generic = drug["generic_name"]
        drug_class = drug["drug_class"]
        covered: bool = drug["covered"]

        # list_price_per_year: use annual_cost_if_uncovered when available,
        # else fall back to DEFAULT so the trap math stays accurate.
        list_price = float(
            drug.get("annual_cost_if_uncovered") or DEFAULT_SPECIALTY_LIST_PRICE
        )

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

        metadata: dict = {
            "plan": moss_id,
            "type": "drug",
            "drug_name": drug_name.lower(),
            "generic_name": generic.lower(),
            "drug_class": drug_class,
            # String "true"/"false" — engine does meta.get("covered","false").lower()=="true"
            "covered": "true" if covered else "false",
            "list_price_per_year": str(list_price),
            "fills_per_year": "12",
            "source": drug["source"],
        }

        if covered and drug.get("member_cost_per_month") is not None:
            metadata["copay_per_fill"] = str(drug["member_cost_per_month"])

        if drug.get("note"):
            metadata["note"] = drug["note"]

        client.add_document(text=text, metadata=metadata)
        count += 1

    return count


def index_network(client: "MossClient", plan: dict, moss_id: str) -> int:
    """
    Emit one doc per provider with field names matching _fetch_plan_data:
      in_network         → "true" / "false"  (string, NOT bool)
      out_of_network_cost → "0" (not tracked in JSON; engine uses it for uncapped OON cost)
    """
    plan_name = plan["plan_name"]
    count = 0

    for provider in plan.get("network", []):
        name = provider["provider_name"]
        specialty = provider["specialty"]
        in_network: bool = provider["in_network"]
        status = "in-network" if in_network else "OUT-OF-NETWORK"

        text = f"{name} {specialty} is {status} on {plan_name}"
        if not in_network:
            text += ". No out-of-network coverage except emergencies."

        metadata: dict = {
            "plan": moss_id,
            "type": "provider",
            "provider_name": name.lower(),
            "specialty": specialty,
            # String "true"/"false" — engine does meta.get("in_network","true").lower()=="true"
            "in_network": "true" if in_network else "false",
            "out_of_network_cost": "0",
            "source": provider["source"],
        }
        if provider.get("note"):
            metadata["note"] = provider["note"]

        client.add_document(text=text, metadata=metadata)
        count += 1

    return count


def main() -> None:
    print("Building Moss fact-level index...")
    client = MossClient()
    plans = load_plans()

    total_docs = 0
    for plan in plans:
        json_id = plan["plan_id"]
        moss_id = PLAN_ID_MAP.get(json_id, json_id)

        b = index_benefit_facts(client, plan, moss_id)
        f = index_formulary(client, plan, moss_id)
        n = index_network(client, plan, moss_id)
        plan_total = b + f + n
        total_docs += plan_total
        print(f"  {json_id} → {moss_id}: {b} benefit + {f} formulary + {n} network = {plan_total} docs")

    print(f"\nIndexing {total_docs} documents...")
    client.build_index()
    print(f"Index built. {total_docs} docs across {len(plans)} plans.")
    print("\nExpected Moss plan IDs for compare_plans_engine:")
    for j, m in PLAN_ID_MAP.items():
        print(f"  {m}  (from {j})")


if __name__ == "__main__":
    main()
