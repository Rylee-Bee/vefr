"""Declared reply shapes: a route can't quietly drop or add a field."""
import pytest
from pydantic import ValidationError

from vefr.main import app
from vefr.replies import LibraryReply

DECLARED = {"/api/library", "/api/teach", "/api/teach/mode", "/api/teach/recognize", "/api/teach/got-it", "/room", "/room/cards"}

BOOK = {"id": "b", "title": "B", "kind": "book", "found": "shelf", "at": None, "speaker": "",
        "when": "", "pages": ["p"], "found_words": "on the shelf", "shelf": "how-vefr-works"}


def _routes(routes):
    for r in routes:
        inner = getattr(r, "original_router", None)  # FastAPI 0.141 wraps included routers
        yield from _routes(inner.routes) if inner is not None else [r]


def test_these_routes_keep_a_declared_shape():
    declared = {r.path for r in _routes(app.routes) if getattr(r, "response_model", None) is not None}
    assert DECLARED <= declared, sorted(DECLARED - declared)


def test_a_book_without_its_shelf_is_rejected():
    """The 2026-09-27 bug: /api/library dropped `shelf`; now that can't pass."""
    book = {k: v for k, v in BOOK.items() if k != "shelf"}
    with pytest.raises(ValidationError, match="shelf"):
        LibraryReply.model_validate({"world": "", "books": [], "studio": [book]})


def test_an_unexpected_field_is_rejected():
    with pytest.raises(ValidationError, match="extra"):
        LibraryReply.model_validate({"world": "", "books": [], "studio": [{**BOOK, "surprise": 1}]})
