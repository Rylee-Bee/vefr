"""Blueprint A1, A2: expansion equals today's hand-written records.

FROZEN CONTRACT (docs/adr/0008-blueprint-format.md). Strict xfail until the
core lands (plan PR 2); the implementer removes the mark, never edits the test.
"""

import pytest

from blueprint_helpers import contract, mk, normalized_pack, tree_hash, vefr  # noqa: F401

def test_legacy_equivalence(tmp_path):
    """A1: structural equality (parsed JSON ==; key order ignored, list order significant)."""
    from vefr import blueprint

    pack = mk.build(tmp_path, legacy=True, blueprint=mk.STD_BLUEPRINT)
    expanded = blueprint.expand(blueprint.read(pack / "blueprint.json"), pack_dir=pack)
    assert expanded == mk.STD_LEGACY
    for region, records in mk.STD_LEGACY.items():
        assert contract(pack, region.split("/")[1])["enemies"] == records


@pytest.mark.xfail(strict=True, reason="needs the normalize verb (plan PR 3)")
def test_canonical_bytes(tmp_path):
    """A2: normalize twice leaves identical bytes; untouched files and keys stay byte-identical."""
    pack = mk.build(tmp_path, legacy=False, blueprint=mk.STD_BLUEPRINT)
    before_untouched = (pack / "world.json").read_bytes()
    town_before = (pack / "acts/act-1/town/contract.json").read_bytes()
    assert vefr("normalize", "--pack", pack, "--out", pack)[0] == 0
    first = tree_hash(pack)
    assert vefr("normalize", "--pack", pack, "--out", pack)[0] == 0
    assert tree_hash(pack) == first
    assert (pack / "world.json").read_bytes() == before_untouched
    assert (pack / "acts/act-1/town/contract.json").read_bytes() == town_before
    import json
    cave = json.loads((pack / "acts/act-1/cave-2/contract.json").read_text())
    town = json.loads((pack / "acts/act-1/town/contract.json").read_text())
    assert set(cave) - {"enemies"} == set(town) - {"enemies"}  # other keys of an owned contract survive
