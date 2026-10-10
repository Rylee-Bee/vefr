"""vefr#351: a family's `depth` range is the floors of its Section it lives on.

The shape typed `depth` on a Section's family entry and nothing read it, so a
family declared `depth: [7, 9]` - meant for the last three floors of a
nine-floor Section - spawned on every one of the Section's floors. The
Cottage worker found that by counting spawns on a play run, not by reading the
code, and had already written a NOTES.md paragraph describing wardens that
were in fact on every floor. So the tests here count too.

The parity half - that the JavaScript twin reads the same range - lives with
the rest of the per-stage Python/JavaScript comparison, in
`tests/test_descent_parity.py`. This file is the behaviour on its own, and it
runs without node.
"""

import copy

from vefr import delve

# One Section, nine floors, and three families that between them cover every
# floor: `rat` everywhere, `moth` only at the top of the descent, `beetle`
# only at the bottom. Nothing here is the engine's canon - a rat, a moth and a
# beetle are the fixture pack's own creatures.
SECTION = {
    "id": "deep",
    "floors": 9,
    "size": {"w": [32, 36], "h": [24, 26]},
    "rooms": [6, 8],
    "families": [
        {"family": "rat", "weight": 3, "depth": [1, 9]},
        {"family": "moth", "weight": 2, "depth": [1, 3]},
        {"family": "beetle", "weight": 2, "depth": [7, 9]},
    ],
}


def descent(*sections) -> dict:
    return {"run_seed": "run-a", "sections": [copy.deepcopy(s) for s in sections]}


def drawn(depth: int, pack: dict) -> set:
    """The families drawn on the floor at this depth."""
    return {mob["family"] for mob in delve.floor_plan(pack, depth)["mobs"]}


def test_a_family_appears_only_on_the_floors_its_range_names():
    """The regression itself: `depth: [7, 9]` is three floors, not nine."""
    pack = descent(SECTION)
    for depth in range(1, 10):
        families = drawn(depth, pack)
        assert "rat" in families, f"floor {depth} lost its every-floor family"
        assert ("moth" in families) == (depth <= 3), \
            f"floor {depth} drew {sorted(families)}"
        assert ("beetle" in families) == (depth >= 7), \
            f"floor {depth} drew {sorted(families)}"


def test_the_range_counts_from_the_sections_own_first_floor():
    """`depth` is the Section's, not the descent's global depth.

    Two Sections, and a family in the second that is meant for that Section's
    first floor only. At a global depth of 10 that is the first floor a hero
    meets of the second Section, so the family is on depth 10 and on no other
    depth of the whole descent - which is what a pack author's Section means
    when they write it.
    """
    first = dict(SECTION, id="first")
    second = dict(SECTION, id="second", floors=3, families=[
        {"family": "shade", "weight": 1, "depth": [1, 1]},
    ])
    pack = descent(first, second)
    seen = {depth for depth in range(1, 13) if "shade" in drawn(depth, pack)}
    assert seen == {10}, sorted(seen)


def test_a_family_that_names_no_range_is_on_every_floor():
    """The default is what an author who wrote nothing gets."""
    section = dict(SECTION, families=[{"family": "rat", "weight": 2}])
    pack = descent(section)
    for depth in range(1, 10):
        assert drawn(depth, pack) == {"rat"}, depth


def test_a_range_that_covers_the_floor_draws_exactly_what_no_range_draws():
    """Reading the range costs no draw and moves no monster.

    `[1, 9]` over a nine-floor Section and no range at all are the same pool,
    so the floors have to come out byte for byte equal - otherwise honouring
    the range would have moved walls or tiles by spending a random.
    """
    ranged = dict(SECTION, families=[{"family": "rat", "weight": 3, "depth": [1, 9]}])
    plain = dict(SECTION, families=[{"family": "rat", "weight": 3}])
    for depth in range(1, 10):
        assert delve.floor_plan(descent(ranged), depth)["mobs"] == \
            delve.floor_plan(descent(plain), depth)["mobs"], depth


def test_a_range_that_is_not_a_pair_of_whole_numbers_is_every_floor():
    """A range a floor cannot read drops no family off a floor.

    `vefr check` refuses most of these at the shape (a list of one, a string,
    a half that is not a whole number); `[3, 1]` is a pair and passes it. A
    floor lays either way, and reads both as "no range" - never as a range
    that silently empties a Section.
    """
    for bad in ([1], "1-3", [1, "3"], [3, 1], None, [1, True]):
        section = dict(SECTION, families=[{"family": "rat", "weight": 2, "depth": bad}])
        pack = descent(section)
        for depth in range(1, 10):
            assert drawn(depth, pack) == {"rat"}, (bad, depth)