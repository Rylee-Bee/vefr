"""The placer's two rules a floor only shows on a bad one.

ADR 0013's Placement section is written for the generator, and most of it
is the kind of rule a sweep over 3200 floors never catches: a stamp that
is placed twice on one floor, or a vault anchor on a Section that named
no vault, are both things that have to be true to be seen, and neither
one is a seed the sweep is likely to draw. So they are asked here
directly, against the two functions that decide them.

The rooms in these tests are drawn by hand rather than swept for, because
the question is what the placer does with the slots it is given, and a
floor it drew itself is a floor whose rooms and spine it knows.
"""

from __future__ import annotations

import random

from vefr import delve_v3, stamps


VAULT = {
    "stamp": 1, "id": "test-vault", "role": "vault", "tags": ["cellar"],
    "rows": ["#####", "#CNH#", "+...#", "#####", "#####"],
    "legend": {"C": {"anchor": "chest"}, "N": {"anchor": "note"},
               "H": {"anchor": "home"}},
}


def _canvas(*rects) -> delve_v3.Canvas:
    """A canvas with one plain room per rectangle, in the order given."""
    canvas = delve_v3.Canvas(24, 16)
    for index, rect in enumerate(rects):
        canvas.rooms.append([rect[0], rect[1], rect[2], rect[3], "hall"])
        canvas.carve_room(rect, index)
    return canvas


# ------------------------------------------------- max_per_floor on the pinned try


def test_the_pinned_try_does_not_place_a_stamp_twice(monkeypatch):
    """A stamp that has reached `max_per_floor` drops out, pinned or not.

    The last try takes the first id of the role in sorted order and pins
    it, and a stamp already on the floor has spent its one place on that
    floor whichever try put it there. Two of the same stamp is a room the
    pack never drew, painted twice, and a pack that declared a limit of
    one got two.

    The two vault slots are forced rather than drawn, because the slot
    list is the plan's arithmetic and no floor draws two vaults: what is
    under test is the limit, and the limit is the placer's rule whichever
    slot asks for the stamp.
    """
    record = stamps.read_v1(VAULT)
    canvas = _canvas((2, 2, 6, 4))
    monkeypatch.setattr(delve_v3, "_stamp_slots", lambda plan: ["vault", "vault"])
    placed, missing = delve_v3._stamp_stage(
        random.Random(7), canvas, {}, [record], [0], (4, 3), pinned=True)
    assert [placement["id"] for placement in placed] == ["test-vault"]
    assert missing == ["vault"], "the second slot should be given up, not filled"


def test_a_stamp_under_its_limit_is_pinned_twice(monkeypatch):
    """The same two slots, on a stamp that allows two: both place.

    The limit is the thing under test, so the test that says the limit is
    honoured has to say it is not a blanket "one per floor" rule.
    """
    record = stamps.read_v1({**VAULT, "max_per_floor": 2})
    canvas = _canvas((2, 2, 6, 4))
    monkeypatch.setattr(delve_v3, "_stamp_slots", lambda plan: ["vault", "vault"])
    placed, missing = delve_v3._stamp_stage(
        random.Random(7), canvas, {}, [record], [0], (4, 3), pinned=True)
    assert [placement["id"] for placement in placed] == ["test-vault", "test-vault"]
    assert missing == []


