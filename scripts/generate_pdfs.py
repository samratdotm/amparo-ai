"""
Generate realistic-looking insurance plan PDFs from plan JSONs.

Each PDF has 3 pages:
  Page 1 — Summary of Benefits (premium, deductible, OOP max, HSA)
  Page 2 — Drug Formulary table
  Page 3 — Provider Network Directory

Output: data/pdfs/{plan_id}.pdf  (also copied to frontend/public/pdfs/)

Usage:
    cd agent-py && uv run python ../scripts/generate_pdfs.py
"""

import json
import shutil
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning, module="fpdf")

from fpdf import FPDF

ROOT = Path(__file__).parent.parent
PLANS_DIR = ROOT / "data" / "plans"
OUT_DIR = ROOT / "data" / "pdfs"
FRONTEND_PDF_DIR = ROOT / "frontend" / "public" / "pdfs"

PLAN_ID_MAP = {
    "hmo_2024": "bronze-2024",
    "ppo_2024": "silver-2024",
    "hdhp_2024": "gold-2024",
    "epo_2024": "platinum-2024",
}

# Colors
DARK_BLUE = (30, 58, 138)
MID_BLUE = (59, 130, 246)
LIGHT_BLUE = (219, 234, 254)
RED = (220, 38, 38)
LIGHT_RED = (254, 226, 226)
GRAY_HEADER = (71, 85, 105)
LIGHT_GRAY = (241, 245, 249)
WHITE = (255, 255, 255)
BLACK = (15, 23, 42)
GREEN = (22, 163, 74)


class PlanPDF(FPDF):
    def __init__(self, plan_name: str, plan_type: str):
        super().__init__()
        self.plan_name = plan_name
        self.plan_type = plan_type
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_fill_color(*DARK_BLUE)
        self.rect(0, 0, 210, 14, "F")
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*WHITE)
        self.set_xy(18, 3)
        self.cell(0, 8, f"AMPARO AI  |  {self.plan_name}  |  2024 Plan Year", ln=0)
        self.set_text_color(*BLACK)
        self.ln(10)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5, "This is a synthetic plan document for demonstration purposes only. Not for clinical or legal use.", align="C")

    def plan_title_block(self, subtitle: str):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*DARK_BLUE)
        self.cell(0, 10, self.plan_name, ln=True)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*GRAY_HEADER)
        self.cell(0, 6, subtitle, ln=True)
        self.ln(4)

    def section_header(self, title: str):
        self.set_fill_color(*MID_BLUE)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, f"  {title}", ln=True, fill=True)
        self.set_text_color(*BLACK)
        self.ln(1)

    def table_header(self, cols: list[tuple[str, float]], row_h: float = 7):
        self.set_fill_color(*GRAY_HEADER)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 8)
        for label, w in cols:
            self.cell(w, row_h, f"  {label}", border=0, fill=True)
        self.ln()
        self.set_text_color(*BLACK)

    def table_row(self, cells: list[tuple[str, float]], row_h: float = 7,
                  highlight: bool = False, highlight_red: bool = False):
        if highlight_red:
            self.set_fill_color(*LIGHT_RED)
        elif highlight:
            self.set_fill_color(*LIGHT_BLUE)
        else:
            self.set_fill_color(*LIGHT_GRAY)
        self.set_font("Helvetica", "", 8)

        # Draw row background
        x_start = self.get_x()
        y_start = self.get_y()
        total_w = sum(w for _, w in cells)
        self.rect(x_start, y_start, total_w, row_h, "F")

        for text, w in cells:
            self.cell(w, row_h, f"  {text}", border=0)
        self.ln()

    def divider(self):
        self.set_draw_color(*LIGHT_BLUE)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(2)


def safe(text: str) -> str:
    """Replace non-latin-1 characters so fpdf core fonts don't choke."""
    return (
        text
        .replace("—", "-")   # em dash
        .replace("–", "-")   # en dash
        .replace("‘", "'").replace("’", "'")  # smart quotes
        .replace("“", '"').replace("”", '"')
        .encode("latin-1", errors="replace").decode("latin-1")
    )


def fmt_dollars(val) -> str:
    if val is None:
        return "N/A"
    return f"${int(val):,}"


def fmt_covered(covered: bool) -> str:
    return "Covered" if covered else "NOT COVERED"


def generate_plan_pdf(plan: dict) -> Path:
    plan_id = plan["plan_id"]
    plan_name = plan["plan_name"]
    plan_type = plan["plan_type"]

    pdf = PlanPDF(plan_name, plan_type)

    # ── PAGE 1: SUMMARY OF BENEFITS ──────────────────────────────────────────
    pdf.add_page()
    pdf.plan_title_block("2024 Summary of Benefits and Coverage")

    # Legal notice box
    pdf.set_fill_color(*LIGHT_BLUE)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(30, 58, 138)
    pdf.multi_cell(
        0, 5,
        "This Summary of Benefits and Coverage (SBC) has important information about this health plan. "
        "This is only a summary. For more information about your coverage, or to get a copy of the "
        "complete terms of coverage, call the number on your ID card.",
        fill=True
    )
    pdf.set_text_color(*BLACK)
    pdf.ln(4)

    pdf.section_header("Key Plan Information")
    cols_info = [("Field", 80), ("Individual", 50), ("Family", 44)]
    pdf.table_header(cols_info)

    rows = [
        ("Plan Type", plan_type, "-"),
        ("HSA Eligible", "Yes" if plan.get("hsa_eligible") else "No", "-"),
        ("Monthly Premium", fmt_dollars(plan["premium_monthly_individual"]), fmt_dollars(plan["premium_monthly_family"])),
        ("Annual Deductible", fmt_dollars(plan["deductible_individual"]), fmt_dollars(plan["deductible_family"])),
        ("Out-of-Pocket Maximum", fmt_dollars(plan["oop_max_individual"]), fmt_dollars(plan["oop_max_family"])),
    ]
    for i, (field, ind, fam) in enumerate(rows):
        pdf.table_row(
            [(field, 80), (ind, 50), (fam, 44)],
            highlight=(i % 2 == 0),
        )

    pdf.ln(6)

    # Important notes
    pdf.section_header("Important Coverage Notes")
    pdf.set_font("Helvetica", "", 8.5)
    notes = plan.get("cost_notes", {})
    for key, val in notes.items():
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*MID_BLUE)
        pdf.cell(0, 6, key.replace("_", " ").title() + ":", ln=True)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*BLACK)
        pdf.multi_cell(0, 5, safe(val))
        pdf.ln(1)

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, f"Source: {plan.get('source', '')}", ln=True)

    # ── PAGE 2: DRUG FORMULARY ───────────────────────────────────────────────
    pdf.add_page()
    pdf.plan_title_block("2024 Prescription Drug Formulary")

    pdf.set_font("Helvetica", "", 8.5)
    pdf.multi_cell(
        0, 5,
        "The formulary lists prescription drugs covered by this plan. Drugs not listed are NOT covered "
        "and costs are the full member responsibility. Uncovered specialty drugs do NOT count toward "
        "the out-of-pocket maximum.",
    )
    pdf.ln(4)

    pdf.section_header("Formulary Drug List")
    cols_drug = [("Drug Name", 38), ("Generic Name", 38), ("Class", 30), ("Tier", 12), ("Covered", 22), ("Member Cost/Mo", 34)]
    pdf.table_header(cols_drug, row_h=7)

    for i, drug in enumerate(plan.get("formulary", [])):
        covered = drug["covered"]
        name = drug["drug_name"]
        generic = drug["generic_name"]
        drug_class = drug["drug_class"]
        tier = str(drug["tier"]) if drug["tier"] is not None else "N/A"
        cost = fmt_dollars(drug.get("member_cost_per_month")) if covered else "FULL PRICE"
        is_humira = name.lower() == "humira"
        is_red = is_humira and not covered

        pdf.table_row(
            [(name, 38), (generic, 38), (drug_class, 30), (tier, 12), (fmt_covered(covered), 22), (cost, 34)],
            highlight=(i % 2 == 0),
            highlight_red=is_red,
        )

        # Add note row if present
        if drug.get("note"):
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(10, 5, "", border=0)
            pdf.multi_cell(0, 5, safe(f"  Note: {drug['note']}"))
            pdf.set_text_color(*BLACK)

        # Citation line
        pdf.set_font("Helvetica", "I", 6.5)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(0, 4, f"      Source: {drug.get('source', '')}", ln=True)
        pdf.set_text_color(*BLACK)
        pdf.ln(1)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*RED)
    pdf.multi_cell(
        0, 5,
        "WARNING: Specialty biologics not on this formulary (e.g. Humira/adalimumab on HMO plans) "
        "are entirely the member's financial responsibility and do NOT count toward the out-of-pocket maximum. "
        "The annual list price for such drugs may exceed $38,000.",
    )
    pdf.set_text_color(*BLACK)

    # ── PAGE 3: PROVIDER NETWORK ─────────────────────────────────────────────
    pdf.add_page()
    pdf.plan_title_block("2024 Provider Network Directory (Partial Listing)")

    pdf.set_font("Helvetica", "", 8.5)
    pdf.multi_cell(
        0, 5,
        "The following providers are included in this plan's network for the San Francisco metro area. "
        "Out-of-network care is not covered except for emergency services, unless otherwise noted.",
    )
    pdf.ln(4)

    pdf.section_header("San Francisco Area Providers")
    cols_prov = [("Provider Name", 65), ("Specialty", 40), ("Network Status", 30), ("Notes", 39)]
    pdf.table_header(cols_prov, row_h=7)

    for i, provider in enumerate(plan.get("network", [])):
        name = provider["provider_name"]
        specialty = provider["specialty"]
        in_net = provider["in_network"]
        status = "IN-NETWORK" if in_net else "OUT-OF-NETWORK"
        note = provider.get("note") or ""
        is_ucsf = "ucsf" in name.lower()
        is_red = is_ucsf and not in_net

        # Truncate note for table cell
        note = safe(note)
        short_note = (note[:55] + "...") if len(note) > 55 else note

        pdf.table_row(
            [(name, 65), (specialty, 40), (status, 30), (short_note, 39)],
            highlight=(i % 2 == 0),
            highlight_red=is_red,
        )

        # Full note
        if note and len(note) > 55:
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(100, 116, 139)
            pdf.multi_cell(0, 5, safe(f"      {note}"))
            pdf.set_text_color(*BLACK)

        # Citation
        pdf.set_font("Helvetica", "I", 6.5)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(0, 4, f"      Source: {provider.get('source', '')}", ln=True)
        pdf.set_text_color(*BLACK)
        pdf.ln(1)

    out_path = OUT_DIR / f"{plan_id}.pdf"
    pdf.output(str(out_path))
    return out_path


def main():
    plan_paths = sorted(PLANS_DIR.glob("*.json"))
    if not plan_paths:
        print(f"No plan JSONs found in {PLANS_DIR}")
        return

    for path in plan_paths:
        with open(path) as f:
            plan = json.load(f)

        plan_name = plan["plan_name"]
        out_path = generate_plan_pdf(plan)
        print(f"  Generated: {out_path.name}  ({plan_name})")

        # Copy to frontend public dir for static serving
        dst = FRONTEND_PDF_DIR / out_path.name
        shutil.copy2(out_path, dst)
        print(f"  Copied to: frontend/public/pdfs/{out_path.name}")

    print(f"\nDone — {len(plan_paths)} PDFs generated.")


if __name__ == "__main__":
    main()
