#!/usr/bin/env python3
"""import_art.py: bring Rylee's generated art into web/art/ as small, credited game-size files.

  uv run --with pillow python tools/art/import_art.py [--media DIR] [--out web/art]

The originals (1024 px and up, 600 MB in all) live in the Media Archive. By
default this tool reads them from an archive export (`media export --project
vefr`), resolved via `VEFR_ART_MEDIA` or `MEDIA_ARCHIVE_HOME/exports/vefr`,
falling back to the legacy shared `media_files/designs/vefr/art/` until the
migration retires that path. This tool writes
game-size WebP derivatives into `web/art/` and records every file in
`web/art/MANIFEST.json`: where it came from, how big it is, and who made it. A file's credit
says "Wan 2.7 Image Pro" only when a Wan record in the source folder names that file;
otherwise it says the tool was not recorded. Nothing is ever credited by guess.

Idempotent: running it again rewrites the same files. Existing art is adopted into the
manifest (without a source) the first time, so `tests/test_art_manifest.py` can demand a
credit for every file under web/art/.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from PIL import Image

SRC_ROOT = "designs/vefr/art"
OWNERS = "Rylee and Claude"
ADOPTED = "Owner's studio art; provenance is in web/art/README.md"
# (source dir under SRC_ROOT, destination dir under web/art, edge px)
PLAN = [
    ("stickers", "stickers", 192, None),            # only the ones web/art lacks
    ("delve/items", "delve/items", 128, None),
    ("delve/spells", "delve/spells", 128, None),
    ("delve/town", "delve/town", 128, None),
    ("delve/tiles", "delve/tiles", 96, None),
    ("surface-tiles", "surfaces", 96, None),
]
THEMES = "themes"


def edge_for_theme_file(name: str) -> int:
    return 96 if name.startswith("tile-") else 128


def resolve_media(root: Path) -> Path:
    """Where the source art lives.

    Preferred: a Media Archive export (`media export --project vefr`), so this
    tool stops depending on the shared, mutable media library. Set
    ``VEFR_ART_MEDIA`` to the export directory, or ``MEDIA_ARCHIVE_HOME`` and we
    use ``<that>/exports/vefr``. Falls back to the legacy sibling
    ``media_files`` until the archive migration retires that path.
    """
    candidates: list[Path] = []
    if os.environ.get("VEFR_ART_MEDIA"):
        candidates.append(Path(os.environ["VEFR_ART_MEDIA"]).expanduser())
    if os.environ.get("MEDIA_ARCHIVE_HOME"):
        candidates.append(Path(os.environ["MEDIA_ARCHIVE_HOME"]).expanduser()
                         / "exports" / "vefr")
    # Archive is a sibling of the estate root (`<code>/media-archive`), i.e. two
    # levels up from this repo. Discovered, not hard-coded to a home dir.
    candidates.append(root.parent.parent / "media-archive" / "exports" / "vefr")
    for candidate in candidates:
        if (candidate / SRC_ROOT).is_dir():
            return candidate.resolve()
    return root.parent / "media_files"


def wan_models(src_dir: Path) -> dict:
    """{file name: model} from every *.wan-prompts.json beside the pictures."""
    out = {}
    for p in src_dir.glob("*.wan-prompts.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(data, dict):
            for fname, rec in data.items():
                if isinstance(rec, dict) and rec.get("model"):
                    out[fname] = rec["model"]
    return out


def credit_for(model) -> str:
    if model and "wan" in model.lower():
        return f"{OWNERS}; Wan 2.7 Image Pro"
    return f"{OWNERS}; tool not recorded in the source folder"


def save_webp(src: Path, dest: Path, edge: int) -> tuple[int, int]:
    im = Image.open(src)
    im = im.convert("RGBA" if "A" in im.getbands() or im.mode == "P" else "RGB")
    im = im.resize((edge, edge), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "WEBP", quality=82, method=6)
    return im.size


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--media", default=None, help="the media_files folder")
    ap.add_argument("--out", default="web/art")
    a = ap.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    media = Path(a.media).resolve() if a.media else resolve_media(root)
    out = (root / a.out) if not Path(a.out).is_absolute() else Path(a.out)
    base = media / SRC_ROOT
    if not base.is_dir():
        print(f"import_art: no art library at {base}", file=sys.stderr)
        return 2

    mpath = out / "MANIFEST.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() else {"version": 1, "files": {}}
    files = manifest["files"]

    # adopt what is already here
    for p in sorted(out.rglob("*")):
        if p.suffix.lower() in {".webp", ".png", ".svg", ".jpg"} and p.is_file():
            rel = p.relative_to(out).as_posix()
            files.setdefault(rel, {"source": None, "credit": ADOPTED})

    made = 0

    def put(src: Path, rel: str, edge: int, models: dict) -> None:
        nonlocal made
        w, h = save_webp(src, out / rel, edge)
        files[rel] = {"source": f"{SRC_ROOT}/{src.relative_to(base).as_posix()}",
                      "credit": credit_for(models.get(src.name)), "size": f"{w}x{h}"}
        made += 1

    for srcd, destd, edge, _ in PLAN:
        d = base / srcd
        models = wan_models(d)
        for src in sorted(d.glob("*.png")):
            rel = f"{destd}/{src.stem}.webp"
            if srcd == "stickers" and (out / rel).exists() and files.get(rel, {}).get("source") is None:
                continue                      # already in the repo: keep the existing picture
            put(src, rel, edge, models)

    for tdir in sorted((base / THEMES).iterdir()):
        if not tdir.is_dir():
            continue
        models = wan_models(tdir)
        for src in sorted(tdir.glob("*.png")):
            put(src, f"themes/{tdir.name}/{src.stem}.webp", edge_for_theme_file(src.name), models)

    mpath.write_text(json.dumps({"version": 1, "files": dict(sorted(files.items()))},
                                indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"import_art: wrote {made} files; manifest lists {len(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
