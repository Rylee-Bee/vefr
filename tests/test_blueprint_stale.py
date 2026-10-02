"""Blueprint A6, A7, A8: stale output is rejected; the whole normalized pack is validated."""

import json

import pytest

from blueprint_helpers import mk, normalized_pack, tree_hash, vefr


def _bp(tmp_path):
    return normalized_pack(tmp_path)


def test_fresh_pack_checks_clean(tmp_path):
    from vefr import blueprint

    assert blueprint.check_errors(_bp(tmp_path)) == []


def test_editing_the_blueprint_without_normalizing_is_stale(tmp_path):
    pack = _bp(tmp_path)
    source = json.loads((pack / "blueprint.json").read_text())
    source["families"]["beetle"]["defaults"]["hp"] = 7
    (pack / "blueprint.json").write_text(json.dumps(source))
    rc, out = vefr("check", "--pack", pack)
    assert rc != 0 and "stale" in out.lower()


def test_hand_editing_a_generated_record_is_stale_and_names_file_and_pointer(tmp_path):
    from vefr import blueprint

    pack = _bp(tmp_path)
    path = pack / "acts/act-1/cave-2/contract.json"
    data = json.loads(path.read_text())
    data["enemies"][1]["hp"] = 99
    path.write_text(json.dumps(data))
    errors = blueprint.check_errors(pack)
    joined = " ".join(errors)
    assert errors and "stale" in joined.lower()
    assert "acts/act-1/cave-2/contract.json" in joined and "/enemies/1" in joined


def test_lock_missing_or_without_blueprint_fails(tmp_path):
    from vefr import blueprint

    pack = _bp(tmp_path)
    (pack / "blueprint.lock.json").unlink()
    assert blueprint.check_errors(pack)
    pack2 = _bp(tmp_path / "two")
    (pack2 / "blueprint.json").unlink()
    assert blueprint.check_errors(pack2)


def test_newer_normalizer_fails_older_equal_output_passes_with_a_note(tmp_path):
    from vefr import blueprint

    pack = _bp(tmp_path)
    lock_path = pack / "blueprint.lock.json"
    lock = json.loads(lock_path.read_text())
    lock["normalizer"] = 999
    lock_path.write_text(json.dumps(lock))
    assert blueprint.check_errors(pack)
    lock["normalizer"] = 0
    lock_path.write_text(json.dumps(lock))
    assert blueprint.check_errors(pack) == []
    rc, out = vefr("check", "--pack", pack)
    assert rc == 0 and "normalize" in out.lower()


def test_weave_refuses_stale_and_weaves_fresh(tmp_path):
    from vefr import cli

    pack = _bp(tmp_path)
    assert cli.weave_html(pack)
    path = pack / "acts/act-1/cave-2/contract.json"
    data = json.loads(path.read_text())
    data["enemies"][0]["atk"] = 50
    path.write_text(json.dumps(data))
    with pytest.raises(Exception) as err:
        cli.weave_html(pack)
    assert "stale" in str(err.value).lower()


def test_valid_source_that_fails_the_whole_pack_is_caught_and_restored(tmp_path):
    """A8: the second validation (today's validator on the whole normalized pack) catches
    what source checks cannot, and `--out PACK` puts the previous bytes back."""
    source = {"blueprint": 1,
              "families": {"b": {"defaults": {"name": "a beetle", "sprite": "beetle",
                                              "hp": 3, "atk": 1, "xp": 2}}},
              "regions": {"act-1/town": {"enemies": [{"id": "t1", "family": "b", "at": [2, 4]}]}}}
    pack = mk.build(tmp_path, legacy=True, blueprint=source)  # no growth: enemy xp is an error
    before = tree_hash(pack)
    rc, out = vefr("normalize", "--pack", pack, "--out", pack)
    assert rc == 1 and "levels mode" in out
    assert tree_hash(pack) == before
