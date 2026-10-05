"""stamps - hand-painted rooms as data, and the reader that vets them.

ADR 0013. A stamp is one small room drawn by hand and kept as JSON at
`stamps/<id>.json` in a world pack. This module is the library half: it
reads a stamp, says whether it is legal, and hands back the oriented
grid the placer paints. It never carves and never draws - placement
belongs to the v3 layout stage (`delve_v3`), beside the stream that owns
it.

The format is closed, and that is the point: twelve keys, six glyphs,
eight anchors, one legend key, and nothing else. Every refusal is one
plain sentence naming the JSON pointer of the value the author has to
change, and `vefr stamp check` prints exactly those sentences:

    stamp wine-alcove: no door socket (+) on its edge, so nothing can
    reach it; put a + in the outer wall. /rows

Two owner decisions (ADR 0013, open questions 1 and 2) are rules here,
not suggestions: the size cap is 21x21 so a throne room can be redrawn
at full size, and a story room - a landmark, a warden hall or a vault -
never rotates or mirrors, so only decorative rooms turn.

Determinism: the reader, the transform and the eligibility rule read
only the file. The draw order - which stamp, which orientation, which
tile - belongs to the layout stream and is written down in
`delve_v3`'s stage comment, so a JavaScript twin can follow it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

FORMAT = 1

# The size cap. ADR 0013 wrote 15x15 in its shape rules; the owner
# decided 21x21 (open question 1, "go bigger, for the throne-room
# redraw") and that decision is the rule.
MAX_SIDE = 21

# The six roles, in the order the layout stage places them: the three
# story rooms first, then the decorative ones. `REQUIRED_ROLES` are the
# ones a floor cannot do without (ADR 0013, Placement 1).
ROLES = ("landmark", "warden-hall", "vault", "secret", "special", "filler")
REQUIRED_ROLES = ("warden-hall", "vault", "landmark")
OPTIONAL_ROLES = ("special", "secret", "filler")
ORDER = REQUIRED_ROLES + OPTIONAL_ROLES

# The eight anchors a legend entry may name. `u` and `d` are the stairs
# on a generated floor, which is why every stamp letter is a capital.
ANCHORS = ("up", "down", "warden", "chest", "note", "home", "poi", "spawn")

WALL = "#"
FLOOR = "."
DOOR = "+"
SECRET = "?"
OUTSIDE = " "
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# The glyphs a stamp tile may carry, and the ones the hero can stand on.
GLYPHS = frozenset(WALL + FLOOR + DOOR + SECRET + OUTSIDE + LETTERS)
STANDING = frozenset(FLOOR + LETTERS)

# The twelve keys, and nothing else. Required: stamp, id, role, rows.
TOP_KEYS = frozenset({
    "stamp", "id", "role", "tags", "depth", "weight", "max_per_floor",
    "rotate", "mirror", "rows", "legend", "poi",
})
LEGEND_KEYS = frozenset({"anchor"})

# What a key the author left out means. A stamp that says nothing about
# its weight is a weight of 1, not a weight of "whatever is in the file".
DEFAULTS: dict = {
    "tags": [],
    "depth": (1, 99),
    "weight": 1,
    "max_per_floor": 1,
    "rotate": False,
    "mirror": False,
    "legend": {},
    "poi": None,
}

# How many attempts one stamp gets at a spot on the floor, and the tag
# that lets a Section ask for every stamp there is.
ATTEMPTS = 24
ANY_TAG = "any"
# A required stamp may be at most this fraction of a Section's smallest
# side: a stamp that fills a third of the floor leaves the rest of it
# walkable (ADR 0013, Validation).
FIT_SHARE = 3

_ID = re.compile(r"^[a-z0-9-]+$")
_STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


class StampError(Exception):
    """A stamp that cannot be read.

    `str(err)` is the whole line `vefr stamp check` prints, sentence and
    JSON pointer together; `.pointer` is the pointer on its own, for a
    caller that wants to point at the offending value itself.
    """

    def __init__(self, sentence: str, pointer: str = "") -> None:
        super().__init__(sentence)
        self.pointer = pointer


# --------------------------------------------------------------- the reader


def read(path: str | Path) -> dict:
    """Parse one stamp file and return its JSON, unchanged."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StampError(f"stamp {path.stem}: the file could not be read") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise StampError(f"stamp {path.stem}: the file is not valid JSON") from exc


def load(directory: str | Path) -> list[dict]:
    """Every stamp in `directory`, read and in sorted id order.

    One file per stamp, named `<id>.json`, and the name is the id: a
    stamp whose file says `wine-alcove` and is called `cellar.json` is a
    stamp whose Section content hash would not change when it is edited.
    A refusal anywhere stops the load, because a half-read stamp set is
    how a floor ends up with the wrong room in it.
    """
    records: list[dict] = []
    for path in sorted(Path(directory).glob("*.json")):
        record = read_v1(read(path), name=path.stem)
        if record["id"] != path.stem:
            raise StampError(
                sentence(path.stem,
                         f"the file is named {path.stem} but its id is "
                         f"{record['id']!r}; the file name and the id are the same name",
                         "/id"),
                "/id")
        records.append(record)
    records.sort(key=lambda record: record["id"])
    return records


def read_v1(source: dict, name: str = "") -> dict:
    """Validate a format-1 stamp and return it with the defaults filled in.

    `name` is what the refusal sentences call the stamp when the file
    itself has no usable id - the file name, in practice.
    """
    found = _find(source, name)
    if found:
        who = _who(source, name)
        raise StampError(sentence(who, *found[0]), found[0][1])
    return _record(source)


def problems(source, name: str = "") -> list[str]:
    """Every refusal one stamp draws, in the order they are checked.

    All of them, not the first: `vefr stamp check` reports a whole stamp
    at once, so an author fixes it in one pass. `read_v1` raises the
    first, which is the one a caller has to fix before anything else
    means anything.
    """
    who = _who(source, name)
    return [sentence(who, problem, pointer) for problem, pointer in _find(source, name)]


def _who(source, name: str) -> str:
    """The name the sentences call this stamp by.

    A stamp's own id is its name, so the sentence points at the value the
    author will search for; a file with no usable id falls back to the
    name it was loaded under, which is its file name.
    """
    if isinstance(source, dict):
        stamp_id = source.get("id")
        if isinstance(stamp_id, str) and stamp_id:
            return stamp_id
    return name


def _find(source, name: str) -> list[tuple[str, str]]:
    """Every `(problem, pointer)` one stamp draws, in a fixed order."""
    out: list[tuple[str, str]] = []
    if not isinstance(source, dict):
        return [("a stamp must be a JSON object", "")]
    say = out.append

    # 1. the envelope: version, closed keys, id, role.
    if type(source.get("stamp")) is not int or source.get("stamp") != FORMAT:
        say((f"stamp version must be the integer {FORMAT}", "/stamp"))
    for key in sorted(source):
        if key not in TOP_KEYS:
            say((f"unknown key {key!r}", f"/{key}"))
    stamp_id = source.get("id")
    if not isinstance(stamp_id, str) or not _ID.match(stamp_id):
        say(("id must be lowercase words and dashes (a-z0-9-)", "/id"))
    role = source.get("role")
    if role not in ROLES:
        say((f"role must be one of {', '.join(ROLES)}", "/role"))

    # 2. the numbers, each with its own whole-number rule.
    tags = source.get("tags", DEFAULTS["tags"])
    if not isinstance(tags, list) or any(
            not isinstance(tag, str) or not tag for tag in tags):
        say(("tags must be a list of short names", "/tags"))
    depth = source.get("depth", list(DEFAULTS["depth"]))
    if not _is_pair(depth) or depth[0] > depth[1]:
        say(("depth must be [first, last], the floors of a Section this stamp may "
             "appear on", "/depth"))
    weight = source.get("weight", DEFAULTS["weight"])
    if not _is_whole(weight) or weight < 0:
        say(("weight must be a whole number of 0 or more", "/weight"))
    per_floor = source.get("max_per_floor", DEFAULTS["max_per_floor"])
    if not _is_whole(per_floor) or per_floor < 1:
        say(("max_per_floor must be a whole number of 1 or more", "/max_per_floor"))
    turn = source.get("rotate", DEFAULTS["rotate"])
    flip = source.get("mirror", DEFAULTS["mirror"])
    for key, value in (("rotate", turn), ("mirror", flip)):
        if not isinstance(value, bool):
            say((f"{key} must be true or false", f"/{key}"))
    # Owner decision 2: a story room is drawn once and stays as drawn.
    if role in REQUIRED_ROLES:
        for key in ("rotate", "mirror"):
            if source.get(key) is True:
                say((f"a {role} is a story room, so it may not rotate or mirror; "
                     "hand-draw a second one, or make the room a filler", f"/{key}"))
    poi = source.get("poi", DEFAULTS["poi"])
    if poi is not None and (not isinstance(poi, str) or not poi.strip()):
        say(("poi must be a short sentence (a string), or left out", "/poi"))

    # 3. the rows: a rectangle, of glyphs the format knows.
    rows = source.get("rows")
    if not isinstance(rows, list) or any(not isinstance(row, str) for row in rows):
        say(("rows must be a list of strings, one per line", "/rows"))
        return out
    if not rows:
        say(("a stamp needs at least one row", "/rows"))
        return out
    width = len(rows[0])
    for number, row in enumerate(rows, 1):
        if len(row) != width:
            say((f"row {number} is {len(row)} characters and row 1 is {width}; every "
                 "row of a stamp is the same length", f"/rows/{number}"))
    if width > MAX_SIDE or len(rows) > MAX_SIDE:
        say((f"this stamp is {width} by {len(rows)}; a stamp is at most {MAX_SIDE} "
             f"by {MAX_SIDE} (ADR 0013)", "/rows"))
    for number, row in enumerate(rows):
        for glyph in row:
            if glyph in GLYPHS:
                continue
            if glyph.isalpha():
                say((f"row {number} carries {glyph!r}; lowercase letters are "
                     "reserved, because 'u' and 'd' are stairs, so a stamp letter "
                     "is a capital one", f"/rows/{number}"))
            else:
                say((f"row {number} carries {glyph!r}, which is not a stamp glyph; "
                     "use '#' wall, '.' floor, '+' door, '?' secret, a space, or a "
                     "capital letter", f"/rows/{number}"))
            break
    if len({len(row) for row in rows}) > 1 or any(
            glyph not in GLYPHS for row in rows for glyph in row):
        # The rectangle itself is unreadable, so nothing below it can be
        # measured against it.
        return out

    # 4. the legend: one entry per letter, one key per entry.
    legend = source.get("legend", DEFAULTS["legend"])
    if not isinstance(legend, dict):
        say(("legend must be an object, one entry per letter", "/legend"))
        return out
    anchors: dict[str, str] = {}
    for glyph in sorted(legend):
        entry = legend[glyph]
        where = f"/legend/{glyph}"
        if not isinstance(glyph, str) or len(glyph) != 1 or glyph not in LETTERS:
            say((f"the legend names {glyph!r}, which is not a letter; a legend entry "
                 "is named by the glyph it explains", where))
            continue
        if not isinstance(entry, dict):
            say(("a legend entry must be an object", where))
            continue
        for key in sorted(entry):
            if key not in LEGEND_KEYS:
                say((f"unknown key {key!r}", f"{where}/{key}"))
        anchor = entry.get("anchor")
        if anchor not in ANCHORS:
            say((f"{anchor!r} is not a known anchor; an anchor is one of "
                 f"{', '.join(ANCHORS)}", f"{where}/anchor"))
            continue
        anchors[glyph] = anchor
    drawn: dict[str, int] = {}
    for y, row in enumerate(rows):
        for x, glyph in enumerate(row):
            if glyph not in LETTERS:
                continue
            drawn[glyph] = drawn.get(glyph, 0) + 1
            if glyph not in anchors:
                say((f"the letter {glyph!r} stands at row {y} column {x} but the "
                     "legend does not name it; give every letter a legend entry",
                     "/legend"))
            elif drawn[glyph] == 2:
                say((f"the letter {glyph!r} is drawn twice; a letter is one named "
                     "anchor, so it appears exactly once", f"/rows/{y}"))
    for glyph in sorted(anchors):
        if glyph not in drawn:
            say((f"the legend names {glyph!r} but the rows never draw it; the legend "
                 "entry is dead weight", f"/legend/{glyph}"))

    # 5. the shape: one room, standing on nothing but itself.
    for problem, pointer in _shape_problems(rows):
        say((problem, pointer))

    # 6. the role: the sockets and the anchors this role owes.
    if role in ROLES:
        for problem, pointer in _role_problems(role, rows, anchors, poi):
            say((problem, pointer))
    return out


# ------------------------------------------------------------- the sentences


def sentence(who: str, problem: str, pointer: str = "") -> str:
    """One refusal, as the line the author reads.

    The stamp, then what is wrong, then - when there is a value to point
    at - the JSON pointer of that value. The space before the pointer is
    part of the sentence, and is the ADR's.
    """
    line = f"stamp {who}: {problem}"
    return f"{line} {pointer}" if pointer else line


def _is_whole(value) -> bool:
    """A whole number, and not a bool pretending to be one."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_pair(value) -> bool:
    """A `[lo, hi]` pair of whole numbers, and nothing else."""
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(_is_whole(item) for item in value))


# ------------------------------------------------------------------ the shape


def _pieces(tiles: set, neighbours) -> int:
    """How many 4-connected pieces a set of tiles falls into."""
    seen: set = set()
    count = 0
    for start in sorted(tiles):
        if start in seen:
            continue
        count += 1
        seen.add(start)
        stack = [start]
        while stack:
            x, y = stack.pop()
            for nx, ny in neighbours(x, y):
                if (nx, ny) in tiles and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    stack.append((nx, ny))
    return count


def _shape_problems(rows: list[str]):
    """The rules every stamp owes whatever its role: one room, one way in.

    Returned in a fixed order - pieces, then spaces, then sockets - so
    the first refusal of a badly drawn stamp is always the same one.
    """
    height = len(rows)
    width = len(rows[0])
    standing = {
        (x, y)
        for y in range(height) for x in range(width) if rows[y][x] in STANDING
    }
    sockets = {
        (x, y)
        for y in range(height) for x in range(width)
        if rows[y][x] in (DOOR, SECRET)
    }

    # The floor, the anchors and the sockets are one 4-connected piece:
    # a stamp is a room, and a room with a sealed corner is a mistake.
    def inside(x, y):
        for step in _STEPS:
            here = (x + step[0], y + step[1])
            if 0 <= here[0] < width and 0 <= here[1] < height:
                yield here

    rooms = standing | sockets
    if rooms and _pieces(rooms, inside) > 1:
        yield ("the floor, the anchors and the sockets are in "
               f"{_pieces(rooms, inside)} separate pieces; a stamp is one room, so "
               "all of them must touch", "/rows")

    # A space is outside the stamp and the generator decides what happens
    # out there, so the room may not stand on it.
    for y in range(height):
        for x in range(width):
            if rows[y][x] != OUTSIDE:
                continue
            if any(here in standing for here in inside(x, y)):
                yield (f"the space at row {y} column {x} touches floor; a space is "
                       "outside the stamp, so the room may not lean on it", "/rows")
                return

    # A socket has exactly one way in, and a mouth for the corridor.
    for y in range(height):
        for x in range(width):
            if rows[y][x] not in (DOOR, SECRET):
                continue
            walk = [here for here in inside(x, y) if rows[here[1]][here[0]] in STANDING]
            where = f"/rows/{y}"
            if len(walk) != 1:
                yield (f"the door socket at row {y} column {x} has {len(walk)} tiles "
                       "to walk from; a socket has exactly one", where)
                continue
            mx = x - (walk[0][0] - x)
            my = y - (walk[0][1] - y)
            if 0 <= mx < width and 0 <= my < height and rows[my][mx] != OUTSIDE:
                yield (f"the door socket at row {y} column {x} has its mouth on a "
                       "wall, so no corridor can reach it; put a space, or the edge "
                       "of the rows, on the far side", where)


# ------------------------------------------------------------------ the roles


def _role_problems(role: str, rows: list[str], anchors: dict[str, str], poi):
    """What one role owes: its sockets, and the anchors it must carry."""
    doors = sum(row.count(DOOR) for row in rows)
    secrets = sum(row.count(SECRET) for row in rows)
    # A list, not a set: two letters may both name the warden, and that is
    # exactly what the warden-hall rule below is looking for.
    named = [anchors[glyph] for glyph in sorted(anchors)]

    if doors == 0 and role != "secret":
        # The ADR's own example sentence, verbatim: this is what a stamp
        # with no way in gets, whatever its role. A secret room is the one
        # role that owes no door - it is found, not walked into.
        yield ("no door socket (+) on its edge, so nothing can reach it; put a + in "
               "the outer wall.", "/rows")
    if role == "landmark" and "poi" not in named and not poi:
        yield ("a landmark needs something to be famous for: a 'poi' anchor, or a "
               "poi sentence beside the stamp", "/poi")
    if role == "warden-hall":
        wardens = named.count("warden")
        if wardens != 1:
            yield (f"a warden-hall has exactly one warden, and this one has {wardens}",
                   "/legend")
    if role == "vault":
        if doors > 1:
            yield (f"a vault has exactly one door, and this one has {doors}", "/rows")
        if secrets:
            yield ("a vault has no secret socket (?); a vault's chest is the reward, "
                   "not a secret", "/rows")
        missing = [name for name in ("chest", "note", "home") if name not in named]
        if missing:
            yield (f"a vault needs a chest, a note and a home anchor, and this one is "
                   f"missing {', '.join(missing)}", "/legend")
    if role == "secret":
        if doors:
            yield ("a secret room is found, not walked into: it may not carry a door "
                   "socket (+)", "/rows")
        if secrets == 0:
            yield ("no secret socket (?) on its edge, so the room is not a secret; put "
                   "a ? in the outer wall", "/rows")
        if "warden" in named:
            yield ("a secret room may not hold the warden; the warden is found, not "
                   "stumbled on", "/legend")


# --------------------------------------------------------------- the record


def _record(source: dict) -> dict:
    """The stamp as the generator reads it, every key present.

    A copy, never the caller's dict: a record that changed under the
    author would be a worse bug than a slow copy.
    """
    depth = source.get("depth", list(DEFAULTS["depth"]))
    legend = source.get("legend", DEFAULTS["legend"])
    return {
        "stamp": FORMAT,
        "id": source["id"],
        "role": source["role"],
        "tags": list(source.get("tags", DEFAULTS["tags"])),
        "depth": (int(depth[0]), int(depth[1])),
        "weight": int(source.get("weight", DEFAULTS["weight"])),
        "max_per_floor": int(source.get("max_per_floor", DEFAULTS["max_per_floor"])),
        "rotate": bool(source.get("rotate", DEFAULTS["rotate"])),
        "mirror": bool(source.get("mirror", DEFAULTS["mirror"])),
        "rows": list(source["rows"]),
        "legend": {glyph: dict(entry) for glyph, entry in legend.items()},
        "poi": source.get("poi"),
    }


# ----------------------------------------------------------- the orientations

# The two flags, the eight ways of looking at a room. ADR 0013's
# Orientation section, as code:
#
#     1. if o >= 4, mirror first: x' = w-1-x
#     2. then turn clockwise o % 4 times, one turn mapping (x,y) in a
#        w x h grid to (h-1-y, x) in an h x w grid
#
# Nothing here draws. A letter is a letter in every orientation, which
# is the whole reason an anchor is named by its glyph and not by an
# arrow, so the chest is still the chest after three turns.

_STEP_NAMES = {(1, 0): "right", (-1, 0): "left", (0, 1): "down", (0, -1): "up"}


def _turn(rows: list[str]) -> list[str]:
    """One turn clockwise: a w x h grid comes back as an h x w grid.

    The top row of the old grid becomes the right-hand column of the new
    one, so `["##", "#.", "#+"]` - a room whose door is in the floor of
    its bottom wall - comes back with that door in the left-hand wall.
    """
    height = len(rows)
    return [
        "".join(rows[height - 1 - x][y] for x in range(height))
        for y in range(len(rows[0]))
    ]


def orient(rows: list[str], o: int) -> list[str]:
    """The grid as it looks at orientation `o`, `o` in `0..7`.

    Read-only, and a fresh list of fresh strings every call: the placer
    paints onto the result, so handing back the author's rows would let a
    carve reach the file in memory.
    """
    if not 0 <= o <= 7:
        raise ValueError(f"orientation {o} is not one of 0..7")
    drawn = [row[::-1] for row in rows] if o >= 4 else list(rows)
    for _ in range(o % 4):
        drawn = _turn(drawn)
    return drawn


def orientations(record: dict) -> tuple[int, ...]:
    """Which orientations this stamp's two flags allow, in draw order.

    The order is the order the ADR writes and the order a random draw
    indexes, so `allowed[_pick(len(allowed))]` is the whole rule: `[0]`,
    plus `1..3` when `rotate` is set, plus `4` when only `mirror` is set
    or `4..7` when both are. A story room has already been refused a
    `rotate` or `mirror` by the reader, so it comes back as `(0,)`.
    """
    if record.get("rotate") and record.get("mirror"):
        return (0, 1, 2, 3, 4, 5, 6, 7)
    if record.get("rotate"):
        return (0, 1, 2, 3)
    if record.get("mirror"):
        return (0, 4)
    return (0,)


# ------------------------------------------------------------------ the sockets


def sockets(rows: list[str]) -> list[dict]:
    """Every socket of a drawn grid, in row-major order, ready to route to.

    One dict per `+` or `?`:

        at     (x, y)  the socket tile itself
        kind   "door" or "secret"
        into   (x, y)  the single tile a corridor steps onto
        mouth  (x, y)  the tile on the far side of the socket: off the
                       grid, or a space, so a corridor may start there
        step   (dx, dy) the direction out of the mouth, which follows
                       the orientation the placer chose

    The reader has already promised each socket exactly one way in and a
    clear mouth, so this walks and does not re-argue. Ties between two
    sockets are the placer's to break: ADR 0013 says nearest mouth first,
    and row-major order is the tie-break.
    """
    height = len(rows)
    width = len(rows[0])
    found = []
    for y in range(height):
        for x in range(width):
            if rows[y][x] not in (DOOR, SECRET):
                continue
            walk = [
                (x + dx, y + dy)
                for dx, dy in _STEPS
                if 0 <= x + dx < width and 0 <= y + dy < height
                and rows[y + dy][x + dx] in STANDING
            ]
            into = walk[0]
            mouth = (2 * x - into[0], 2 * y - into[1])
            found.append({
                "at": (x, y),
                "kind": "door" if rows[y][x] == DOOR else "secret",
                "into": into,
                "mouth": mouth,
                "step": (mouth[0] - x, mouth[1] - y),
            })
    return found


def step_name(step: tuple[int, int]) -> str:
    """`(1, 0)` reads as `"right"`, for the pinned try and for messages."""
    return _STEP_NAMES[step]


# ------------------------------------------------------------------ the anchors


def anchors(rows: list[str], legend: dict) -> dict:
    """Where each letter of the legend stands in a drawn grid.

    A glyph is a glyph in all eight orientations, so the turn never
    renames anything: the map is glyph -> `{"at": (x, y), "anchor":
    "chest"}`, and the placer looks a stamp's anchors up by name after
    the turn, not before it.
    """
    found = {}
    for y, row in enumerate(rows):
        for x, glyph in enumerate(row):
            if glyph in legend:
                found[glyph] = {"at": (x, y), "anchor": legend[glyph]["anchor"]}
    return found
