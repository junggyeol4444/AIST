"""Phase 1 CLI: talk to the streamer persona, or sample fake-viewer chats.

Examples:
    # Chat with the streamer (mock backend, no model needed):
    python scripts/persona_chat.py --role streamer --backend mock

    # Same but against a real Ollama model:
    python scripts/persona_chat.py --role streamer --backend ollama

    # Print N sampled fake-viewer chat lines:
    python scripts/persona_chat.py --role viewer --backend mock --count 8
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import yaml

import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chat.persona_loader import PersonaPool, load_viewer_personas  # noqa: E402
from core.logger import get_logger  # noqa: E402
from llm.engine import LLMEngine, build_backend  # noqa: E402

log = get_logger("cli")


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


async def run_streamer(engine: LLMEngine, persona: dict) -> None:
    print(f"=== '{persona.get('name')}' 스트리머와 대화 (빈 줄 입력 시 자유발화, 'q' 종료) ===")
    while True:
        try:
            user = input("나> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user.lower() in {"q", "quit", "exit"}:
            break
        if user:
            engine.context.add_viewer_chat("나", user)
        reply = await engine.streamer_say(persona, trigger=user or None)
        print(f"{persona.get('name')}> {reply}")


async def run_viewer(pool: PersonaPool, engine: LLMEngine, count: int,
                     context: str) -> None:
    print(f"=== 가짜 시청자 채팅 {count}개 (context: {context or '없음'}) ===")
    for _ in range(count):
        persona = pool.sample(cooldown=2)
        line = await engine.viewer_chat(persona, stream_context=context)
        print(f"[{persona['nickname']}] {line}")


async def amain(args: argparse.Namespace) -> None:
    settings = _load_yaml(ROOT / "config" / "settings.yaml")
    backend = build_backend(settings, kind=args.backend)
    max_turns = settings.get("llm", {}).get("context", {}).get("sliding_window_turns", 20)
    engine = LLMEngine(backend, max_context_turns=max_turns)

    if args.role == "streamer":
        persona = _load_yaml(ROOT / "config" / "streamer_persona.yaml")
        await run_streamer(engine, persona)
    else:
        personas = load_viewer_personas()
        pool = PersonaPool(personas)
        await run_viewer(pool, engine, args.count, args.context)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--role", choices=["streamer", "viewer"], default="streamer")
    ap.add_argument("--backend", choices=["mock", "ollama"], default="mock")
    ap.add_argument("--count", type=int, default=8, help="viewer: number of chats")
    ap.add_argument("--context", default="", help="viewer: current stream situation")
    args = ap.parse_args()
    asyncio.run(amain(args))


if __name__ == "__main__":
    main()
