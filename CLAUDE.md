# CLAUDE.md — Amparo AI

Amparo AI: a multilingual **voice agent** that helps employees understand their health
insurance — instant, personalized, *cited* comparison of their plans (coverage + real cost)
plus year-round coverage Q&A. Hackathon project (Moss @ YC). **Read `Build.md` fully before
writing code** — it has the timeline, tracks, demo script, and verification.

## Golden rules — do NOT deviate
1. **Coverage navigator, NOT a clinical advisor.** State what plans cover/cost and how plan
   processes work, always cited. NEVER recommend a drug, give dosing/safety advice, diagnose,
   or claim a license. Any clinical question → route to "your doctor or pharmacist."
2. **Numbers are computed in deterministic code, never by the LLM.** The model only extracts
   constraints and phrases answers. A hallucinated cost is a project-ending bug.
3. **Every coverage fact comes from Moss and is cited to its source** — never from model memory.
4. **Moss is the hero: fire many precise lookups per turn, concurrently** (~40 in <100ms).
   Do NOT precompute comparisons or swap in a slow vector DB — that defeats the entire thesis.
5. **Synthetic personas + public plan docs only. No real PHI.**
6. **Ship the P0 MVP before anything else.** Use the descope ladder in Build.md; don't gold-plate.

## Core loop (per user turn)
STT (LiveKit) → `extract_constraints` (LLM → structured) → **parallel Moss retrieval**
(each plan × each drug/provider/dimension, `asyncio.gather`) → **deterministic cost math**
(plain code; uncovered-drug costs are NOT capped by OOP-max — that's the trap) → cited,
plain-language **decision-support** reply (clinical Q → handoff) → TTS (MiniMax/Qwen, user's
language) → stream lookups + latency + comparison table to the frontend panel.

## Stack — build ON the starter, don't reinvent
Base repo: `github.com/livekit-examples/moss-hacker-starter`.
LiveKit (voice) · **Moss** (in-process retrieval, the hero) · Unsiloed (parse plan PDFs →
structured + citable) · MiniMax/Qwen (multilingual TTS) · TrueFoundry (gateway, optional) ·
AWS (deploy, optional).

## Moss data model
Index at the FACT level — one doc per (plan, fact): benefit fields; formulary entries
`{plan, type:'drug', tier, cost, covered, source}`; network entries
`{plan, type:'provider', in_network, source}`. Query = hybrid (`alpha≈0.6`) + metadata
filter by `{plan, type}`.

## Where Moss is wired

| Where | File | What it does |
|---|---|---|
| **Credentials + preload** | `agent.py:108` + `on_enter` | `MossClient(project_id, project_key)` created once; both indexes preloaded on session start |
| **Query time** | `compare_plans_engine.py:57` | `_moss_query()` fires `moss.query(index, query, QueryOptions(top_k=1, alpha=0.6, filter=_plan_filter(plan_id)))` — 24 concurrent queries per Maria turn |
| **Index population** | `src/create_index.py` | **Track C's job** — loads plan docs into Moss; agent queries this at runtime |

### Metadata shape Track C must produce (one doc per plan × fact)
```
# Benefit
{"plan": "silver-2024", "type": "benefit", "field": "premium",     "value": "350",  "source": "Silver 2024 SBC p.1"}
{"plan": "silver-2024", "type": "benefit", "field": "oop_max",     "value": "6000", "source": "Silver 2024 SBC p.2"}
# Drug covered
{"plan": "silver-2024", "type": "drug", "covered": "true",  "coinsurance": "0.30", "fills_per_year": "12", "list_price_per_year": "50000", "source": "Silver 2024 formulary p.3"}
# Drug NOT covered
{"plan": "bronze-2024", "type": "drug", "covered": "false", "list_price_per_year": "84000", "source": "Bronze 2024 formulary"}
# Provider
{"plan": "silver-2024", "type": "provider", "in_network": "true",  "source": "Silver 2024 directory"}
```

### Fallback (no Track C data yet)
`compare_plans_engine.py` treats missing drug docs as uncovered at `$84k/year` — the Bronze trap fires even without real data, so a demo is possible before Track C finishes.

### Provider resolution must fail SAFE (fixed Jun 7 2026)
Provider lookups use `top_k=1`, which always returns the *nearest* doc even when a plan
has **no** entry for the queried provider. The old code read that wrong doc's `in_network`
flag (defaulting to `"true"` when absent), so an absent provider could be silently scored
**in-network → $0**, hiding a real network trap (this is the "hallucinated cost = project-ending"
rule). Symptom seen live: Stanford flagged out-of-network on CCHP/Trio but **not** Kaiser,
despite none of the three having a Stanford record.
**Fix:** `_provider_matches()` verifies the matched doc is `type=provider` AND its
`provider_name` actually corresponds to the queried provider. On no match the provider is
treated as **out-of-network at `_DEFAULT_OON_COST` ($25k)** — mirroring the uncovered-drug
fallback. Regression tests in `tests/test_compare_plans.py`
(`test_provider_absent_falls_back_to_out_of_network`, `_non_provider_doc_falls_back`,
`_match_uses_real_doc`, `test_provider_matches_keyword_containment`).
## Code practices
- Match the starter's structure/conventions; reuse its tools and panel — don't rebuild.
- Small, single-purpose, typed functions; clear names.
- Determinism for all math; retrieval + citation for all facts; never fabricate plan data.
- Voice is the critical path: keep retrieval concurrent; add timeouts + graceful fallback.
- Golden tests: assert each persona's computed cost, ranking, and trap-flag match hand-verified values.
- Commit in small working increments; add no deps/features outside the current P-scope.

## Definition of done (P0)
Voice in → Maria's messy ask → 4-plan personalized comparison in <~1.5s, the cheap-plan
trap exposed, panel showing ~40 lookups at <100ms. Then layer: citations → clinical-handoff
guardrail → curveball → multilingual.

## Track A progress
- [x] Step 1: Agent instructions rewritten to Amparo insurance navigator + safety guardrail (other session)
- [x] Step 2: `extract_constraints` @function_tool + `Constraints` dataclass + 11 tests passing
- [x] Step 3: Deterministic cost math (`src/cost_math.py`) + 17 golden tests passing
  - `PlanData`, `DrugCoverage`, `ProviderCoverage`, `CostResult` typed structs
  - `compute_annual_cost(plan, drugs, providers)` — formula: `premium*12 + min(covered_oop, oop_max) + uncovered_costs`
  - `rank_plans(results)` — sort by annual_total cheapest first
  - Key invariant: uncovered drug costs are NOT capped by OOP-max (the trap)
  - Golden test values for Maria's 4-plan scenario: Silver $8,200 < Gold $9,000 < Platinum $10,200 < Bronze $51,800 (trap)
- [x] Step 4: `compare_plans` — parallel Moss retrieval + cost math + trap flag
  - `compare_plans_engine.py`: `_fetch_plan_data()` fires 6 Moss queries/plan concurrently, `run_comparison()` fires all 4 plans in parallel (24 total queries)
  - `compare_plans` @function_tool wired into agent, gracefully errors if `extract_constraints` not called first
  - 18 tests passing (query count, plan filter, trap flag, serialization, tool behavior)
- [x] Step 5: Clinical-handoff guardrail — deterministic regex classifier + `on_user_turn_completed` hook + 28 tests passing
  - `src/guardrail.py`: `is_clinical_question(text)` — no LLM, instant; `_COVERAGE_EXEMPTIONS` regex exempts coverage-framed questions
  - `CLINICAL_HANDOFF` constant: "That's a question for your doctor or pharmacist. I can tell you what your plan covers, but medical advice isn't something I can give."
  - `agent.py`: `on_user_turn_completed` injects system-level guardrail instruction when clinical question detected, before LLM sees the message
  - Integration evals (test_agent.py) skip cleanly without real credentials; run automatically with `.env.local`

## Track A — ALL 5 STEPS COMPLETE ✓

## Moss Panel — plan_comparison message — DONE (Jun 7 2026)
- `_publish_plan_comparison(payload)` added to `agent.py` — fires after every `compare_plans` call
- Message shape (`type: "plan_comparison"`):
  - `data.plans`: ranked CostResult list (cheapest first, all fields)
  - `data.lookup_count`: total Moss queries fired this turn
  - `data.trap`: bool — True if any plan has uncovered specialty drug costs
  - `data.trap_plan_id`: plan_id of cheapest trap plan, or null
  - `data.timestamp`: epoch seconds
- Frontend consumes this to populate the live comparison table
- 85 tests passing, 3 skipped

## Curveball Re-grounding — DONE (Jun 7 2026)
- `Constraints.merge(new)` added to `constraints.py` — unions lists, latches scalars
  - Lists (drugs, providers, events): unioned, case-insensitive dedup — nothing dropped
  - `family_size`: updated only if new > 1 (1 = LLM default for "not mentioned this turn")
  - `hsa_interest`: latches True — once mentioned, always remembered
  - `budget`: updated only if new is not None
  - `language`: always takes latest (reflects current turn)
- `extract_constraints` now merges into `self._constraints` instead of replacing it
- Docstring updated: "only pass what the user mentioned THIS turn — prior items kept automatically"
- 13 new merge tests added to `test_extract_constraints.py` — 85 total, 3 skipped
- **Live verified**: "I take Humira at UCSF" → "what about Stanford?" → Humira + UCSF + Stanford all present in `compare_plans` (28 lookups, trap=True)

## Multilingual TTS — DONE (Jun 7 2026)
- TTS is **MiniMax `speech-02-turbo`** (40+ languages, auto code-switching) — hackathon sponsor tool
- Plugin: `livekit-plugins-minimax==1.3.0` installed with `--no-deps` (pins to agents==1.2.9 but is compatible with 1.5.16 at runtime)
- Credentials: `MINIMAX_API_KEY` + `MINIMAX_GROUP_ID` in `agent-py/.env.local` ($30 hackathon voucher applied)
- **API endpoint**: `https://api.minimax.io/v1/t2a_v2` (NOT `api.minimax.chat` — wrong endpoint for this account)
- **Local adapter**: `src/minimax_tts.py` — subclasses upstream plugin with two fixes:
  1. Single `start_segment()`/`end_segment()` per utterance (agents 1.5.x requirement)
  2. Proper SSE line buffering (`iter_any()` + byte buffer) so split chunks parse correctly
  3. Overrides `base_url` to `api.minimax.io`
- Import: `from minimax_tts import TTS as MinimaxTTS` → `tts=MinimaxTTS()` in `agent.py`
- ~~ElevenLabs was incorrectly substituted by a prior session~~ — reverted; MiniMax is correct
- Added language instruction to agent: "Always respond in the same language the user speaks"
- STT already runs `language="multi"` (Deepgram nova-3) — no STT change needed
- No dynamic model switching required: LLM outputs Spanish → MiniMax speaks Spanish automatically
- **Smoke tested (Jun 7 2026)**: voice heard, STT transcribing, MiniMax streaming sentence by sentence, no errors

## Track C — COMPLETE (Jun 7 2026, updated with real plans Jun 7 2026)
- 4 **real** CA ACA plan JSONs: `data/plans/{cchp,trio,kaiser,ppo}_2024.json`
  - **CCHP Balance Bronze 60 HMO** (`cchp-2024`) — $989.76/mo, UCSF excluded ← CHEAP PLAN TRAP
  - **Blue Shield Silver Trio HMO** (`trio-2024`) — $1,163.34/mo, UCSF excluded (narrow Trio network)
  - **Kaiser Permanente Gold 80 HMO** (`kaiser-2024`) — $1,392.09/mo, UCSF excluded (closed system, 5-star)
  - **Blue Shield HDHP PPO** (`ppo-2024`) — $1,472.88/mo, UCSF in-network ← TRUE WINNER
- **The real trap**: network exclusion, NOT drug coverage — all 4 plans cover Humira (~$250-500/fill). 3 of 4 exclude UCSF. $25k uncovered UCSF delivery cost bypasses OOP max.
- Maria persona: `data/personas/maria.json` (coverage_tier: individual)
- Index builder: `scripts/create_index.py` — run from `agent-py/` dir: `uv run python ../scripts/create_index.py`
- Moss `knowledge` index seeded: **37 docs** (4 plans × 9-10 facts each)
- `out_of_network_cost` now flows from plan JSON → Moss metadata → cost math (was hardcoded "0")
- Moss `memory` index: 1 seed doc (per-user memory store)
- 27 golden tests passing: `cd agent-py && uv run pytest ../tests/test_golden.py -v`
- Plan ID mapping: `cchp_2024→cchp-2024`, `trio_2024→trio-2024`, `kaiser_2024→kaiser-2024`, `ppo_2024→ppo-2024`

## Full P0 Demo — END-TO-END VERIFIED (Jun 7 2026)
Ran `uv run python src/agent.py console` with real LiveKit + Moss + MiniMax credentials.
All three P0 test cases passed with real Moss data (not fallback).

**Maria's demo ask with REAL plan data** (expected, not re-verified after real plan swap):
- `extract_constraints` → `drugs=['Humira'], providers=['UCSF'], events=['pregnancy']`
- `compare_plans` → parallel queries, `trap=True`
- Expected ranking: PPO $23,675 < Trio $44,960 < CCHP $45,877 < Kaiser $47,705
- Agent exposes UCSF OON trap: $25k uncovered delivery NOT capped by OOP max
- CCHP (cheapest premium $990/mo) costs $22k MORE/yr than PPO for Maria

**Curveball — "What about Stanford?"** (28 Moss lookups):
- Merged constraints: `providers=['UCSF', 'Stanford']`, Humira preserved — nothing dropped

**Clinical guardrail — "What's the right dose of Humira?"**:
- Exact handoff line fired instantly (regex, no LLM): "That's a question for your doctor or pharmacist..."

## Phone number — DONE (Jun 7 2026)
- **Number:** `+1 (415) 417-6002` — purchased via `lk number purchase`
- **Dispatch rule:** the catch-all (`SipTrunks: <any>`, Type `Direct`) → room `amparo-demo`, **no agent field** (the rule ID rotates; check `lk sip dispatch list`). The agent joins via **automatic dispatch**, see SIP Dispatch section.
- Any call to the number routes to room `amparo-demo`; the auto-dispatched worker is already present and answers
- Live-tested: full call pipeline worked end-to-end (STT → extract_constraints → compare_plans → MiniMax TTS)
- **Browser panel** joins room `amparo-demo` as a subscriber-only observer to display `plan_comparison` data — panel may be opened before or after the call (automatic dispatch tolerates either order)

### LiveKit dispatch rule gotchas (hard-won)
- **Catch-all rules (`SipTrunks: <any>`) are the only thing that works for LiveKit hosted numbers.** They cannot be "assigned" to a number via the API (that API call errors), but they route correctly regardless.
- **Dashboard-created rules** (with `SipTrunks: PN_*`) do NOT route correctly — the SIP engine doesn't match the phone number ID as a trunk.
- **Stale room** (was a problem under explicit dispatch): no longer blocks calls — automatic dispatch puts the agent in `amparo-demo` regardless of who created it. Just start the worker BEFORE the room is created (auto-dispatch fires on room *creation*); if the worker started after the room already existed, restart it or `lk room delete amparo-demo` once.
- **`ctx.connect()` MUST come before `AgentSession()` and `session.start()`** — reversed order silently prevents SIP calls from being answered. The agent registers but never joins the room.

## Agent tuning — DONE (Jun 7 2026)
- Noise cancellation: `QUAIL_VF_S` (reverted back to original — better quality for demo; ~540 MB memory warning is cosmetic)
- Turn handling migrated off deprecated params: `turn_detection=` + `preemptive_generation=` → `turn_handling={"turn_detection": MultilingualModel(), "preemptive_generation": {"enabled": True}}`

## Track B — Frontend Panel — DONE (Jun 7 2026)
- Next.js app at `frontend/` — `pnpm dev` serves on `localhost:3000`
- `frontend/.env.local` is a symlink to `agent-py/.env.local` — same credentials, no duplication
- **`frontend/app/api/token/route.ts`**: generates subscriber-only LiveKit JWT (canSubscribe, canPublish=false, canPublishData=false) for room `amparo-demo`
- **`frontend/hooks/usePlanComparison.ts`**: connects to LiveKit room, listens for `RoomEvent.DataReceived`, parses `{type: "plan_comparison"}` messages
- **`frontend/components/PlanComparisonPanel.tsx`**: dark panel with green status dot, Moss lookup counters, trap warning banner, ranked plan cards (annual cost breakdown, uncovered drugs/providers, sources), `CitationChip` for real PDF links
- Plan ID → label mapping (real plans): `cchp-2024→CCHP Bronze HMO`, `trio-2024→Blue Shield Trio HMO`, `kaiser-2024→Kaiser Gold HMO`, `ppo-2024→Blue Shield HDHP PPO`
- **Live verified (Jun 7 2026)**: panel updates in real-time during phone calls, lookup counter increments, sources from Moss shown, out-of-network providers highlighted in yellow
- **Citation chips** render under each plan card linking to real Covered CA PDFs served from `frontend/public/pdfs/`

## Unsiloed Citations — DONE (Jun 7 2026)
- **What it does**: every benefit fact the agent states is linked to its exact location in the real Covered California PDF — page number + normalized bbox coordinates. Judges click a chip and see the actual "$989.76/month" row in the real insurer document.
- **Why it matters**: closes the loop on the Moss thesis — retrieval quality *demonstrated*, not just asserted. Insurance is a trust-deficit domain; bbox citations from real documents are the hard moat.
- **Real PDFs** (from Covered California 2024) stored in `data/pdfs/` and `frontend/public/pdfs/`

### Files
| File | What it does |
|---|---|
| `data/pdfs/{plan_id}.pdf` | Real Covered California "Health Plan Details" PDFs (10 pages each, ~100-400KB) |
| `scripts/parse_with_unsiloed.py` | Submits each real PDF to Unsiloed, searches ALL pages for keywords (not fixed pages), maps segments → fact keys, normalizes bbox to 0–1. Output: `data/citations/{plan_id}_citations.json` |
| `scripts/create_index.py` | Loads citation JSON and injects `pdf_url`, `bbox_page`, `bbox_left/top/width/height` into each Moss doc's metadata. Also reads `out_of_network_cost` from plan JSON (was hardcoded "0") |
| `src/cost_math.py` | `Citation` dataclass; `DrugCoverage` + `ProviderCoverage` carry `citation: Citation | None`; `CostResult` carries `citations: list[Citation]` |
| `src/compare_plans_engine.py` | `_citation_from_meta()` extracts bbox fields from Moss metadata at query time |
| `frontend/hooks/usePlanComparison.ts` | `Citation` interface and `citations: Citation[]` on `CostResult` |
| `frontend/components/PlanComparisonPanel.tsx` | `CitationChip` — blue chip, opens PDF at `#page=N`; trap banner text updated for network trap |

### Citation coverage (real PDFs)
Covered CA plan summary documents contain benefit facts but NOT full formulary/network data:
- **Found**: premium (page 1-2), deductible (page 2), OOP max (page 2), HSA eligible (page 2) — 3-4 per plan
- **Not found**: Humira, UCSF — these require full formulary + network PDFs (not included in plan summary docs)
- Citations are injected on benefit docs only; drug/provider Moss docs have no bbox (still work, just no chip)

### Unsiloed API
- Endpoint: `POST https://prod.visionapi.unsiloed.ai/parse`
- Auth: `api-key: $UNSILOED_API_KEY` header (key in `agent-py/.env.local`)
- Async: submit → poll `GET /parse/{job_id}` until `status == "Succeeded"` (~90s per PDF)
- bbox format: `{left, top, width, height}` in pixels; normalize by `page_width` / `page_height`
- Script searches ALL pages per keyword (real PDFs vary in page layout unlike synthetic ones)

### To re-run the full pipeline
```
cd agent-py
# Real PDFs are already in data/pdfs/ — no need to generate synthetic ones
uv run python ../scripts/parse_with_unsiloed.py  # re-parse with Unsiloed (~6 min for 4 PDFs)
uv run python ../scripts/create_index.py          # re-seed Moss with bbox metadata
```

### Demo moment
Agent says "CCHP Bronze looks cheapest at $990/month — but UCSF is out-of-network, adding $25,000 that's NOT capped by your OOP maximum" → panel shows `⚠ TRAP` + blue chip `CCHP Balance Bronze 60 HMO SBC 2024` → judge clicks → real Covered California PDF opens at page showing premium and cost table.

## Team assignment
- **Track A (core engine)** — handled by Samrat: `extract_constraints`, `compare_plans`, cost math, guardrail
- **Track B (frontend panel)** — DONE: Next.js subscriber panel at `frontend/`
- **Track C (data)** — handled by teammate: 4 plan JSONs, Maria's persona, Moss index builder (`create_index.py`)

## Environment setup (already done)
- LiveKit CLI installed (`brew install livekit-cli`) and authenticated to project **amparo-ai**
- Credentials written to `agent-py/.env.local` via `lk app env -w`
- LiveKit Docs MCP server connected at `https://docs.livekit.io/mcp/` (project `.mcp.json`)
- To re-auth or refresh credentials: `lk cloud auth` then `lk app env -w` from `agent-py/`

## Commands
`pnpm setup` · `lk app env -w` · build the Moss index · `pnpm dev`  (confirm against starter README).
- Agent dev loop: `cd agent-py && uv run python src/agent.py download-files` (first run only), then `uv run python src/agent.py console` (local terminal test) or `uv run python src/agent.py dev` (with frontend).

## SIP Dispatch — Automatic Dispatch (updated Jun 7 2026)

### Current model: automatic dispatch — NO watch script, NO agent_name
`agent.py` registers the entrypoint as `@server.rtc_session()` with **no `agent_name`**.
This is **automatic dispatch**: the worker joins every new room the instant it's created.
So whether the **SIP call** or the **browser panel** creates `amparo-demo` first, the agent
is already there. The entrypoint then *waits for the actual caller* (ignoring the
`panel-observer-*` participant) before greeting, so the caller hears audio instantly.

**Why automatic dispatch and not explicit:** explicit dispatch (`agent_name` set + a SIP rule
or watch script) only fires an agent job on **room creation**. The browser panel pre-creating
`amparo-demo` therefore meant a later call joined the existing room and **never dispatched an
agent → silent call, no logs**. Automatic dispatch is immune to that ordering entirely.

**Demo setup (current):**
1. SIP rule routes calls to `amparo-demo` (direct, no agent field) — already exists:
   ```bash
   lk sip dispatch create --direct amparo-demo
   ```
2. Run ONE agent worker: `cd agent-py && uv run python src/agent.py dev` — confirm `registered worker`.
3. Call the number. Open the browser panel whenever — order no longer matters.

**`scripts/watch_and_dispatch.sh` is DEPRECATED** — not needed with automatic dispatch.
Do NOT run it; combining it with the worker double-dispatches and two agents join the room.

### Correction to a prior note: `roomConfig.agents` IS settable
The old "`agentDispatches` field is not settable" note was from an older CLI (v1.x). On
**`lk` v2.16.4** a SIP rule can carry the agent via `roomConfig.agents`
(`{"rule": {...}, "roomConfig": {"agents": [{"agentName": "agent-py"}]}}` to
`lk sip dispatch create`). We chose automatic dispatch over this anyway, because
`roomConfig.agents` still only dispatches on **room creation** — it shares the panel-pre-creates-room
footgun. Automatic dispatch does not.

### No-logs + no-audio despite panel updating
If the panel updates (Moss queries fire) but the agent terminal shows no logs and the caller hears silence:
- **Root cause**: another agent process is handling the call (background process from a prior session, or teammate's agent)
- **Fix**: `pkill -f "agent.py"` → restart clean → confirm single `registered worker` log

### No audio (TTS silent) despite agent logs appearing
- Check MiniMax balance at `platform.minimax.io` (balance must be > 0 in Voucher)
- MiniMax adapter is in `src/minimax_tts.py` — overrides `base_url` to `api.minimax.io` (not `api.minimax.chat`)
- If MiniMax fails, switch TTS in `agent.py` to `inference.TTS()` (OpenAI TTS via LiveKit Inference) as a fallback

### Stale room (no longer blocks dispatch under automatic dispatch)
With automatic dispatch the agent joins every new room, so a pre-existing `amparo-demo`
no longer blocks the agent from answering. `agent.py` still auto-deletes the room after the
**caller** leaves (`participant_disconnected` → `lkapi...room.delete_room()`), now keyed on
`_is_caller()` so it fires even while the browser panel observer is still connected.
