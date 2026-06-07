"""
Parse real Covered California plan PDFs with Unsiloed and extract bbox citations per fact.

Real PDFs are multi-page Covered California "Health Plan Details" documents:
  - Page 1:   Plan summary / household info
  - Page 2:   Key Costs and Features table (premium, deductible, OOP max, HSA)
  - Pages 3+: Drug coverage, provider network, additional benefits

We search ALL pages for keywords (not fixed page numbers) since page layout
varies across insurers.

Output: data/citations/{plan_id}_citations.json
  {
    "plan_id": "cchp_2024",
    "moss_id": "cchp-2024",
    "pdf_filename": "cchp_2024.pdf",
    "facts": {
      "benefit:premium":            {"page": 2, "left": 0.32, "top": 0.12, ...},
      "drug:humira":                {"page": 4, ...},
      "provider:ucsf medical center": {"page": 7, ...},
      ...
    }
  }

Usage:
    cd agent-py && uv run python ../scripts/parse_with_unsiloed.py
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
_env = ROOT / "agent-py" / ".env.local"
if _env.exists():
    load_dotenv(_env)

PDFS_DIR = ROOT / "data" / "pdfs"
CITATIONS_DIR = ROOT / "data" / "citations"
CITATIONS_DIR.mkdir(exist_ok=True)

# Must match compare_plans_engine.PLAN_IDS and create_index.PLAN_ID_MAP
PLAN_ID_MAP: dict[str, str] = {
    "cchp_2024": "cchp-2024",
    "trio_2024": "trio-2024",
    "kaiser_2024": "kaiser-2024",
    "ppo_2024": "ppo-2024",
}

API_BASE = "https://prod.visionapi.unsiloed.ai"
POLL_INTERVAL = 5   # seconds between status checks
MAX_WAIT = 300      # seconds before timeout (real PDFs can be slower)

# Benefit fact → ordered list of keywords to try (Covered CA PDF language)
# First match across ALL pages wins.
BENEFIT_KEYWORDS: dict[str, list[str]] = {
    "premium":     ["monthly premium", "your premium", "premium"],
    "deductible":  ["yearly deductible", "annual deductible", "medical deductible", "deductible"],
    "oop_max":     ["out-of-pocket maximum", "out of pocket maximum", "out-of-pocket limit"],
    "hsa_eligible": ["health savings account", "hsa eligible", "hsa-eligible", "hsa"],
}


def get_headers() -> dict:
    key = os.getenv("UNSILOED_API_KEY")
    if not key:
        print("ERROR: UNSILOED_API_KEY not set in .env.local")
        sys.exit(1)
    return {"accept": "application/json", "api-key": key}


def submit_pdf(pdf_path: Path) -> str:
    """Upload PDF to Unsiloed, return job_id."""
    url = f"{API_BASE}/parse"
    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path.name, f, "application/pdf")}
        data = {
            "use_high_resolution": "true",
            "layout_analysis": "smart_layout_detection",
            "ocr_strategy": "auto_detection",
            "merge_tables": "true",
            "segment_filter": "Table,Text,SectionHeader,Title",
        }
        resp = requests.post(url, headers=get_headers(), files=files, data=data, timeout=120)
    resp.raise_for_status()
    result = resp.json()
    job_id = result.get("job_id")
    if not job_id:
        raise ValueError(f"No job_id in response: {result}")
    return job_id


def poll_job(job_id: str) -> dict:
    """Poll until job succeeds, return full result."""
    url = f"{API_BASE}/parse/{job_id}"
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        resp = requests.get(url, headers=get_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "")
        if status == "Succeeded":
            return data
        if status == "Failed":
            raise RuntimeError(f"Unsiloed job {job_id} failed: {data}")
        print(f"    status={status}, waiting {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Job {job_id} did not complete within {MAX_WAIT}s")


def normalize_bbox(bbox: dict, page_width: float, page_height: float) -> dict:
    """Normalize pixel bbox to 0-1 fractions."""
    if not page_width or not page_height:
        return {"left": 0, "top": 0, "width": 0, "height": 0}
    return {
        "left":   bbox.get("left", 0)   / page_width,
        "top":    bbox.get("top", 0)    / page_height,
        "width":  bbox.get("width", 0)  / page_width,
        "height": bbox.get("height", 0) / page_height,
    }


def extract_segments(result: dict) -> list[dict]:
    """Flatten all chunks → segments into a single list."""
    segments = []
    for chunk in result.get("chunks", []):
        for seg in chunk.get("segments", []):
            segments.append(seg)
    return segments


def seg_text(segment: dict) -> str:
    """Concatenate all text fields from a segment, lowercased."""
    return (
        segment.get("content", "") +
        " " + segment.get("markdown", "") +
        " " + segment.get("html", "")
    ).lower()


def find_best_segment(segments: list[dict], keywords: list[str]) -> dict | None:
    """Search ALL pages for the first keyword that matches any segment.

    Returns the segment that contains the first matching keyword.
    Earlier keywords in the list take priority (ordered by specificity).
    """
    for keyword in keywords:
        for seg in segments:
            if keyword.lower() in seg_text(seg):
                return seg
    return None


def build_citation(seg: dict, source_label: str) -> dict:
    bbox = seg.get("bbox", {})
    pw = seg.get("page_width", 0)
    ph = seg.get("page_height", 0)
    norm = normalize_bbox(bbox, pw, ph)
    return {
        "page":        seg.get("page_number", 1),
        "left":        round(norm["left"], 4),
        "top":         round(norm["top"], 4),
        "width":       round(norm["width"], 4),
        "height":      round(norm["height"], 4),
        "source_text": source_label,
    }


def extract_citations(result: dict, plan: dict, moss_id: str) -> dict:
    """Map Unsiloed segments to our fact keys by keyword search across all pages."""
    segments = extract_segments(result)
    facts: dict[str, dict] = {}
    plan_name = plan["plan_name"]

    print(f"    Total segments: {len(segments)}")
    pages_seen = sorted({s.get('page_number', 0) for s in segments})
    print(f"    Pages with content: {pages_seen}")

    # ── Benefit facts ─────────────────────────────────────────────────────────
    plan_source = plan.get("source", f"{plan_name} SBC 2024")
    for field, keywords in BENEFIT_KEYWORDS.items():
        seg = find_best_segment(segments, keywords)
        if seg:
            facts[f"benefit:{field}"] = build_citation(seg, plan_source)
            print(f"    benefit:{field} → page {seg.get('page_number')} ('{keywords[0]}')")
        else:
            print(f"    benefit:{field} → NOT FOUND (tried: {keywords})")

    # ── Drug formulary facts ──────────────────────────────────────────────────
    for drug in plan.get("formulary", []):
        drug_name = drug["drug_name"].lower()
        generic = drug["generic_name"].lower()
        keywords = [drug_name, generic]
        seg = find_best_segment(segments, keywords)
        if seg:
            source = drug.get("source", f"{plan_name} Formulary 2024")
            facts[f"drug:{drug_name}"] = build_citation(seg, source)
            print(f"    drug:{drug_name} → page {seg.get('page_number')}")
        else:
            print(f"    drug:{drug_name} → NOT FOUND in PDF")

    # ── Provider network facts ────────────────────────────────────────────────
    for provider in plan.get("network", []):
        prov_name = provider["provider_name"].lower()
        # Build keyword list: full name, then first 2 words, then first word
        words = prov_name.split()
        keywords = [prov_name]
        if len(words) >= 2:
            keywords.append(words[0] + " " + words[1])
        keywords.append(words[0])
        seg = find_best_segment(segments, keywords)
        if seg:
            source = provider.get("source", f"{plan_name} Provider Directory 2024")
            facts[f"provider:{prov_name}"] = build_citation(seg, source)
            print(f"    provider:{prov_name} → page {seg.get('page_number')}")
        else:
            print(f"    provider:{prov_name} → NOT FOUND in PDF")

    return {
        "plan_id":      plan["plan_id"],
        "moss_id":      moss_id,
        "pdf_filename": f"{plan['plan_id']}.pdf",
        "facts":        facts,
    }


def process_plan(plan_json_path: Path) -> dict:
    with open(plan_json_path) as f:
        plan = json.load(f)

    plan_id = plan["plan_id"]
    moss_id = PLAN_ID_MAP.get(plan_id, plan_id)
    pdf_path = PDFS_DIR / f"{plan_id}.pdf"

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}\n"
            f"Copy the real plan PDF from Desktop to {PDFS_DIR}/{plan_id}.pdf"
        )

    print(f"\n[{plan_id} → {moss_id}] Submitting {pdf_path.name} to Unsiloed...")
    job_id = submit_pdf(pdf_path)
    print(f"  job_id: {job_id}")

    print(f"  Polling for result (max {MAX_WAIT}s)...")
    result = poll_job(job_id)
    total_chunks = result.get("total_chunks", 0)
    print(f"  Done — {total_chunks} chunks returned.")

    citations = extract_citations(result, plan, moss_id)
    matched = len(citations["facts"])
    print(f"  Matched {matched} fact citations.")

    # Save raw Unsiloed output for debugging / re-extraction
    raw_out = CITATIONS_DIR / f"{plan_id}_raw.json"
    with open(raw_out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"  Raw output saved: {raw_out.name}")

    # Save processed citations
    out = CITATIONS_DIR / f"{plan_id}_citations.json"
    with open(out, "w") as f:
        json.dump(citations, f, indent=2)
    print(f"  Citations saved: {out.name}")

    return citations


def main():
    plan_paths = sorted((ROOT / "data" / "plans").glob("*.json"))
    if not plan_paths:
        print("No plan JSONs found in data/plans/.")
        sys.exit(1)

    print(f"Processing {len(plan_paths)} plans...")
    all_citations: dict[str, dict] = {}
    for path in plan_paths:
        try:
            cits = process_plan(path)
            all_citations[cits["plan_id"]] = cits
        except FileNotFoundError as e:
            print(f"  SKIP {path.stem}: {e}")
        except Exception as e:
            print(f"  ERROR for {path.name}: {e}")

    # Summary
    print(f"\n{'='*55}")
    print("Citation extraction summary:")
    for plan_id, cits in all_citations.items():
        facts = cits["facts"]
        print(f"\n  {plan_id} ({cits['moss_id']}): {len(facts)} facts matched")
        for key in sorted(facts.keys()):
            c = facts[key]
            print(f"    {key:<45} page {c['page']}  top={c['top']:.3f}")

    print("\nDone. Run create_index.py next to seed Moss with bbox metadata.")


if __name__ == "__main__":
    main()
