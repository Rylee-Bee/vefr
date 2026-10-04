"""Build web/packaged.html from its parts (docs/plans/player-split/PLAN.md).

The woven player's source lives in web/player/parts/, in the order web/player/manifest.json lists them. This script
joins them, byte for byte, into web/packaged.html, which stays committed so every consumer still reads one file.
Never edit web/packaged.html by hand: edit a part, then run this.

  uv run python scripts/build_player.py            rewrite web/packaged.html from the parts
  uv run python scripts/build_player.py --check    exit 1 if the committed file is stale or a part is orphaned
  --root DIR                                       use DIR instead of the repository (tests)
"""
import argparse
import json
import sys
from pathlib import Path


def build(root: Path) -> tuple[bytes, list[str]]:
    player = root / "web" / "player"
    manifest = json.loads((player / "manifest.json").read_text(encoding="utf-8"))
    parts = player / "parts"
    problems = []
    listed = set(manifest)
    if len(listed) != len(manifest):
        problems.append("a part is listed twice in web/player/manifest.json")
    on_disk = {p.name for p in parts.iterdir() if p.is_file()}
    for name in sorted(on_disk - listed):
        problems.append(f"orphaned part not in the manifest: {name}")
    for name in sorted(listed - on_disk):
        problems.append(f"manifest names a missing part: {name}")
    if problems:
        return b"", problems
    return b"".join((parts / n).read_bytes() for n in manifest), []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args(argv)
    root = Path(args.root)
    data, problems = build(root)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    target = root / "web" / "packaged.html"
    if args.check:
        if not target.is_file() or target.read_bytes() != data:
            print("web/packaged.html is stale: run `uv run python scripts/build_player.py` and commit the result.",
                  file=sys.stderr)
            return 1
        print(f"ok: web/packaged.html is exactly its {len(data.splitlines())} lines of parts")
        return 0
    target.write_bytes(data)
    print(f"wrote web/packaged.html ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
