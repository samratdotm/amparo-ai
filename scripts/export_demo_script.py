"""Generate DEMO_SCRIPT.pdf from the demo script content."""
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="fpdf")

from fpdf import FPDF
from pathlib import Path

OUT = Path(__file__).parent.parent / "DEMO_SCRIPT.pdf"


def safe(text: str) -> str:
    return (text
        .replace("—", "-").replace("–", "-")
        .replace("‘", "'").replace("’", "'")
        .replace("“", '"').replace("”", '"')
        .encode("latin-1", errors="replace").decode("latin-1")
    )

DARK = (20, 20, 20)
WHITE = (255, 255, 255)
GREEN = (52, 211, 153)
RED = (239, 68, 68)
YELLOW = (251, 191, 36)
GRAY = (160, 160, 160)
LIGHT_GRAY = (40, 40, 40)


class PDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 8, safe(f"Amparo AI Demo Script  |  Page {self.page_no()}"), align="C")

    def section(self, title, color=GREEN):
        self.ln(4)
        self.set_fill_color(*LIGHT_GRAY)
        self.set_text_color(*color)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, safe(title), new_x="LMARGIN", new_y="NEXT", fill=True)
        self.set_text_color(*WHITE)
        self.ln(1)

    def body(self, text, size=10, bold=False, color=WHITE, indent=0):
        self.set_font("Helvetica", "B" if bold else "", size)
        self.set_text_color(*color)
        self.set_x(self.l_margin + indent)
        self.multi_cell(0, 6, safe(text))
        self.ln(1)

    def say(self, text):
        """Quoted speech block."""
        self.set_fill_color(35, 35, 35)
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(200, 230, 200)
        self.set_x(self.l_margin + 4)
        self.multi_cell(0, 6, safe(f'"{text}"'), fill=True)
        self.ln(2)

    def narrate(self, text):
        """Narration block."""
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*GRAY)
        self.set_x(self.l_margin + 4)
        self.multi_cell(0, 5, safe(f"[NARRATE] {text}"))
        self.ln(2)

    def check(self, text, done=False):
        mark = "[x]" if done else "[ ]"
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*WHITE)
        self.set_x(self.l_margin + 4)
        self.cell(0, 6, safe(f"{mark}  {text}"), new_x="LMARGIN", new_y="NEXT")

    def table_row(self, cols, widths, bold=False, color=WHITE):
        self.set_font("Helvetica", "B" if bold else "", 9)
        self.set_text_color(*color)
        for text, w in zip(cols, widths):
            self.cell(w, 6, safe(text), border=1)
        self.ln()


def build():
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(*DARK)
    pdf.rect(0, 0, 210, 297, "F")

    # Title
    pdf.set_y(10)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 12, "Amparo AI", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 8, "Demo Script  |  2.5 minutes", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*YELLOW)
    pdf.cell(0, 8, safe("Phone: +1 (415) 417-6002"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Pre-flight
    pdf.section("BEFORE YOU START", YELLOW)
    pdf.check("Agent running:  uv run python src/agent.py dev")
    pdf.check("Panel open:  localhost:3000")
    pdf.check("Screen recording: ON")
    pdf.check("Phone: charged, silent, notifications off")
    pdf.check('Panel shows: "Waiting for a call..." pulsing dot')
    pdf.ln(2)
    pdf.body("Numbers to know cold:", bold=True, color=YELLOW)
    pdf.body("  PPO (winner):   ~$20,675/yr", color=GREEN)
    pdf.body("  CCHP (trap):    ~$42,877/yr  despite $990/mo premium", color=RED)
    pdf.body("  Delta:  CCHP costs Maria $22,000 MORE per year", bold=True, color=RED)

    # Turn 0 — Hook
    pdf.section("[0:00 - 0:25]  HOOK  — Narrate, no call yet")
    pdf.narrate("Show panel in 'Waiting for a call' state.")
    pdf.say(
        "Every year, 150 million Americans pick a health plan in under 10 minutes. "
        "Studies show the majority pick the wrong one — the cheapest-looking plan "
        "that ends up costing tens of thousands more.\n\n"
        "The tools that exist today either can't talk, or just route you to a human. "
        "Nobody fuses live voice with real-time, personalized, multi-plan comparison. "
        "Until now.\n\n"
        "This is Amparo AI. Let me show you what happens when Maria calls."
    )

    # Turn 1
    pdf.section("[0:25 - 0:50]  TURN 1 — Maria's Ask")
    pdf.body("CALL  +1 (415) 417-6002", bold=True, color=YELLOW)
    pdf.ln(1)
    pdf.body("Say to agent:", bold=True)
    pdf.say(
        "Hi, I'm pregnant and due in March. I take Humira for my arthritis, "
        "and I really want to deliver at UCSF Medical Center. "
        "Can you compare my plan options and tell me which one actually makes sense for me?"
    )
    pdf.body("While agent responds, narrate:", bold=True)
    pdf.narrate(
        "Watch the panel. 28 Moss queries just fired simultaneously across 4 real "
        "Covered California plans. Premium, deductible, OOP max, Humira formulary, "
        "UCSF network status — all in parallel, under 100 milliseconds."
    )
    pdf.body("When trap banner appears, narrate:", bold=True)
    pdf.narrate(
        "The agent found the trap. CCHP looks cheapest at $990 a month. But UCSF "
        "is out of network — that $25,000 delivery cost sits outside the OOP maximum. "
        "It doesn't get capped. Maria pays it on top of everything else. "
        "The PPO — which looks more expensive — costs $22,000 LESS per year."
    )
    pdf.body("Point to citation chip, narrate:", bold=True)
    pdf.narrate(
        "Every fact is cited. Click that chip — it opens the actual Covered California PDF. "
        "Not AI-generated. The real insurer document."
    )

    # Turn 2
    pdf.section("[0:50 - 1:10]  TURN 2 — Clinical Guardrail")
    pdf.body("Still on the call. Say:", bold=True)
    pdf.say("What's the right dose of Humira for someone who's pregnant?")
    pdf.body("Agent fires handoff instantly. Narrate:", bold=True)
    pdf.narrate(
        "That fired before the LLM even saw the message. A deterministic regex — "
        "no AI, no latency, no hallucination risk. In healthcare you cannot let an AI "
        "guess on clinical questions. So we don't. Instant. Absolute."
    )

    # Turn 3
    pdf.section("[1:10 - 1:35]  TURN 3 — Curveball")
    pdf.body("Still on the call. Say:", bold=True)
    pdf.say("Actually — what if I also want to see doctors at Stanford?")
    pdf.body("Panel re-fires. Narrate:", bold=True)
    pdf.narrate(
        "Humira still remembered. UCSF still remembered. Stanford merged in. "
        "Re-fired all queries — re-ranked in real time. Nothing dropped. "
        "This is what year-round benefits navigation looks like — "
        "not a static brochure. A live conversation."
    )
    pdf.body("HANG UP.", bold=True, color=YELLOW)

    # Moss punchline
    pdf.section("[1:35 - 2:00]  MOSS PUNCHLINE — Narrate to camera")
    pdf.say(
        "Here's why Moss is irreplaceable.\n\n"
        "We needed 28 precise facts across 4 plans in under 100 milliseconds "
        "— on a voice call where silence kills the experience.\n\n"
        "A normal vector database: 350ms per query. "
        "28 queries sequentially: 10 seconds of dead air. Voice agent dies.\n\n"
        "Moss in-process retrieval: 3 to 10ms per query. "
        "All 28 fire simultaneously. Total wait equals the slowest single query.\n\n"
        "And the numbers were NEVER computed by AI. The LLM extracted what Maria said. "
        "Moss retrieved the facts. Plain Python did the math. "
        "That's the only way to build something trustworthy when being wrong "
        "costs someone $25,000."
    )

    # Close
    pdf.section("[2:00 - 2:20]  CLOSE — Narrate to camera")
    pdf.say(
        "58% of insured Americans hit a coverage problem every year. "
        "45% get a bill they thought was covered. "
        "Employers spend billions on benefits nobody understands.\n\n"
        "Amparo is a year-round benefits concierge. "
        "Employer pays. Employee calls anytime. "
        "Open enrollment is the wedge.\n\n"
        "The number is live right now. Try it: +1 (415) 417-6002\n\n"
        "LiveKit for voice. Moss for retrieval. "
        "Unsiloed for citations. MiniMax for 40 languages.\n\n"
        "This is Amparo AI."
    )

    # Spanish
    pdf.section("[2:20 - 2:30]  OPTIONAL — Spanish Beat")
    pdf.body("Call again. Say:", bold=True)
    pdf.say("Hola, estoy embarazada y tomo Humira. Puedes comparar mis planes de salud?")
    pdf.narrate(
        "Same agent. MiniMax auto-detects Spanish, responds in Spanish. "
        "No switching, no separate model. The access story — built in."
    )

    # Numbers table
    pdf.section("KEY NUMBERS", YELLOW)
    widths = [62, 32, 52, 28]
    pdf.table_row(["Plan", "Monthly", "Annual (Maria)", ""], widths, bold=True, color=YELLOW)
    pdf.set_text_color(*GREEN)
    pdf.table_row(["Blue Shield HDHP PPO", "$1,473", "~$20,675", "WINNER"], widths, color=GREEN)
    pdf.table_row(["CCHP Bronze HMO", "$990", "~$42,877", "TRAP"], widths, color=RED)
    pdf.table_row(["Kaiser Gold HMO", "$1,392", "~$44,705", "TRAP"], widths, color=RED)
    pdf.table_row(["Blue Shield Trio HMO", "$1,163", "~$66,960", "TRAP"], widths, color=RED)
    pdf.ln(4)
    pdf.body(
        "CCHP costs $22,000 MORE than PPO because UCSF is out-of-network\n"
        "and that $25,000 delivery cost is NOT capped by the OOP maximum.",
        bold=True, color=RED
    )

    # If breaks
    pdf.section("IF SOMETHING BREAKS", RED)
    pdf.body("Call drops     ->  'Live demo, let me reconnect' — keep going", color=WHITE)
    pdf.body("Panel lag      ->  Narrate about Moss latency while waiting", color=WHITE)
    pdf.body("Agent slow     ->  Narrate over the silence", color=WHITE)
    pdf.body("Total failure  ->  PLAY THE BACKUP VIDEO", bold=True, color=RED)

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 8, safe("You built something real. Go show it."), align="C")

    pdf.output(str(OUT))
    print(f"PDF saved: {OUT}")


build()
