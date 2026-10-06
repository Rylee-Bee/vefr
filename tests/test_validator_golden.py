"""S0 (tighten-shapes). FROZEN: validator sentences are byte-identical across the schema-table migration.
The golden was captured on main before shapes.py existed (tests/golden/validator/gen.py). A change here needs a
written reason in the PR.

S2 added the `rules` and `album` blocks to FN, before the event migration and with none of the
captured values edited: the two `when` validators were the sentences this slice moves onto one
table and no case covered them. See tests/test_event_table.py.

E4 added the `section` block to FN, before `src/vefr/shapes.py` grew it and with none of the
captured values edited: the Section pack is the whole of PLAN.md section 2's data shapes, and no
case covered a single one of its refusals. Its expected sentences were written out by hand from the
table's own defaults and put in cases.json before the block existed, then re-captured from the code
afterwards to prove the block says them (tests/golden/validator/gen.py). A `section` case is not a
world block, so it carries a `section` and the pack's affix list and the resolver a Blueprint would
give, and FN is called with the whole case rather than with `c["world"]` - a change to how the
runner is called, not to any sentence it pins."""
import json
from pathlib import Path

import pytest

from vefr import maplab

CASES = json.loads((Path(__file__).parent / "golden" / "validator" / "cases.json").read_text())


def _resolve(family_id: str):
    """The one family the golden's Blueprint has. See gen.py."""
    if family_id != "rat":
        return None
    return {"name": "a rat", "hp": 2, "atk": 1, "xp": 1}


FN = {"saves": lambda c: maplab.saves_errors(c["world"]),
      "sound": lambda c: maplab.sound_errors(c["world"]),
      "rules": lambda c: maplab.rules_errors(c["world"]),
      "album": lambda c: maplab.album_errors(c["world"]),
      "section": lambda c: maplab.section_block_errors(
          c["section"], c["affixes"], _resolve, "sections/cellar.json")}


@pytest.mark.parametrize("c", CASES, ids=lambda c: f"{c['block']}:{c['case']}")
def test_validator_sentences_and_order_do_not_change(c):
    assert FN[c["block"]](c) == c["errors"]