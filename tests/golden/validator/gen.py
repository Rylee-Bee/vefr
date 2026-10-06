"""Capture the validator golden from the code as it stands. Run once on main, before any
migration, then never again without a written reason: `uv run python tests/golden/validator/gen.py`.

S2 added the `rules` and `album` cases (the two `when` validators), BEFORE the migration, with the
reason in tests/test_event_table.py: S0 captured `saves` and `sound` only, so the sentences this
slice moves onto one table were never pinned, and the sentence the plan expected to regenerate
("the six events") had already been corrected on main by c364adb. Nothing was regenerated or
edited after the migration: the added cases are the proof that moving the vocabulary onto
`shapes.EVENTS` changed no sentence and no order."""
import json
from pathlib import Path

from vefr import maplab

SAVES = [None, 0, "x", [], {}, {"rules": "persist"}, {"rules": "reset"}, {"rules": "nope"},
         {"rules": 3}, {"rules": "persist", "legacy": "fresh"}, {"rules": "persist", "legacy": "from-log"},
         {"legacy": "bad"}, {"legacy": None}, {"extra": 1}, {"rules": "x", "legacy": "y", "extra": 1, "more": 2},
         {"zeta": 1, "rules": "persist", "alpha": 2}]
SOUND = [None, 0, "x", [], {}, {"theme": "soft"}, {"theme": "loud"}, {"theme": 1}, {"theme": None},
         {"theme": "soft", "volume": 3}, {"volume": 3}, {"b": 1, "a": 2}, {"theme": "loud", "x": 1}]

# The world every `when` case is written into: one region, two items,
# one phase, one flag, so a case that names a real id says nothing and
# a case that names an absent one says exactly one sentence. No pack
# directory: every id below comes from the world itself.
WHENS = [
    "starts",
    {"starts": {}},
    {},
    {"starts": {}, "enters": {"place": "town"}},
    {"bogus": {}},
    {"starts": []},
    {"enters": {"place": "town"}},
    {"enters": {"place": "nowhere"}},
    {"enters": {"place": 3}},
    {"enters": {}},
    {"enters": {"place": "town", "extra": 1}},
    {"comes-near": {"who": "torch", "distance": 0}},
    {"comes-near": {"who": "torch", "distance": 2}},
    {"comes-near": {"who": "ghost", "distance": 1}},
    {"comes-near": {"who": "torch", "distance": True}},
    {"comes-near": {"who": "torch", "distance": 10}},
    {"comes-near": {"who": "torch", "distance": -1}},
    {"opens": {"what": "torch"}},
    {"opens": {"what": "ghost"}},
    {"picks-up": {"what": "chalked-map"}},
    {"picks-up": {"what": "ghost"}},
    {"uses-with": {"item": "torch", "with": "chalked-map"}},
    {"uses-with": {"item": "ghost", "with": "chalked-map"}},
    {"uses-with": {"item": "torch", "with": "ghost"}},
    {"uses-with": {"item": "torch"}},
    {"defeats": {"what": "rat"}},
    {"buys": {"what": "chalked-map"}},
    {"sells": {"what": "chalked-map"}},
    {"reads": {"what": "almanac"}},
    {"reads": {"what": "ghost"}},
    {"phase-changes": {"to": "dawn"}},
    {"phase-changes": {"to": "dusk"}},
]
BASE = {
    "regions": {"town": {"name": "Town"}},
    "items": {"torch": {"name": "torch"}, "chalked-map": {"name": "map"}},
    "phases": {"dawn": "dawn"},
    "flags": {"lit": "the torch burns"},
}
RULE = {"id": "r1", "then": [{"set": "lit"}]}
STICKER = {"id": "s1", "name": "A sticker", "kind": "open"}


def whens():
    for when in WHENS:
        yield "rules", json.dumps(when), dict(BASE, rules=[dict(RULE, when=when)])
        yield "album", json.dumps(when), dict(BASE, album=[dict(STICKER, when=when)])


def cases():
    for name, fn, values in (("saves", maplab.saves_errors, SAVES), ("sound", maplab.sound_errors, SOUND)):
        for v in values:
            if v is None:
                yield name, "absent", {}, fn({})
            w = {name: v}
            yield name, json.dumps(v), w, fn(w)
    for name, case, w in whens():
        fn = maplab.rules_errors if name == "rules" else maplab.album_errors
        yield name, case, w, fn(w)


if __name__ == "__main__":
    out = [{"block": b, "case": c, "world": w, "errors": e} for b, c, w, e in cases()]
    Path(__file__).with_name("cases.json").write_text(json.dumps(out, indent=1) + "\n")
    print(len(out), "cases")
