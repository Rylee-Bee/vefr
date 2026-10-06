"""S0 (tighten-shapes). FROZEN: validator sentences are byte-identical across the schema-table migration.
The golden was captured on main before shapes.py existed (tests/golden/validator/gen.py). A change here needs a
written reason in the PR.

S2 added the `rules` and `album` blocks to FN, before the event migration and with none of the
captured values edited: the two `when` validators were the sentences this slice moves onto one
table and no case covered them. See tests/test_event_table.py."""
import json
from pathlib import Path

import pytest

from vefr import maplab

CASES = json.loads((Path(__file__).parent / "golden" / "validator" / "cases.json").read_text())
FN = {"saves": maplab.saves_errors, "sound": maplab.sound_errors,
      "rules": maplab.rules_errors, "album": maplab.album_errors}


@pytest.mark.parametrize("c", CASES, ids=lambda c: f"{c['block']}:{c['case']}")
def test_validator_sentences_and_order_do_not_change(c):
    assert FN[c["block"]](c["world"]) == c["errors"]
