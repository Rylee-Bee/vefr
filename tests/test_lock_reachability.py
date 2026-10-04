"""Can this pack be finished? `vefr check` follows the locks (Cottage release 1, plan V2). FROZEN CONTRACT.

`vefr.locks.findings(pack_dir)` returns plain sentences (empty list = fine), and `vefr check` prints
them and fails. It reasons from the start region, opening a lock once its key can be OBTAINED in a
region already reached. A key can be obtained from: an enemy `drops`, a chest/book `drops` on the
map, a shop's stock (a speaker with `shop`), or a rule that `give`s it.

Findings (each names the item and the place):
  - a key that cannot be obtained in any region reachable before its lock ("unreachable"),
  - a lock whose key exists only behind that same lock ("behind its own lock"),
  - a key item that has a `value` (it can be sold to a trader, which would break the game).
A pack with no `requires` at all produces no findings and `check` output is unchanged.
Flag locks (`requires: {flag}`) are out of scope: they are never reported.
Neutral fixtures only.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
sys.path.insert(0, str(ROOT / "tests"))
import make_lock_pack as mk  # noqa: E402

from vefr import locks  # noqa: E402


def make(tmp_path, *, key_value=False, key_in="chest", lock=True):
    """The lock fixture: the town door to the cellar needs `brass-ring`.

    key_in: "chest" (a chest in the town drops it), "cellar-enemy" (only a cellar enemy drops it),
    "nowhere". key_value: leave the ring's `value` in (sellable)."""
    pack = mk.build(tmp_path, requires=mk.RING if lock else None)
    world_path = pack / "world.json"
    world = json.loads(world_path.read_text(encoding="utf-8"))
    if not key_value:
        world["items"]["brass-ring"].pop("value", None)
    world_path.write_text(json.dumps(world), encoding="utf-8")
    chest = pack / "library" / "gate-ledger.md"
    text = chest.read_text(encoding="utf-8")
    if key_in != "chest":
        text = text.replace("drops: cloudy-potion, brass-ring", "drops: cloudy-potion")
        chest.write_text(text, encoding="utf-8")
    if key_in == "cellar-enemy":
        cdir = pack / "acts" / "act-1" / "cellar"
        contract = json.loads((cdir / "contract.json").read_text(encoding="utf-8"))
        contract["enemies"] = [{"id": "cellar-rat", "name": "a rat", "at": [2, 1], "hp": 3,
                                "atk": 1, "sight": 0, "sprite": "rat", "drops": ["brass-ring"]}]
        (cdir / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    return pack


def test_a_solvable_pack_has_no_findings(tmp_path):
    assert locks.findings(make(tmp_path)) == []


def test_a_pack_without_locks_has_no_findings(tmp_path):
    assert locks.findings(make(tmp_path, lock=False, key_in="nowhere")) == []


def test_a_key_behind_its_own_lock_is_named(tmp_path):
    out = locks.findings(make(tmp_path, key_in="cellar-enemy"))
    assert any("brass-ring" in f and "behind its own lock" in f for f in out), out


def test_a_key_that_exists_nowhere_is_named(tmp_path):
    out = locks.findings(make(tmp_path, key_in="nowhere"))
    assert any("brass-ring" in f and "unreachable" in f for f in out), out


def test_a_sellable_key_is_named(tmp_path):
    out = locks.findings(make(tmp_path, key_value=True))
    assert any("brass-ring" in f and "sold" in f for f in out), out


def test_a_rule_that_gives_the_key_counts(tmp_path):
    pack = make(tmp_path, key_in="nowhere")
    world_path = pack / "world.json"
    world = json.loads(world_path.read_text(encoding="utf-8"))
    world["flags"], world["claims"], world["people"] = {}, {}, {}
    world["rules"] = [{"id": "gift", "when": {"starts": {}}, "then": [{"give": "brass-ring"}]}]
    world_path.write_text(json.dumps(world), encoding="utf-8")
    assert locks.findings(pack) == []


def test_flag_locks_are_never_reported(tmp_path):
    pack = mk.build(tmp_path, requires=mk.GATE_FLAG)
    assert locks.findings(pack) == []


def test_check_prints_findings_and_fails(tmp_path):
    from blueprint_helpers import vefr

    rc, out = vefr("check", "--pack", make(tmp_path / "bad", key_in="nowhere"))
    assert rc != 0 and "brass-ring" in out and "unreachable" in out
    rc2, out2 = vefr("check", "--pack", make(tmp_path / "ok"))
    assert "unreachable" not in out2 and "behind its own lock" not in out2
