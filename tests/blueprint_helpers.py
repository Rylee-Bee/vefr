"""Shared helpers for the Blueprint tests (docs/adr/0008-blueprint-format.md)."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_blueprint_pack as mk  # noqa: E402,F401

CLI = ("import sys; from vefr.cli import vefr_main; "
       "sys.argv = ['vefr'] + sys.argv[1:]; sys.exit(vefr_main())")


def vefr(*args, cwd=None):
    """Run the real `vefr` front door in a subprocess: (returncode, stdout+stderr)."""
    proc = subprocess.run([sys.executable, "-c", CLI, *map(str, args)],
                          capture_output=True, text=True, cwd=cwd or ROOT)
    return proc.returncode, proc.stdout + proc.stderr


def tree_hash(path: Path) -> str:
    """One digest over every file path and byte under `path`."""
    h = hashlib.sha256()
    for f in sorted(p for p in Path(path).rglob("*") if p.is_file()):
        h.update(str(f.relative_to(path)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def normalized_pack(tmp_path, blueprint=None, legacy=False):
    """A pack with a Blueprint, refreshed in place by `vefr normalize`."""
    pack = mk.build(tmp_path, legacy=legacy,
                    blueprint=blueprint if blueprint is not None else mk.STD_BLUEPRINT)
    rc, out = vefr("normalize", "--pack", pack, "--out", pack)
    assert rc == 0, out
    return pack


def contract(pack, region="cave-2"):
    return json.loads((Path(pack) / "acts" / "act-1" / region / "contract.json").read_text())
