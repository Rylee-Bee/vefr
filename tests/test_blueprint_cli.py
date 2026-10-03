"""Blueprint A9, A12: the `normalize` verb, and determinism."""

import json
import subprocess
import sys


from blueprint_helpers import ROOT, contract, mk, normalized_pack, tree_hash, vefr



def test_read_only_normalize_writes_nothing_and_exit_codes(tmp_path):
    pack = mk.build(tmp_path, blueprint=mk.STD_BLUEPRINT)
    before = tree_hash(pack)
    rc, out = vefr("normalize", "--pack", pack)
    assert tree_hash(pack) == before
    assert rc == 1  # nothing generated yet: not fresh
    fresh = normalized_pack(tmp_path / "fresh")
    rc, out = vefr("normalize", "--pack", fresh)
    assert rc == 0 and "fresh" in out.lower()


def test_out_dir_copies_and_leaves_the_pack_untouched(tmp_path):
    pack = mk.build(tmp_path, blueprint=mk.STD_BLUEPRINT)
    before = tree_hash(pack)
    out_dir = tmp_path / "copy"
    rc, out = vefr("normalize", "--pack", pack, "--out", out_dir)
    assert rc == 0, out
    assert tree_hash(pack) == before
    assert (out_dir / "blueprint.lock.json").exists()
    assert contract(out_dir, "cave-2")["enemies"] == mk.STD_LEGACY["act-1/cave-2"]


def test_out_dir_refuses_a_non_empty_directory(tmp_path):
    pack = mk.build(tmp_path, blueprint=mk.STD_BLUEPRINT)
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "keep.txt").write_text("mine")
    rc, out = vefr("normalize", "--pack", pack, "--out", busy)
    assert rc == 1 and (busy / "keep.txt").read_text() == "mine"
    assert not (busy / "blueprint.lock.json").exists()


def test_deterministic_in_one_process_and_across_processes(tmp_path):
    """A12: same Blueprint, same lock and records."""
    from vefr import blueprint

    pack = mk.build(tmp_path, blueprint=mk.STD_BLUEPRINT)
    source = blueprint.read(pack / "blueprint.json")
    a = blueprint.expand(source, pack_dir=pack)
    assert a == blueprint.expand(source, pack_dir=pack)
    assert blueprint.canonical_hash(source) == blueprint.canonical_hash(json.loads(json.dumps(source)))
    code = ("import sys,json; from pathlib import Path; from vefr import blueprint; p=Path(sys.argv[1]); "
            "s=blueprint.read(p/'blueprint.json'); print(json.dumps(blueprint.expand(s,pack_dir=p),sort_keys=True), "
            "blueprint.canonical_hash(s))")
    runs = [subprocess.run([sys.executable, "-c", code, str(pack)], capture_output=True, text=True,
                           cwd=ROOT).stdout for _ in range(2)]
    assert runs[0] and runs[0] == runs[1]
