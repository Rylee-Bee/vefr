"""VEFR as a Worlds room (Play-Nice `room/0`), offering its Library.

Worlds gathers every connected room's library (Play-Nice `library/0`) and
shows each keeper's shelves side by side. VEFR's keeper is Fróði, and its
shelves are the studio's own books in web/library/ (never a world's books:
those belong to the world's author).

VEFR has nothing that needs the owner and no actions, so cards is one
Library card, needs-you and actions are empty, and every action call is a
labelled refusal. The only extras are `library` and `art` (an allow-list of
three pictures).

Switched off unless VEFR_ROOM_TOKEN is set; every /room request must carry
it as a bearer token. The token never appears in a response or a log.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, JSONResponse

from .library import load_shelf, studio_shelf_dir
from .paths import app_home, resolve_under
from .replies import RoomCard, RoomDescriptor

router = APIRouter()

KEEPER = {"id": "frodi", "name": "Fróði", "look": "vefr"}
SHELVES = [
    {"id": "how-games-are-made", "name": "How games are made", "look": "vefr", "cover": "library",
     "blurb": "The studio handbook: the seven stages every game passes through."},
    {"id": "how-vefr-works", "name": "How VEFR works", "look": "vefr", "cover": "frodi-ladder",
     "blurb": "Real words for what's inside: maps, layers, stories, pictures, saving, and the engine."},
]
ART = {"frodi": "residents/frodi.webp", "frodi-ladder": "poses/frodi-library-ladder.webp",
       "library": "poses/library-empty.webp"}
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
KIND_HEADINGS = (("## words to know", "words"), ("## under the hood", "technical"), ("## in ", "voice"))


class _Refused(Exception):
    def __init__(self, status: int, error: str):
        self.status, self.error = status, error


def _require_token(request: Request) -> None:
    expected = os.environ.get("VEFR_ROOM_TOKEN", "")
    if not expected:
        raise _Refused(503, "VEFR's room is switched off here.")
    got = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not secrets.compare_digest(got, expected):
        raise _Refused(401, "unauthorized")


def refused_handler(_request: Request, exc: _Refused) -> JSONResponse:
    return JSONResponse({"error": exc.error}, status_code=exc.status)


guard = [Depends(_require_token)]


def _iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _commit() -> str | None:
    if os.environ.get("VEFR_COMMIT"):
        return os.environ["VEFR_COMMIT"]
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=app_home(), capture_output=True,
                             text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return (out.stdout.strip() or None) if out.returncode == 0 else None


def _version() -> str:
    try:
        from importlib.metadata import version
        return version("vefr")
    except Exception:  # noqa: BLE001 - a dev checkout may not be installed
        return "unknown"


def _updated_at() -> datetime | None:
    files = list(studio_shelf_dir().glob("*.md")) + [_glossary_path()]
    times = [f.stat().st_mtime for f in files if f.is_file()]
    return datetime.fromtimestamp(max(times), timezone.utc) if times else None


def _glossary_path() -> Path:
    return app_home() / "web" / "library" / "glossary.json"


def load_glossary() -> dict:
    """web/library/glossary.json: every real word the Library, Fróði and the room teach."""
    return json.loads(_glossary_path().read_text(encoding="utf-8"))


def _lookup(glossary: dict, word: str) -> str | None:
    w = " ".join(word.lower().split())
    if w in glossary:
        return w
    return next((k for k, e in glossary.items() if w in e.get("also", [])), None)


def words_page(pages: list[str], glossary: dict) -> str | None:
    """The book's own 'Words to know', built from the words it italicises,
    so the page and the glossary can never drift apart."""
    seen: list[str] = []
    for page in pages:
        text = re.sub(r"```.*?```", "", page, flags=re.S)
        text = re.sub(r"\*\*[^*]+\*\*", "", " ".join(text.split()))
        for word in re.findall(r"\*([^*]+)\*", text):
            key = _lookup(glossary, word)
            if key and key not in seen:
                seen.append(key)
    if not seen:
        return None
    lines = []
    for key in seen:
        e = glossary[key]
        line = f"- *{key}*: {e['plain']}"
        if e.get("vefr"):
            line += f" (In VEFR: {e['vefr']}.)"
        lines.append(line)
    return "\n".join(lines)[:8000]


def _page(text: str) -> dict:
    first = text.lstrip().split("\n", 1)[0].strip().lower()
    for prefix, kind in KIND_HEADINGS:
        if first.startswith(prefix):
            page = {"kind": kind, "text": text[:8000]}
            if kind == "voice":
                page["voice"] = text.lstrip().split("\n", 1)[0].strip()[len("## In "):].removesuffix("'s words").strip()[:60]
            return page
    return {"kind": "plain", "text": text[:8000]}


def library_document() -> dict:
    glossary = load_glossary()
    shelf_ids = {s["id"] for s in SHELVES}
    books = []
    for order, b in enumerate(load_shelf(studio_shelf_dir())):
        extra = b.get("extra") or {}
        shelf, short = str(extra.get("shelf", "")), str(extra.get("short", "")).strip()
        if shelf not in shelf_ids or not SLUG.match(b["id"]) or not b["title"] or not short:
            continue
        pages = [_page(p) for p in b["pages"] if p.strip()][:39]
        if not pages or pages[0]["kind"] != "plain":
            continue
        words = words_page(b["pages"], glossary) if not any(p["kind"] == "words" for p in pages) else None
        if words:
            pages.append({"kind": "words", "text": words})
        book = {"id": b["id"], "shelf": shelf, "title": b["title"][:120], "short": short[:300],
                "order": order, "pages": pages, "link": "/#library"}
        if extra.get("source"):
            book["source"] = f"vefr: {extra['source']}"[:300]
        books.append(book)
    stamp = _updated_at() or _now()
    return {"contract": "library/0", "generated_at": _iso(stamp), "keeper": dict(KEEPER),
            "shelves": [dict(s) for s in SHELVES], "books": books, "glossary": contract_glossary(glossary)}


def contract_glossary(glossary: dict) -> dict:
    """The tap-to-learn words in library 1.1.0's shape (VEFR's `vefr` name is `local`)."""
    out = {}
    for key, e in glossary.items():
        entry = {"plain": e["plain"][:300]}
        if e.get("vefr"):
            entry["local"] = e["vefr"][:80]
        if e.get("also"):
            entry["also"] = [a[:60] for a in e["also"]][:20]
        out[key] = entry
    return out


def _status() -> str:
    try:
        if not library_document()["books"]:
            return "unhealthy"
    except (OSError, ValueError):
        return "unhealthy"
    return "healthy" if _commit() else "unknown"


@router.get("/room", dependencies=guard, response_model=RoomDescriptor)
def room() -> dict:
    t = _updated_at()
    return {"contract": "room/0", "id": "vefr", "name": "VEFR", "icon": "tree",
            "version": _version(), "commit": _commit(), "status": _status(),
            "offers": ["art", "library", "views"], "updated_at": _iso(t) if t else None}


@router.get("/room/cards", dependencies=guard, response_model=list[RoomCard])
def cards() -> list[dict]:
    try:
        doc = library_document()
    except (OSError, ValueError):
        return []
    n, t = len(doc["books"]), _updated_at() or _now()
    return [{"id": "library", "title": "Fróði's Library",
             "body": f"{n} books on {len(doc['shelves'])} shelves: how games are made, and how VEFR works.",
             "link": "/#library", "lane": "work", "tone": "update",
             "freshness": {"observed_at": _iso(t), "stale_after_s": 30 * 86400}}]


@router.get("/room/needs-you", dependencies=guard)
def needs_you() -> list[dict]:
    return []


@router.get("/room/actions", dependencies=guard)
def actions() -> list[dict]:
    return []


@router.post("/room/actions/{action_id}", dependencies=guard)
def run_action(action_id: str, request: Request) -> JSONResponse:
    ok_key = bool(request.headers.get("idempotency-key", ""))
    summary = "There's no action with that name." if ok_key else "An Idempotency-Key header is required."
    return JSONResponse({"action_id": action_id[:100], "ok": False, "summary": summary, "changed": [],
                         "at": _iso(_now())}, status_code=404 if ok_key else 400)


@router.get("/room/library", dependencies=guard)
def library() -> JSONResponse:
    try:
        return JSONResponse(library_document())
    except (OSError, ValueError):
        return JSONResponse({"error": "The library can't be read right now."}, status_code=503)


@router.get("/room/views/stickers", dependencies=guard)
def stickers_view() -> JSONResponse:
    """VEFR's page for the Worlds sticker album (Play-Nice stickers/0)."""
    from . import achievements
    try:
        return JSONResponse(achievements.room_view())
    except (OSError, ValueError):
        return JSONResponse({"error": "The sticker book can't be read right now."}, status_code=503)


@router.get("/room/art/{name}.webp", dependencies=guard)
def art(name: str):
    # `name` is a request value that becomes a path segment. Both
    # allow-lists below already refuse an unknown id, and resolve_under
    # is the second layer over the join itself: a sticker's id is
    # pasted into a filename, so a "../" in it must not walk out of
    # web/art/ even if the membership test were ever removed.
    if name.startswith("stickers-"):          # a sticker's art, only for ids the book defines
        from . import achievements
        sid = name[len("stickers-"):]
        known = {d["id"] for d in achievements.definitions()}
        try:
            path = resolve_under(app_home() / "web" / "art" / "stickers", f"{sid}.webp")
        except ValueError:
            path = None
        if sid in known and path is not None and path.is_file():
            return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "private, max-age=3600"})
        return JSONResponse({"error": "No such picture."}, status_code=404)
    rel = ART.get(name)
    try:
        path = resolve_under(app_home() / "web" / "art", rel) if rel else None
    except ValueError:
        path = None
    if not path or not path.is_file():
        return JSONResponse({"error": "No such picture."}, status_code=404)
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "private, max-age=3600"})
