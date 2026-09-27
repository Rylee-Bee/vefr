"""Declared reply shapes for the studio's routes.

A route with `response_model=` must return every required field, so a route that
forgets one fails loudly in tests instead of quietly dropping it (on 2026-09-27
/api/library dropped each book's `shelf` and every book fell onto one shelf; only
the live site showed it). Extra keys are forbidden, so the shape can't drift either.

Start with the routes that broke; add a model when you touch a route.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Reply(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- /api/library ------------------------------------------------------------

class LibraryBook(Reply):
    id: str
    title: str
    kind: str
    found: str
    at: list[int] | str | None
    speaker: str
    when: str
    pages: list[str]
    found_words: str
    shelf: str


class LibraryReply(Reply):
    world: str
    books: list[LibraryBook]
    studio: list[LibraryBook]


# --- /api/teach --------------------------------------------------------------

class TeachCard(Reply):
    term: str
    stage: Literal["first", "again"]
    plain: str
    why: str
    context: str
    local: str | None = None
    first_context: str | None = None


class TeachReply(Reply):
    teach: TeachCard | None
    why_not: str


class GotItReply(Reply):
    term: str
    stage: Literal["first", "again", "familiar"]
    got_it: int


class TeachConcept(Reply):
    group: str
    stage: Literal["new", "first", "again", "familiar"]
    offered: int
    got_it: int
    first_context: str


class TeachState(Reply):
    concepts: dict[str, TeachConcept]
    mode: Literal["build", "tips", "off"] | None = None   # Worlds' setting, when connected


class ModeReply(Reply):
    mode: Literal["build", "tips", "off"]
    shared: bool          # True when Worlds took it (one switch across projects)


# --- /room (Play-Nice room/0) --------------------------------------------------

class RoomDescriptor(Reply):
    contract: Literal["room/0"]
    id: str
    name: str
    icon: str
    version: str
    commit: str | None
    status: Literal["healthy", "degraded", "unhealthy", "unknown"]
    offers: list[str]
    updated_at: str | None


class Freshness(Reply):
    observed_at: str
    stale_after_s: int


class RoomCard(Reply):
    id: str
    title: str
    body: str
    link: str
    lane: Literal["personal", "work"]
    tone: Literal["good_news", "update", "when_ready"] | None = None
    freshness: Freshness
