"""sections - Sections: the depth curve, the floor pattern, the landings.

PLAN.md section 2 is the spec. A Section is a pack file, `sections/<id>.json`,
holding everything one descent is made of: how many floors it has, how big
they are, what lives on them, and what each floor is FOR. This module is
the engine's read of that file, and it is pure - no clock, no model call,
no global, no dictionary iterated while a draw is consumed.

Everything here is one of four things:

- **where a floor is.** `locate(depth, pack)` turns a global depth into
  `(cycle, section, k)`, and `floor_key(run_seed, section, cycle, k)` names
  it. PLAN.md section 2 writes both, and the story is cycle 0.
- **what a floor is.** `pattern`, `slot`, `floor_kind` and `floor_size`:
  the four things a floor is drawn from, each on its own stream.
- **what the hero can get back to.** `landings`, `landing_flag` and
  `recorded_landings` are the elevator rule of PLAN.md section 4: two
  landings a Section, recorded permanently, and no lift down past a floor
  the hero has not reached.
- **what a floor is the same as.** `content_hash` and `identity` are the
  floor identity of PLAN.md section 2 - `(gen version, section content
  hash, floor_key)` - so that editing a pack's Section data invalidates
  that Section's floors rather than replaying old deltas onto new maps.

THE FLOOR KEY AND `delve_v3`

`floor_key` is what this slice means by a floor's name, and it is the
seed the caller hands `generate_floor_v3`. That function builds its own
stream name as `<seed>/<section id>/<floor kind>`, so a caller that passed
a bare run seed would give floors 2 and 3 of one Section the SAME floor:
both are `normal`. Every caller in this slice passes
`floor_key(run_seed, section, cycle, k)` as the seed, and the kind is
appended to it, so a floor is `run_seed/section.id/cycle/k/kind` and two
floors of one Section are two maps. That is why E4 did not edit
`delve_v3`: the key it builds is the tail of this one, and moving it there
would have invalidated E2's six floor goldens and the E3 parity branch for
no gain. Slice E3's JavaScript twin has to take the same key.

THE SIZE AND THE SPECIAL FLOOR

Two draws that are not in PLAN.md section 2's list of streams, both on
their own stream and both off the floor key:

- `|size` draws the floor's `w` then its `h` inside the Section's own
  `size` range. It is its own stream so that a pack that edits its room
  quota does not move a wall: the sub-seed rule of section 2 is the whole
  reason the stages do not share a stream.
- `|special` draws which of the Section's `specials` a `special` slot is,
  the way PLAN.md section 4's three kinds are meant to appear.

Both are one `floor(rng() * n)` draw with `n < 2^31`, which is the only
float PLAN.md section 2 allows, and both read a list that is already in
pack order.

TOUCH POINTS (written down before the first edit, as the slice asks)

| what | where |
|---|---|
| the Section pack shape | `shapes.SECTION` and its sub-blocks; `shapes.check_section` |
| the validator door | `maplab.section_block_errors`, called by `maplab.section_errors` |
| this module | `sections.py` |
| the sweep over Sections | `locks.section_findings`, printed by `cmd_map` |
| the bake | `cmd_delve --section`, which wires the doors and records the landings |
| the golden | `tests/golden/validator/cases.json`, block `section` |
| the tests | `tests/test_sections_e4.py`, two packs under `tests/fixtures/sections/` |

NOT IN THIS SLICE

The endless cycles are E10: a depth past the last floor of the story
raises rather than being clamped onto the last Section, because clamping
would send a hero down floors that do not exist. The warden, the vault and
the key that opens them are E8's, and the three special floor kinds are
E9's - E4 draws WHICH of them a special slot is and leaves the rest to
`delve_v3`, which already knows all three.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .delve import prng

# The Section directory inside a pack, and the file name pattern under it.
SECTIONS_DIR = 'sections'

# The pattern PLAN.md section 4 writes for a nine-floor Section: a landing
# to come down to, two special floors, a landing on the fifth, and the
# warden with its vault on the ninth. A Section that names no pattern gets
# this one, padded with `n` to as many floors as it has.
DEFAULT_PATTERN = ('entry', 'n', 'n', 'special', 'landing', 'n', 'special',
                   'n', 'warden')

# The slots a pattern may name, and the two of them that are a landing.
# `entry` is a landing too: it is the floor a hero comes down to, and
# PLAN.md section 4 counts the first floor of a Section as one of its two.
PATTERN_SLOTS = ('entry', 'n', 'special', 'landing', 'warden')
LANDING_SLOTS = ('entry', 'landing')

# The floor kind every slot but `special` is. `special` draws one of the
# Section's own `specials` instead, which is the same four kinds the
# generator already knows.
ORDINARY_KIND = 'normal'

# What a Section gets when it names nothing: nine floors, and the two
# sizes of PLAN.md section 3 that are a candidate default rather than the
# stress size.
DEFAULT_FLOORS = 9
DEFAULT_SIZE = ((64, 64), (48, 48))

# The closed range a Section's size may be in, which is the range of
# PLAN.md section 3's table plus a little. A pack outside it has been
# refused by `vefr check`; the clamp here is for a Section read off disk
# without its check, and a floor the generator can actually lay is better
# than an exception from inside a sweep.
SIZE_BOUNDS = ((32, 128), (24, 96))

# The flag a reached landing sets, and the prefix of every one of them. The
# id has to name the Section and the floor and nothing else, because it is
# written once and kept forever (PLAN.md section 2, save deltas).
LANDING_FLAG = 'landing-{section}-{k}'

# The region name the bake gives floor `k` of a Section.
REGION_NAME = '{section}-{k}'


# ------------------------------------------------------------- reading a pack


def section_id(section: dict) -> str:
    """The id a Section is named by, or the empty string when it has none."""
    if not isinstance(section, dict):
        return ''
    value = section.get('id')
    return value if isinstance(value, str) else ''


def load(pack_dir) -> list[dict]:
    """Every Section pack in `pack_dir/sections`, sorted by id.

    The same leniency `vefr.stamp_check` reads sections with: a file that
    cannot be read is left out rather than stopping the read, because the
    validator is what says so out loud and a sweep that stops on the first
    broken Section checks none of the rest. Returns the dicts as they are
    on disk, with no id filled in from the file name: a pack whose file and
    id disagree is `vefr check`'s sentence, not this module's guess.
    """
    directory = Path(pack_dir) / SECTIONS_DIR
    if not directory.is_dir():
        return []
    out: list[dict] = []
    for path in sorted(directory.glob('*.json')):
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(value, dict):
            out.append(value)
    return ordered(out)


def ordered(sections) -> list[dict]:
    """A pack's Sections in the order the dungeon descends through them.

    By the Section's own number first and its id second, so a pack that
    numbers its Sections the way PLAN.md section 6 does descends in that
    order whatever the files are named. The id breaks a tie, and Python's
    sort is stable, so two Sections that share both keep the order they
    were read in - a list, never a dictionary, for the reason PLAN.md
    section 2 gives.
    """
    def rank(section):
        number = section.get('section') if isinstance(section, dict) else None
        return (number if isinstance(number, int) and not isinstance(number, bool)
                else 0, section_id(section))
    return sorted([s for s in sections if isinstance(s, dict)], key=rank)


def floors(section: dict) -> int:
    """How many floors a Section has, defaulting to nine."""
    value = section.get('floors') if isinstance(section, dict) else None
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return DEFAULT_FLOORS


def specials(section: dict) -> tuple[str, ...]:
    """The floor kinds a `special` slot may draw, in pack order.

    PLAN.md section 4 names three - treasure, infested, hub - and a pack
    that names its own draws from those instead. An empty list falls back
    to the three, so a Section that wrote `specials: []` is swept rather
    than skipped; `vefr check` is what tells the author about the empty
    list itself.
    """
    raw = section.get('specials') if isinstance(section, dict) else None
    if isinstance(raw, list):
        named = [kind for kind in raw if isinstance(kind, str) and kind]
        if named:
            return tuple(named)
    return ('treasure', 'infested', 'hub')


def _pair(value, fallback: tuple[int, int]) -> tuple[int, int]:
    """A `[lo, hi]` pair of whole numbers, ordered, or `fallback`."""
    if isinstance(value, (list, tuple)) and len(value) == 2:
        if all(isinstance(n, int) and not isinstance(n, bool) for n in value):
            return (min(value), max(value))
    return fallback


def _clamp(value: int, bounds: tuple[int, int]) -> int:
    return max(bounds[0], min(bounds[1], value))


# --------------------------------------------------------------- the pattern


def pattern(section: dict) -> tuple[str, ...]:
    """The Section's pattern, one slot per floor, ending at its last floor.

    A Section that names no pattern gets `DEFAULT_PATTERN`; a pattern
    shorter than the Section is padded with `n`, and one longer than it is
    kept whole rather than cut, so a Section with more slots than floors
    keeps the warden its last slot names. Neither direction raises: the
    validator is what says a pattern that does not match its Section is
    wrong, and this module is what lays out whatever is on disk.
    """
    raw = section.get('pattern') if isinstance(section, dict) else None
    slots = [slot for slot in raw
             if isinstance(slot, str) and slot in PATTERN_SLOTS] \
        if isinstance(raw, list) else list(DEFAULT_PATTERN)
    count = floors(section)
    if len(slots) < count:
        slots.extend(['n'] * (count - len(slots)))
    return tuple(slots)


def slot(section: dict, k: int) -> str:
    """What floor `k` of a Section is FOR, 1-based.

    A floor past the end of the pattern is an ordinary one: the pattern is
    what a Section says about its floors, and a floor it did not describe
    is described here rather than raising in the middle of a descent.
    """
    slots = pattern(section)
    if isinstance(k, int) and not isinstance(k, bool) and 1 <= k <= len(slots):
        return slots[k - 1]
    return 'n'


def is_landing(section: dict, k: int) -> bool:
    """Whether floor `k` is one of the Section's landings."""
    return slot(section, k) in LANDING_SLOTS


def landings(section: dict) -> tuple[int, ...]:
    """The floors of a Section a hero can climb back to town from.

    PLAN.md section 4: the first floor and the fifth, which is Stardew's
    every-five. Here they are the pattern's own `entry` and `landing`
    slots, in pattern order, so a Section that moves a landing has said so
    in its data rather than in this module.
    """
    return tuple(k for k, name in enumerate(pattern(section), 1)
                 if name in LANDING_SLOTS)


def landing_flag(section: dict, k: int) -> str:
    """The rule flag that records floor `k` of a Section as reached."""
    return LANDING_FLAG.format(section=section_id(section), k=k)


def recorded_landings(section: dict, flags) -> tuple[int, ...]:
    """The landings of a Section the hero has reached, in pattern order.

    The set of flags is a set: it has no order two languages would agree
    on, so the answer is the pattern's order every time (PLAN.md section 2,
    the forbidden-list rule). A flag for a floor that is not a landing of
    this Section is not one of them.
    """
    reached = flags if isinstance(flags, (set, frozenset)) else set(flags or ())
    return tuple(k for k in landings(section)
                 if landing_flag(section, k) in reached)


# ------------------------------------------------------------- the depth curve


def locate(depth: int, pack) -> tuple[int, dict, int]:
    """Where a global `depth` is: `(cycle, section, k)`.

    Pure, and derived only from the pack's Section list - PLAN.md section 2
    says so, and it is what lets the player locate a floor it has not
    loaded without loading the pack's floors. Depth 1 is the first floor of
    the first Section; the Sections are walked in `ordered` order, each for
    as many floors as it has.

    `pack` is a list of Sections or a pack directory. The story is cycle 0;
    a depth past the last floor of it raises `ValueError`, because the
    endless cycles are slice E10 and clamping would answer with a floor
    that is not there.
    """
    if isinstance(pack, (str, Path)):
        pack = load(pack)
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
        raise ValueError(f'depth must be a whole number of 1 or more, and it is {depth!r}')
    for section in ordered(pack or ()):
        count = floors(section)
        if depth <= count:
            return 0, section, depth
        depth -= count
    raise ValueError(
        'that depth is past the last floor of the story; the endless '
        'cycles are slice E10 and no Section answers for them yet')


def depth(section: dict, k: int, pack=None) -> int | None:
    """The global depth of floor `k` of `section` - `locate`'s inverse.

    `pack` is the Section list the depth is counted within and defaults to
    the Section itself. `None` when `section` is not one of them, or when
    `k` is not one of its floors: a depth that cannot be counted is not a
    depth of zero, and zero is floor one.
    """
    target = section_id(section)
    walked = 0
    for candidate in ordered(pack if pack is not None else [section]):
        if section_id(candidate) == target:
            return walked + k if 1 <= k <= floors(candidate) else None
        walked += floors(candidate)
    return None


# ------------------------------------------------------------- floor identity


def floor_key(run_seed: str, section: dict, cycle: int = 0, k: int = 1) -> str:
    """`run_seed/section.id/cycle/k`, the name of one floor.

    PLAN.md section 2 writes it exactly like this, and it is the seed every
    caller hands `delve_v3.generate_floor_v3` - see the module docstring for
    why that is the floor's whole identity and not just a label.
    """
    return f'{run_seed}/{section_id(section)}/{cycle}/{k}'


def floor_region(section: dict, k: int) -> str:
    """The region name floor `k` of a Section is baked as.

    `<section id>-<k>`, in the Section's own order, so the depth curve and
    the pack's region directory say the same thing about the same floor.
    """
    return REGION_NAME.format(section=section_id(section), k=k)


def content_hash(section: dict) -> str:
    """A digest over one Section's data, and nothing else.

    Sixteen hex characters of a SHA-256 over the record with its keys
    sorted, so two reads of the same file hash the same however the file
    was written. This is the middle of PLAN.md section 2's floor identity:
    editing any key of a Section changes the identity of every floor in it,
    which is what tells the save to regenerate those floors instead of
    replaying deltas recorded on maps that no longer exist.
    """
    text = json.dumps(section, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def identity(gen: int, section: dict, floor_key_: str) -> str:
    """The identity triple of one floor, as one string: `v<gen>:<hash>:<key>`."""
    return f'v{gen}:{content_hash(section)}:{floor_key_}'


# ------------------------------------------------------------- drawing a floor


def size_range(section: dict) -> tuple[int, int, int, int]:
    """A Section's own floor size range: `(w_lo, w_hi, h_lo, h_hi)`.

    Both halves of both pairs, clamped into `SIZE_BOUNDS` so a Section read
    off disk without its check still asks for a floor the generator can
    lay. `vefr stamp check` reads the same `size` key and measures a stamp
    against the SMALL end of it, so the two ends mean the same thing here.
    """
    raw = section.get('size') if isinstance(section, dict) else None
    width = _pair(raw.get('w') if isinstance(raw, dict) else None,
                  DEFAULT_SIZE[0])
    height = _pair(raw.get('h') if isinstance(raw, dict) else None,
                   DEFAULT_SIZE[1])
    return (_clamp(width[0], SIZE_BOUNDS[0]), _clamp(width[1], SIZE_BOUNDS[0]),
            _clamp(height[0], SIZE_BOUNDS[1]),
            _clamp(height[1], SIZE_BOUNDS[1]))


def floor_size(section: dict, floor_key_: str) -> tuple[int, int]:
    """The `(w, h)` of one floor, drawn from the Section's range.

    On the `v3|<floor key>|size` stream: the width first, then the height,
    each one `lo + floor(rng() * (hi - lo + 1))`. A Section whose two ends
    are the same number draws that number every time, which is what a pack
    asking for one fixed size is asking for.
    """
    w_lo, w_hi, h_lo, h_hi = size_range(section)
    rng = prng(f'v3|{floor_key_}|size')
    width = w_lo + int(rng() * (w_hi - w_lo + 1))
    height = h_lo + int(rng() * (h_hi - h_lo + 1))
    return width, height


def floor_kind(section: dict, k: int, run_seed: str, cycle: int = 0) -> str:
    """Which of the four floor kinds floor `k` of a Section is.

    Every slot but `special` is an ordinary floor - a landing and a warden
    floor are floors like any other to the generator, and what makes them
    those things is the Section's data rather than the geometry. A
    `special` slot draws one of the Section's own `specials` on the
    `v3|<floor key>|special` stream: one `floor(rng() * n)` draw, so the
    same floor key is the same kind in both languages.
    """
    if slot(section, k) != 'special':
        return ORDINARY_KIND
    kinds = specials(section)
    rng = prng(f'v3|{floor_key(run_seed, section, cycle, k)}|special')
    return kinds[int(rng() * len(kinds))]


# ------------------------------------------------------------------ families


def families(section: dict, resolve=None) -> list[dict]:
    """A Section's family table with each family's base record attached.

    A Section names Blueprint families by id and carries no record of its
    own (ADR 0014), so the base - `hp`, `atk`, `xp`, `sight` - comes from
    `vefr.blueprint.resolve_family` behind the `resolve` callable this
    module takes rather than imports. The Section's own keys win: a family
    id, a weight and a depth range are the Section's to write, and a
    Blueprint that happened to carry a `weight` would not get to overwrite
    one.

    A family the Blueprint does not have comes back as the entry alone, with
    no base - `vefr check` refuses that Section with `/families/0/family`,
    so a caller that never validated its pack still lays a floor rather
    than raising inside a sweep.
    """
    raw = section.get('families') if isinstance(section, dict) else None
    entries = [entry for entry in raw if isinstance(entry, dict)] \
        if isinstance(raw, list) else []
    out: list[dict] = []
    for entry in entries:
        name = entry.get('family')
        base = resolve(name) if resolve is not None and isinstance(name, str) \
            and name else None
        out.append(dict(base) if isinstance(base, dict) else {})
        out[-1].update(entry)
    return out
