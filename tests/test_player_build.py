"""The player is built from parts (docs/plans/player-split/PLAN.md). FROZEN CONTRACT.

`web/packaged.html` stays committed and is GENERATED from the files named in `web/player/manifest.json`, in order,
by `scripts/build_player.py`. Nothing else changes: every consumer (the weaver, the tests, the wheel) still reads
`web/packaged.html`.
  - `build_player.py --check` exits 0 when the committed file is exactly the concatenation of the parts, else 1
    with one plain sentence naming the first differing part-boundary or "stale".
  - `build_player.py` (no flag) rewrites the file from the parts; `--root DIR` builds a copy elsewhere (tests).
  - the manifest is a JSON list of part file names under `web/player/parts/`; every listed file exists and no file in
    that folder is missing from the list (an orphan part would silently not ship).
  - parts are joined with nothing added or removed: byte-for-byte.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_player.py"


def run(*args, root=None):
    cmd = [sys.executable, str(BUILD), *args]
    if root is not None:
        cmd += ["--root", str(root)]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


def clone(tmp_path):
    dest = tmp_path / "repo"
    (dest / "web").mkdir(parents=True)
    shutil.copytree(ROOT / "web" / "player", dest / "web" / "player")
    shutil.copy(ROOT / "web" / "packaged.html", dest / "web" / "packaged.html")
    return dest


def test_the_committed_player_is_exactly_its_parts():
    r = run("--check")
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_manifest_matches_the_parts_folder():
    manifest = json.loads((ROOT / "web" / "player" / "manifest.json").read_text(encoding="utf-8"))
    parts = ROOT / "web" / "player" / "parts"
    listed = set(manifest)
    on_disk = {p.name for p in parts.iterdir() if p.is_file()}
    assert len(manifest) == len(listed), "a part is listed twice"
    assert listed == on_disk, f"missing {listed - on_disk}, orphaned {on_disk - listed}"


def test_the_parts_join_byte_for_byte():
    manifest = json.loads((ROOT / "web" / "player" / "manifest.json").read_text(encoding="utf-8"))
    joined = b"".join((ROOT / "web" / "player" / "parts" / n).read_bytes() for n in manifest)
    assert joined == (ROOT / "web" / "packaged.html").read_bytes()


def test_a_hand_edit_to_the_generated_file_is_caught(tmp_path):
    repo = clone(tmp_path)
    gen = repo / "web" / "packaged.html"
    gen.write_bytes(gen.read_bytes() + b"<!-- hand edit -->\n")
    r = run("--check", root=repo)
    assert r.returncode == 1 and "stale" in (r.stdout + r.stderr).lower()


def test_editing_a_part_then_building_fixes_it(tmp_path):
    repo = clone(tmp_path)
    manifest = json.loads((repo / "web" / "player" / "manifest.json").read_text(encoding="utf-8"))
    part = repo / "web" / "player" / "parts" / manifest[0]
    part.write_bytes(part.read_bytes() + b"<!-- edited part -->\n")
    assert run("--check", root=repo).returncode == 1
    assert run(root=repo).returncode == 0
    assert run("--check", root=repo).returncode == 0
    assert b"<!-- edited part -->" in (repo / "web" / "packaged.html").read_bytes()


def test_an_orphan_part_is_refused(tmp_path):
    repo = clone(tmp_path)
    (repo / "web" / "player" / "parts" / "zz-orphan.js").write_text("// not listed\n", encoding="utf-8")
    r = run("--check", root=repo)
    assert r.returncode == 1 and "zz-orphan.js" in (r.stdout + r.stderr)
