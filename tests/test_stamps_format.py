"""The stamp format: the reader, and one golden sentence per refusal.

This is the format half of `docs/adr/0013-stamp-format.md`, written
before `src/vefr/stamps.py`. The table of golden sentences below IS the
contract: every way a stamp can be refused has exactly one plain
sentence, and that sentence names the JSON pointer of the value the
author has to change. A new refusal without a sentence, or a sentence
that moves, is a change to the author-facing contract and needs a
written reason.

Three sentences are quoted from the ADR itself and are marked below; the
rest follow the same shape - what is wrong, then the fix, then the
pointer:

    stamp wine-alcove: no door socket (+) on its edge, so nothing can
    reach it; put a + in the outer wall. /rows
"""

from __future__ import annotations

import json
import re

import pytest

from vefr import stamps

# A minimal legal stamp, and one case per rule. Every case is this stamp
# with one thing changed, so a golden sentence can only move when that
# one rule moves.
GOOD = {
    "stamp": 1,
    "id": "wine-alcove",
    "role": "landmark",
    "rows": ["##+##", "#...#", "+.A.+", "#...#", "#####"],
    "legend": {"A": {"anchor": "poi"}},
    "poi": "the wine alcove",
}

# A stamp that is legal but is not the example: a 21x21 room with a door
# top and bottom, which is the size cap the owner decided (ADR 0013,
# open question 1).
BIG = ["##+##" + "#" * 16] + ["#" + "." * 19 + "#"] * 19 + ["#" * 10 + "+" + "#" * 10]


class _Remove:
    """The value that means "this key is not here at all"."""


_REMOVE = _Remove()


def case(**changes) -> dict:
    """The good stamp with `changes` written over it."""
    source = json.loads(json.dumps(GOOD))
    for key, value in changes.items():
        if value is _REMOVE:
            source.pop(key, None)
        else:
            source[key] = value
    return source


def test_the_good_stamp_is_read():
    """The example from the ADR reads, and the defaults are filled in."""
    record = stamps.read_v1(case(), name="wine-alcove")
    assert record["id"] == "wine-alcove"
    assert record["tags"] == []
    assert record["depth"] == (1, 99)
    assert record["weight"] == 1
    assert record["max_per_floor"] == 1
    assert record["rotate"] is False
    assert record["mirror"] is False
    assert record["legend"] == {"A": {"anchor": "poi"}}


def test_read_v1_does_not_mutate_the_source():
    """The reader returns a new record; the caller's dict is untouched."""
    source = case()
    stamps.read_v1(source, name="wine-alcove")
    assert "tags" not in source


# --------------------------------------------------------------- the goldens
# (case name, the source, the sentence the reader must print). The
# sentence is the whole line `vefr stamp check` prints, pointer and all.

GOLDENS: list[tuple[str, dict, str]] = [
    # -- the envelope -----------------------------------------------------
    ("not an object",
     ["nope"],
     "stamp wine-alcove: a stamp must be a JSON object"),
    ("no version",
     {k: v for k, v in case().items() if k != "stamp"},
     "stamp wine-alcove: stamp version must be the integer 1 /stamp"),
    ("version is a string",
     case(stamp="1"),
     "stamp wine-alcove: stamp version must be the integer 1 /stamp"),
    ("unknown key",
     case(colour="red"),
     "stamp wine-alcove: unknown key 'colour' /colour"),
    ("no id",
     {k: v for k, v in case().items() if k != "id"},
     "stamp wine-alcove: id must be lowercase words and dashes (a-z0-9-) /id"),
    ("id with an underscore",
     case(id="wine_alcove"),
     "stamp wine_alcove: id must be lowercase words and dashes (a-z0-9-) /id"),
    ("unknown role",
     case(role="larder"),
     "stamp wine-alcove: role must be one of landmark, warden-hall, vault, "
     "secret, special, filler /role"),

    # -- the numbers ------------------------------------------------------
    ("tags is a string",
     case(tags="cellar"),
     "stamp wine-alcove: tags must be a list of short names /tags"),
    ("depth is one number",
     case(depth=3),
     "stamp wine-alcove: depth must be [first, last], the floors of a Section "
     "this stamp may appear on /depth"),
    ("weight is a fraction",
     case(weight=1.5),
     "stamp wine-alcove: weight must be a whole number of 0 or more /weight"),
    ("max_per_floor is zero",
     case(max_per_floor=0),
     "stamp wine-alcove: max_per_floor must be a whole number of 1 or more "
     "/max_per_floor"),
    ("rotate is a number",
     case(rotate=1),
     "stamp wine-alcove: rotate must be true or false /rotate"),
    ("mirror is a number",
     case(mirror="yes"),
     "stamp wine-alcove: mirror must be true or false /mirror"),

    # -- story rooms never turn (owner decision 2, ADR 0013 open question 2)
    ("a landmark rotates",
     case(rotate=True),
     "stamp wine-alcove: a landmark is a story room, so it may not rotate or "
     "mirror; hand-draw a second one, or make the room a filler /rotate"),
    ("a vault mirrors",
     {"stamp": 1, "id": "wine-alcove", "role": "vault", "mirror": True,
      "rows": ["##+##", "#.A.#", "#.B.#", "#.C.#", "#####"],
      "legend": {"A": {"anchor": "chest"}, "B": {"anchor": "note"},
                 "C": {"anchor": "home"}}},
     "stamp wine-alcove: a vault is a story room, so it may not rotate or "
     "mirror; hand-draw a second one, or make the room a filler /mirror"),

    # -- the rows ---------------------------------------------------------
    ("rows is a string",
     case(rows="##+##"),
     "stamp wine-alcove: rows must be a list of strings, one per line /rows"),
    ("rows is empty",
     case(rows=[]),
     "stamp wine-alcove: a stamp needs at least one row /rows"),
    ("ragged rows",
     case(rows=["#####", "##+##", "#.."]),
     "stamp wine-alcove: row 3 is 3 characters and row 1 is 5; every row of a "
     "stamp is the same length /rows/3"),
    ("too wide",
     case(rows=["#" * 22] * 22),
     "stamp wine-alcove: this stamp is 22 by 22; a stamp is at most 21 by 21 "
     "(ADR 0013) /rows"),
    ("unknown glyph",
     case(rows=["#####", "#.*.#", "#...#", "#.A.#", "#####"]),
     "stamp wine-alcove: row 1 carries '*', which is not a stamp glyph; use "
     "'#' wall, '.' floor, '+' door, '?' secret, a space, or a capital letter "
     "/rows/1"),
    ("lowercase letter",
     case(rows=["#####", "#.a.#", "#...#", "#.A.#", "#####"]),
     "stamp wine-alcove: row 1 carries 'a'; lowercase letters are reserved, "
     "because 'u' and 'd' are stairs, so a stamp letter is a capital one "
     "/rows/1"),

    # -- the legend -------------------------------------------------------
    ("a letter with no legend entry",
     case(rows=["#####", "#.A.#", "#...#", "#.B.#", "#####"]),
     "stamp wine-alcove: the letter 'B' stands at row 3 column 2 but the "
     "legend does not name it; give every letter a legend entry /legend"),
    ("a legend entry with no letter",
     case(legend={"A": {"anchor": "poi"}, "Z": {"anchor": "chest"}}),
     "stamp wine-alcove: the legend names 'Z' but the rows never draw it; the "
     "legend entry is dead weight /legend/Z"),
    ("a letter drawn twice",
     case(rows=["#####", "#.A.#", "#...#", "#.A.#", "#####"]),
     "stamp wine-alcove: the letter 'A' is drawn twice; a letter is one named "
     "anchor, so it appears exactly once /rows/3"),
    ("an unknown anchor",
     case(legend={"A": {"anchor": "boss"}}),
     "stamp wine-alcove: 'boss' is not a known anchor; an anchor is one of up, "
     "down, warden, chest, note, home, poi, spawn /legend/A/anchor"),
    ("a legend entry with a second key",
     case(legend={"A": {"anchor": "poi", "label": "the wine"}}),
     "stamp wine-alcove: unknown key 'label' /legend/A/label"),

    # -- the shape --------------------------------------------------------
    ("two pieces",
     case(rows=["#####", "#.A.#", "#####", "#...#", "#####"]),
     "stamp wine-alcove: the floor, the anchors and the sockets are in 2 "
     "separate pieces; a stamp is one room, so all of them must touch /rows"),
    ("a space against floor",
     case(rows=["#####", "# A #", "#..##", "+..##", "#####"]),
     "stamp wine-alcove: the space at row 1 column 1 touches floor; a space is "
     "outside the stamp, so the room may not lean on it /rows"),
    ("a door with two ways in",
     case(rows=["######", "#..+.#", "######"], legend={}),
     "stamp wine-alcove: the door socket at row 1 column 3 has 2 tiles to walk "
     "from; a socket has exactly one /rows/1"),
    ("a door facing a wall",
     case(rows=["#####", "#.A.#", "##+##", "#####", "#####"]),
     "stamp wine-alcove: the door socket at row 2 column 2 has its mouth on a "
     "wall, so no corridor can reach it; put a space, or the edge of the rows, "
     "on the far side /rows/2"),

    # -- the roles (the sockets, the anchors each role owes) --------------
    # The ADR's own example sentence, verbatim.
    ("no connectable socket",
     case(rows=["#####", "#.A.#", "#...#", "#####", "#####"]),
     "stamp wine-alcove: no door socket (+) on its edge, so nothing can reach "
     "it; put a + in the outer wall. /rows"),
    ("a landmark with no point of interest",
     case(poi=_REMOVE, legend={"A": {"anchor": "chest"}}),
     "stamp wine-alcove: a landmark needs something to be famous for: a 'poi' "
     "anchor, or a poi sentence beside the stamp /poi"),
    ("a warden hall with two wardens",
     {"stamp": 1, "id": "wine-alcove", "role": "warden-hall",
      "rows": ["##+##", "#.AB#", "#...#", "#...#", "#####"],
      "legend": {"A": {"anchor": "warden"}, "B": {"anchor": "warden"}}},
     "stamp wine-alcove: a warden-hall has exactly one warden, and this one "
     "has 2 /legend"),
    ("a vault with two doors",
     {"stamp": 1, "id": "wine-alcove", "role": "vault",
      "rows": ["##+##", "#.A.#", "#.B.+", "#..C#", "#####"],
      "legend": {"A": {"anchor": "chest"}, "B": {"anchor": "note"},
                 "C": {"anchor": "home"}}},
     "stamp wine-alcove: a vault has exactly one door, and this one has 2 "
     "/rows"),
    ("a vault with a secret",
     {"stamp": 1, "id": "wine-alcove", "role": "vault",
      "rows": ["#######", "#.A...#", "#.B...#", "#.C...#", "+.###?#"],
      "legend": {"A": {"anchor": "chest"}, "B": {"anchor": "note"},
                 "C": {"anchor": "home"}}},
     "stamp wine-alcove: a vault has no secret socket (?); a vault's chest is "
     "the reward, not a secret /rows"),
    ("a vault with no home",
     {"stamp": 1, "id": "wine-alcove", "role": "vault",
      "rows": ["##+##", "#.A.#", "#.B.#", "#####", "#####"],
      "legend": {"A": {"anchor": "chest"}, "B": {"anchor": "note"}}},
     "stamp wine-alcove: a vault needs a chest, a note and a home anchor, and "
     "this one is missing home /legend"),
    ("a secret with a door",
     {"stamp": 1, "id": "wine-alcove", "role": "secret",
      "rows": ["#######", "#.A...#", "#.....#", "+.###?#"],
      "legend": {"A": {"anchor": "chest"}}},
     "stamp wine-alcove: a secret room is found, not walked into: it may not "
     "carry a door socket (+) /rows"),
    ("a secret with no secret",
     {"stamp": 1, "id": "wine-alcove", "role": "secret",
      "rows": ["#####", "#.A.#", "#####", "#####", "#####"],
      "legend": {"A": {"anchor": "chest"}}},
     "stamp wine-alcove: no secret socket (?) on its edge, so the room is not "
     "a secret; put a ? in the outer wall /rows"),
    ("a secret holding the warden",
     {"stamp": 1, "id": "wine-alcove", "role": "secret",
      "rows": ["#####", "#.A.#", "#...#", "#...#", "##?##"],
      "legend": {"A": {"anchor": "warden"}}},
     "stamp wine-alcove: a secret room may not hold the warden; the warden is "
     "found, not stumbled on /legend"),
]

SENTENCE = re.compile(r"^stamp [^:]+: .+( /[^ ]*)?$")


@pytest.mark.parametrize("name, source, sentence", GOLDENS,
                         ids=[entry[0] for entry in GOLDENS])
def test_every_refusal_is_one_golden_sentence(name, source, sentence):
    """One sentence per refusal, with the pointer of the value to change."""
    problems = stamps.problems(source, name="wine-alcove")
    assert problems, f"{name} was expected to be refused"
    assert problems[0] == sentence


def test_a_legal_stamp_has_no_problems():
    """The good stamp is not in the golden table for a reason."""
    assert stamps.problems(case(), name="wine-alcove") == []


def test_a_legal_twenty_one_by_twenty_one_stamp_reads():
    """The cap is a cap, not a smaller cap: 21x21 is a legal stamp."""
    record = stamps.read_v1(
        {"stamp": 1, "id": "big-hall", "role": "filler", "rows": BIG},
        name="big-hall")
    assert len(record["rows"]) == 21
    assert len(record["rows"][0]) == 21


def test_every_golden_is_one_line_that_names_its_pointer():
    """A sentence with no pointer and no fix is not a sentence."""
    for name, _source, sentence in GOLDENS:
        assert "\n" not in sentence, name
        assert SENTENCE.match(sentence), sentence
        if " /" not in sentence:
            # The one refusal with no value to point at: the file itself.
            assert name == "not an object", name


def test_read_v1_raises_the_first_sentence():
    """The reader's own API: the first refusal, as a `StampError`."""
    source = case(role="larder", weight=1.5)
    with pytest.raises(stamps.StampError) as caught:
        stamps.read_v1(source, name="wine-alcove")
    unknown_role = next(s for n, _s, s in GOLDENS if n == "unknown role")
    assert str(caught.value) == unknown_role
    assert caught.value.pointer == "/role"


def test_the_cap_is_twenty_one_in_both_directions():
    """Owner decision 1 (ADR 0013, open question 1): 21x21, not 15x15.

    A 22-wide stamp is refused and so is a 22-tall one, so the cap is the
    number the owner decided in both directions.
    """
    for bigger in (["#" * 22] * 21, ["#" * 21] * 22):
        problems = stamps.problems(case(rows=bigger), "cap")
        assert problems and "at most 21 by 21" in problems[0]


def test_a_socket_with_nothing_behind_it_is_a_second_refusal():
    """A door with no floor behind it is named, after the piece rule.

    The two always come together - a socket with no neighbour is its own
    piece - so the shape rule speaks first and the socket rule is the
    second sentence. Both are in the list, which is what `stamp check`
    prints.
    """
    found = stamps.problems(
        case(rows=["##+##", "#####", "#...#", "#.A.#", "#####"]), name="wine-alcove")
    assert found == [
        "stamp wine-alcove: the floor, the anchors and the sockets are in 2 "
        "separate pieces; a stamp is one room, so all of them must touch /rows",
        "stamp wine-alcove: the door socket at row 0 column 2 has 0 tiles to "
        "walk from; a socket has exactly one /rows/0",
    ]


def test_the_file_name_and_the_id_are_the_same_name(tmp_path):
    """`load` reads a directory in sorted id order, and holds the names."""
    good = case()
    (tmp_path / "wine-alcove.json").write_text(json.dumps(good), encoding="utf-8")
    (tmp_path / "alcove.json").write_text(
        json.dumps({**good, "id": "cellar-nook"}), encoding="utf-8")
    with pytest.raises(stamps.StampError) as caught:
        stamps.load(tmp_path)
    assert "the file is named alcove but its id is 'cellar-nook'" in str(caught.value)
    assert caught.value.pointer == "/id"


def test_load_returns_stamps_in_sorted_id_order(tmp_path):
    """Ids are walked in order, never in a directory listing's order."""
    for stamp_id in ("zulu-nook", "alpha-nook", "mike-nook"):
        (tmp_path / f"{stamp_id}.json").write_text(
            json.dumps(case(id=stamp_id)), encoding="utf-8")
    assert [record["id"] for record in stamps.load(tmp_path)] == [
        "alpha-nook", "mike-nook", "zulu-nook"]
