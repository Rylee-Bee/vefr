"""Stamps reach play (2026-10-09; ADR 0013, the ground E8b's vaults stand on).

The weave carries a pack's `stamps/` records in the descent block, and the descent passes them to v3 in both
languages, so a play floor carries the stamped rooms - the warden hall and the vault among them - that
`vefr check` swept. A floor's identity hash covers the stamps too, so a stamp edit redraws floors rather than
replaying deltas on a map that changed; a pack with no stamps hashes and weaves exactly as before. The two
languages agreeing on stamped floors is tests/test_descent_parity.py (its Blueprint descent uses them).
"""
import copy
import json
import re
import shutil
from pathlib import Path

import pytest

import play_kit
from vefr import delve, stamps
from test_descent_deltas import TOWN, TOWN_HERO, _go
from test_descent_floors import DESCENT

STAMPS = Path(__file__).resolve().parent / "fixtures" / "stamps"
RECORDS = json.loads(json.dumps(stamps.load(STAMPS)))


def _woven_descent(html: Path) -> dict | None:
    text = html.read_text(encoding="utf-8")
    m = re.search(r"window\.VEFR_DESCENT_DEF\s*=\s*(.*?);\s*\n", text)
    assert m, "the woven player carries no descent block"
    return json.loads(m.group(1))


def _stamped(descent):
    out = copy.deepcopy(descent)
    out["sections"][0]["stamps"] = ["cellar"]
    out["sections"][0]["vault"] = "vault-cellar"
    return out


def test_a_pack_with_stamps_weaves_them_and_one_without_does_not(tmp_path):
    plain = play_kit.pack(tmp_path / "plain", "descent")
    assert "stamps" not in _woven_descent(play_kit.weave(plain, tmp_path / "plain"))
    stamped = play_kit.pack(tmp_path / "stamped", "descent")
    shutil.copytree(STAMPS, Path(stamped) / "stamps")
    block = _woven_descent(play_kit.weave(stamped, tmp_path / "stamped"))
    assert [r["id"] for r in block["stamps"]] == [r["id"] for r in RECORDS]


def test_no_stamps_hashes_as_before_and_a_stamp_edit_changes_the_identity():
    section = DESCENT["sections"][0]
    assert delve.section_hash(section) == delve.section_hash(section, []) == delve.section_hash(section, None)
    with_stamps = delve.section_hash(section, RECORDS)
    assert with_stamps != delve.section_hash(section)
    edited = copy.deepcopy(RECORDS)
    edited[0]["depth"] = [1, 2]
    assert delve.section_hash(section, edited) != with_stamps


def test_a_floor_draws_with_the_stamps_the_descent_carries():
    plain = delve.floor_plan(_stamped(DESCENT), 1)
    stamped = delve.floor_plan({**_stamped(DESCENT), "stamps": RECORDS}, 1)
    assert stamped["rows"] != plain["rows"], "the stamps were not drawn"
    assert stamped["gen"] == plain["gen"] == 3
    assert stamped["identity"]["hash"] != plain["identity"]["hash"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_woven_game_walks_onto_the_stamped_floor_python_draws(tmp_path):
    descent = _stamped(DESCENT)
    stamped = play_kit.pack(tmp_path / "pack", "descent", patch={"world.json": {"descent": descent}})
    shutil.copytree(STAMPS, Path(stamped) / "stamps")
    html = play_kit.weave(stamped, tmp_path)
    want = delve.floor_plan(_woven_descent(html), 1)
    assert want["anchors"]["vault"] is not None
    got = play_kit.play(html, {"steps": ["begin", _go(TOWN, TOWN_HERO, descent["entry"]["at"]),
                                         "click:#interact", "wait:150"],
                               "read": ["VEFR_DESCENT.floor"]})
    assert got["errors"] == [], got["errors"]
    floor = got["reads"]["VEFR_DESCENT.floor"]
    assert floor["rows"] == want["rows"]
    assert floor["anchors"] == want["anchors"]
    assert floor["identity"] == want["identity"]
