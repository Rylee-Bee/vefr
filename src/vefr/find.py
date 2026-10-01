"""`vefr find` - a local, read-only search of a pack and its journal.

A search tool that never touches the pack: the markdown lines and the
journal entries are copied into an FTS5 virtual table that lives in
:memory: for the length of one run, queried once, and dropped - no
file is created, moved or rewritten, no HTTP route exists, and no
model is called. The query is plain words: split on whitespace, each
term ANDed - never a query language, and a user's raw string is never
handed to FTS5 MATCH syntax unescaped (it is treated as terms).

Hits print as `path:line [source] excerpt`, sorted by (path, line) so
the same input always prints the same order. A search that finds
nothing prints UNKNOWN and still succeeds; a missing pack is refused
by the caller (cli.cmd_find) instead.
"""

import os
import sqlite3
from pathlib import Path
from typing import NamedTuple

from . import journal as journal_mod

# An excerpt is a line, not a paragraph: collapse whitespace, cap it.
EXCERPT_MAX = 120

# ---- sources ----
# NOTE: the search set this settled on (plan: logbok/ledger/voices/
# library, widening to world-tree and the acts tree only where cheap
# and natural - both are, so both are in):
#
#   logbok.md, ledger.md, world-tree.md    -> logbok, ledger, tree
#   voices/*.md, library/*.md              -> voices, library
#   acts/**/*.md                           -> acts   (recursive: region
#       trees, their voices, their maps; the source class follows the
#       glob that found the file)
#   the session journal (journal.entries()) -> journal
#
# Deliberately outside the set: top-level map.md is a character grid,
# not prose - its lines carry no word tokens, so it would cost without
# ever matching; assets/** holds third-party docs and licenses, not
# world text; handbok.md is derived and was not in the plan's set.
# Nothing outside the pack and the journal is ever read.
TOP_FILES = (
    ('logbok.md', 'logbok'),
    ('ledger.md', 'ledger'),
    ('world-tree.md', 'tree'),
)
DIR_TREES = (
    ('voices', 'voices', '*.md'),
    ('library', 'library', '*.md'),
    ('acts', 'acts', '**/*.md'),
)


class Hit(NamedTuple):
    """One match: where it is, and one short line of what it says."""

    path: str    # display path: relative to the cwd when inside it
    line: int    # 1-based markdown line; 1-based entry ordinal for the journal
    source: str  # logbok | ledger | tree | voices | library | acts | journal
    excerpt: str


# ---- collecting the documents ----

def _display(path: Path) -> str:
    """A path to print: relative to the cwd when it lives inside it."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _excerpt(text: str) -> str:
    """One short line: whitespace collapsed, hard-capped."""
    collapsed = ' '.join(text.split())
    if len(collapsed) > EXCERPT_MAX:
        return collapsed[:EXCERPT_MAX - 3] + '...'
    return collapsed


def _add_file(path: Path, source: str, docs: list[dict]) -> None:
    """Index every non-blank line of one markdown file, in file order.

    A file that will not read (absent, unreadable) is skipped, never
    raised: the search is a look-around, and one bad file must not
    fail the whole run - the same tolerance journal.entries() has.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return
    if not text:
        return
    shown = _display(path)
    for n, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            docs.append({'path': shown, 'line': n, 'source': source,
                         'text': line})


def _inside_pack(pack_real: str, path: Path) -> bool:
    """True when the REAL path of `path` is inside the pack's real path.

    NOTE: a symlink in a downloaded pack must not make `vefr find` index and print a file
    outside it (for example a link named library/notes.md pointing at a private file).
    """
    real = os.path.realpath(path)
    return real.startswith(pack_real + os.sep)


def _pack_docs(pack: Path) -> list[dict]:
    """The pack's markdown (TOP_FILES, DIR_TREES), a stable walk."""
    docs: list[dict] = []
    pack_real = os.path.realpath(pack)
    for name, source in TOP_FILES:
        if _inside_pack(pack_real, pack / name):
            _add_file(pack / name, source, docs)
    for dirname, source, pattern in DIR_TREES:
        base = pack / dirname
        if not base.is_dir() or not _inside_pack(pack_real, base):
            continue
        # sorted(): the glob's own order is the filesystem's, which is
        # not guaranteed - deterministic output starts here.
        for f in sorted(base.glob(pattern)):
            if f.is_file() and _inside_pack(pack_real, f):
                _add_file(f, source, docs)
    return docs


def _journal_docs() -> list[dict]:
    """The session journal, through the public read (entries()).

    The journal is a JSON list of dicts, not lines: `line` here is the
    entry's 1-based position in that list. An absent or unreadable
    journal reads as empty - entries()'s own contract, unchanged.
    NOTE: scoping stays exactly what journal.entries() resolves (the
    default session, world-scoped); --pack picks the markdown, and
    was not wired into the journal path - the public read is the seam
    the plan named.
    """
    docs: list[dict] = []
    shown = _display(journal_mod.journal_path())
    for i, entry in enumerate(journal_mod.entries(), start=1):
        if not isinstance(entry, dict):
            continue
        body = ' '.join(str(v) for v in entry.values())
        if body.strip():
            docs.append({'path': shown, 'line': i, 'source': 'journal',
                         'text': body})
    return docs


# ---- the query ----

def _terms(query: str) -> list[str]:
    """The query as FTS5 terms: whitespace-split, quote-stripped.

    NOTE: the restrictive reading of "keep the query simple": each
    token loses any `"` (a raw quote would end the phrase early -
    fts5's "unterminated string"), and a token with no letter or
    digit at all is dropped (an empty or symbol-only phrase is an
    fts5 syntax error). Every surviving term is then wrapped in
    quotes and ANDed, so operators are never passed through: an input
    containing AND / OR / NEAR / * is searched as plain words, never
    as FTS5 MATCH syntax.
    """
    terms: list[str] = []
    for token in str(query).split():
        token = token.replace('"', '')
        if any(ch.isalnum() for ch in token):
            terms.append(token)
    return terms


# ---- the search ----

def search(query: str, pack: Path) -> list[Hit]:
    """Every hit for `query` in `pack` + the journal, by (path, line).

    Read-only end to end: the FTS5 index is built in :memory: per run
    and closed before returning - nothing on disk is created or
    touched. No terms (empty or symbol-only input) matches nothing;
    an empty MATCH is an fts5 syntax error, so it is never issued.
    """
    terms = _terms(query)
    if not terms:
        return []
    docs = _pack_docs(pack) + _journal_docs()
    if not docs:
        return []
    conn = sqlite3.connect(':memory:')
    try:
        conn.execute('CREATE VIRTUAL TABLE hits USING fts5(body)')
        conn.executemany('INSERT INTO hits(body) VALUES (?)',
                         [(d['text'],) for d in docs])
        match = ' AND '.join(f'"{t}"' for t in terms)
        # rowid order is insertion order, so the result set is stable;
        # the final sort below is what the caller sees.
        rowids = [r[0] for r in conn.execute(
            'SELECT rowid FROM hits WHERE hits MATCH ? ORDER BY rowid',
            (match,))]
    finally:
        conn.close()
    hits = [Hit(docs[i - 1]['path'], docs[i - 1]['line'],
                docs[i - 1]['source'], _excerpt(docs[i - 1]['text']))
            for i in rowids]
    return sorted(hits, key=lambda h: (h.path, h.line))
