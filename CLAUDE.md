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

## Smoke test — PASSED (Jun 7 2026)
Ran `uv run python src/agent.py console` with real LiveKit + Moss credentials.
- STT transcribed voice input correctly
- `extract_constraints` fired → `drugs: ['Humira'], providers: ['UCSF OB']`
- `compare_plans` fired 24 parallel Moss queries in ~460ms
- Cost math ran and `trap=True` — Bronze trap detected and flagged
- Graceful fallback worked: Moss returned 503s (index not seeded yet) but no crash
- **Blocker:** `knowledge` Moss index does not exist yet — Track C must run `create_index.py` to seed it

## Team assignment
- **Track A (core engine)** — handled by Samrat: `extract_constraints`, `compare_plans`, cost math, guardrail
- **Track C (data)** — handed off to teammate: 4 plan JSONs, Maria's persona, Moss index builder (`create_index.py`)
- **Track B (frontend panel)** — TBD

## Environment setup (already done)
- LiveKit CLI installed (`brew install livekit-cli`) and authenticated to project **amparo-ai**
- Credentials written to `agent-py/.env.local` via `lk app env -w`
- LiveKit Docs MCP server connected at `https://docs.livekit.io/mcp/` (project `.mcp.json`)
- To re-auth or refresh credentials: `lk cloud auth` then `lk app env -w` from `agent-py/`

## Commands
`pnpm setup` · `lk app env -w` · build the Moss index · `pnpm dev`  (confirm against starter README).
- Agent dev loop: `cd agent-py && uv run python src/agent.py download-files` (first run only), then `uv run python src/agent.py console` (local terminal test) or `uv run python src/agent.py dev` (with frontend).
