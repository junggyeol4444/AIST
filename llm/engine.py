"""Local LLM inference engine.

Two backends:
  * ``OllamaBackend`` — talks to a running Ollama server over HTTP (async via
    aiohttp, imported lazily so the module loads without it). This is the real
    path; point ``llm.model`` in settings.yaml at a pulled model.
  * ``MockBackend``  — no dependencies, no server. Returns a deterministic
    persona-flavoured reply so the whole pipeline (persona -> prompt -> reply)
    is testable offline.

The engine itself is backend-agnostic and exposes streamer/viewer helpers used
by the orchestrator and the Phase 1 CLI.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, Protocol

from core.logger import get_logger
from llm import prompt_builder
from llm.context_manager import ConversationContext

log = get_logger("llm.engine")


class LLMBackend(Protocol):
    async def chat(self, messages: list[dict], **opts) -> str: ...
    def chat_stream(self, messages: list[dict], **opts) -> AsyncIterator[str]: ...


class OllamaBackend:
    """HTTP client for an Ollama server (https://github.com/ollama/ollama)."""

    def __init__(self, model: str, host: str = "http://localhost:11434",
                 temperature: float = 0.8, repetition_penalty: float = 1.1,
                 max_tokens: int = 256) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.options = {
            "temperature": temperature,
            "repeat_penalty": repetition_penalty,
            "num_predict": max_tokens,
        }

    def _payload(self, messages: list[dict], stream: bool, opts: dict) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {**self.options, **opts},
        }

    async def chat(self, messages: list[dict], **opts) -> str:
        aiohttp = _require_aiohttp()
        url = f"{self.host}/api/chat"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=self._payload(messages, False, opts)) as r:
                r.raise_for_status()
                data = await r.json()
        return (data.get("message", {}) or {}).get("content", "").strip()

    async def chat_stream(self, messages: list[dict], **opts) -> AsyncIterator[str]:
        aiohttp = _require_aiohttp()
        url = f"{self.host}/api/chat"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=self._payload(messages, True, opts)) as r:
                r.raise_for_status()
                async for raw in r.content:
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    import json
                    chunk = json.loads(line)
                    token = (chunk.get("message", {}) or {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break


class MockBackend:
    """Dependency-free backend for offline testing.

    Produces a short deterministic reply derived from the system persona and the
    last user message, so persona wiring is observable without a real model.
    """

    async def chat(self, messages: list[dict], **opts) -> str:
        await asyncio.sleep(0)  # keep it a real coroutine / yield control
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        name = _extract_name(system)
        if last_user:
            return f"[mock:{name}] '{_clip(last_user)}' 에 대한 반응이야 (모의 응답)"
        return f"[mock:{name}] 음 오늘 뭐 하고 놀까 (모의 응답)"

    async def chat_stream(self, messages: list[dict], **opts) -> AsyncIterator[str]:
        text = await self.chat(messages, **opts)
        for tok in text.split(" "):
            await asyncio.sleep(0)
            yield tok + " "


class LLMEngine:
    """High-level wrapper: persona + context -> backend -> reply."""

    def __init__(self, backend: LLMBackend, max_context_turns: int = 20) -> None:
        self.backend = backend
        self.context = ConversationContext(max_turns=max_context_turns)

    async def streamer_say(self, persona: dict, trigger: str | None = None,
                           use_context: bool = True) -> str:
        recent = self.context.recent_streamer_utterances(5) if use_context else []
        system = prompt_builder.build_streamer_system_prompt(persona, recent)
        messages = [{"role": "system", "content": system}]
        if use_context:
            messages += self.context.as_messages()
        if trigger:
            messages.append({"role": "user", "content": trigger})
        reply = await self.backend.chat(messages)
        self.context.add_streamer_speech(persona.get("name", "스트리머"), reply)
        return reply

    async def viewer_chat(self, persona: dict, stream_context: str = "") -> str:
        system = prompt_builder.build_viewer_system_prompt(persona, stream_context)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "채팅 한 줄:"},
        ]
        return await self.backend.chat(messages)


def build_backend(settings: dict, kind: str = "ollama") -> LLMBackend:
    """Construct a backend from the ``llm`` section of settings.yaml."""
    if kind == "mock":
        return MockBackend()
    if kind == "ollama":
        cfg = settings.get("llm", {})
        model = cfg.get("model")
        if not model or model == "TODO":
            raise ValueError(
                "llm.model is not set in settings.yaml (pull a model with "
                "`ollama pull qwen2.5:14b-instruct-q4_K_M` and set it)."
            )
        return OllamaBackend(
            model=model,
            host=cfg.get("host", "http://localhost:11434"),
            temperature=cfg.get("temperature", 0.8),
            repetition_penalty=cfg.get("repetition_penalty", 1.1),
            max_tokens=cfg.get("max_tokens", 256),
        )
    raise ValueError(f"unknown backend kind: {kind}")


def _require_aiohttp():
    try:
        import aiohttp  # noqa: WPS433 (lazy import is intentional)
    except ImportError as exc:  # pragma: no cover - env dependent
        raise RuntimeError(
            "aiohttp is required for the Ollama backend. "
            "Install deps: pip install -r requirements.txt"
        ) from exc
    return aiohttp


def _extract_name(system_prompt: str) -> str:
    # best-effort pull of the persona name from the first prompt line
    for token in ("'", "‘", "’"):
        if token in system_prompt:
            parts = system_prompt.split(token)
            if len(parts) >= 2 and parts[1].strip():
                return parts[1].strip()
    return "persona"


def _clip(text: str, n: int = 20) -> str:
    text = text.strip()
    return text if len(text) <= n else text[:n] + "…"
