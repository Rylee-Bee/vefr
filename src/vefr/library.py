"""The Library - books and notes a world keeps, and the studio's own shelf.

A pack may carry a `library/` folder of markdown books, one file each:

    worlds/<name>/library/a-miners-note.md

    ---
    title: A Miner's Note
    found: map            # shelf | map | resident | earned  (default: shelf)
    at: [7, 4]            # map: the tile the book lies on (x, y)
    region: town          # map: which region (default: town)
    speaker: keeper       # resident: the voice that hands it over
    when: bell            # earned: what has to happen first
    kind: note            # book | note | terminal  (default: book)
    ---
    The first page.

    * * *

    The second page.

A line holding only `* * *` starts a new page. The author writes every
word; the engine only reads, checks and shows them. No model call ever
touches a book (the Library is a deterministic surface, like export).

The engine's own shelf lives in `web/library/` in the same format: the
studio handbook, how games are made. It belongs to no world.

Earned books name the moment that unlocks them (`when`). The events the
engine knows are in EARNED_EVENTS; `book:<id>` means "after reading that
book". The finding itself happens in play (a later slice); this module
defines the contract, loads it, and validates it.
"""

from __future__ import annotations

import re
from pathlib import Path

FOUND_KINDS = ("shelf", "map", "resident", "earned")
BOOK_KINDS = ("book", "note", "terminal")
# Moments an earned book can wait for. `book:<id>` is checked separately.
EARNED_EVENTS = ("bell", "first-visit", "act-complete", "rumor-verified")
PAGE_BREAK = "* * *"

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)
_AT_RE = re.compile(r"^\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]$")


def studio_shelf_dir() -> Path:
    """The engine's own shelf: web/library/ (shipped in the image with web/)."""
    from .paths import app_home
    return app_home() / "web" / "library"


def parse_book(text: str, book_id: str) -> dict:
    """Parse one book file into its canonical shape.

    Unknown front-matter keys are kept under `extra` so a pack can carry
    notes for itself without the engine rejecting them. Values are plain
    strings except `at`, which becomes [x, y] when it reads as two ints.
    """
    meta: dict[str, object] = {}
    body = text
    m = _FRONT_RE.match(text.replace("\r\n", "\n"))
    if m:
        for line in m.group(1).splitlines():
            if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key, value = key.strip(), value.strip()
            if key != "title":
                # an inline "  # comment" after a value is a note, not data
                value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
            meta[key] = value
        body = m.group(2)

    at = meta.get("at")
    if isinstance(at, str):
        am = _AT_RE.match(at)
        at = [int(am.group(1)), int(am.group(2))] if am else at

    pages = [p.strip() for p in re.split(r"(?m)^\s*\*\s\*\s\*\s*$", body)]
    known = {"title", "found", "at", "region", "speaker", "when", "kind", "act"}
    return {
        "id": book_id,
        "title": str(meta.get("title", "")).strip(),
        "found": str(meta.get("found", "shelf")).strip() or "shelf",
        "at": at,
        "region": str(meta.get("region", "town")).strip() or "town",
        "act": str(meta.get("act", "")).strip(),
        "speaker": str(meta.get("speaker", "")).strip(),
        "when": str(meta.get("when", "")).strip(),
        "kind": str(meta.get("kind", "book")).strip() or "book",
        "pages": pages,
        "extra": {k: v for k, v in meta.items() if k not in known},
    }


def load_shelf(folder: Path) -> list[dict]:
    """Every *.md book in a folder, in filename order. Missing folder = []."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    books = []
    for f in sorted(folder.glob("*.md")):
        if f.name.lower() == "readme.md":
            continue
        books.append(parse_book(f.read_text(encoding="utf-8"), f.stem))
    return books


def load_library(pack: Path) -> list[dict]:
    """A pack's books: worlds/<name>/library/*.md."""
    return load_shelf(Path(pack) / "library")


def _walkable(town: dict, x: int, y: int) -> bool:
    m = town.get("map") or []
    if y < 0 or y >= len(m) or x < 0 or x >= len(m[0]):
        return False
    entry = (town.get("legend") or {}).get(m[y][x], {})
    if isinstance(entry.get("solid"), bool):
        return entry["solid"] is False
    return m[y][x] not in "#~"


def validate_books(books: list[dict], *, town: dict | None = None,
                   speakers: object = None) -> list[str]:
    """Every contract check for a shelf. Returns problems (empty = good).

    `town` is the validator's town block (map + legend) for map books;
    `speakers` is the act's speakers (a dict or a list of names).
    """
    errors: list[str] = []
    ids = {b["id"] for b in books}
    if isinstance(speakers, dict):
        speaker_names = set(speakers)
    elif isinstance(speakers, list):
        speaker_names = {s if isinstance(s, str) else s.get("name", s.get("id", "")) for s in speakers}
    else:
        speaker_names = set()

    for b in books:
        where = f"library book '{b['id']}'"
        if not _ID_RE.match(b["id"]):
            errors.append(f"{where}: file names are lowercase letters, digits and dashes")
        if not b["title"]:
            errors.append(f"{where}: needs a title")
        if not b["pages"] or not all(p for p in b["pages"]):
            errors.append(f"{where}: every page needs words (check for an empty page around '* * *')")
        if b["kind"] not in BOOK_KINDS:
            errors.append(f"{where}: kind must be one of {', '.join(BOOK_KINDS)}")
        found = b["found"]
        if found not in FOUND_KINDS:
            errors.append(f"{where}: found must be one of {', '.join(FOUND_KINDS)}")
            continue
        if found == "map":
            at = b["at"]
            if not (isinstance(at, list) and len(at) == 2):
                errors.append(f"{where}: a map book needs at: [x, y]")
            elif b["region"] == "town" and town is not None and not _walkable(town, at[0], at[1]):
                errors.append(f"{where}: at {at} is off the map or not walkable ground")
        elif found == "resident":
            if not b["speaker"]:
                errors.append(f"{where}: a given book needs speaker: <who hands it over>")
            elif speaker_names and b["speaker"] not in speaker_names:
                errors.append(f"{where}: speaker '{b['speaker']}' is not one of this act's residents")
        elif found == "earned":
            when = b["when"]
            if when.startswith("book:"):
                if when[5:] not in ids:
                    errors.append(f"{where}: when '{when}' names a book this library doesn't have")
            elif when not in EARNED_EVENTS:
                errors.append(
                    f"{where}: when must be one of {', '.join(EARNED_EVENTS)} or book:<id>")
    return errors


def found_words(book: dict) -> str:
    """How a book is found, in plain words (the studio shows this)."""
    f = book.get("found")
    if f == "map":
        at = book.get("at")
        return f"lies on the map at {at[0]}, {at[1]}" if isinstance(at, list) and len(at) == 2 else "lies on the map"
    if f == "resident":
        return f"given by {book.get('speaker') or 'a resident'}"
    if f == "earned":
        when = book.get("when", "")
        if when.startswith("book:"):
            return f"earned after reading '{when[5:]}'"
        return {"bell": "earned when the bell rings", "first-visit": "earned on the first visit",
                "act-complete": "earned when the act is done",
                "rumor-verified": "earned when a rumor is proven true"}.get(when, "earned")
    return "on the shelf from the start"
