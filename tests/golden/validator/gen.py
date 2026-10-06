"""Capture the validator golden from the code as it stands. Run once on main, before any
migration, then never again without a written reason: `uv run python tests/golden/validator/gen.py`."""
import json
from pathlib import Path

from vefr import maplab

SAVES = [None, 0, "x", [], {}, {"rules": "persist"}, {"rules": "reset"}, {"rules": "nope"},
         {"rules": 3}, {"rules": "persist", "legacy": "fresh"}, {"rules": "persist", "legacy": "from-log"},
         {"legacy": "bad"}, {"legacy": None}, {"extra": 1}, {"rules": "x", "legacy": "y", "extra": 1, "more": 2},
         {"zeta": 1, "rules": "persist", "alpha": 2}]
SOUND = [None, 0, "x", [], {}, {"theme": "soft"}, {"theme": "loud"}, {"theme": 1}, {"theme": None},
         {"theme": "soft", "volume": 3}, {"volume": 3}, {"b": 1, "a": 2}, {"theme": "loud", "x": 1}]


def cases():
    for name, fn, values in (("saves", maplab.saves_errors, SAVES), ("sound", maplab.sound_errors, SOUND)):
        for v in values:
            if v is None:
                yield name, "absent", {}, fn({})
            w = {name: v}
            yield name, json.dumps(v), w, fn(w)


if __name__ == "__main__":
    out = [{"block": b, "case": c, "world": w, "errors": e} for b, c, w, e in cases()]
    Path(__file__).with_name("cases.json").write_text(json.dumps(out, indent=1) + "\n")
    print(len(out), "cases")
