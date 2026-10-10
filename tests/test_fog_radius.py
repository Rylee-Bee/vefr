"""vefr #364: how far a Section sees. The ceiling is a fraction of the floor.

`shapes.FOG` caps a Section's `fog.radius` at 32 tiles. It capped it at
8, which no ADR, PLAN.md or Section pack records the reason for, and at 8
the lit disc was 17 tiles across - a fifth of the floor a cellar-shaped
Section declares, drawn in the middle of a floor that is rooms.

The number is not a bare constant here: it is a quarter of the widest
floor `shapes.SIZE` lets a Section declare, read out of `SIZE` at import
(`shapes.FOG_RADIUS_MAX`), so a Section says how far it sees as a
fraction of its own floor and the two move together. The tests below
hold four things:

- the ceiling IS that fraction of `SIZE`, and the disc it names still
  fits inside the largest floor the schema permits on both axes, so no
  radius a pack may name is a disc no floor could hold;
- a Section may declare any radius from 2 to the ceiling, including one
  above the old ceiling of 8, and `vefr check --pack` accepts the pack;
- the low end is unmoved: below 2 the sentence still names
  `/section/fog/radius`;
- a Section that says nothing about fog still gets exactly what it got
  before this change (`delve.DEFAULT_FOG_RADIUS`), and a Section that
  says 4 still gets 4 - the bounds move, the defaults do not.

The fog *shape* is out of scope on purpose: at 32 the disc reads even
more plainly as a circle in a set of rooms, and what to draw instead is
Rylee's call, not this slice's. See the return in vefr #364.

Run with:

    bash tests/run.sh tests/test_fog_radius.py
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import pytest

from blueprint_helpers import normalized_pack
from vefr import delve, maplab, shapes

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sections"

RADIUS = next(k for k in shapes.FOG.keys if k.name == "radius")
SIZE_W = next(k for k in shapes.SIZE.keys if k.name == "w")
SIZE_H = next(k for k in shapes.SIZE.keys if k.name == "h")

# The lit area on a generated floor is a filled disc, so its width in
# tiles is one more than twice the radius.
def disc_across(radius: int) -> int:
    return 2 * radius + 1


def fixture_section(name: str = "cellar") -> dict:
    """One committed fixture pack's Section, read off disk (not written
    out here, so the tests hold against the same bytes a pack author
    ships)."""
    return json.loads((FIXTURES / name / "sections" / f"{name}.json").read_text(
        encoding="utf-8"))


def only(problems) -> tuple[str, str]:
    assert len(problems) == 1, [p.sentence for p in problems]
    return problems[0].pointer, problems[0].sentence


def descent_with(section: dict) -> dict:
    """A one-Section descent, the shape `delve.floor_plan` reads."""
    return {"run_seed": "fog-radius", "entry": {"region": "town", "at": [4, 5]},
            "sections": [copy.deepcopy(section)]}


def pack_with_fog(tmp_path, name: str, radius: int) -> Path:
    """A real pack carrying a fixture Section with this fog radius.

    Built the shipped way - `make_blueprint_pack` plus a real `vefr
    normalize` - over the fixture's own Blueprint, so the Section's
    families resolve, and then the one value under test is written into
    the pack's `sections/<id>.json`. This is the file a pack author
    writes, which is the point: the acceptance is about `vefr check
    --pack`, not about a dict handed to a function.
    """
    built = normalized_pack(
        tmp_path,
        blueprint=json.loads((FIXTURES / name / "blueprint.json").read_text(
            encoding="utf-8")))
    (built / "sections").mkdir(exist_ok=True)
    (built / "affixes.json").write_text(
        (FIXTURES / name / "affixes.json").read_text(encoding="utf-8"),
        encoding="utf-8")
    section = fixture_section(name)
    section["fog"] = {"radius": radius}
    (built / "sections" / f"{name}.json").write_text(
        json.dumps(section, indent=1), encoding="utf-8")
    return built


# ------------------------------------------------- what the ceiling is

def test_the_ceiling_is_a_quarter_of_the_widest_floor_a_section_may_declare():
    """The grounding, held as a fact about the table rather than a note.

    `FOG`'s ceiling is read out of `SIZE` at import, so this also fails if
    someone writes the number into `FOG` by hand again - which is how the
    8 that no record explains got there.
    """
    assert shapes.FOG_RADIUS_MAX == SIZE_W.hi // 4
    assert RADIUS.hi == shapes.FOG_RADIUS_MAX
    assert RADIUS.hi == 32
    assert SIZE_W.hi == 128


def test_the_largest_disc_still_fits_inside_the_largest_floor_the_schema_allows():
    """SIZE's largest `w` does not let a radius name a disc no floor holds.

    `SIZE` allows a floor up to 128 wide and 96 tall. At the ceiling the
    lit disc is 65 tiles across, which fits inside BOTH of those: the
    biggest sight a pack may ask for is still smaller than the biggest
    floor the schema lets it draw, on its narrow axis as well as its
    long one.
    """
    assert disc_across(RADIUS.hi) <= SIZE_W.hi
    assert disc_across(RADIUS.hi) <= SIZE_H.hi
    assert SIZE_H.hi == 96


# ------------------------------------------------- a Section may say more

@pytest.mark.parametrize("radius", [2, 5, 8, 9, 12, 16, 24, RADIUS.hi])
def test_a_section_may_declare_any_radius_up_to_the_ceiling(radius):
    """9..32 were refused a moment ago and are legal now. 8 still is."""
    section = dict(fixture_section(), fog={"radius": radius})
    assert shapes.check(shapes.SECTION, section) == []


def test_a_radius_above_the_ceiling_is_refused_at_the_fog_pointer():
    section = dict(fixture_section(), fog={"radius": RADIUS.hi + 1})
    assert only(shapes.check(shapes.SECTION, section)) == (
        "/section/fog/radius",
        f"section.fog.radius must be between {RADIUS.lo} and {RADIUS.hi}")


def test_a_radius_below_two_is_still_refused_at_the_same_pointer():
    """The low end does not move with the ceiling: same pointer, same shape,
    one number in the sentence."""
    section = dict(fixture_section(), fog={"radius": 1})
    assert only(shapes.check(shapes.SECTION, section)) == (
        "/section/fog/radius",
        f"section.fog.radius must be between {RADIUS.lo} and {RADIUS.hi}")


# ------------------------------------------- through the real `vefr check`

def test_vefr_check_accepts_a_pack_whose_section_sees_further_than_eight(tmp_path,
                                                                        capsys):
    """Acceptance 1, through the door an author walks through.

    `vefr check --pack P` is `maplab.cmd_validate` (`cli.py` sets
    `map_cmd='validate'`), and `validate` is what reads every pack's
    `sections/` - so this is the command, in process.
    """
    pack = pack_with_fog(tmp_path / "wide", "cellar", 16)
    assert maplab.cmd_validate(argparse.Namespace(pack=str(pack))) == 0
    assert capsys.readouterr().out.startswith("ok:")


def test_vefr_check_names_the_fog_pointer_when_a_radius_is_too_wide(tmp_path,
                                                                  capsys):
    """Acceptance 1's other half: above the ceiling is still a refusal, and
    it is the same pointer an author can act on."""
    pack = pack_with_fog(tmp_path / "wider", "cellar", RADIUS.hi + 1)
    assert maplab.cmd_validate(argparse.Namespace(pack=str(pack))) == 1
    out = capsys.readouterr().out
    assert "sections/cellar.json: /section/fog/radius" in out
    assert f"must be between {RADIUS.lo} and {RADIUS.hi}" in out


# ------------------------------------------------- the defaults do not move

def test_a_section_that_says_nothing_about_fog_still_gets_the_engine_default():
    """No key, no key named: the same radius, on every floor of the Section.

    `delve.DEFAULT_FOG_RADIUS` is what a pack that leaves `fog` out has
    always got, and raising a ceiling on what a pack may ASK for cannot
    move it. Pinned at the value the player part's twin also carries
    (`web/player/parts/397-the-descent.js`, `DEFAULT_FOG_RADIUS = 5`).
    """
    assert delve.DEFAULT_FOG_RADIUS == 5
    section = fixture_section()
    del section["fog"]
    descent = descent_with(section)
    assert [delve.floor_plan(descent, d)["fog"] for d in (1, 3, 9)] == \
        [{"radius": 5}] * 3


def test_a_section_that_declares_four_still_gets_four_on_every_floor():
    """The pack that ships: 4 is inside the range before and after, and every
    floor it draws says 4, so its lit disc is the same disc it was."""
    section = fixture_section()
    assert section["fog"] == {"radius": 4}
    descent = descent_with(section)
    assert {delve.floor_plan(descent, d)["fog"]["radius"]
            for d in (1, 2, 5, 9)} == {4}


def test_a_section_may_declare_the_new_ceiling_and_get_it_on_every_floor():
    """The ceiling is not only accepted by the validator: a floor drawn from
    such a Section carries the radius the pack asked for, unclamped."""
    section = dict(fixture_section(), fog={"radius": RADIUS.hi})
    descent = descent_with(section)
    assert {delve.floor_plan(descent, d)["fog"]["radius"]
            for d in (1, 4, 9)} == {RADIUS.hi}


def test_the_shipped_sample_pack_declares_a_radius_inside_the_new_range():
    """Emberfield's town fog rides the region contract, not a Section, so it
    was never in this table - it is read here so a pack that ever grows a
    Section above 8 cannot be introduced by a change to that file."""
    contract = json.loads(
        (Path(__file__).resolve().parents[1] / "worlds" / "sample-world" /
         "acts" / "act-1" / "town" / "contract.json").read_text(encoding="utf-8"))
    assert RADIUS.lo <= contract["fog"]["radius"] <= RADIUS.hi