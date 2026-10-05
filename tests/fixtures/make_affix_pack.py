"""Build the SAMPLE affix fixture pack: one `affixes.json` at a pack root.

ADR 0014, "Affix." Affixes live in one list in `affixes.json` at the pack
root, shared by every Section, and every id is unique. This is the sample
list the owner edits; nothing in `src/` or `web/` may carry a name from
it. The engine ships only the neutral ids (`plump`, `prickly`, `sparkly`,
`grumpy`, `big`, `quick`, `glowing`) and looks the label up in the pack.

Two groups of records, and the split is the point:

- the four cozy ones (ADR 0014, "Owner decisions" item 4: cozy and cute
  names, Plump, Prickly, Sparkly, Grumpy), each with a plain label that
  still names the threat;
- the three neutral ones the engine tests already use as ids, so a pack
  can be built whose `elites.affixes` are `big`, `quick` and `glowing`
  (see `tests/test_floor_v3_properties.py`).

Rules every record here holds, checked in `tests/test_affix_fixture.py`:
`id` and `label` required and the label carries the literal `{name}`;
`hp`, `atk` and `xp` in [1.0, 2.0] and `scale` in [1.0, 1.5], all in
whole hundredths; `sight` and `extra_drops` whole numbers in [0, 2]; and
no `moves` key - it is reserved and rejected until the AI can grant an
extra move (that question is still open, so `quick` is `sight: 1` and
nothing else).
"""

import json
import shutil
import sys
from pathlib import Path

NAME = "affix-test"

# The whole sample list, in pack order: the four cozy names first, then
# the neutral ids the engine tests name. Every key is a closed key from
# ADR 0014; the omitted ones are no change (1.0, or 0).
AFFIXES = [
    # Cozy. A plump thing is a bigger, softer target: more hp, no speed.
    {"id": "plump", "label": "Plump {name}", "hp": 1.5, "xp": 1.5,
     "scale": 1.3, "extra_drops": 1},
    # Cozy. A prickly thing hits harder but is slow to get near.
    {"id": "prickly", "label": "Prickly {name}", "atk": 1.4, "hp": 1.1,
     "scale": 1.1},
    # Cozy. A sparkly thing is worth the walk.
    {"id": "sparkly", "label": "Sparkly {name}", "xp": 1.8, "scale": 1.1,
     "extra_drops": 1},
    # Cozy. A grumpy thing hits hard and is hard to walk past.
    {"id": "grumpy", "label": "Grumpy {name}", "atk": 1.5, "xp": 1.2},
    # Neutral canon, the ids the engine tests already use.
    {"id": "big", "label": "Big {name}", "hp": 1.5, "atk": 1.0, "xp": 1.5,
     "sight": 0, "scale": 1.3, "extra_drops": 1},
    # Quick is `sight: 1` and only that. It is UNKNOWN whether the AI can
    # grant an extra move, so `moves` is reserved and must not appear
    # here until that question is answered (ADR 0014, "Affix.").
    {"id": "quick", "label": "Quick {name}", "hp": 1.0, "atk": 1.2, "xp": 1.2,
     "sight": 1, "scale": 1.0},
    # Neutral canon.
    {"id": "glowing", "label": "Glowing {name}", "xp": 1.5, "sight": 1,
     "extra_drops": 1},
]


def build(dest: Path) -> Path:
    """Write the sample pack and return the pack root.

    The pack is a bare directory holding `affixes.json` and nothing else:
    this fixture is about the affix list, so it does not copy a sample
    world the way the other builders do.
    """
    pack = dest / "worlds" / NAME
    if pack.exists():
        shutil.rmtree(pack)
    pack.mkdir(parents=True)
    (pack / "affixes.json").write_text(
        json.dumps(AFFIXES, indent=2) + "\n", encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))
