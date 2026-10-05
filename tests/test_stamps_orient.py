"""The orientation transform: eight ways to look at a hand-drawn room.

ADR 0013's Orientation section, written before the transform. Two things
are pinned here, and the second is the one the ADR calls out as the
reason the format is letters and not arrows:

* all eight orientations of every fixture stamp match the goldens, so a
  JavaScript twin can be written from `stamps.orient` and know it is
  looking at the same room;
* every letter keeps its letter. An anchor is named by its glyph, so
  turning a room never loses the chest or renames the warden.

The goldens live in `tests/golden/stamps/orientations.json` and are
rewritten only by `tests/golden/stamps/gen.py`, by hand, with the diff
read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vefr import stamps

FIXTURES = Path(__file__).parent / "fixtures" / "stamps"
GOLDEN = Path(__file__).parent / "golden" / "stamps" / "orientations.json"

# The turn and the mirror, written out by hand rather than generated, so
# the transform itself is pinned and not only its effect on the fixtures.
# A 2-wide, 3-tall room with one door in its bottom wall, facing down.
TINY = ["##", "#.", "#+"]
# Where that door's mouth points, once per orientation: 0 is as drawn,
# 1..3 turn clockwise, 4 mirrors first and then does the same.
TINY_MOUTH = ("down", "left", "up", "right", "down", "left", "up", "right")
# The first two, worked out by hand: as drawn, and after one turn.
TINY_ROWS = {
    0: ["##", "#.", "#+"],
    1: ["###", "+.#"],
}

DIRECTION = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


@pytest.fixture(scope="module")
def records() -> list[dict]:
    """Every fixture stamp, read by the real reader."""
    return stamps.load(FIXTURES)


@pytest.fixture(scope="module")
def goldens() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_the_fixture_set_covers_every_role(records):
    """One fixture per role, or the transform is only half tested."""
    assert {record["role"] for record in records} == set(stamps.ROLES)


def test_one_fixture_is_twenty_one_by_twenty_one(records):
    """Owner decision 1: the cap is 21x21, and a fixture is at it."""
    assert any(len(record["rows"]) == stamps.MAX_SIDE
               and len(record["rows"][0]) == stamps.MAX_SIDE
               for record in records), "no 21x21 fixture"


# ------------------------------------------------------- the transform itself


@pytest.mark.parametrize("o", [0, 1])
def test_the_first_two_orientations_by_hand(o):
    """Two orientations worked out on paper, before the goldens exist."""
    assert stamps.orient(TINY, o) == TINY_ROWS[o]


@pytest.mark.parametrize("o", range(8))
def test_the_door_turns_with_the_room(o):
    """A room's door points where the room was turned, not where it was drawn.

    The rule the placer depends on: a corridor leaves a socket through
    its mouth, so the mouth's direction has to follow the orientation.
    """
    turned = stamps.orient(TINY, o)
    (socket,) = stamps.sockets(turned)
    assert DIRECTION[TINY_MOUTH[o]] == socket["step"]


def test_a_mirror_flips_the_room_left_to_right():
    """Orientation 4 mirrors first, and 5 mirrors before it turns.

    Not "the mirror of orientation 1": a mirror and a turn do not
    commute, so `5` is the turn of the mirrored room, which is the order
    ADR 0013 writes and the order the placer has to agree with.
    """
    assert stamps.orient(TINY, 4) == ["##", ".#", "+#"]
    assert stamps.orient(TINY, 5) == ["+.#", "###"]


def test_no_orientation_loses_the_room():
    """Eight ways in, and every one of them comes back.

    Four turns undoes four turns, and a mirrored room is its own
    mirror, so the orientation that undoes `o` is `(4 - o) % 4` for an
    unmirrored room and `o` itself for a mirrored one. If a change to
    `_turn` broke this, a stamp could be placed with a tile where no rule
    said it should be.
    """
    for o in range(8):
        undo = (4 - o) % 4 if o < 4 else o
        assert stamps.orient(stamps.orient(TINY, o), undo) == TINY, o


# --------------------------------------------------------- the allowed draws


@pytest.mark.parametrize("rotate, mirror, allowed", [
    (False, False, (0,)),
    (True, False, (0, 1, 2, 3)),
    (False, True, (0, 4)),
    (True, True, (0, 1, 2, 3, 4, 5, 6, 7)),
])
def test_the_allowed_orientations_follow_the_two_flags(rotate, mirror, allowed):
    """ADR 0013: `[0]`, plus turns if `rotate`, plus the mirror if `mirror`."""
    record = {"rotate": rotate, "mirror": mirror}
    assert stamps.orientations(record) == allowed


def test_a_story_room_only_ever_looks_one_way(records):
    """Owner decision 2: a landmark, a hall and a vault never turn.

    The reader refuses the flags on those three roles, so every fixture
    that carries one is pinned at orientation 0 and the generator can
    rely on the room being where it was drawn.
    """
    for record in records:
        if record["role"] in stamps.REQUIRED_ROLES:
            assert stamps.orientations(record) == (0,), record["id"]
        else:
            assert stamps.orientations(record) != (0,), record["id"]


# ------------------------------------------------------------ the goldens


@pytest.mark.parametrize("stamp_id", sorted(p.stem for p in FIXTURES.glob("*.json")))
def test_every_orientation_matches_the_golden(records, goldens, stamp_id):
    """All eight orientations of one fixture, rows and sockets, as pinned."""
    record = next(item for item in records if item["id"] == stamp_id)
    drawn = []
    for o in range(8):
        rows = stamps.orient(record["rows"], o)
        drawn.append({
            "rows": rows,
            "sockets": [[s["at"][0], s["at"][1], s["kind"],
                         s["mouth"][0], s["mouth"][1], s["step"][0], s["step"][1]]
                        for s in stamps.sockets(rows)],
        })
    assert drawn == goldens[stamp_id], (
        f"{stamp_id}: an orientation moved. Rewrite the goldens with "
        "python tests/golden/stamps/gen.py and read the diff; if the "
        "transform did not move on purpose, this is a regression")


@pytest.mark.parametrize("stamp_id", sorted(p.stem for p in FIXTURES.glob("*.json")))
def test_anchors_keep_their_letters(records, stamp_id):
    """Every letter of the legend is still drawn, and still means the same.

    The whole reason an anchor is named by its glyph: turn a room and the
    chest is still the chest.
    """
    record = next(item for item in records if item["id"] == stamp_id)
    for o in range(8):
        found = stamps.anchors(stamps.orient(record["rows"], o), record["legend"])
        assert set(found) == set(record["legend"]), f"{stamp_id} at {o}"
        for glyph, entry in record["legend"].items():
            assert found[glyph]["anchor"] == entry["anchor"], f"{stamp_id} {glyph} at {o}"
            row = stamps.orient(record["rows"], o)[found[glyph]["at"][1]]
            assert row[found[glyph]["at"][0]] == glyph, f"{stamp_id} {glyph} at {o}"


@pytest.mark.parametrize("stamp_id", sorted(p.stem for p in FIXTURES.glob("*.json")))
def test_a_square_stamp_stays_square_and_a_long_one_swaps(records, stamp_id):
    """The grid is h x w before the turn and w x h after it, every time."""
    record = next(item for item in records if item["id"] == stamp_id)
    height = len(record["rows"])
    width = len(record["rows"][0])
    for o in range(8):
        rows = stamps.orient(record["rows"], o)
        turns = o % 4
        expect = (height, width) if turns % 2 == 0 else (width, height)
        assert (len(rows), len(rows[0])) == expect, f"{stamp_id} at {o}"
