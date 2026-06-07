"""MiniMax TTS adapter compatible with livekit-agents 1.5.x.

livekit-plugins-minimax==1.3.0 targets agents==1.2.9 and calls
start_segment()/end_segment() once per sentence. Agents 1.5.x enforces
exactly one start_segment()/end_segment() pair per _run() call — a second
start_segment() before end_segment() raises RuntimeError.

This adapter opens the segment once, streams all sentences through it,
then closes it — preserving the MiniMax API call structure unchanged.
"""

from __future__ import annotations

import json
import time

import aiohttp
from livekit.agents import tts, utils
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions
from livekit.plugins.minimax.log import logger
from livekit.plugins.minimax.tts import TTS as _UpstreamTTS, TTSOptions
from osc_data.text_stream import TextStreamSentencizer


class _SynthesizeStream(tts.SynthesizeStream):
    def __init__(
        self,
        *,
        tts: _UpstreamTTS,
        opts: TTSOptions,
        session: aiohttp.ClientSession,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> None:
        super().__init__(tts=tts, conn_options=conn_options)
        self._opts = opts
        self._session = session
        # platform.minimax.io accounts use api.minimax.io, not api.minimax.chat
        self._opts.base_url = "https://api.minimax.io/v1/t2a_v2"

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        output_emitter.initialize(
            request_id=utils.shortuuid(),
            sample_rate=self._opts.sample_rate,
            mime_type="audio/pcm",
            stream=True,
            num_channels=1,
        )
        # One segment for the entire utterance — required by agents 1.5.x.
        output_emitter.start_segment(segment_id=utils.shortuuid())

        splitter = TextStreamSentencizer()
        first_sentence_spent: float | None = None
        start_time = time.perf_counter()

        async for token in self._input_ch:
            if isinstance(token, self._FlushSentinel):
                sentences = splitter.flush()
            else:
                sentences = splitter.push(text=token)

            for sentence in sentences:
                if not sentence.strip():
                    continue

                if first_sentence_spent is None:
                    first_sentence_spent = time.perf_counter() - start_time
                    logger.info(
                        "llm first sentence",
                        extra={"spent": str(first_sentence_spent)},
                    )

                logger.info("tts start", extra={"sentence": sentence})
                async with self._session.post(
                    self._opts.get_http_url(),
                    json=self._opts.get_query_params(text=sentence),
                    timeout=aiohttp.ClientTimeout(
                        total=300,
                        sock_connect=self._conn_options.timeout,
                    ),
                    headers=self._opts.get_http_header(),
                ) as resp:
                    resp.raise_for_status()
                    # SSE stream: buffer raw bytes into complete lines so we
                    # never try to json.loads() a mid-chunk split.
                    buf = b""
                    async for raw in resp.content.iter_any():
                        buf += raw
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            line = line.strip()
                            if not line.startswith(b"data:"):
                                continue
                            try:
                                parsed = json.loads(line[5:])
                            except json.JSONDecodeError:
                                continue
                            if "data" in parsed and "extra_info" not in parsed:
                                audio_hex = parsed["data"].get("audio", "")
                                if audio_hex:
                                    output_emitter.push(bytes.fromhex(audio_hex))
                logger.info("tts end")

        output_emitter.end_segment()


class TTS(_UpstreamTTS):
    """MiniMax TTS with agents 1.5.x-compatible segment lifecycle."""

    def stream(
        self, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> _SynthesizeStream:
        return _SynthesizeStream(
            tts=self,
            conn_options=conn_options,
            opts=self._opts,
            session=self._ensure_session(),
        )
