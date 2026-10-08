"""A bake that fails must leave the pack exactly as it was. FROZEN.

The defect this pins, measured on merged vefr main before the fix:
`norns delve --section <id>` wrote every floor of the Section and rewrote the
act's `world.json` FIRST, and only then asked the validator. When the pack did
not validate, the command printed "the pack does not validate after the
write", listed the failures and exited non-zero - and left the floors and the
rewritten act sitting on disk. An author reading that output is told nothing
was kept. It was kept.

So a bake is one change: it lands whole, or it does not land at all.

The failure these tests provoke is deliberately NOT a drawing failure. It is a
pack that draws every floor perfectly and then fails validation, which is
exactly the case the old order got wrong. `world.json` gets a `descent` block
whose Section is written as a record rather than named by id; `delve.descent_of`
only reads `sections/<id>.json` for a plain string, so the record reaches the
schema table itself and is refused for holding no `families`. Drawing a Section
never reads the descent block, so the bake succeeds right up to the validate.

Run with:

    bash tests/run.sh tests/test_bake_rollback.py
"""

from __future__ import annotations

import json
from pathlib import Path

from blueprint_helpers import normalized_pack, vefr

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sections"


def a_pack(tmp_path, name: str = "cellar") -> Path:
    """A real pack carrying one committed fixture pack's Section data."""
    built = normalized_pack(
        tmp_path,
        blueprint=json.loads((FIXTURES / name / "blueprint.json").read_text(
            encoding="utf-8")))
    for part in ("sections", "affixes.json"):
        source = FIXTURES / name / part
        target = built / part
        if source.is_dir():
            target.mkdir(exist_ok=True)
            for path in sorted(source.glob("*.json")):
                (target / path.name).write_text(
                    path.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            target.write_text(source.read_text(encoding="utf-8"),
                              encoding="utf-8")
    return built


def break_the_pack_only_at_validation(built: Path) -> None:
    """Make the pack fail validation while every floor still draws."""
    path = built / "world.json"
    world = json.loads(path.read_text(encoding="utf-8"))
    world["descent"] = {
        "run_seed": "rollback-test",
        "entry": {"region": "town", "at": [2, 2]},
        # A record, not a string: delve.descent_of leaves it alone and the
        # schema table refuses it for holding no `families`.
        "sections": [{"id": "cellar"}],
    }
    path.write_text(json.dumps(world, indent=2) + "\n", encoding="utf-8")


def snapshot(built: Path) -> dict[str, bytes]:
    """Every file under the pack's acts/, by relative path."""
    act = built / "acts"
    out = {}
    for path in sorted(act.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(built))] = path.read_bytes()
    return out


def bake(built: Path, seed: str, *extra: str):
    return vefr("delve", "--pack", built, "--seed", seed,
                "--from-region", "town", "--from-at", "2,2",
                "--section", "cellar", *extra)


# --------------------------------------------------------------- the rollback


def test_a_bake_that_fails_leaves_the_pack_exactly_as_it_was(tmp_path):
    """The first bake of a Section. Nothing was there; nothing should be."""
    built = a_pack(tmp_path, "cellar")
    break_the_pack_only_at_validation(built)
    before = snapshot(built)

    rc, out = bake(built, "run-1")

    assert rc != 0, out
    assert "rolled back" in out, out
    assert snapshot(built) == before, "a failed bake left files behind"
    assert not (built / "acts" / "act-1" / "cellar-1").exists()


def test_a_forced_bake_that_fails_puts_the_old_floors_back(tmp_path):
    """A re-bake over floors that already exist puts THOSE back, not the new."""
    built = a_pack(tmp_path, "cellar")
    rc, out = bake(built, "run-1")
    assert rc == 0, out
    good = snapshot(built)
    assert (built / "acts" / "act-1" / "cellar-1").is_dir()

    break_the_pack_only_at_validation(built)
    rc, out = bake(built, "run-2", "--force")

    assert rc != 0, out
    assert "rolled back" in out, out
    after = snapshot(built)
    for name, data in good.items():
        if name.startswith("acts/act-1/cellar-"):
            assert after.get(name) == data, name


def test_a_bake_that_succeeds_still_says_what_it_wrote(tmp_path):
    """The fix must not cost the author the list of floors they just made."""
    built = a_pack(tmp_path, "cellar")
    rc, out = bake(built, "run-1")

    assert rc == 0, out
    assert "the pack validates green" in out, out
    assert out.count("wrote acts/act-1/cellar-") == 9, out