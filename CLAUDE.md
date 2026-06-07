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

## Commands
`pnpm setup` · `lk app env` · build the Moss index · `pnpm dev`  (confirm against starter README).
