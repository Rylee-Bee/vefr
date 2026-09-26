"""Build the neutral library fixture pack (sample-world + library/) for
tests and local playtests. Neutral engine-test canon only: these books
are about nothing but the contract."""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "worlds" / "sample-world"

BOOKS = {
    "a-shelf-book": "---\ntitle: A Shelf Book\n---\nThe first page.\n\n* * *\n\nThe second page.\n",
    "a-map-note": "---\ntitle: A Map Note\nfound: map\nat: [1, 1]\nkind: note\n---\nIt lay on the ground.\n",
    "a-given-book": "---\ntitle: A Given Book\nfound: resident\nspeaker: keeper\n---\nHanded over.\n",
    "a-bell-book": "---\ntitle: A Bell Book\nfound: earned\nwhen: bell\n---\nAfter the bell.\n",
    "a-sequel": "---\ntitle: A Sequel\nfound: earned\nwhen: book:a-shelf-book\nkind: terminal\n---\nRead the first one first.\n",
}


def build(dest: Path, books: dict | None = None) -> Path:
    pack = dest / "worlds" / "library-test"
    if pack.exists():
        shutil.rmtree(pack)
    pack.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE, pack)
    lib = pack / "library"
    lib.mkdir(exist_ok=True)
    for name, text in (BOOKS if books is None else books).items():
        (lib / f"{name}.md").write_text(text, encoding="utf-8")
    return pack


if __name__ == "__main__":
    print(str(build(Path(sys.argv[1]))))
