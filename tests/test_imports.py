"""Phase 0 smoke test: every package imports and settings.yaml parses.

Run with:  pytest -q
"""
import importlib
from pathlib import Path

import yaml

PACKAGES = [
    "core",
    "llm",
    "tts",
    "chat",
    "chat.collectors",
    "overlay",
    "game_context",
    "scripts",
]

ROOT = Path(__file__).resolve().parent.parent


def test_packages_importable():
    for pkg in PACKAGES:
        importlib.import_module(pkg)


def test_settings_yaml_parses():
    settings_path = ROOT / "config" / "settings.yaml"
    assert settings_path.exists(), "config/settings.yaml is missing"
    with settings_path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    assert isinstance(cfg, dict)
    for section in ("broadcast", "llm", "tts", "overlay", "fake_chat"):
        assert section in cfg, f"settings.yaml missing section: {section}"
