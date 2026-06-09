"""Generate the promo-video voiceover with MiniMax TTS (speech-02-hd).

Produces ONE MP3 per beat (video/public/vo/vo-1.mp3 ...) so each line can be
placed at its exact scene start in Remotion — this is what keeps audio, visuals,
and captions in sync.

Uses the agent's MiniMax credentials (agent-py/.env.local). Run from agent-py so
python-dotenv is available:
    cd agent-py && uv run python ../scripts/generate_voiceover.py

Tweak voice/pace via env:
    MINIMAX_VOICE_ID (default Friendly_Person), MINIMAX_TTS_SPEED (default 0.96)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "agent-py" / ".env.local")

API_KEY = os.environ.get("MINIMAX_API_KEY")
GROUP_ID = os.environ.get("MINIMAX_GROUP_ID")
VOICE_ID = os.environ.get("MINIMAX_VOICE_ID", "Friendly_Person")
MODEL = os.environ.get("MINIMAX_TTS_MODEL", "speech-02-hd")
SPEED = float(os.environ.get("MINIMAX_TTS_SPEED", "0.96"))

# One line per beat. Keep them short — they double as the on-screen captions.
# id is referenced from video/src/beats.ts.
SEGMENTS = [
    (1, "The cheapest health plan is often the most expensive."),
    (2, "But nobody reads eighty pages of fine print."),
    (3, "Meet Amparo. Just ask, out loud, in any language."),
    (4, "It fires around forty live lookups in milliseconds, and computes your real cost."),
    (5, "The lowest premium? Actually twenty-two thousand dollars more a year, because your hospital is out of network."),
    (6, "Every number computed in code. Every fact cited to the real plan document."),
    (7, "And it speaks your language. Forty and counting."),
    (8, "Amparo AI. Coverage clarity, in your language."),
]


def synth(text: str) -> bytes:
    url = f"https://api.minimax.io/v1/t2a_v2?GroupId={GROUP_ID}"
    payload = {
        "model": MODEL,
        "text": text,
        "stream": False,
        "language_boost": "English",
        "voice_setting": {"voice_id": VOICE_ID, "speed": SPEED, "vol": 1.0, "pitch": 0},
        "audio_setting": {"sample_rate": 44100, "bitrate": 128000, "format": "mp3", "channel": 1},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read())
    base = body.get("base_resp", {})
    if base.get("status_code") not in (0, None):
        raise RuntimeError(f"MiniMax error: {json.dumps(base)}")
    audio_hex = body.get("data", {}).get("audio")
    if not audio_hex:
        raise RuntimeError(f"No audio in response: {json.dumps(body)[:600]}")
    return bytes.fromhex(audio_hex)


def main() -> int:
    if not API_KEY or not GROUP_ID:
        print("Missing MINIMAX_API_KEY / MINIMAX_GROUP_ID in agent-py/.env.local")
        return 1

    out_dir = ROOT / "video" / "public" / "vo"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating {len(SEGMENTS)} beats · model={MODEL} voice={VOICE_ID} speed={SPEED}")
    for seg_id, text in SEGMENTS:
        audio = synth(text)
        out = out_dir / f"vo-{seg_id}.mp3"
        out.write_bytes(audio)
        print(f"  ✓ vo-{seg_id}.mp3 ({len(audio) / 1024:.0f} KB) — {text[:48]}...")
    print("Done. Next: measure durations and wire beats.ts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
