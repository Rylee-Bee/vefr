"""story_status - which words in a pack are drafts (vefr #339).

An agent may draft a whole story, and nothing ships as canon until the
owner has read and edited it. Nothing in the engine could tell an
agent-written line from an approved one, so the only enforcement was
whoever remembered to look. This module is that gate: an **optional**
`status: draft | approved` on the five places a pack keeps words (a
voice file in both of the ways a pack names it), and
`vefr check --release` to list the drafts.

Three promises the rest of the pack contract depends on:

- **Additive and optional.** The key is absent in every pack that
  predates it, and absent means `approved`. Such a pack validates and
  reads exactly as it did before.
- **No draft mode.** A draft word plays exactly as an approved word
  does. Nothing here changes how a word is read, said or shown; it only
  changes what `vefr check --release` can say about it.
- **No new format.** Where the key sits follows one rule - a *sibling
  key on the object that already owns the words* - so no surface gets a
  wrapper object and no existing pack changes shape.

| words | `status` sits beside | in |
|---|---|---|
| a book | the other front-matter keys | `library/<id>.md` |
| a voice file | `file` / `strike` | `world.json` `voices.<id>` |
| a speaker's voice file | `voice_file` / `seeds` | `world.json` `speakers.<id>` |
| a `say` rule | `when` / `if` / `then` | `world.json` `rules[]` |
| an album sticker name | `name` / `kind` / `when` | `world.json` `album[]` |
| an item name | `name` / `light` | `world.json` `items.<id>` |

A voice file is the one surface with no front matter of its own: the
whole `.md` is the prompt the weaver sends, so a `---` block would
become words. The status therefore rides on the record that NAMES the
file, which is where `file` and `voice_file` already live.

A rule's status is on the rule, not on the `say` action, because an
action names exactly one thing to do and the woven player's rule engine
reads that action object key by key - a second key there would be one
more thing for the JS twin to hold equal with this table.

Everything here reads the pack's own files, like `blueprint.check_errors`
and `sections.errors`: no model call, no write, no clock. Every path is
built from `pack_dir` and a fixed name - no id taken from pack data ever
becomes part of a path - so a pack cannot point this reader outside
itself. `maplab.validate` runs `errors` so an unknown value is refused
like every other typed key; `vefr check --release` runs `drafts` to
print the list.
"""

from __future__ import annotations

import json
from collections import namedtuple
from pathlib import Path

# The two words a pack may write. Absent means `approved`, which is
# what every pack that predates this key already is - `library.parse_book`
# supplies that default for a book, and a JSON record without the key is
# simply not a draft.
STATUSES = ('draft', 'approved')

_CHOICES = '"draft" or "approved"'

# One draft word: which surface, which file, which line in it, and the
# label that names it to a human reading the gate's output.
Draft = namedtuple('Draft', 'surface file line label')


# ------------------------------------------------- reading the pack

def _json_packs(root: Path):
    """Every pack JSON file the words can live in, in read order.

    The flat shape keeps them in `world.json`; the acts shape keeps one
    per act. A pack that has neither says nothing here.
    """
    yield root / 'world.json'
    acts = root / 'acts'
    if acts.is_dir():
        for act in sorted(p for p in acts.iterdir() if p.is_dir()):
            yield act / 'world.json'


def _read(path: Path):
    """One pack file as text, or "" when it is not there or unreadable.

    A file this module cannot read is a file another validator already
    speaks about; naming it here too would report one mistake twice.
    """
    try:
        return path.read_text(encoding='utf-8')
    except (OSError, ValueError):
        return ''


# ------------------------------------------------- where the key sits

def _records(data: dict):
    """Every record in one pack file that may carry `status`.

    Each is `(surface, anchors, label, value)`: the anchors are the
    texts that locate the record in the file - its own id, as JSON
    writes it - so the gate can name a line as well as a file, and the
    label is what a human reads. More than one anchor per record
    because a hand-written pack spaces its JSON differently: the keyed
    form first, then the bare id.
    """
    items = data.get('items')
    if isinstance(items, dict):
        for iid, spec in items.items():
            if isinstance(spec, dict) and 'status' in spec:
                yield ('item', _anchors(iid),
                       f"item {str(iid)!r}{_titled(spec.get('name'))}",
                       spec['status'])

    voices = data.get('voices')
    if isinstance(voices, dict):
        for vkey, voice in voices.items():
            if isinstance(voice, dict) and 'status' in voice:
                yield ('voice', _anchors(vkey),
                       f"voice {str(vkey)!r}{_titled(voice.get('file'))}",
                       voice['status'])

    speakers = data.get('speakers')
    if isinstance(speakers, dict):
        for name, speaker in speakers.items():
            if isinstance(speaker, dict) and 'status' in speaker:
                # A speaker's words are its `voice_file` and its
                # `seeds`, so the file is named when there is one.
                yield ('speaker', _anchors(name),
                       f"speaker {str(name)!r}{_titled(speaker.get('voice_file'))}",
                       speaker['status'])

    rules = data.get('rules')
    if isinstance(rules, list):
        for rule in rules:
            if isinstance(rule, dict) and 'status' in rule:
                rid = rule.get('id')
                yield ('rule', _anchors(rid),
                       f"rule {str(rid)!r}", rule['status'])

    album = data.get('album')
    if isinstance(album, list):
        for sticker in album:
            if isinstance(sticker, dict) and 'status' in sticker:
                sid = sticker.get('id')
                yield ('sticker', _anchors(sid),
                       f"sticker {str(sid)!r}{_titled(sticker.get('name'))}",
                       sticker['status'])


def _anchors(identifier) -> tuple:
    """The texts that find a record: its id as a key, then as a value.

    A record under a key (`"torch": {`) and one that carries its id
    (`"id": "draft-greet"`) are written differently, and a pack may
    space either with or without a space after the colon. The bare id is
    the last resort: it is the anchor that always exists, and the line
    it names is still the record's neighbourhood.
    """
    if not isinstance(identifier, str):
        return ()
    quoted = json.dumps(identifier)
    return (f'{quoted}:', f'"id": {quoted}', quoted)


def _titled(text) -> str:
    """The `- <what it calls itself>` half of a label, or ""."""
    return f" - {text}" if isinstance(text, str) and text else ""


def _books(pack: Path):
    """Every book in the pack's library as `(path, parsed book, line)`.

    The value comes from the Library's own parser, so a book is read the
    one way the player reads it. The line is found by scanning the front
    matter for the key, which is exact: front matter is one key per line
    by construction.
    """
    from .library import parse_book

    folder = pack / 'library'
    if not folder.is_dir():
        return
    for path in sorted(folder.glob('*.md')):
        if path.name.lower() == 'readme.md':
            continue
        text = _read(path)
        if not text:
            continue
        book = parse_book(text, path.stem)
        yield path, book, _front_line(text)


def _front_line(text: str):
    """The 1-based line the front matter's `status:` is on, or None."""
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith('status:'):
            return number
    return None


# ------------------------------------------------- lines

def _line_of(text: str, index: int) -> int:
    return text.count('\n', 0, index) + 1


def _start(text: str, anchors: tuple) -> int:
    """Where a record begins in the file: the first anchor that is there.

    -1 when none of them is, which happens only for a record whose id
    the file does not spell the way JSON would (an author who wrote
    the id by hand in an odd encoding).
    """
    for anchor in anchors:
        at = text.find(anchor)
        if at >= 0:
            return at
    return -1


def _locate(text: str, start: int, stops: list[int]) -> int:
    """The line a record's `status` sits on, or the record's own line.

    A pack is hand-written JSON, so the record is found by the anchor
    its own id gives and the status is the first `"status"` key between
    that anchor and the next record's - the search is bounded so one
    record's key can never be reported on another's line. A record
    written without a visible key (or on one line) answers with the
    anchor's own line, which still names where the record is.
    """
    if start < 0:
        return 1
    end = min((s for s in stops if s > start), default=len(text))
    found = text.find('"status"', start, end)
    return _line_of(text, found if found >= 0 else start)


def _stops(text: str, records) -> list[int]:
    """Where every record of one file begins: the anchors bound a search.

    One offset per record, not one per anchor: two anchors of the same
    record sit a few characters apart, and the later one would cut the
    earlier record's own search off at its own first line.
    """
    return sorted(at for at in (_start(text, anchors)
                                for _, anchors, _, _ in records) if at >= 0)


# ------------------------------------------------- the two questions

def _scan(pack):
    """Every `(draft_or_None, error)` this pack carries, in read order."""
    root = Path(pack)
    for path in _json_packs(root):
        text = _read(path)
        if not text:
            continue
        try:
            data = json.loads(text)
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        rel = str(path.relative_to(root))
        records = list(_records(data))
        stops = _stops(text, records)
        for surface, anchors, label, value in records:
            if value == 'draft':
                yield Draft(surface, rel,
                            _locate(text, _start(text, anchors), stops), label)
            elif value not in STATUSES:
                yield f"{rel}: {label} status must be {_CHOICES}, not {value!r}"

    for path, book, line in _books(root):
        rel = str(path.relative_to(root))
        label = f"book {book['id']!r}{_titled(book.get('title'))}"
        status = book.get('status')
        if status == 'draft':
            yield Draft('book', rel, line or 1, label)
        elif status not in STATUSES:
            yield f"{rel}: {label} status must be {_CHOICES}, not {status!r}"


def drafts(pack) -> list[Draft]:
    """Every draft word in the pack, in file and line order.

    Empty is the ordinary answer: a pack that writes no `status` has no
    drafts, and says nothing.
    """
    found = [d for d in _scan(pack) if isinstance(d, Draft)]
    return sorted(found, key=lambda d: (d.file, d.line, d.label))


def errors(pack) -> list[str]:
    """Every way a `status` is written that means nothing.

    An unknown value is refused here rather than at play, and named the
    way every other typed-key error is: the file, the record, and the
    two words it may be.
    """
    return [e for e in _scan(pack) if isinstance(e, str)]


def report(pack) -> list[str]:
    """The sentences `vefr check --release` prints, drafts and header.

    A pack with no drafts gets one short line and nothing else, so the
    gate is silent in the common case and says something only when a
    human has to act.
    """
    return format_report(drafts(pack))


def format_report(found) -> list[str]:
    """The same sentences for drafts the caller already has.

    The CLI needs the list twice - to print it, and to decide the exit
    code - and a pack is read once.
    """
    found = list(found)
    if not found:
        return ['no drafts - every word in this pack is approved']
    lines = [f"{len(found)} draft word(s):"]
    lines += [f"  {d.file}:{d.line}  {d.label} is a draft" for d in found]
    return lines