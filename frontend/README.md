# Amparo AI — Frontend Panel

Next.js app that displays live plan comparison data during phone calls.

## What it does

- Connects to the LiveKit room `amparo-demo` as a **subscriber-only** observer (no audio publish)
- Polls `/api/room-status` every 3s before connecting — won't create a stale room
- Listens for `plan_comparison` data messages from the agent
- Renders ranked plan cards, Moss lookup counter, trap warning banner, and citation chips that link to real Covered California PDFs

## Setup

```bash
pnpm install

# Symlink credentials from agent-py (no duplication)
ln -sf ../agent-py/.env.local .env.local

pnpm dev
```

Open `http://localhost:3000`.

## Environment variables (via symlinked .env.local)

```
LIVEKIT_URL
LIVEKIT_API_KEY
LIVEKIT_API_SECRET
NEXT_PUBLIC_LIVEKIT_URL
```
