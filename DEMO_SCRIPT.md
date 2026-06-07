# Amparo AI — Demo Script
**2.5 minutes | Phone: +1 (415) 417-6002**

---

## BEFORE YOU START

- [ ] Agent running: `uv run python src/agent.py dev`
- [ ] Panel open: `localhost:3000`
- [ ] Screen recording: ON
- [ ] Phone: charged, silent
- [ ] Panel shows: "Waiting for a call…" pulsing dot

**Numbers to know cold:**
- PPO (winner): ~$20,675/yr
- CCHP (trap): ~$42,877/yr despite $990/mo premium
- Delta: CCHP costs Maria **$22,000 MORE** per year

---

## [0:00 – 0:25] HOOK
*Narrate. No call yet. Show panel.*

> "Every year, 150 million Americans pick a health plan
> in under 10 minutes. Studies show the majority pick
> the wrong one — the cheapest-looking plan that ends
> up costing tens of thousands more.
>
> The tools that exist today either can't talk, or just
> route you to a human. Nobody fuses live voice with
> real-time, personalized, multi-plan comparison.
> Until now.
>
> This is Amparo AI. Let me show you what happens
> when Maria calls."

---

## [0:25 – 0:50] TURN 1 — Maria's Ask
**CALL +1 (415) 417-6002**

### Say to agent:
> "Hi, I'm pregnant and due in March. I take Humira
> for my arthritis, and I really want to deliver at
> UCSF Medical Center. Can you compare my plan options
> and tell me which one actually makes sense for me?"

### While agent responds, narrate:
> "Watch the panel. 28 Moss queries just fired —
> simultaneously — across 4 real Covered California
> plans. Premium, deductible, OOP max, Humira
> formulary, UCSF network status — all in parallel,
> under 100 milliseconds."

### When panel populates, narrate:
> "The agent found the trap. CCHP looks cheapest at
> $990 a month. But UCSF is out of network — that
> $25,000 delivery cost sits outside the OOP maximum.
> It doesn't get capped. Maria pays it on top of
> everything else.
>
> The PPO — which looks more expensive — actually
> costs $22,000 LESS per year for her situation."

### Point to citation chip:
> "Every fact is cited. Click that chip — it opens
> the actual Covered California PDF. Not AI-generated.
> The real insurer document."

---

## [0:50 – 1:10] TURN 2 — Clinical Guardrail
*Still on the call.*

### Say to agent:
> "What's the right dose of Humira for someone
> who's pregnant?"

### Agent fires handoff instantly. Narrate:
> "That fired before the LLM even saw the message.
> A deterministic regex — no AI, no latency, no
> hallucination risk. In healthcare you cannot let
> an AI guess on clinical questions. So we don't.
> Instant. Absolute."

---

## [1:10 – 1:35] TURN 3 — Curveball
*Still on the call.*

### Say to agent:
> "Actually — what if I also want to see doctors
> at Stanford?"

### Panel re-fires. Narrate:
> "Humira still remembered. UCSF still remembered.
> Stanford merged in. Re-fired all queries — re-ranked
> in real time. Nothing dropped.
>
> This is what year-round benefits navigation looks
> like — not a static brochure. A live conversation."

**HANG UP.**

---

## [1:35 – 2:00] MOSS PUNCHLINE
*Narrate to camera.*

> "Here's why Moss is irreplaceable.
>
> We needed 28 precise facts across 4 plans in under
> 100 milliseconds — on a voice call where silence
> kills the experience.
>
> A normal vector database: 350ms per query.
> 28 queries sequentially: 10 seconds of dead air.
> Voice agent dies.
>
> Moss in-process retrieval: 3–10ms per query.
> All 28 fire simultaneously. Total wait = slowest
> single query. That's what you see on the panel.
>
> And the numbers were NEVER computed by AI. The LLM
> extracted what Maria said. Moss retrieved the facts.
> Plain Python did the math. That's the only way to
> build something trustworthy when being wrong costs
> someone $25,000."

---

## [2:00 – 2:20] CLOSE
*Narrate to camera.*

> "58% of insured Americans hit a coverage problem
> every year. 45% get a bill they thought was covered.
> Employers spend billions on benefits nobody
> understands.
>
> Amparo is a year-round benefits concierge.
> Employer pays. Employee calls anytime.
> Open enrollment is the wedge.
>
> The number is live right now.
> Try it: +1 (415) 417-6002
>
> LiveKit for voice. Moss for retrieval.
> Unsiloed for citations. MiniMax for 40 languages.
>
> This is Amparo AI."

---

## [2:20 – 2:30] OPTIONAL — Spanish Beat
**CALL AGAIN**

### Say to agent:
> "Hola, estoy embarazada y tomo Humira.
> ¿Puedes comparar mis planes de salud?"

### Narrate:
> "Same agent. MiniMax auto-detects Spanish, responds
> in Spanish. No switching, no separate model.
> The access story — built in."

---

## IF SOMETHING BREAKS

- Call drops → stay calm: *"Live demo — let me reconnect"*
- Panel doesn't update → *"Panel updates after the agent responds"*
- Agent slow → narrate over the silence about Moss latency
- Total failure → **play the backup video**

---

## KEY NUMBERS (memorize these)

| Plan | Monthly | Annual (Maria) |
|---|---|---|
| Blue Shield PPO | $1,473 | ~$20,675 ✅ WINNER |
| CCHP Bronze | $990 | ~$42,877 ⚠ TRAP |
| Kaiser Gold | $1,392 | ~$44,705 ⚠ TRAP |
| Blue Shield Trio | $1,163 | ~$66,960 ⚠ TRAP |

**The trap in one sentence:**
CCHP costs $22,000 MORE than PPO because UCSF is
out-of-network and that $25,000 delivery cost is
NOT capped by the OOP maximum.

---

*Good luck. You built something real. Go show it.*
