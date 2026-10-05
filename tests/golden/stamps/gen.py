"""Rewrite the orientation goldens, by hand, on purpose.

There is no `__main__` in the tests and no `--update` flag, so a golden
in this directory can only change when a person runs this file and then
reads the diff:

    python tests/golden/stamps/gen.py

What it writes is `orientations.json`: for every stamp in
`tests/fixtures/stamps/`, all eight orientations, as the rows and as
the sockets the placer would route to. The format is the transform, so
a JavaScript twin of `vefr stamp check` can be written against this file
and know it is looking at the same room.

Read the diff before committing it. Every line that moved is either a
fixture redrawn or a transform that changed on purpose, and a transform
that changed on purpose wants a line in ADR 0013 saying so.
"""

from __future__ import annotations

import json
from pathlib import Path

from vefr import stamps

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parent.parent / "fixtures" / "stamps"
GOLDEN = HERE / "orientations.json"


def drawn(record: dict) -> list[dict]:
    """All eight orientations of one stamp: its rows and its sockets."""
    out = []
    for o in range(8):
        rows = stamps.orient(record["rows"], o)
        out.append({
            "rows": rows,
            "sockets": [
                [s["at"][0], s["at"][1], s["kind"],
                 s["mouth"][0], s["mouth"][1], s["step"][0], s["step"][1]]
                for s in stamps.sockets(rows)
            ],
        })
    return out


def main() -> None:
    records = stamps.load(FIXTURES)
    payload = {record["id"]: drawn(record) for record in records}
    GOLDEN.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {GOLDEN.relative_to(HERE.parents[2])} "
          f"for {len(records)} stamps x 8 orientations")


if __name__ == "__main__":
    main()
