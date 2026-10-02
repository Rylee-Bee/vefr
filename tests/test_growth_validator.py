"""Growth, T1: the pack fields (design/growth.md). `growth` is optional and
additive; a pack without it loads and validates exactly as before."""

import copy
import json
import sys
from pathlib import Path

import pytest

from vefr import maplab

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
import make_growth_pack as mk  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def errors_for(tmp_path, growth, xp=None):
    pack = mk.build(tmp_path, growth=growth, xp=xp)
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def has(errors, *needles):
    return any(all(n in e for n in needles) for e in errors)


def test_valid_levels_and_practice_packs_pass(tmp_path):
    assert errors_for(tmp_path, mk.LEVELS, xp=3) == []
    assert errors_for(tmp_path, mk.PRACTICE) == []


def test_a_pack_without_growth_is_unchanged(tmp_path):
    assert errors_for(tmp_path, None) == []
    assert "growth" not in maplab.load_pack(ROOT / "worlds" / "sample-world")
    pack = mk.build(tmp_path, growth=None)
    assert "growth" not in maplab.load_pack(pack)


def test_load_pack_passes_a_declared_growth_through(tmp_path):
    pack = mk.build(tmp_path, growth=mk.LEVELS)
    assert maplab.load_pack(pack)["growth"] == mk.LEVELS


@pytest.mark.parametrize("mutate,needles", [
    (lambda g: g.update(mode="classic"), ("growth", "mode")),
    (lambda g: g["levels"].update(xp=[5, 10]), ("xp",)),
    (lambda g: g["levels"].update(xp=[0, 10, 10]), ("xp",)),
    (lambda g: g["levels"].update(xp=list(range(21))), ("xp",)),
    (lambda g: g["levels"].update(xp=[0, 1.5]), ("xp",)),
    (lambda g: g["levels"].update(gain={"hp": 10}), ("gain",)),
    (lambda g: g["levels"].update(gain={"mana": 1}), ("gain", "mana")),
    (lambda g: g.pop("levels"), ("growth", "levels")),
    (lambda g: g.update(practice={}), ("growth",)),
])
def test_bad_levels_blocks_are_named(tmp_path, mutate, needles):
    g = copy.deepcopy(mk.LEVELS)
    mutate(g)
    assert has(errors_for(tmp_path, g, xp=3), *needles), needles


@pytest.mark.parametrize("mutate,needles", [
    (lambda p: p["atk"].update(by="jumps"), ("by",)),
    (lambda p: p["atk"].update(every=0), ("every",)),
    (lambda p: p["atk"].update(every=100), ("every",)),
    (lambda p: p["atk"].update(cap=0), ("cap",)),
    (lambda p: p["atk"].pop("cap"), ("cap",)),
    (lambda p: p["atk"].update(gain=10), ("gain",)),
    (lambda p: p.update(mana={"by": "strikes", "every": 1, "gain": 1, "cap": 1}),
     ("mana",)),
])
def test_bad_practice_blocks_are_named(tmp_path, mutate, needles):
    g = copy.deepcopy(mk.PRACTICE)
    mutate(g["practice"])
    assert has(errors_for(tmp_path, g), *needles), needles


def test_enemy_xp_rules(tmp_path):
    assert has(errors_for(tmp_path, mk.LEVELS, xp=-1), "rat-1", "xp")
    assert has(errors_for(tmp_path, mk.LEVELS, xp=1.5), "rat-1", "xp")
    assert has(errors_for(tmp_path, mk.PRACTICE, xp=3), "rat-1", "xp")
    assert has(errors_for(tmp_path, None, xp=3), "rat-1", "xp")
    assert errors_for(tmp_path, mk.LEVELS, xp=0) == []


def test_the_bake_carries_growth_and_enemy_xp(tmp_path):
    from vefr import cli
    pack = mk.build(tmp_path, growth=mk.LEVELS, xp=3)
    html = cli.weave_html(pack)
    assert "window.VEFR_GROWTH = " in html
    assert '"mode": "levels"' in html
    assert '"xp": 3' in html            # the enemy's xp rides in VEFR_ENEMIES
    plain = cli.weave_html(mk.build(tmp_path, growth=None))
    assert "window.VEFR_GROWTH = null;" in plain
