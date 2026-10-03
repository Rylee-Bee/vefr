"""Blueprint `--out DIR` safety (plan T9): the copy never escapes, never recurses, never lingers.

Not part of the frozen A1-A12 contract; these guard the integrator's security review.
"""

import json

from blueprint_helpers import mk, tree_hash, vefr


def test_out_dir_inside_the_pack_is_refused(tmp_path):
    pack = mk.build(tmp_path, blueprint=mk.STD_BLUEPRINT)
    before = tree_hash(pack)
    rc, out = vefr("normalize", "--pack", pack, "--out", pack / "acts" / "copy")
    assert rc == 1 and "inside the pack" in out
    assert tree_hash(pack) == before and not (pack / "acts" / "copy").exists()


def test_a_symlink_in_the_pack_is_copied_as_a_link_not_followed(tmp_path):
    secret = tmp_path / "outside-secret.txt"
    secret.write_text("do not copy me")
    pack = mk.build(tmp_path / "p", blueprint=mk.STD_BLUEPRINT)
    (pack / "link-to-secret").symlink_to(secret)
    dest = tmp_path / "copy"
    rc, out = vefr("normalize", "--pack", pack, "--out", dest)
    assert rc == 0, out
    assert (dest / "link-to-secret").is_symlink()          # a link, not a copy of the secret


def test_a_failed_refresh_into_a_new_directory_leaves_nothing_behind(tmp_path):
    source = {"blueprint": 1,
              "families": {"b": {"defaults": {"name": "a beetle", "sprite": "beetle",
                                              "hp": 3, "atk": 1, "xp": 2}}},
              "regions": {"act-1/town": {"enemies": [{"id": "t1", "family": "b", "at": [2, 4]}]}}}
    pack = mk.build(tmp_path / "p", blueprint=source)       # enemy xp without levels mode: invalid
    dest = tmp_path / "copy"
    rc, out = vefr("normalize", "--pack", pack, "--out", dest)
    assert rc == 1 and "levels mode" in out
    assert not dest.exists()
    empty = tmp_path / "empty"
    empty.mkdir()
    rc, _ = vefr("normalize", "--pack", pack, "--out", empty)
    assert rc == 1 and list(empty.iterdir()) == []


def test_the_lock_records_provenance_for_every_record(tmp_path):
    pack = mk.build(tmp_path, blueprint=mk.STD_BLUEPRINT)
    assert vefr("normalize", "--pack", pack, "--out", pack)[0] == 0
    lock = json.loads((pack / "blueprint.lock.json").read_text())
    assert lock["blueprint"] == 1 and lock["normalizer"] == 1 and len(lock["source_sha256"]) == 64
    cave3 = next(o for o in lock["outputs"] if o["file"].endswith("cave-3/contract.json"))
    assert cave3["pointer"] == "/enemies"
    assert cave3["records"][0] == {"source": "/regions/act-1~1cave-3/enemies/0",
                                   "families": ["beetle", "deep-beetle"], "overrides": []}


def test_weaving_a_stale_pack_from_the_cli_is_a_plain_refusal_not_a_traceback(tmp_path):
    pack = mk.build(tmp_path, blueprint=mk.STD_BLUEPRINT)          # Blueprint, no lock yet
    rc, out = vefr("weave", "--pack", pack, "--out", tmp_path / "out")
    assert rc == 1 and "refused:" in out and "Traceback" not in out
    assert "vefr normalize" in out


def test_normalize_on_a_pack_without_a_blueprint_says_so_instead_of_fresh():
    from blueprint_helpers import ROOT

    rc, out = vefr("normalize", "--pack", ROOT / "worlds" / "sample-world")
    assert rc == 0 and "no blueprint" in out.lower() and "fresh" not in out.lower()
