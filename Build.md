# Amparo AI — Build Plan (Conversational AI Hackathon, Moss @ YC, Jun 6–7 2026)

## Context

**Why this project:** Choosing and using a health plan is a high-stakes decision people are provably bad at — the *majority* of 23,894 employees in one study picked a financially **dominated** plan, overspending ~24% of premium (QJE 2017); only **14%** can define the four basic insurance terms (J. Health Econ. 2013); **58%** of insured adults hit a coverage problem each year and **45%** get a bill they thought was covered (KFF / Commonwealth Fund 2024). Today's tools are split: web tools (Nayya, Healthpilot) **can't talk**; voice tools (eHealth, Fair Square) **just route you to a human**. **Nobody fuses live voice + real, personalized, multi-plan comparison** — CMS literally issued an RFI for exactly this (Feb 2026). That gap is verified-open.

**What we're building:** **Amparo AI** — a multilingual voice agent that lets an employee describe their life in plain speech and instantly get a personalized, cited comparison of *their* plans (what's covered, what it really costs), plus year-round coverage Q&A. Positioned as a **year-round benefits concierge** (open enrollment is the wedge; the **employer** is the buyer).

**Why this stack is necessary (not arbitrary):** The product imposes five hard constraints — voice-native, huge knowledge base (formularies/networks), facts must be exact (healthcare liability), personalized, and live/re-grounding. Answering "which plan for me" = **30–40 precise lookups per turn**. At a normal vector DB's ~350ms/query that's seconds of dead air on a voice call — the wall that has kept this unbuilt. **Moss's in-process ~3–10ms retrieval is the only thing that makes it possible.** That's the demo *and* the moat.

**Safety boundary (non-negotiable):** Amparo is a **coverage & cost navigator, NOT a clinical advisor.** It states what plans cover/cost (cited to the source) and explains plan processes; it **never** recommends a specific drug, gives dosing/safety advice, diagnoses, or claims a license. Every clinical question routes to "your doctor or pharmacist." Demo uses **synthetic personas + public plan documents** — zero real PHI. (Grounded in the DoNotPay/NEDA-Tessa/PA-Character.AI precedents.)

---

## Scope: MVP vs. layered priorities

**MVP — must work or we have no demo (P0):**
1. Voice in → Maria describes her messy situation → Amparo answers in <~1.5s, no hold.
2. Real-time **parallel comparison of 4 plans** across her drugs/doctors/dimensions.
3. The **gotcha**: the cheapest-premium plan exposed as a ~$38k trap (uncovered specialty drug).
4. The **panel** showing the lookups firing (counter + latency) and the comparison table building live.

**Layered priorities (add in this order):**
- P1: **Citations** (surface the source line via Unsiloed) — also a safety feature.
- P1: **Clinical-handoff guardrail** (detect a clinical question → route to a human). Cheap, high credibility.
- P2: **Curveball** re-grounding ("what if I deliver at a different hospital?").
- P2: **Multilingual** beat (Spanish via MiniMax/Qwen) — the access story + a sponsor prize.
- P3: **TrueFoundry** gateway (live provider failover + "info-not-advice" guardrail on a dashboard).
- P3: Deploy on AWS (a tunnel/local demo is acceptable if needed).

---

## Architecture

**Reuse the official starter:** `github.com/livekit-examples/moss-hacker-starter` (MIT). It already wires a **Python LiveKit agent** (three `@function_tool`s over Moss) to a **Next.js "Knowledge Matches" panel**, needs only LiveKit + Moss creds (STT/LLM/TTS via LiveKit Inference — no extra keys), and ships `pnpm setup` / `lk app env` / `pnpm moss:index` / `pnpm dev`. **We build on top of this, not from scratch.**

**Stack & one-line justification:**
- **LiveKit** — real-time voice pipeline (STT→LLM→TTS, turn-taking, barge-in) + the `@function_tool` hook to inject retrieval mid-turn. *Core.*
- **Moss** — in-process ~3–10ms retrieval; enables 30–40 lookups/turn. *The hero; irreplaceable.*
- **Unsiloed** — parse dense, multi-page plan tables → structured + **bbox-citable** data. *Accuracy + citations.*
- **MiniMax (or Qwen)** — multilingual TTS (40-lang inline code-switching) for the access beat. *Swappable but on-mission.*
- **TrueFoundry** — gateway: failover, latency/cost observability, central guardrail. *Bolt-on, not core.*
- **AWS** — hosting. (Deliberately **not** Nova Sonic — it would collapse the pipeline and sideline the Moss-as-tool moment + the voice prizes.)

**The core engine (the one hard thing — Track A owns it).** Per user turn:
1. **STT** (LiveKit) → utterance.
2. **Constraint extraction** (1 LLM call) → structured `{drugs[], providers[], events[e.g. pregnancy], family[], hsa_interest, budget, language}`.
3. **Parallel retrieval (the Moss hero)** — `asyncio.gather` fires, concurrently, for **each plan × each constraint**: drug → formulary tier/cost; provider → in/out-of-network; plus premium, deductible, OOP-max, HSA eligibility. ~10 lookups × 4 plans ≈ **40 Moss queries, ~ms each**.
4. **Deterministic cost computation (plain code, NOT the LLM — this is the anti-hallucination guarantee):** for each plan, `annual = premium*12 + capped_covered_OOP + uncovered_costs`. Key trap logic: **uncovered drug costs are NOT capped by OOP-max** → that's what makes the cheap plan catastrophic. Flag hard constraints (preferred provider out-of-network = "loses your doctor").
5. **Response generation** (LLM) — compose a plain-language, **cited**, decision-support answer from the structured result. Guardrail: if a clinical question is detected, return the **handoff** line instead.
6. **TTS** (MiniMax/Qwen, in the user's language) → voice out.
7. **Stream** retrieval events (lookups + latency) + the comparison table to the frontend panel.

**Moss data model (Track C owns it) — index at the FACT level** so each lookup is one precise fact (this is what makes "40 lookups" real and citable):
- Benefit facts: one doc per (plan, field) — premium/deductible/OOP/HSA. `metadata: {plan, type:'benefit', field, value, source}`
- Formulary: one doc per (plan, drug) for in-scope drugs. `text:"Humira (adalimumab) specialty biologic", metadata:{plan, type:'drug', tier, cost, covered, source}`
- Network: one doc per (plan, provider/facility). `text:"UCSF Medical Center — OB-GYN", metadata:{plan, type:'provider', in_network, source}`
- Query via Moss hybrid search (`QueryOptions(top_k, alpha≈0.6)`) + **metadata filter** by `{plan, type}`. Semantic match resolves "my OB-GYN at UCSF" → the UCSF doc, "Humira" → its formulary entry (+ class, for the coverage-breadth beat). Embeddings: built-in `moss-minilm` (no extra key).

---

## Critical components to build

| Component | Where | Notes |
|---|---|---|
| `extract_constraints` tool | starter's Python agent (the `@function_tool` file) | LLM → structured constraints |
| `compare_plans` tool | same file | the parallel-retrieval + deterministic-cost engine (P0) |
| year-round Q&A | keep starter's `search_knowledge` + memory tools | "is X covered / why this bill" single-lookup path |
| Moss index builder | replace `pnpm moss:index` script | fact-level docs + metadata (above) |
| Plan data | `data/plans/*.json` | 4 curated plans; personas' drugs/doctors covered |
| Unsiloed parse | `scripts/parse_sbc.*` | parse ≥1 SBC live → JSON + citations; curate the rest |
| Amparo panel | starter's "Knowledge Matches" Next.js component | split-screen: transcript ∣ lookup counter+latency + live comparison table + citation popovers |
| Guardrail | response step | clinical-question detector → handoff line + disclaimer |

---

## Team tracks (assign people here; scales 2–4)

- **Track A — Voice + retrieval engine** (your strongest builder): the agent loop, `compare_plans`, cost math, guardrail. *Owns the MVP.*
- **Track B — Frontend / demo panel:** the split-screen, lookup counter + latency, live table, citations. *The "make Moss visible" weapon.*
- **Track C — Data + correctness:** the 4 plans, Unsiloed parse, Moss index, and a **golden test set** verifying every demo answer is correct.
- **Track D (if 4+) — Demo & pitch owner:** rehearses the script, builds the backup video, preps Q&A, wires multilingual/TrueFoundry.

*If 2–3 people:* A also does the guardrail; B absorbs D; C is shared. **Always protect Track A's MVP first.**

---

## Timeline (~20h; clock-mapped, with sleep rotation)

- **2:30–3:30 PM** — *Phase 0 Setup:* clone starter, get LiveKit + Moss keys, run baseline voice loop end-to-end, assign tracks, lock the 4 plans + 2 personas (Maria; Spanish-speaker).
- **3:30–6:30 PM** — *Phase 1 Foundation:* C builds plan JSON + Moss fact index (≥1 plan via Unsiloed); A builds the extract→retrieve scaffold (1 plan, 1 question working); B forks the panel + layout.
- **6:30–7:15 PM** — dinner.
- **7:15–11:00 PM** — *Phase 2 Core engine (P0):* A finishes the **4-plan parallel comparison + cost math** for full Maria; C finalizes all 4 plans + golden tests; B streams live lookups + table to the panel. **Checkpoint by 11pm: the MVP demo works end-to-end.**
- **11:00 PM–1:00 AM** — *Phase 3 Beats + safety (P1):* the $38k gotcha; citations; clinical-handoff guardrail + disclaimer.
- **1:00–3:00 AM** — *Phase 4 Polish (P2):* curveball re-grounding; multilingual Spanish beat; (deploy/TrueFoundry if ahead). *Start sleep rotation.*
- **3:00–7:30 AM** — buffer / sleep rotation / catch-up.
- **7:30–9:30 AM** — *Phase 5 Harden:* pre-warm Moss index (cache first query), run the **exact demo 10×**, **record a flawless backup video**.
- **~9:30 AM** — **FREEZE BUILD.** No new features.
- **9:30–10:30 AM** — rehearse pitch + Q&A.
- **10:30–11:00 AM** — submit + buffer.

---

## Demo script (2.5 min)

Hook ("who re-enrolled without comparing?") → Maria's messy ask (panel **erupts: 37 lookups · 94 ms**) → **the $38k gotcha** (cheap plan's uncovered drug) with a **page-4 citation** → **clinical handoff** ("that's for your doctor — here's what I *can* tell you") → **curveball** (different hospital, re-checks live) → **Moss punchline** ("40 lookups, under 100ms — a normal DB is 15s of silence; that's why Amparo needs Moss") → close (market + "selection is the wedge; 58% hit a coverage problem every year — we're there all year"). Optional Spanish beat. **Have the backup video ready.**

---

## Descope plan (if behind)

Cut in this order, last-first: TrueFoundry → AWS deploy (run local) → multilingual → curveball → live Unsiloed parse (use pre-curated JSON). **Never cut:** the 4-plan comparison, the gotcha, the panel, the clinical-handoff line.

## Risks & fallbacks

- **Wrong answer on stage = fatal** → cost math is deterministic code; golden test set; every number cited; keep to 4 plans.
- **Dead air kills the demo** → pre-warm/cache Moss; rehearse the exact path; pre-record caller lines as backup so human STT can't tank you.
- **Anything breaks live** → narrate over the backup video. Non-negotiable to have it.
- **Provider/API outage** → TrueFoundry failover if built; else a local LLM/TTS fallback config.

## Verification (how we know it works)

1. **Unit:** golden test set — for each persona, assert the computed annual cost + ranking + the trap flag match hand-verified values for all 4 plans.
2. **Retrieval:** log every Moss query + latency; confirm ~30–40 lookups/turn at <~10ms each (the panel proves it live).
3. **End-to-end:** run the full spoken demo 10× — Maria's ask, the gotcha, the curveball, the clinical handoff — with zero wrong numbers and no >2s pause.
4. **Safety:** fire 5 clinical questions ("should I switch drugs", "is this safe", "what dose") → all must return the handoff, never advice.

## Sponsor-prize mapping

Moss (the retrieval hero) · LiveKit (voice pipeline) · Unsiloed (parse + citations) · MiniMax/Qwen (multilingual access) · TrueFoundry (failover + guardrail) · AWS (deploy). Each is *load-bearing or visibly demoed* — which is how "best use of X" is actually won.
