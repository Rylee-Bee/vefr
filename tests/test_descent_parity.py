"""Play-time floors, R: the JavaScript twin answers exactly what Python answers.

The player is one static HTML file, so the descent is walked in the
browser and Python is only the reference. This replays `locate` and the
whole floor plan (size, rooms, rows, stairs, mobs, identity) for a dozen
depths and two runs through the REAL woven player in jsdom
(`window.VEFR_DESCENT`) and demands identical answers, in both
directions: nothing may be in one language and not the other.

The last two cases are the vefr#315 review finding: a Section names a
Blueprint family by id and carries no record of its own (ADR 0014), so a
floor that read the Section's entry and stopped drew every monster at the
engine's own floor of 1 HP, 1 atk and no drops. The descent carries the
pack's Blueprint (`blueprint`), both twins resolve each family through it,
and the same floor is compared in both languages.
"""

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli, delve
from test_descent_floors import DESCENT

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "descent_parity_harness.mjs"
DEPTHS = list(range(1, 13))
RUNS = [0, 1, 2]

# ADR 0014: a Section's `families` entry names a Blueprint family by id
# and carries no record of its own, so `hp`, `atk`, `sight`, `name` and
# `drops` come from the pack's Blueprint - here the one the descent
# carries, which is what the weave writes beside the Sections.
# `gutter-rat` extends `rat` and overrides only its `hp`, which is the
# whole-value replacement over the root chain; `ghost` is named by a
# Section and defined by no Blueprint, and that is the validator's
# sentence rather than a floor's.
BLUEPRINT = {
    "blueprint": 1,
    "families": {
        "rat": {"defaults": {"name": "a grey rat", "sprite": "rat", "hp": 4,
                             "atk": 2, "sight": 5, "drops": ["pebble"]}},
        "gutter-rat": {"extends": "rat", "defaults": {"hp": 9}},
        "moth": {"defaults": {"name": "a pale moth", "sprite": "moth", "hp": 2,
                              "atk": 1, "sight": 3}},
        "shade": {"extends": "moth", "defaults": {"name": "a cold shade"}},
    },
    "regions": {},
}

# The same descent with the Blueprint beside it and the cellar's families
# naming ids that exercise it: one through an `extends` chain, one at the
# root, and one the Blueprint does not have.
BLUEPRINT_DESCENT = copy.deepcopy(DESCENT)
BLUEPRINT_DESCENT["blueprint"] = BLUEPRINT
BLUEPRINT_DESCENT["sections"][0]["families"] = [
    {"family": "gutter-rat", "weight": 2, "depth": [1, 3]},
    {"family": "moth", "weight": 1, "depth": [1, 3]},
    {"family": "ghost", "weight": 1, "depth": [1, 3]},
]
# E8a: the cellar ends on a warden floor, so the third floor carries monster
# `w` on the v3 warden anchor and the plan's warden record in both languages.
BLUEPRINT_DESCENT["sections"][0]["pattern"] = ["entry", "n", "warden"]
BLUEPRINT_DESCENT["sections"][0]["warden"] = "gutter-rat"


@pytest.fixture(scope="module")
def replay(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("descent-parity")
    html = home / "p.html"
    html.write_text(cli.weave_html(ROOT / "worlds" / "sample-world"), encoding="utf-8")
    cases = home / "cases.json"
    cases.write_text(json.dumps({"descent": DESCENT, "depths": DEPTHS,
                                 "runs": RUNS,
                                 "blueprintDescent": BLUEPRINT_DESCENT,
                                 "blueprintDepths": [1, 2, 3]}),
                     encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(html), str(cases)],
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr + run.stdout
    return json.loads(run.stdout)


def _canonical(value):
    return json.dumps(value, sort_keys=True)


def test_the_twin_exists(replay):
    assert replay["hasApi"] is True


def test_locate_matches_for_every_depth(replay):
    got = replay["located"]
    assert len(got) == len(DEPTHS)
    for depth, answer in zip(DEPTHS, got):
        cycle, section, k = delve.locate(depth, DESCENT)
        assert answer == [cycle, section["id"], k], depth


def test_the_whole_floor_matches_field_for_field(replay):
    got = replay["plans"]
    assert len(got) == len(DEPTHS) + len(RUNS)
    for depth, plan in zip(DEPTHS, got):
        want = delve.floor_plan(DESCENT, depth)
        assert _canonical(plan) == _canonical(want), depth


def test_a_second_run_is_another_floor_on_both_sides(replay):
    got = replay["plans"][len(DEPTHS):]
    for run, plan in zip(RUNS, got):
        descent = copy.deepcopy(DESCENT)
        want = delve.floor_plan(descent, 1, run=run)
        assert _canonical(plan) == _canonical(want), run


def test_the_plan_carries_no_grid_in_its_identity(replay):
    for plan in replay["plans"]:
        assert set(plan["identity"]) == {"gen", "hash", "key"}
        assert plan["name"] == plan["name"].lower()


def test_a_family_is_resolved_from_the_blueprint_rather_than_the_sections_entry():
    """The Python half of the vefr#315 finding, read off the floor itself.

    A Section names a Blueprint family by id and carries no record of its
    own (ADR 0014), so `hp`, `atk`, `sight`, `name` and `drops` are the
    Blueprint's answer to that id. A floor that read the Section's entry
    and stopped drew every monster at 1 HP, 1 atk and no drops, which is
    the same floor twice and a game where nothing can be fought.
    """
    plan = delve.floor_plan(BLUEPRINT_DESCENT, 1)
    assert plan["mobs"], "the cellar's first floor drew no monsters"
    for mob in plan["mobs"]:
        if mob["family"] == "gutter-rat":
            # The chain: `gutter-rat` overrides `hp` over `rat`, and takes
            # everything else from the root.
            assert (mob["hp"], mob["atk"], mob["sight"]) == (9, 2, 5), mob
            assert mob["name"] == "a grey rat", mob
            assert mob["drops"] == ["pebble"], mob
        elif mob["family"] == "moth":
            assert (mob["hp"], mob["atk"], mob["sight"]) == (2, 1, 3), mob
            assert mob["name"] == "a pale moth", mob
        else:
            # A family no Blueprint has: no base, so the engine's own
            # floor of 1 and the id the Section wrote. `vefr check` refuses
            # that Section with `/families/0/family`; a floor lays anyway.
            assert mob["family"] == "ghost", mob
            assert (mob["hp"], mob["atk"], mob["drops"]) == (1, 1, []), mob


def test_a_family_the_blueprint_cannot_resolve_lays_the_floor_at_one():
    """Every refusal `resolve_family` makes is the validator's, not a floor's.

    An unknown family, one that extends itself, one whose parent is
    missing and one caught in a cycle all come back with no base, and a
    floor with no base draws the monster anyway - at the engine's own
    floor of 1, with the id the Section wrote.
    """
    broken = {"families": {
        "loop": {"extends": "loop", "defaults": {"hp": 6}},
        "orphan": {"extends": "ghost", "defaults": {"hp": 6}},
        "spare": {"extends": "loop", "defaults": {"hp": 6}},
    }}
    for family in ("ghost", "loop", "orphan", "spare"):
        assert delve.family_base(broken, family) is None, family
    assert delve.family_base(None, "rat") is None

    descent = copy.deepcopy(BLUEPRINT_DESCENT)
    descent["blueprint"] = broken
    descent["sections"][0]["families"] = [{"family": "orphan", "weight": 1}]
    plan = delve.floor_plan(descent, 1)
    assert plan["mobs"]
    for mob in plan["mobs"]:
        assert (mob["family"], mob["hp"], mob["atk"], mob["drops"]) \
            == ("orphan", 1, 1, []), mob


def test_the_blueprint_floor_is_the_same_floor_in_both_languages(replay):
    """The same floor with a Blueprint beside it, in both languages.

    Both twins resolve the same ids through the same chain and agree on
    every field, so the mobs a browser draws are the mobs Python drew -
    including the stats, which are the whole of the finding.
    """
    got = replay["blueprint"]["plans"]
    assert len(got) == 3
    for depth, plan in zip([1, 2, 3], got):
        want = delve.floor_plan(BLUEPRINT_DESCENT, depth)
        assert _canonical(plan) == _canonical(want), depth
    assert {mob["hp"] for mob in got[0]["mobs"]} != {1}, \
        "every monster drew at 1 HP: the Blueprint was never read"


def test_the_weave_hands_the_player_the_families_it_resolves(tmp_path):
    """The other end of the same fix: where the twin's Blueprint comes from.

    A floor can only resolve a family id if the pack's Blueprint travels
    with the descent, so `weave_html` bakes its `families` in beside the
    Sections. A pack with no Blueprint bakes none, which is the same
    answer the validator gives such a pack: nothing to resolve, and the
    engine's own floor of 1.
    """
    sys.path.insert(0, str(ROOT / "tests"))
    sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
    from blueprint_helpers import normalized_pack  # noqa: E402
    import make_descent_pack  # noqa: E402

    withblueprint = normalized_pack(tmp_path / "a", blueprint=BLUEPRINT)
    _with_descent(withblueprint, copy.deepcopy(DESCENT))
    baked = _baked_descent(cli.weave_html(withblueprint))
    assert baked["blueprint"]["families"] == BLUEPRINT["families"]
    assert baked["legend"], "the legend beside it is still baked"

    without = make_descent_pack.build(tmp_path / "b")
    assert _baked_descent(cli.weave_html(without))["blueprint"] == {}


def _with_descent(pack: Path, descent) -> None:
    """The pack's `world.json` carrying this descent block."""
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    world["descent"] = descent
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")


def _baked_descent(html: str) -> dict:
    """The descent block as `weave_html` wrote it into the player."""
    line = next(row for row in html.splitlines()
                if row.startswith("window.VEFR_DESCENT_DEF = "))
    return json.loads(line.split(" = ", 1)[1].rstrip().rstrip(";"))