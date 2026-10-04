"""Print a SHA-256 of the woven single-file player for each pack given (default: the shipped packs).

A refactor of web/packaged.html that must not change behaviour is proven by this: run it before and after and
the lines must match byte for byte.   usage: uv run python scripts/weave_digest.py [pack ...]
"""
import hashlib
import sys
from pathlib import Path

from vefr import cli

root = Path(__file__).resolve().parents[1]
packs = [Path(p) for p in sys.argv[1:]] or [root / "worlds" / "sample-world", root / "worlds" / "lore"]
for pack in packs:
    first, second = cli.weave_html(pack), cli.weave_html(pack)
    assert first == second, f"{pack.name}: the weave is not deterministic"
    print(f"{pack.name} {hashlib.sha256(first.encode()).hexdigest()} {len(first)}")
