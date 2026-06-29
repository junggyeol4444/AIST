"""Phase 1 tests — personas, prompt building, context window, mock engine.

All offline: no Ollama server and no aiohttp required.
Run with `pytest -q` or via `python tests/run_checks.py`.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import yaml

from chat.persona_loader import PersonaPool, load_viewer_personas
from llm import prompt_builder
from llm.context_manager import ConversationContext
from llm.engine import LLMEngine, MockBackend

ROOT = Path(__file__).resolve().parent.parent


def test_viewer_personas_load_and_validate():
    personas = load_viewer_personas()
    assert len(personas) >= 10
    nicks = [p["nickname"] for p in personas]
    assert len(nicks) == len(set(nicks)), "viewer nicknames must be unique"


def test_streamer_persona_has_required_fields():
    persona = yaml.safe_load((ROOT / "config" / "streamer_persona.yaml").read_text("utf-8"))
    for field in ("name", "speech_style", "ai_question_response"):
        assert persona.get(field), f"streamer persona missing {field}"
    assert persona["ai_question_response"] in {"humor_deflect", "admit", "deny"}


def test_streamer_prompt_mentions_name_and_repetition_block():
    persona = {"name": "별밤", "speech_style": ["밝음"], "ai_question_response": "admit"}
    prompt = prompt_builder.build_streamer_system_prompt(persona, ["가보자고"])
    assert "별밤" in prompt
    assert "반복" in prompt  # repetition-avoidance section present
    assert "AI" in prompt    # D3 guidance present


def test_viewer_prompt_distinguishes_personas():
    personas = load_viewer_personas()
    p_a, p_b = personas[0], personas[1]
    prompt_a = prompt_builder.build_viewer_system_prompt(p_a)
    prompt_b = prompt_builder.build_viewer_system_prompt(p_b)
    assert p_a["nickname"] in prompt_a
    assert p_b["nickname"] in prompt_b
    assert prompt_a != prompt_b


def test_context_sliding_window():
    ctx = ConversationContext(max_turns=4)
    for i in range(10):
        ctx.add_viewer_chat(f"v{i}", f"msg{i}")
    assert len(ctx) == 4
    assert ctx.summary, "older turns should fold into a summary"
    assert ctx.as_messages()[-1]["content"].endswith("msg9")


def test_persona_pool_cooldown_avoids_immediate_repeat():
    personas = load_viewer_personas()
    pool = PersonaPool(personas)
    prev = None
    for _ in range(20):
        cur = pool.sample(cooldown=1)["nickname"]
        assert cur != prev, "same persona twice in a row violates cooldown"
        prev = cur


def test_mock_engine_streamer_and_viewer():
    async def _run():
        engine = LLMEngine(MockBackend(), max_context_turns=10)
        persona = {"name": "별밤", "speech_style": ["밝음"], "ai_question_response": "humor_deflect"}
        reply = await engine.streamer_say(persona, trigger="안녕")
        assert reply and "별밤" in reply
        assert len(engine.context) >= 1  # streamer turn recorded
        viewer = load_viewer_personas()[0]
        chat = await engine.viewer_chat(viewer)
        assert chat
        return True

    assert asyncio.run(_run())
