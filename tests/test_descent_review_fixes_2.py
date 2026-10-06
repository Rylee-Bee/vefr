"""The ten findings of the vefr#308 second-family review, one test each.

Not a frozen contract: this file is the review pass, the same way
tests/test_descent_review_fixes.py is the first pass. Each test here is
one finding, written to fail on the head it reviews. The three that
need the running player (the two that are player-facing, and the byte
budget) are played through the shared play kit and the review harness,
in the REAL woven file, so the kills, the walk and the save are the
shipped code and not a re-implementation of it. The rest are plain
Python and run without node.

The numbering in the names is the finding's number in the review.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
import make_descent_pack  # noqa: E402

import play_kit
from vefr import cli, delve, maplab

from test_descent_deltas import (ONE_MOB_PATCH, TOWN, TOWN_HERO, _descend, _doc,
                                 _go, _path)
from test_descent_floors import DESCENT
from test_descent_review_fixes import _bytes, _doc_of, _record

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "descent_review_harness.mjs"

# The region, the enemies and the save: what the walk is read back from.
# `VEFR_COMBAT.enemies` is the player's own snapshot of the floor, taken
# when a region is entered, so it says which of the floor's monsters are
# still standing.
READS = ["VEFR_COMBAT.region", "VEFR_COMBAT.hero", "VEFR_COMBAT.enemies",
         "VEFR_DESCENT.floor", "VEFR_DESCENT.doc", "store"]


def _play(tmp_path, steps, store=None, patch=None):
    html = play_kit.weave(play_kit.pack(tmp_path, "descent", patch=patch), tmp_path)
    spec = {"steps": steps, "read": list(READS)}
    if store:
        spec["store"] = store
    return play_kit.play(html, spec)


def _run(tmp_path, cases):
    html = play_kit.weave(play_kit.pack(tmp_path, "descent"), tmp_path)
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(html), str(path)],
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr + run.stdout
    out = json.loads(run.stdout)
    assert out["hasApi"] is True
    return out


# ---- finding 1: a kill remembered on a generated floor --------------------

def _fight_floor_one():
    """Walk out of town, onto the one monster, and kill it."""
    plan = delve.floor_plan(DESCENT, 1)
    mob = plan["mobs"][0]
    steps = ["begin", _go(TOWN, TOWN_HERO, DESCENT["entry"]["at"]),
             "click:#interact", "wait:150",
             _go(plan, plan["anchors"]["up"], mob["at"],
                 [m["at"] for m in plan["mobs"] if m["at"] != mob["at"]])]
    return steps + ["wait:100"] * 6


@needs_node
def test_a_monster_killed_on_a_generated_floor_stays_killed_after_a_reload(tmp_path):
    # The descent's own save holds the kill, beside the floor's explored
    # bitset, so a floor that was never baked still remembers what was done
    # on it. On the head this reviews the save held a bare `m0` while the
    # matcher in the hazards part looked for `m0#<signature>`, so no kill
    # ever matched and every slain monster was standing again on reload.
    killed = _play(tmp_path, _fight_floor_one(), patch=ONE_MOB_PATCH)
    assert killed["errors"] == [], killed["errors"]
    assert _doc(killed)["floors"]["cellar-0-1"]["kills"] == ["m0"]
    assert [e["alive"] for e in killed["reads"]["VEFR_COMBAT.enemies"]] == [False]

    # The same save, the same floor, walked again: the monster is still down.
    again = _play(tmp_path, _descend(1), store=killed["store"], patch=ONE_MOB_PATCH)
    assert again["errors"] == [], again["errors"]
    assert again["reads"]["VEFR_COMBAT.region"] == "cellar-0-1"
    standing = again["reads"]["VEFR_COMBAT.enemies"]
    assert [e["alive"] for e in standing] == [False], \
        f"the kill did not survive the reload; the floor came back un-killed: {standing}"


# ---- findings 2 and 7: the player can leave floor one again ----------------

@needs_node
def test_the_hero_can_still_descend_after_the_new_descent_control(tmp_path):
    # The New-descent control starts run 1: the floors go, the transitions
    # are rebuilt. The town captured the transition list when the game
    # opened, so after this control the new floor's stairs were wired into
    # an array nobody reads any more, and the hero was stranded on floor
    # one with a stair underfoot that did nothing.
    #
    # The walk happens in the SAME session as the control, because that is
    # where the two lists come apart: a second session starts from a freshly
    # woven player and would wire the stairs into the list it captured.
    #
    # The frozen lifecycle test stops the moment the hero lands, which is
    # why nothing caught this; this one walks to the stair of the floor the
    # new run drew and uses it. The walk is planned against
    # `floor_plan(..., run=1)`, which is the floor run 1 draws - same seed,
    # same streams, proven equal by the parity harness.
    plan = delve.floor_plan(DESCENT, 1, run=1)
    path = _path(plan, plan["anchors"]["up"], plan["anchors"]["down"],
                 [m["at"] for m in plan["mobs"]])
    assert path, "floor one must have a walk from its own stair down"
    play = _play(tmp_path, ["begin", "menu:descent", "wait:150",
                            "click:#descent-new", "wait:400",
                            "walk:" + ",".join(path),
                            "click:#interact", "wait:200"])
    assert play["errors"] == [], play["errors"]
    doc = play["reads"]["VEFR_DESCENT.doc"]
    assert doc["run"] == 1, "the control did not start a new run"
    assert doc["floors"]["cellar-0-1"]["n"] == 1, \
        "the walk did not happen on the floor the new run drew"
    assert play["reads"]["VEFR_COMBAT.region"] == "cellar-0-2", \
        "the hero is stranded on floor one: its stair down is not wired"


# ---- findings 3 and 4: a Section id is pack data, like every other name ---

def _pack(tmp_path, sections):
    """The descent fixture pack, its Sections named by id instead."""
    pack = make_descent_pack.build(tmp_path / "home")
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    world["descent"]["sections"] = sections
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")
    return pack, world


def _section_at(path):
    """A perfectly valid Section record, written where it is asked for."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"id": "loot", "floors": 2}), encoding="utf-8")
    return path


def test_a_section_named_by_id_may_not_reach_outside_the_pack(tmp_path):
    # Every other name out of pack data - an act id, a region, a tile file -
    # goes through cli._inside first, so `../x` can never make the engine
    # look outside the pack. A Section id joined straight into a path was
    # the one name that skipped it.
    #
    # Each file below is a VALID Section and is reachable, so a check that
    # only asked "did it resolve" would see nothing wrong. What is being
    # proved is that it is refused at all, and that the bake refuses too.
    beside = _section_at(tmp_path / "home" / "worlds" / "outside" / "loot.json")
    absolute = _section_at(tmp_path / "elsewhere" / "loot.json")
    assert beside.is_file() and absolute.is_file(), \
        "the test wrote nothing for the id to reach, so a refusal would prove nothing"
    for named in ("../../outside/loot", str(absolute.with_suffix(""))):
        assert Path(named).name == "loot", named
        pack, world = _pack(tmp_path, [named])
        # A pack that names its Sections has the folder they are named in,
        # and `..` really does traverse out of it when it does.
        (pack / "sections").mkdir(exist_ok=True)
        errors = maplab.descent_errors(world, pack_dir=pack)
        assert errors, f"a Section id that leaves the pack was read: {named}"
        said = " ".join(errors)
        assert "loot" in said, errors
        assert "pack" in said.lower(), errors
        with pytest.raises(ValueError):
            cli.weave_html(pack)


def test_vefr_check_says_a_sentence_when_there_is_no_pack_to_read_from(tmp_path):
    # `vefr check` on a single world file has no pack directory beside it,
    # and a Section named by id has nothing to read. That is a sentence like
    # every other one - not an AttributeError out of `None.read_text`,
    # which is not a sentence and is not caught by the handler around it.
    pack, _ = _pack(tmp_path, ["cellar"])
    # What `vefr check <world.json>` reads, with no pack beside it.
    errors = maplab.validate(maplab.load_pack(pack))
    assert errors, "a named Section with nothing to read was accepted"
    assert any("cellar" in e for e in errors), errors
    assert all(isinstance(e, str) and e.strip() for e in errors), errors


# ---- finding 6: FLOOR_BYTES is a budget, not a comment --------------------

# One visited floor carrying far more than the per-floor budget of PLAN §3:
# a big bitset and 250 dropped items, on the record shape a pack's own
# deltas take. Forty of these fit inside SAVE_BYTES together, so the whole
# save is not the thing at stake - the record is.
OVER_FLOOR_BUDGET = _doc_of([_record(0, drops=250, fog="f" * 700)])


@needs_node
def test_a_floor_record_is_never_stored_over_its_own_byte_budget(tmp_path):
    assert _bytes(OVER_FLOOR_BUDGET) < delve.SAVE_BYTES, "the save itself is inside it"
    got = _run(tmp_path, {"mode": "budget", "seedDoc": _doc_of([_record(0)]),
                          "docs": [OVER_FLOOR_BUDGET]})["results"][0]
    assert got["refusal"] in (None, ""), "it fits, so nothing is refused"
    assert got["storedFloors"] == 1, "the floor is still remembered"
    assert got["maxFloorBytes"] <= delve.FLOOR_BYTES, (
        f"a floor record of {got['maxFloorBytes']} bytes was stored against a "
        f"budget of {delve.FLOOR_BYTES}")


@needs_node
def test_a_floor_over_its_budget_gives_up_its_memory_before_its_deltas(tmp_path):
    got = _run(tmp_path, {"mode": "budget", "seedDoc": _doc_of([_record(0)]),
                          "docs": [OVER_FLOOR_BUDGET]})["results"][0]
    record = got["floors"]["cellar-0-1-0"]
    assert record["fog"] == "", "the explored bitset is memory, and memory goes first"
    assert record["k"] and record["h"] and record["n"] == 1, \
        "the floor is still itself: its identity triple is never given up"
    assert 0 < len(record["drops"]) < 250, \
        "the deltas that fit are kept, not thrown away to make a point"


# ---- finding 10: a part ends its own lines --------------------------------

def test_every_part_but_the_last_ends_with_a_newline():
    # `packaged.html` is the parts joined byte for byte, with nothing added
    # between them (tests/test_player_build.py is the frozen contract). A
    # part with no trailing newline does not lose a line of its own: it
    # glues its last line onto the first line of whatever comes next, and
    # the joined file still passes `--check`. The descent part had no
    # newline, so the last line of the descent was joined to the first line
    # of `400-setup-town-open.js` and only the next part's newline closed
    # it.
    #
    # The last part is exempt: nothing follows it to supply the newline.
    manifest = json.loads((ROOT / "web" / "player" / "manifest.json")
                          .read_text(encoding="utf-8"))
    parts = ROOT / "web" / "player" / "parts"
    for name in manifest[:-1]:
        data = (parts / name).read_bytes()
        assert data.endswith(b"\n"), f"{name} has no trailing newline"
