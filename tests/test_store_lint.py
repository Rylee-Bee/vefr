"""The storage helper's ban-lint (tighten-shapes K2). FROZEN CONTRACT.

web/player/parts/065-store.js defines `store`, the one place the player touches browser storage
(get, set, getJSON, setJSON; each a try/catch that never throws, so a sandboxed iframe or blocked
storage cannot break play). Every other part goes through it. This test turns that prose rule into a check:
no part names `localStorage` except 065-store.js and 230-engine-startover.js (whose `startoverKeys(storage)`
takes the storage as a parameter so a fake can be passed in tests).
"""

from pathlib import Path

PARTS = Path(__file__).resolve().parent.parent / "web" / "player" / "parts"
ALLOWED = {"065-store.js", "230-engine-startover.js"}


def test_the_store_part_exists_and_is_in_the_manifest():
    assert (PARTS / "065-store.js").exists()
    manifest = (PARTS.parent / "manifest.json").read_text(encoding="utf-8")
    assert "065-store.js" in manifest


def test_no_part_touches_localstorage_directly():
    offenders = [p.name for p in sorted(PARTS.glob("*.js")) if p.name not in ALLOWED
                 and "localStorage" in p.read_text(encoding="utf-8")]
    assert offenders == [], f"use store.get/set/getJSON/setJSON instead of localStorage in: {offenders}"
