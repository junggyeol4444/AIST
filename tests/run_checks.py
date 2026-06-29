"""Run all test_* functions in the tests package without requiring pytest.

Usage:  python tests/run_checks.py
"""
from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEST_MODULES = ["tests.test_imports", "tests.test_phase1"]


def main() -> int:
    failures = 0
    total = 0
    for mod_name in TEST_MODULES:
        mod = importlib.import_module(mod_name)
        for attr in sorted(dir(mod)):
            if not attr.startswith("test_"):
                continue
            fn = getattr(mod, attr)
            if not callable(fn):
                continue
            total += 1
            try:
                fn()
                print(f"PASS  {mod_name}.{attr}")
            except Exception:  # noqa: BLE001
                failures += 1
                print(f"FAIL  {mod_name}.{attr}")
                traceback.print_exc()
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
