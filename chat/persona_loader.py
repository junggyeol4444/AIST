"""Loading and sampling of viewer personas.

Production personas come from ``nvidia/Nemotron-Personas-Korea`` via
``scripts/load_personas.py`` (which writes ``config/viewer_personas.yaml``).
This module just loads that YAML and samples from it; it has no heavy deps so
it works offline with the curated personas shipped in the repo.
"""
from __future__ import annotations

import random
from pathlib import Path

import yaml

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "viewer_personas.yaml"

# Fields each viewer persona is expected to have (mirrors Nemotron columns
# plus chat-style metadata). Missing optional fields fall back to defaults.
REQUIRED_FIELDS = ("nickname", "persona", "tone")


def load_viewer_personas(path: str | Path | None = None) -> list[dict]:
    p = Path(path) if path else _DEFAULT_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"viewer personas not found at {p}. "
            "Run scripts/load_personas.py to generate it from Nemotron, "
            "or restore the curated config/viewer_personas.yaml."
        )
    with p.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    personas = data.get("personas", data if isinstance(data, list) else [])
    if not personas:
        raise ValueError(f"no personas found in {p}")
    for i, persona in enumerate(personas):
        missing = [f for f in REQUIRED_FIELDS if not persona.get(f)]
        if missing:
            raise ValueError(f"persona #{i} missing required fields: {missing}")
    return personas


class PersonaPool:
    """Weighted sampler with per-persona cooldown to avoid back-to-back chats."""

    def __init__(self, personas: list[dict], rng: random.Random | None = None) -> None:
        if not personas:
            raise ValueError("PersonaPool needs at least one persona")
        self.personas = personas
        self._rng = rng or random.Random()
        self._recent: list[str] = []  # nicknames recently used (cooldown order)

    def sample(self, cooldown: int = 1) -> dict:
        """Pick a persona, avoiding the last ``cooldown`` used when possible."""
        blocked = set(self._recent[-cooldown:]) if cooldown > 0 else set()
        candidates = [p for p in self.personas if p["nickname"] not in blocked]
        if not candidates:
            candidates = self.personas
        weights = [float(p.get("weight", 1.0)) for p in candidates]
        chosen = self._rng.choices(candidates, weights=weights, k=1)[0]
        self._recent.append(chosen["nickname"])
        self._recent = self._recent[-max(cooldown, 1) * 2:]
        return chosen
