# Amparo AI

A multilingual **voice agent** that helps employees understand their health insurance — instant, personalized, cited comparison of their plans (coverage + real cost) plus year-round coverage Q&A.

Hackathon project — Moss @ YC.

---

## What it does

Maria says: *"I'm pregnant, on Humira, and my OB is at UCSF. Which plan should I pick?"*

Amparo fires 24 parallel Moss lookups across 4 plans in ~460ms, computes the true annual cost for each (premiums + OOP + uncovered drugs), ranks them cheapest-first, and exposes the Bronze trap: a $200/month plan that looks cheap but costs $51,800/year when Humira isn't covered.

All in one voice turn. Cited. In the user's language.

---

## Architecture

```
STT (Deepgram nova-3, multi-language)
  → extract_constraints (LLM → typed Constraints)
  → parallel Moss retrieval (24 queries, asyncio.gather, ~460ms)
  → deterministic cost math (plain Python, no LLM)
  → cited plain-language reply
  → TTS (MiniMax speech-02-turbo, 40+ languages)
  → frontend panel (plan_comparison + moss_context events)
```

**Key invariant:** uncovered drug costs are NOT capped by the OOP-max. This is the trap a low-premium plan sets when a specialty drug like Humira is off-formulary.

---

## Stack

| Layer | Tool |
|---|---|
| Voice infra | LiveKit Agents 1.5.x |
| Retrieval | Moss (in-process, hybrid search) |
| STT | Deepgram nova-3 (`language="multi"`) |
| TTS | MiniMax `speech-02-turbo` (40+ languages, auto code-switching) |
| LLM | OpenAI GPT (via LiveKit Inference) |
| Plan data | Unsiloed → structured + citable JSON |

---

## Golden rules

1. **Coverage navigator, not a clinical advisor.** Any clinical question → "your doctor or pharmacist."
2. **Numbers are computed in deterministic code, never by the LLM.** A hallucinated cost is a project-ending bug.
3. **Every fact comes from Moss and is cited to its source** — never from model memory.
4. **Moss is the hero:** fire many precise lookups per turn, concurrently.

---

## Setup

### Prerequisites

- [LiveKit CLI](https://docs.livekit.io/home/cli/cli-setup/) — `brew install livekit-cli`
- Python 3.12+ with [uv](https://github.com/astral-sh/uv)
- Moss project credentials
- MiniMax API key + Group ID

### Agent

```bash
cd agent-py

# First run only — downloads model files
uv run python src/agent.py download-files

# Local terminal test (no browser needed)
uv run python src/agent.py console

# With frontend
uv run python src/agent.py dev
```

### Credentials

Copy credentials to `agent-py/.env.local` (gitignored):

```
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
MOSS_PROJECT_ID=...
MOSS_PROJECT_KEY=...
MINIMAX_API_KEY=...
MINIMAX_GROUP_ID=...
```

Or refresh from LiveKit Cloud: `lk cloud auth && lk app env -w` from `agent-py/`.

### Seed the Moss index

```bash
cd agent-py
uv run python src/create_index.py
```

### Tests

```bash
cd agent-py
uv run pytest
```
