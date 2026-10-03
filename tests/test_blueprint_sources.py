"""Blueprint: errors name the declaration that supplied the value, and every family is checked.

Not part of the frozen A1-A12 contract (like test_blueprint_hardening.py). Plan:
docs/plans/language-architecture-sonnet-implementation-update.md, section 5. These all pass now.
"""

import copy
import json

import pytest

from blueprint_helpers import mk, normalized_pack
from vefr import blueprint

# Written out on purpose (not imported): the documented record key order of format 1.
FIELD_ORDER = ["id", "name", "sprite", "at", "hp", "atk", "xp", "sight", "drops"]


def src():
    """A fresh copy of STD_BLUEPRINT for a test to edit."""
    return copy.deepcopy(mk.STD_BLUEPRINT)


def expand(tmp_path, source):
    return blueprint.expand(source, pack_dir=mk.build(tmp_path))


def empty_cave2(source):
    source["regions"]["act-1/cave-2"]["enemies"] = []
    return source


def error_of(tmp_path, source):
    with pytest.raises(blueprint.BlueprintError) as err:
        expand(tmp_path, source)
    return err.value


def test_invalid_family_default_drop_points_at_the_family(tmp_path):
    s = src()
    s["families"]["beetle"]["defaults"]["drops"] = ["nope"]
    err = error_of(tmp_path, s)
    assert "unknown item" in str(err) and err.pointer == "/families/beetle/defaults/drops"


def test_invalid_ancestor_drop_points_at_the_ancestor(tmp_path):
    s = empty_cave2(src())                                  # only deep-beetle instances remain
    s["families"]["beetle"]["defaults"]["drops"] = ["nope"]
    assert error_of(tmp_path, s).pointer == "/families/beetle/defaults/drops"


def test_descendant_drop_points_at_the_descendant(tmp_path):
    s = empty_cave2(src())
    s["families"]["beetle"]["defaults"]["drops"] = ["shell"]
    s["families"]["deep-beetle"]["defaults"]["drops"] = ["nope"]
    assert error_of(tmp_path, s).pointer == "/families/deep-beetle/defaults/drops"


def test_valid_override_hides_an_invalid_inherited_drop(tmp_path):
    s = src()
    s["families"]["beetle"]["defaults"]["drops"] = ["nope"]
    for inst in s["regions"]["act-1/cave-2"]["enemies"]:
        if inst["family"] == "beetle":
            inst["properties"] = {**inst.get("properties", {}), "drops": ["shell"]}
    s["regions"]["act-1/cave-3"]["enemies"] = []            # deep-beetle would inherit "nope"
    assert expand(tmp_path, s)                               # pins today's semantics


def test_family_names_are_escaped_in_the_pointer(tmp_path):
    s = src()
    s["families"]["a/b~c"] = {"defaults": {"name": "x", "sprite": "beetle", "hp": 1, "atk": 1,
                                           "drops": ["nope"]}}
    s["regions"]["act-1/cave-3"]["enemies"].append({"id": "x1", "family": "a/b~c", "at": [1, 1]})
    assert error_of(tmp_path, s).pointer == "/families/a~1b~0c/defaults/drops"


def test_a_non_string_drop_is_a_plain_error(tmp_path):
    s = src()
    s["families"]["beetle"]["defaults"]["drops"] = [{"a": 1}]
    err = error_of(tmp_path, s)                              # today: a raw TypeError
    assert err.pointer == "/families/beetle/defaults/drops"


def test_check_names_the_family_declaration(tmp_path):
    pack = normalized_pack(tmp_path)
    bad = src()
    bad["families"]["beetle"]["defaults"]["drops"] = ["nope"]
    (pack / "blueprint.json").write_text(json.dumps(bad))
    errors = blueprint.check_errors(pack)
    assert len(errors) == 1 and "(/families/beetle/defaults/drops)" in errors[0]


def test_three_level_chain_is_root_first_in_the_lock(tmp_path):
    s = src()
    s["families"]["deeper"] = {"extends": "deep-beetle", "defaults": {"hp": 5}}
    s["regions"]["act-1/cave-3"]["enemies"].append({"id": "d3", "family": "deeper", "at": [2, 2]})
    pack = normalized_pack(tmp_path, blueprint=s)
    lock = json.loads((pack / "blueprint.lock.json").read_text())
    out = next(o for o in lock["outputs"] if o["file"].endswith("cave-3/contract.json"))
    assert out["records"][-1]["families"] == ["beetle", "deep-beetle", "deeper"]
    cave3 = json.loads((pack / "acts/act-1/cave-3/contract.json").read_text())
    assert cave3["enemies"][-1]["hp"] == 5


def test_records_on_disk_follow_the_documented_key_order(tmp_path):
    pack = normalized_pack(tmp_path)
    for cave in ("cave-2", "cave-3"):
        for rec in json.loads((pack / f"acts/act-1/{cave}/contract.json").read_text())["enemies"]:
            assert list(rec) == [k for k in FIELD_ORDER if k in rec]


def test_resolution_does_not_leak_between_instances_or_runs(tmp_path):
    s = src()
    before = copy.deepcopy(s)
    a, b = expand(tmp_path / "a", s), expand(tmp_path / "b", s)
    assert a == b and s == before
    cave2 = {r["id"]: r for r in a["act-1/cave-2"]}
    assert cave2["odd1"]["hp"] == 9 and cave2["b1"]["hp"] == 3


def test_an_unused_family_with_an_unknown_parent_is_rejected(tmp_path):
    s = src()
    s["families"]["orphan"] = {"extends": "nowhere", "defaults": {}}
    err = error_of(tmp_path, s)
    assert "unknown parent" in str(err) and err.pointer == "/families/orphan/extends"


def test_an_unused_family_cycle_is_rejected(tmp_path):
    s = src()
    s["families"]["x"] = {"extends": "y", "defaults": {}}
    s["families"]["y"] = {"extends": "x", "defaults": {}}
    err = error_of(tmp_path, s)
    assert "cycle" in str(err) and err.pointer == "/families"


def test_every_valid_shape_still_expands(tmp_path):
    assert expand(tmp_path / "std", src())
    from pathlib import Path
    for case in sorted((Path(__file__).parent / "fixtures/blueprint/v1/valid").iterdir()):
        pack = mk.build(tmp_path / case.name)
        assert blueprint.expand(blueprint.read(case / "blueprint.json"), pack_dir=pack)
