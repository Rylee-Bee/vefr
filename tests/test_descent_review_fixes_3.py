"""Round 4's descent finding: `vefr check` never asks a Section for its vault.

The E4 lock sweep (`locks.section_findings`, printed by `vefr check`)
claims in its own docstring that every floor of every Section holds "a
vault anchor on a Section that names a vault", and it reads every anchor
it is given - so a floor that came back with `anchors.vault` as `null`
was never asked about it. The generator places a vault only when it has
an off-path room to put one in
(`vefr.delve_v3`, `vault_room = ... if len(off_path) > 2 else None`), so
the day a floor comes back without one the pack validated green, the key
to the vault was never handed out, and nothing anywhere said so.

The test drives the door `vefr check` actually opens - `section_findings`
- over a floor that drew no vault anchor, with the generator replaced by
the floor it would have returned. That is the honest shape for a property
proof: the sweep's job is to notice a floor, not to be the only thing
that can produce one.

The other vefr#315 finding - the descent twins reading raw Section family
entries instead of resolving them through the Blueprint - is proved where
the twins live, in `tests/test_descent_parity.py`.
"""

import json

import pytest

from vefr import locks

SECTION = {
    "section": 1,
    "id": "cellar",
    "floors": 1,
    "size": {"w": [32, 32], "h": [24, 24]},
    "rooms": [6, 6],
    "vault": "vault-cellar",
}

# One connected v3 floor with an up-stair, a down-stair, a warden, a
# landmark and no vault: everything `_defect` reads except the vault holds,
# so a sentence about the vault can only be about the vault.
NO_VAULT_PLAN = {
    "gen": 3,
    "w": 7,
    "h": 3,
    "rows": ["#######", "#u...d#", "#######"],
    "anchors": {"up": [1, 1], "down": [5, 1], "warden": [1, 1],
                "vault": None, "landmark": [1, 1]},
    "pois": [], "secrets": [], "spawns": [], "chests": [],
}


def a_section_pack(tmp_path, section=None) -> "object":
    """A pack directory carrying one Section, which is all a sweep reads."""
    pack = tmp_path / "pack"
    (pack / "sections").mkdir(parents=True, exist_ok=True)
    (pack / "sections" / "cellar.json").write_text(
        json.dumps(SECTION if section is None else section), encoding="utf-8")
    return pack


@pytest.fixture
def no_vault(monkeypatch):
    """Every floor of every Section comes back without a vault anchor."""
    monkeypatch.setattr(locks.delve_v3, "generate_floor_v3",
                        lambda *args, **kwargs: dict(NO_VAULT_PLAN))


def test_a_section_naming_a_vault_is_refused_over_a_floor_that_drew_none(
        tmp_path, no_vault):
    assert locks.section_findings(a_section_pack(tmp_path), seeds=1) == [
        "section cellar: floor 1 at seed check-0 does not hold - "
        "the Section names a vault and the floor has no vault anchor"]


def test_a_section_naming_no_vault_is_not_asked_for_one(tmp_path, no_vault):
    """The other half: the check is about a promise, not about every floor.

    A Section that names no vault gets no vault anchor by design
    (`delve_v3`: "a Section that names no vault has no vault to open"), so
    the same floor over such a Section holds and is not a finding.
    """
    without = {key: value for key, value in SECTION.items() if key != "vault"}
    assert locks.section_findings(a_section_pack(tmp_path, without), seeds=1) == []


def test_a_floor_that_did_draw_its_vault_is_not_a_finding(tmp_path, monkeypatch):
    """And the positive half: the sentence is not standing on its own."""
    plan = dict(NO_VAULT_PLAN)
    plan["anchors"] = dict(NO_VAULT_PLAN["anchors"], vault=[3, 1])
    monkeypatch.setattr(locks.delve_v3, "generate_floor_v3",
                        lambda *args, **kwargs: plan)
    assert locks.section_findings(a_section_pack(tmp_path), seeds=1) == []