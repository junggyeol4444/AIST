"""Download viewer personas from nvidia/Nemotron-Personas-Korea and write
``config/viewer_personas.yaml``.

Usage:
    python scripts/load_personas.py --num 10 --seed 42

Requires ``datasets`` (pip install -r requirements.txt) and network access.
If you cannot run this, the repo already ships a curated placeholder set.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "config" / "viewer_personas.yaml"
CACHE_DIR = ROOT / "data" / "personas_cache"
DATASET = "nvidia/Nemotron-Personas-Korea"

# Demographic / hobby cues that suggest someone likely to watch game/talk streams.
STREAM_FRIENDLY_HOBBIES = (
    "게임", "롤", "피파", "발로란트", "유튜브", "트위치", "케이팝", "애니",
    "노래", "축구", "넷플릭스", "보드게임",
)

_PALETTE = [
    "#FF8FB1", "#7FB3FF", "#9EE37D", "#FFD36E", "#C9C9C9", "#FF6B6B",
    "#B39DDB", "#FFA45B", "#4DB6AC", "#F48FB1",
]


def _looks_stream_friendly(row: dict) -> bool:
    blob = " ".join(str(row.get(k, "")) for k in ("hobbies", "persona", "occupation"))
    return any(cue in blob for cue in STREAM_FRIENDLY_HOBBIES)


def _to_viewer_persona(row: dict, idx: int, rng: random.Random) -> dict:
    nick_seed = str(row.get("persona", ""))[:6] or "시청자"
    return {
        "nickname": f"{nick_seed}{rng.randint(10, 99)}",
        "age": row.get("age"),
        "sex": row.get("sex"),
        "occupation": row.get("occupation"),
        "hobbies": row.get("hobbies"),
        "persona": row.get("persona"),
        "tone": "자연스러운 반말",
        "emoji_frequency": rng.choice(["none", "low", "medium", "high"]),
        "avg_message_length": rng.choice(["short", "short", "medium", "long"]),
        "uses_kk": rng.random() < 0.7,
        "name_color": _PALETTE[idx % len(_PALETTE)],
        "weight": round(rng.uniform(0.7, 1.4), 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--num", type=int, default=10, help="number of personas")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--split", default="train")
    args = ap.parse_args()

    try:
        from datasets import load_dataset
    except ImportError:
        raise SystemExit(
            "`datasets` not installed. Run: pip install -r requirements.txt"
        )

    rng = random.Random(args.seed)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Loading {DATASET} (split={args.split}) ...")
    ds = load_dataset(DATASET, split=args.split, cache_dir=str(CACHE_DIR))

    friendly = [r for r in ds if _looks_stream_friendly(r)]
    pool = friendly or list(ds)
    rng.shuffle(pool)
    chosen = pool[: args.num]
    personas = [_to_viewer_persona(r, i, rng) for i, r in enumerate(chosen)]

    OUT_PATH.write_text(
        yaml.safe_dump({"personas": personas}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"Wrote {len(personas)} personas -> {OUT_PATH}")


if __name__ == "__main__":
    main()
