"""Every picture in web/art/ has a credit, and stays small.

Rylee, 2026-10-02: we may distribute what we generate, and we attribute all of it. Art arrives
through `tools/art/import_art.py`, which writes game-size files and `web/art/MANIFEST.json`
(source, credit, size). This test is the gate: a picture dropped in without a credit fails.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "web" / "art"
IMAGES = {".webp", ".png", ".svg", ".jpg"}
IMPORTED = ("stickers", "delve", "themes", "surfaces")      # game-size derivatives
IMPORTED_CAP = 60_000                                       # bytes per imported file
GENERAL_CAP = 450_000                                       # banners, the hero, illustrations
IMPORTED_TOTAL_CAP = 9_000_000


def manifest():
    return json.loads((ART / "MANIFEST.json").read_text(encoding="utf-8"))["files"]


def pictures():
    return {p.relative_to(ART).as_posix(): p for p in ART.rglob("*")
            if p.is_file() and p.suffix.lower() in IMAGES}


def test_every_picture_has_a_manifest_entry_and_no_entry_is_stale():
    files, pics = manifest(), pictures()
    assert set(pics) - set(files) == set(), f"no credit recorded for: {sorted(set(pics) - set(files))[:8]}"
    assert set(files) - set(pics) == set(), f"manifest names missing files: {sorted(set(files) - set(pics))[:8]}"


def test_every_entry_has_a_real_credit():
    for rel, e in manifest().items():
        assert isinstance(e.get("credit"), str) and len(e["credit"]) > 10, rel
        assert "unknown" not in e["credit"].lower(), rel


def test_imported_art_names_its_source_and_never_credits_a_tool_by_guess():
    for rel, e in manifest().items():
        if rel.split("/")[0] in IMPORTED and e.get("source"):
            assert e["source"].startswith("designs/vefr/art/"), rel
            assert e["credit"].startswith("Rylee and Claude"), rel
            assert ("Wan 2.7 Image Pro" in e["credit"]) or ("not recorded" in e["credit"]), rel


def test_pictures_stay_small():
    total = 0
    for rel, p in pictures().items():
        size = p.stat().st_size
        top = rel.split("/")[0]
        if top in IMPORTED:
            assert size <= IMPORTED_CAP, f"{rel} is {size} bytes"
            total += size
        else:
            assert size <= GENERAL_CAP, f"{rel} is {size} bytes"
    assert total <= IMPORTED_TOTAL_CAP, f"imported art is {total} bytes"


def test_the_readme_points_at_the_manifest():
    assert "MANIFEST.json" in (ART / "README.md").read_text(encoding="utf-8")
