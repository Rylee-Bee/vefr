"""The storage helper keeps every saved key and value exactly as before (tighten-shapes K2). FROZEN CONTRACT.

One scripted play through the shared kit; the whole localStorage after it must equal
tests/fixtures/store_golden.json, captured on main BEFORE store() existed. Same keys, same encodings.
Regenerate only by hand and only on purpose: VEFR_WRITE_GOLDEN=1 writes the file.
"""

import json
import os
import shutil
from pathlib import Path

import pytest

import play_kit

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

GOLDEN = Path(__file__).parent / "fixtures" / "store_golden.json"
ROUTES = {
    "interact": {"steps": ["begin", "walk:down,down,right", "key:e", "wait:300", "menu:journal", "wait:100"], "read": []},
    "library": {"steps": ["begin", "walk:down,right", "key:e", "wait:300"], "read": []},
    "growth": {"steps": ["begin", "walk:right,right,down", "wait:300"], "read": []},
    "equip": {"steps": ["begin", "walk:down,down", "key:e", "wait:300"], "read": []},
}


def dump(tmp_path):
    out = {}
    for base, spec in ROUTES.items():
        d = tmp_path / base
        d.mkdir()
        html = play_kit.weave(play_kit.pack(d, base), d)
        res = play_kit.play(html, spec)
        assert res["errors"] == [], (base, res["errors"])
        out[base] = res["store"]
    return out


def test_every_saved_key_and_value_is_unchanged(tmp_path):
    got = dump(tmp_path)
    if os.environ.get("VEFR_WRITE_GOLDEN") == "1":
        GOLDEN.write_text(json.dumps(got, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    want = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert got == want


def test_the_routes_save_something_worth_comparing():
    want = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert sum(len(v) for v in want.values()) >= 8
