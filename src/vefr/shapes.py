"""shapes - the schema table for world-pack blocks.

One row per block: the keys it may hold, and the sentence each way a
value can be wrong is spoken in. The validators in `maplab.py` call
`check` and keep returning `list[str]`, so no caller changes.

`EVENTS` is the same table for the rules vocabulary: one row per event
a rule or a sticker may fire on, with the payload it carries and what
kind of pack id each field names. Both `when` validators read it, so
the vocabulary is typed here once (vefr #269 was it typed three times
and drifting).

`check(block, value)` returns a list of `Problem(code, pointer,
sentence)`. Emission order is stable: stop at `not-object`; then the
value's unknown keys in the value's own order; then each table key in
table order (a missing required key, else its wrong value, else the
block that key holds - `Key.sub`, which the Section pack is the first
user of).

`known` is accepted and ignored: the id checks (`unknown-ref`) are
spoken by the validators that own the pack, in their own author's
words, and they read `EVENTS` below rather than `check`.

Three of the values a block closes on are not plain scalars, and each
has a kind of its own:

- `hundredths` - a multiplier the pack writes as `1.5` and the table
  bounds in hundredths, so `1.234` is refused: the pack writes whole
  hundredths because a stat is scaled by integer arithmetic in two
  languages (ADR 0014, "Stats, in whole numbers only").
- `pair` - a `[lo, hi]` pair of whole numbers, each half bounded, so
  `groups.minions[1]` names the half that is out of range.
- `ids` - a list of ids, every element checked.

and E4 added five more, all of them because the Section pack of PLAN.md
section 2 writes a value no earlier block had:

- `obj` - a block in its own right, named by `Key.sub`. The sub-block's
  sentences speak for it, so `size`, `fog`, `curve` and `loot` are typed
  where they are read instead of being checked as dictionaries.
- `enums` - a list drawn from a closed set, so a `pattern` entry that is
  not one of the five slots is refused at that entry.
- `glyphs` - the tile table of a Section, every glyph naming a tileset.
- `hundredths-pair` - a `[lo, hi]` pair of multipliers, both halves whole
  hundredths: the monster curve of a Section.
- `list` - a plain list, which `Key.sub` then walks element by element.

and ADR 0017 (rolled loot) added one more, because a trait is a word and
not an id:

- `words` - a list of plain words, every element checked, so a `traits`
  pool holding "quick brown" is refused at that entry rather than
  half-drawn at play time.

A wrong element of a `pair`, an `ids` or an `enums` is reported at that
element's pointer, and the first wrong element is the one reported, so a
key earns one sentence however wrong its value is.

Three checks cannot live in that table, because each spans records
rather than one value: an affix id the pack does not define, a repeated
id, a family a Section names that the Blueprint does not have, and a
group led by an elite in a Section that names no affix. E4 added four
more of the same kind: a Section's pattern as long as its Section, ending
in a warden floor, naming two landings, and asking for a special it does
not name. They are `check_affixes` and `check_section`, and they return
the same `list[Problem]` and speak the same plain sentences.

The module is standard-library only: `shapes.py` must never import from
`vefr`, or `maplab` would import itself into a cycle. So the one
question `shapes` cannot answer for itself - does this family exist in
the Blueprint, and what does it resolve to - is asked through a
`resolve` callable the caller passes in.
"""

from collections import namedtuple
from dataclasses import dataclass, field
from typing import Mapping
import re


Problem = namedtuple('Problem', 'code pointer sentence')

# A plain word: one the pack reads aloud and the bag can print. No spaces,
# no punctuation, 1 to 24 characters, a letter first - so a `traits` pool
# can never carry a sentence that would read as two traits in a sentence
# (ADR 0017).
WORD = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,23}')


@dataclass(frozen=True)
class Key:
    name: str
    kind: str               # 'str' | 'int' | 'bool' | 'enum' | 'obj' | 'list' | 'ref'
                             # | 'hundredths' | 'pair' | 'ids' | 'name-label'
                             # | 'enums' | 'glyphs' | 'hundredths-pair'
                             # | 'words' (a list of plain words)
                             # | 'word' (one plain word)
                             # | 'str-or-obj' (a string, or an object checked by `sub`)
    choices: tuple = ()     # enum values, in sentence order
    lo: int | None = None   # int bounds, str length bounds, or hundredths
    hi: int | None = None
    ref: str | None = None  # unused in this slice
    required: bool = False
    say: Mapping[str, str] = field(default_factory=dict)  # this key's own words
    sub: 'Block | None' = None  # the block this value holds, if any


@dataclass(frozen=True)
class Block:
    name: str               # 'saves'
    example: str            # '{"rules": "persist"}'
    keys: tuple             # tuple[Key, ...] in table order
    say: Mapping[str, str] = field(default_factory=dict)  # code -> sentence override


# The default sentence per error code. A key's `say`, then its block's,
# overrides individual codes; where neither does, these are the bytes.
# The last four are spoken by the checks that span records rather than by
# the table, and they live here for the same reason: one place holds every
# sentence a refusal can be spoken in.
_DEFAULTS = {
    'not-object': '{name} must be an object such as {example}',
    'unknown-key': '{name} has an unknown key {key!r}; it may only hold {keys}',
    'missing-key': '{name} must hold a {key}, such as {example}',
    'not-in-choices': '{path} must be {choices}',
    'wrong-type': '{path} must be a {kind}',
    'out-of-range': '{path} must be between {lo} and {hi}',
    'wrong-element': '{path} must be {noun}, such as {sample}',
    'not-hundredths': '{path} must be a whole number of hundredths, such as {sample}',
    'no-name-slot': '{path} must name the monster as {{name}}',
    'not-a-list': 'affixes must be a list of affix records',
    'duplicate-id': 'every affix id must be its own, and {id!r} is used twice',
    'undefined-affix': ('every affix a section names must be defined by the '
                        'pack, and {id!r} is not'),
    'no-affix-for-elite': ('a group led by an elite needs at least one affix, '
                           'and the section names none'),
    'unknown-family': 'unknown family {id!r}',
    'no-stat': ('every family a section names needs an {stat} in the '
                'blueprint, and {id!r} has none'),
    'pattern-length': ("a section's pattern must have one entry for each of "
                       'its {floors} floors, and it has {given}'),
    'no-warden': ("a section's pattern must end with a warden floor, and "
                  'its last entry is "{slot}"'),
    'too-few-landings': ('every section needs a landing on its first floor '
                         'and another by its fifth, and this pattern names '
                         '{given}'),
    'no-specials': ('a section\'s pattern asks for a special floor, and '
                    'names no specials'),
    'not-a-block-or-list': ('{path} must be one town-states block, such as '
                            '{example}, or a list of them'),
    'duplicate-region': ('every region may name its town states once, and '
                         '{region!r} names them twice'),
    'unknown-region': ('every region a town state names must be one the '
                       'pack declares, and {id!r} is not'),
}

# The kinds whose wrong values need a sentence of their own. A key's `say`
# wins over its block's, and a block's over these - `sections` above.
_KIND_SAY = {
    'str': {'wrong-type': '{path} must be a string'},
    'int': {'wrong-type': '{path} must be a whole number'},
    'bool': {'wrong-type': '{path} must be a yes or a no'},
    'obj': {'wrong-type': '{path} must be an object'},
    'list': {'wrong-type': '{path} must be a list'},
    'enums': {
        'wrong-type': '{path} must be a list of {choices}',
        'not-in-choices': '{path} must be {choices}',
    },
    'glyphs': {
        # The example is a table, so its braces are doubled: every
        # sentence in this table is a `str.format` template.
        'wrong-type': ('{path} must be a table of glyphs, such as '
                       '{{"#": "wall", ".": "floor"}}'),
        'wrong-element': '{path} must name a tileset, such as "wall"',
    },
    'hundredths': {
        'wrong-type': '{path} must be a number, such as 1.5',
        'not-hundredths': ('{path} must be a whole number of hundredths, '
                           'such as 1.25'),
    },
    'hundredths-pair': {
        'wrong-type': ('{path} must be a [lo, hi] pair of numbers, such as '
                       '[1.0, 1.4]'),
        'not-hundredths': ('{path} must be a whole number of hundredths, '
                           'such as 1.25'),
    },
    'pair': {
        'wrong-type': ('{path} must be a [lo, hi] pair of whole numbers, '
                       'such as [1, 2]'),
    },
    'ids': {
        'wrong-type': '{path} must be a list of affix ids, such as ["big"]',
        'wrong-element': '{path} must be an affix id, such as "big"',
    },
    'words': {
        'wrong-type': '{path} must be a list of plain words, such as ["keen"]',
        'wrong-element': '{path} must be a plain word, such as "keen"',
    },
    'word': {
        'wrong-type': '{path} must be a string',
        'wrong-element': '{path} must be a plain word, such as "keen"',
    },
}

# What a `wrong-element` names, per kind.
_ELEMENT_NOUN = {
    'pair': 'a whole number',
    'ids': 'an affix id',
    'hundredths': 'a whole number',
    'hundredths-pair': 'a whole number',
    'words': 'a plain word',
}


def _render_choices(choices) -> str:
    return ' or '.join(f'"{choice}"' for choice in choices)


def _join_keys(block) -> str:
    names = [key.name for key in block.keys]
    if len(names) == 1:
        return names[0]
    return ', '.join(names[:-1]) + ' and ' + names[-1]


def _say(block, key, code) -> str:
    """The sentence for one code about one key: the key's own wording, the
    block's, the kind's, then the default. The most specific has the last
    word.

    Resolved per key rather than per block, because a block may hold
    two kinds that need different words for the same code - `sight` is
    a whole number and `hp` is a number in hundredths, and one block
    saying both wrong ways would be one of them wrong. E4's `section`
    block needs the key's own words for the same reason: `stamps` and
    `pois` are both `ids`, and "a stamp id" is not "a point of interest".
    """
    kind = _KIND_SAY.get(key.kind, {}) if key is not None else {}
    own = getattr(key, "say", None) or {} if key is not None else {}
    return (own.get(code) or block.say.get(code)
            or kind.get(code) or _DEFAULTS[code])


def _as_hundredths(n) -> str:
    """A bound in hundredths as the pack writes it: 100 -> `1.0`."""
    text = f'{n / 100:.2f}'
    return text[:-1] if text.endswith('0') else text


def _type_ok(kind: str, value) -> bool:
    if kind in ('str', 'name-label'):
        return isinstance(value, str)
    if kind == 'str-or-obj':
        return isinstance(value, (str, dict))
    if kind == 'int':
        # bool is not an int here, and vice versa.
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == 'bool':
        return isinstance(value, bool)
    if kind == 'obj':
        return isinstance(value, dict)
    if kind in ('list', 'ids', 'enums', 'words'):
        return isinstance(value, list)
    if kind == 'word':
        return isinstance(value, str)
    if kind == 'glyphs':
        return isinstance(value, dict)
    if kind == 'ref':
        return isinstance(value, str)
    if kind == 'hundredths':
        return (isinstance(value, (int, float))
                and not isinstance(value, bool))
    if kind == 'pair':
        return (isinstance(value, list) and len(value) == 2
                and all(isinstance(n, int) and not isinstance(n, bool)
                        for n in value))
    if kind == 'hundredths-pair':
        return (isinstance(value, list) and len(value) == 2
                and all(isinstance(n, (int, float)) and not isinstance(n, bool)
                        for n in value))
    return True


def _whole_hundredths(value) -> bool:
    scaled = value * 100
    return abs(scaled - round(scaled)) < 1e-9


def _out_of_range(key: Key, value) -> bool:
    """Whether a value of this kind falls outside its bounds.

    A `pair` bounds each of its two halves rather than the pair as one
    number, so it answers for the list it is given and for either half
    of it. A `hundredths-pair` bounds its halves the same way, but a
    value that is out of range is reported at the PAIR: the two ends of a
    curve are one sentence about the curve, not two about its halves.
    """
    if key.kind in ('pair', 'hundredths-pair') and isinstance(value, (list, tuple)):
        return any(_out_of_range(key, n) for n in value)
    if key.kind in ('int', 'pair'):
        return ((key.lo is not None and value < key.lo)
                or (key.hi is not None and value > key.hi))
    if key.kind in ('str', 'name-label') or (key.kind == 'str-or-obj' and isinstance(value, str)):
        n = len(value)
        return ((key.lo is not None and n < key.lo)
                or (key.hi is not None and n > key.hi))
    if key.kind == 'hundredths':
        return ((key.lo is not None and value * 100 < key.lo)
                or (key.hi is not None and value * 100 > key.hi))
    if key.kind == 'hundredths-pair':
        return ((key.lo is not None and value * 100 < key.lo)
                or (key.hi is not None and value * 100 > key.hi))
    return False


def _bounds(key: Key):
    """The two numbers an `out-of-range` sentence quotes for `key`."""
    if key.kind in ('hundredths', 'hundredths-pair'):
        return _as_hundredths(key.lo), _as_hundredths(key.hi)
    return key.lo, key.hi


def _range_problem(block, key, value, path, pointer):
    lo, hi = _bounds(key)
    return Problem('out-of-range', pointer,
                   _say(block, key, 'out-of-range').format(
                       path=path, lo=lo, hi=hi))


def _element_problem(block, key, value, index, path):
    """The one problem with element `index` of a `pair`, an `ids` or an
    `enums`."""
    pointer = f'/{block.name}/{key.name}/{index}'
    here = f'{path}[{index}]'
    if key.kind == 'pair':
        if _out_of_range(key, value):
            return _range_problem(block, key, value, here, pointer)
        return None
    if key.kind == 'enums':
        if value in key.choices:
            return None
        return Problem(
            'not-in-choices', pointer,
            _say(block, key, 'not-in-choices').format(
                name=block.name, key=key.name, path=here,
                choices=_render_choices(key.choices)))
    if key.kind == 'words':
        if isinstance(value, str) and WORD.fullmatch(value):
            return None
        return Problem('wrong-element', pointer,
                       _say(block, key, 'wrong-element').format(
                           path=here, noun=_ELEMENT_NOUN.get(key.kind, 'a value')))
    if isinstance(value, str) and value:
        return None
    return Problem('wrong-element', pointer,
                   _say(block, key, 'wrong-element').format(
                       path=here, noun=_ELEMENT_NOUN.get(key.kind, 'a value')))


def _glyph_problem(block, key, value, path):
    """The one glyph of a tile table that names no tileset.

    The pointer carries the glyph itself rather than an index - `tiles`
    is a table and a table has no order to point into - and the path
    quotes the glyph the way a pack author wrote it.
    """
    for glyph, tileset in value.items():
        if isinstance(tileset, str) and tileset:
            continue
        return Problem(
            'wrong-element', f'/{block.name}/{key.name}/{glyph}',
            _say(block, key, 'wrong-element').format(
                path=f'{path}[{glyph!r}]'))
    return None


def _shape_problem(block, key, value, path):
    """The one problem with a value that is the right type and still
    cannot be read: a label that does not name its monster, a hundredth
    that is not whole, a wrong pair half, a glyph with no tileset, or a
    wrong list element."""
    pointer = f'/{block.name}/{key.name}'
    if key.kind == 'name-label':
        if '{name}' not in value:
            return Problem('no-name-slot', pointer,
                           _say(block, key, 'no-name-slot').format(path=path))
        return None
    if key.kind == 'word':
        if WORD.fullmatch(value):
            return None
        return Problem('wrong-element', pointer,
                       _say(block, key, 'wrong-element').format(path=path))
    if key.kind == 'glyphs':
        return _glyph_problem(block, key, value, path)
    if key.kind == 'hundredths':
        # Whole hundredths before range: a value that is not a hundredth
        # at all is reported as that, not as a bound it never met.
        if not _whole_hundredths(value):
            return Problem('not-hundredths', pointer,
                           _say(block, key, 'not-hundredths').format(path=path))
        return None
    if key.kind == 'hundredths-pair':
        # The half that is not a whole hundredth is named; a half that is
        # out of range is the pair's own `out-of-range` and says so.
        for index, half in enumerate(value):
            if _whole_hundredths(half):
                continue
            return Problem(
                'not-hundredths', f'/{block.name}/{key.name}/{index}',
                _say(block, key, 'not-hundredths').format(
                    path=f'{path}[{index}]'))
        return None
    for index, element in enumerate(value):
        problem = _element_problem(block, key, element, index, path)
        if problem is not None:
            return problem
    return None


def _value_problem(block, key, value, path):
    pointer = f'/{block.name}/{key.name}'
    if key.kind == 'enum':
        if value not in key.choices:
            return Problem(
                'not-in-choices', pointer,
                _say(block, key, 'not-in-choices').format(
                    name=block.name, key=key.name, path=path,
                    choices=_render_choices(key.choices)))
        return None
    if not _type_ok(key.kind, value):
        return Problem(
            'wrong-type', pointer,
            _say(block, key, 'wrong-type').format(
                path=path, kind=key.kind))
    if key.kind == 'hundredths' and not _whole_hundredths(value):
        return _shape_problem(block, key, value, path)
    if key.kind in ('pair', 'glyphs', 'enums'):
        # A pair always reports at the half that is wrong, so it never
        # answers as one value: `groups.minions[1]` names the problem.
        # A tile table and a pattern are read the same way: the glyph
        # and the entry, not the whole key.
        return _shape_problem(block, key, value, path)
    if key.kind == 'hundredths-pair':
        # The halves first - a curve end that is not a whole hundredth is
        # not a bound it ever met - and then the pair's own range, which
        # is one sentence about the curve rather than two about its ends.
        problem = _shape_problem(block, key, value, path)
        if problem is not None:
            return problem
    if _out_of_range(key, value):
        return _range_problem(block, key, value, path, pointer)
    if key.kind in ('name-label', 'ids', 'words', 'word'):
        return _shape_problem(block, key, value, path)
    return None


def _sub_problems(block, key, value, at='') -> list[Problem]:
    """Every problem with the block a key's value holds, moved into place.

    A sub-block's pointer and its sentences are written against the
    sub-block's own name - `/size/w`, `size.w` - and this moves both to
    where the value actually is: `/section/size/w` and `section.size.w`
    for a sub-block of a key, `/section/families/0/weight` for one element
    of a list of them. A pointer without its path moved would leave a
    sentence naming one place and a pointer naming another.
    """
    sub = key.sub
    stem = f'/{block.name}/{key.name}'
    skip = len(sub.name) + 1        # '/size' - the sub-block's own root
    out: list[Problem] = []
    if key.kind == 'list':
        for index, element in enumerate(value):
            root = f'{at or block.name}.{key.name}[{index}]'
            for problem in check(sub, element, None, root):
                out.append(Problem(
                    problem.code,
                    f'{stem}/{index}{problem.pointer[skip:]}',
                    problem.sentence))
        return out
    for problem in check(sub, value, None, f'{at or block.name}.{key.name}'):
        out.append(Problem(problem.code,
                           f'{stem}{problem.pointer[skip:]}',
                           problem.sentence))
    return out


def check(block, value, known=None, at='') -> list[Problem]:
    """Every problem with `value` against `block`, in stable order.

    A non-object value stops at one `not-object` problem. Otherwise the
    value's unknown keys come first, in the value's own order, then
    each table key in table order: a missing required key, else the
    value, else the block the key holds (`Key.sub`) in the same place in
    the order. `known` is accepted and ignored (the id checks are the
    validators' own; see `EVENTS`).

    `at` is the dotted path of this block's own root, and only the
    sub-block walk passes it: it is what makes a sentence inside a
    sub-block name where in the pack the wrong value is.
    """
    if not isinstance(value, dict):
        return [Problem(
            'not-object', f'/{block.name}',
            _say(block, None, 'not-object').format(
                name=block.name, example=block.example))]

    problems: list[Problem] = []
    table_names = {key.name for key in block.keys}
    for name in value:
        if name not in table_names:
            problems.append(Problem(
                'unknown-key', f'/{block.name}/{name}',
                _say(block, None, 'unknown-key').format(
                    name=block.name, key=name, keys=_join_keys(block))))

    for key in block.keys:
        path = f'{at or block.name}.{key.name}'
        if key.required and key.name not in value:
            problems.append(Problem(
                'missing-key', f'/{block.name}/{key.name}',
                _say(block, key, 'missing-key').format(
                    name=block.name, key=key.name, example=block.example)))
            continue
        if key.name not in value:
            continue
        problem = _value_problem(block, key, value[key.name], path)
        if problem is not None:
            problems.append(problem)
            continue
        if key.sub is not None and not (key.kind == 'str-or-obj'
                                        and not isinstance(value[key.name], dict)):
            problems.extend(_sub_problems(block, key, value[key.name], at))
    return problems


def check_item(value, at: str = '') -> list[Problem]:
    """Every problem with an item's ADR 0017 fields: `rarity`, `traits`
    and `roll`. An item with none of the three has no problems at all.

    Only the added keys are read, and the pack's own words for the rest are
    left exactly as they were: see `ITEM` for why the first nine keys are
    in that table and not in this walk. `at` is the item's dotted path, so
    a sentence that names its own field reads `items.potion-1.roll`.
    """
    if not isinstance(value, dict):
        return []
    added = {key: value[key] for key in ITEM_ADDED if key in value}
    return check(ITEM, added, at=at)


def _moved(problem: Problem, name: str) -> Problem:
    """A problem about one affix record, moved to where the record is."""
    return Problem(problem.code, f'/{name}{problem.pointer[len("/affix"):]}',
                   problem.sentence)


SAVES = Block(
    name='saves',
    example='{"rules": "persist"}',
    keys=(
        Key('rules', 'enum', choices=('persist', 'reset')),
        Key('legacy', 'enum', choices=('fresh', 'from-log')),
    ),
)

SOUND = Block(
    name='sound',
    example='{"theme": "soft"}',
    keys=(Key('theme', 'enum', choices=('soft',), required=True),),
    say={
        'unknown-key': '{name} may only hold {keys}, not {key!r}',
        'missing-key': '{name} must hold a {key}, such as {example}',
        'not-in-choices': '{name} {key} must be the string {choices}',
    },
)

# An affix is one record in the pack's `affixes.json`, shared by every
# Section. `id` and `label` are required; every other key is optional
# and a default is no change - 1.0 for a multiplier, 0 for `sight` and
# `extra_drops`. The three multipliers and `scale` are bounded in
# hundredths, which is how the pack writes them and how a stat is
# scaled. `moves` is reserved (ADR 0014) and is refused here as the
# unknown key it is: it is a format-2 key, and this slice adds no
# format.
AFFIX = Block(
    name='affix',
    example='{"id": "big", "label": "Big {name}"}',
    keys=(
        Key('id', 'str', required=True),
        Key('label', 'name-label', required=True),
        Key('hp', 'hundredths', lo=100, hi=200),
        Key('atk', 'hundredths', lo=100, hi=200),
        Key('xp', 'hundredths', lo=100, hi=200),
        Key('sight', 'int', lo=0, hi=2),
        Key('scale', 'hundredths', lo=100, hi=150),
        Key('extra_drops', 'int', lo=0, hi=2),
    ),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

# A Section's `elites` block: how many elites a floor may carry, and the
# affix ids they draw from. `per_floor` is a `[lo, hi]` pair whose `hi`
# is at most 2 (ADR 0014, "Hard caps": 2 lone elites).
ELITES = Block(
    name='elites',
    example='{"per_floor": [1, 2], "affixes": ["big"]}',
    keys=(
        Key('per_floor', 'pair', lo=0, hi=2, required=True),
        Key('affixes', 'ids', required=True),
    ),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

# A Section's `groups` block. `minions` is 1 to 3, so a group is at most
# four members counting its leader; `wake` is frozen at `all`, because
# a partial wake is a rule the AI does not have; `leash` is 3 to 12
# tiles. Only `per_floor` and `minions` are required - the rest have a
# default the generator supplies.
GROUPS = Block(
    name='groups',
    example=('{"per_floor": [1, 2], "minions": [2, 3], "leader": "elite", '
             '"same_family": true, "wake": "all", "leash": 6}'),
    keys=(
        Key('per_floor', 'pair', lo=0, hi=3, required=True),
        Key('minions', 'pair', lo=1, hi=3, required=True),
        Key('leader', 'enum', choices=('elite', 'normal')),
        Key('same_family', 'bool'),
        Key('wake', 'enum', choices=('all',)),
        Key('leash', 'int', lo=3, hi=12),
    ),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

# The descent block (slice E1): the run a descent is drawn from, the
# tile in a baked region it starts at, and the Sections it walks. Only
# the run seed and the Section list are the engine's business; `card`
# is the pack's own sentence for the one-time start-over card.
#
# `story_end` is ADR 0015 Amendment 1 section 1: the flag whose being true
# ends the story and opens the endless board. It is optional and its
# default is the flag the ADR's own design reached for, so a pack that
# names none reads and plays exactly as it did.
DESCENT = Block(
    name='descent',
    example='{"run_seed": "ember", "entry": {"region": "town", "at": [7, 5]},'
            ' "sections": [{"id": "cellar", "floors": 9}]}',
    keys=(
        Key('run_seed', 'str', required=True, lo=1, hi=200),
        Key('entry', 'obj', required=True),
        Key('sections', 'list', required=True),
        Key('card', 'obj'),
        Key('story_end', 'str', lo=1, hi=64,
            say={'wrong-type': '{path} must be the name of a flag, such as '
                               '"king-slain"'}),
    ),
)

# The tile the descent starts from: a baked region of this pack and one
# tile in it.
DESCENT_ENTRY = Block(
    name='descent entry',
    example='{"region": "town", "at": [7, 5]}',
    keys=(
        Key('region', 'str', required=True),
        Key('at', 'pair', required=True, lo=0, hi=999),
    ),
    say={
        'missing-key': '{name} must hold its {key}, such as {example}',
        'wrong-type': '{path} must be a tile as [x, y], such as [7, 5]',
    },
)

# ------------------------------------------------ the Section pack (E4)
#
# PLAN.md section 2 writes the Section pack in one line, and this block is
# that line, key for key and in its order: `section`, `id`, `floors`,
# `size`, `rooms`, `tiles`, `fog`, `families`, `pattern`, `specials`,
# `elites`, `groups`, `curve`, `loot`, `stamps`, `pois`, `warden`,
# `vault`. Nothing here is invented and nothing is dropped.
#
# Only TWO keys are required: `id` and `families`. `id` is the floor key's
# middle - a Section without one gives every floor of the pack the same
# key - and `families` is what the pop stage draws from. Everything else
# defaults in `vefr.sections`, and a Section that names none of it is the
# floor it always was. A table that demanded the whole shape, or even the
# five keys ADR 0014's fixtures carry, would refuse packs the generator
# already reads: `test_a_section_that_names_no_elites_at_all_is_fine` is
# frozen evidence that a Section may leave `elites` out.
#
# `elites` and `groups` are typed as objects HERE and read by their own
# tables in `check_section`, because ADR 0014 pinned their pointers at
# `/elites/per_floor` and a sub-block would have moved them under
# `/section`.
PATTERN_SLOTS = ('entry', 'n', 'special', 'landing', 'warden')
SPECIAL_KINDS = ('treasure', 'infested', 'hub')

SIZE = Block(
    name='size',
    example='{"w": [64, 80], "h": [44, 56]}',
    keys=(
        Key('w', 'pair', lo=32, hi=128, required=True),
        Key('h', 'pair', lo=24, hi=96, required=True,
            say={'wrong-type': ('{path} must be a [lo, hi] pair of whole '
                                'numbers, such as [44, 56]')}),
    ),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

# The widest floor a Section may declare - `SIZE`'s `w` upper bound, read
# from the block rather than written again - and the quarter of it that is
# the largest radius a lit disc may be. Reading it from `SIZE` is what
# keeps the two in step: raise the ceiling on a floor and the fog ceiling
# moves with it.
SIZE_WIDTH_HI = next(k.hi for k in SIZE.keys if k.name == 'w')
FOG_RADIUS_MAX = SIZE_WIDTH_HI // 4

# How far a Section sees. The lit area on a generated floor is a filled
# disc of `radius` tiles around the arrival tile, so the radius reads as
# a fraction of the floor the same Section declares rather than as a
# bare constant. Two properties hold at the ceiling, and
# `tests/test_fog_radius.py` holds both: a Section may ask for any radius
# from 2 to it, and even the largest is a disc (2*32+1 = 65 tiles across)
# that still fits inside the largest floor the schema permits on BOTH
# axes (128 wide, 96 tall) - so no radius a pack may name is a disc no
# floor could hold.
#
# The ceiling was 8, which no ADR, PLAN.md or Section pack records the
# reason for (vefr #364); at 8 the disc is 17 tiles across - a fifth of
# the 80-tile-wide floor a cellar-shaped Section declares, in the middle
# of a floor that is rooms. The lower bound is unchanged at 2: a
# one-tile ring is not fog. A Section that says no `fog` at all still
# gets `delve.DEFAULT_FOG_RADIUS` - this block bounds what a pack may
# ASK for and changes nothing a pack left out.
FOG = Block(
    name='fog',
    example='{"radius": 4}',
    keys=(Key('radius', 'int', lo=2, hi=FOG_RADIUS_MAX, required=True),),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

FAMILY = Block(
    name='family',
    example='{"family": "rat", "weight": 5, "depth": [1, 6]}',
    keys=(
        Key('family', 'str', lo=1, hi=40, required=True),
        Key('weight', 'int', lo=1, hi=99),
        Key('depth', 'pair', lo=1, hi=99),
    ),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

CURVE = Block(
    name='curve',
    example='{"hp": [1.0, 1.4], "atk": [1.0, 1.3]}',
    keys=(
        Key('hp', 'hundredths-pair', lo=100, hi=300, required=True),
        Key('atk', 'hundredths-pair', lo=100, hi=300, required=True),
    ),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

LOOT = Block(
    name='loot',
    example='{"tier": 1}',
    keys=(Key('tier', 'int', lo=1, hi=9, required=True),),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

# What a drawn item may be (ADR 0017, T3 slice 1). `rarity` is the item's
# own table of pack-chosen names and how likely each is; `traits` is the
# pool a draw takes hidden traits from; `chance` is how often a draw bears
# one at all (0..100, the default when a pool is named), and `max` is how
# many at once (0..4, default 1). The bounds are the draw's: the weights are
# whole and small, so `int(rng() * total)` is one floor of a named stream
# and stays under 2**31 in every pack.
#
# Every sentence here is a whole line naming its own field and no path, so
# the item validator can prefix the item it belongs to and a pack author
# reads one sentence: "item 'a cloudy potion' (potion-1) roll must hold a
# rarity table, such as {"common": 60}". The braces in an example and in a
# sentence are doubled, because every one of them is a `str.format`
# template - the same note the glyph table carries.
ROLL = Block(
    name='roll',
    example='{{"rarity": {{"common": 60, "rare": 40}}, "traits": ["keen"], "chance": 50}}',
    keys=(
        Key('rarity', 'obj', required=True, say={
            'missing-key': 'roll must hold a rarity table, such as {{"common": 60}}',
            'wrong-type': 'roll rarity must be a table of names and whole weights'}),
        Key('traits', 'words', say={
            'wrong-type': 'roll traits must be a list of plain words',
            'wrong-element': 'roll traits must each be one plain word, such as "keen"'}),
        Key('chance', 'int', lo=0, hi=100, say={
            'wrong-type': 'roll chance must be a whole number 0 to 100',
            'out-of-range': 'roll chance must be a whole number 0 to 100'}),
        Key('max', 'int', lo=0, hi=4, say={
            'wrong-type': 'roll max must be a whole number 0 to 4',
            'out-of-range': 'roll max must be a whole number 0 to 4'}),
    ),
)

# One entry of a pack's `items` catalog. The first nine keys are what an
# item has been since the loot slice - each of them checked by the
# validator that owns it (`maplab.item_light_errors`,
# `maplab.item_slot_errors`) or read by the bake and dropped when it does
# not form a usable shape. The last three are ADR 0017: the rarity an item
# is fixed at, the traits it is fixed with, and the `roll` a drawn drop of
# it takes from.
#
# `check_item` - not `check` - is this block's entry point, and it checks
# only the last three keys. The first nine are not re-checked here because
# every one of them accepts something today: a `value` of 0, a `heal` of
# "lots" and a `use` of "" are all silently no-ops the bake already drops,
# and a catalog that carried one has been playing fine. Re-checking them
# here would refuse a pack that was never wrong about them. They are in the
# table so the table states the whole item, not because the table judges it.
ITEM = Block(
    name='item',
    example='{{"name": "a cloudy potion", "sprite": "potion", "rarity": "common"}}',
    keys=(
        # The nine the loot slice and the reward slice added.
        Key('name', 'str', lo=1, hi=80),
        Key('sprite', 'str', lo=1, hi=80),
        Key('value', 'int', lo=1, hi=9999),
        Key('heal', 'int', lo=1, hi=999),
        Key('use', 'str', lo=1, hi=40),
        Key('keep', 'bool'),
        Key('light', 'obj'),
        Key('slot', 'str', lo=1, hi=20),
        Key('mods', 'obj'),
        # The three ADR 0017 added.
        Key('rarity', 'word', say={
            'wrong-type': 'rarity must be one plain word, such as "common"',
            'wrong-element': 'rarity must be one plain word, such as "common"'}),
        Key('traits', 'words', say={
            'wrong-type': 'traits must be a list of plain words',
            'wrong-element': 'traits must each be one plain word, such as "keen"'}),
        Key('roll', 'obj', sub=ROLL, say={
            'wrong-type': 'roll must be an object holding a rarity table'}),
    ),
)

# The keys ADR 0017 added to an item, in table order: what `check_item`
# reads, and what it refuses.
ITEM_ADDED = ('rarity', 'traits', 'roll')

# A Section's warden (ADR 0015): the Blueprint family it is, by id, or a
# record naming that family and, optionally, the warden's own id (its flag is
# `warden:<id>:c<cycle>`) and the key it `carries` into the bag when beaten.
# `yields`, `challenge` and `fightable` (ADR 0015 Amendment 1) are E8d's.
WARDEN = Block(
    name='warden',
    example='{"family": "cellar-king", "carries": "cellar-key"}',
    keys=(
        Key('family', 'str', lo=1, hi=40, required=True),
        Key('id', 'str', lo=1, hi=40),
        Key('carries', 'str', lo=1, hi=40),
    ),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

# A Section's vault (ADR 0015). A bare string is a stamp id and nothing
# else, which is the shape E8b shipped and still plays exactly as it did;
# the record adds the one thing E8c needs to gate on - `sets`, the flag
# the vault's note records, which is what tells the engine a Section has
# been seen. A Section that names no `sets` gets no town gate at all,
# which is the same "the pack wrote nothing" answer every other optional
# key here gives. ADR 0015's record also carries `note`, `chest`,
# `needs` and `home`; those are the vault's own contents, E8b's slice,
# and they stay out until the slices that read them land.
VAULT = Block(
    name='vault',
    example='{"stamp": "vault-cellar", "sets": "vault-1-read"}',
    keys=(
        Key('stamp', 'str', lo=1, hi=40, required=True),
        Key('sets', 'str', lo=1, hi=64, required=True),
    ),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

SECTION = Block(
    name='section',
    example='{"section": 1, "id": "cellar", "floors": 9, "rooms": [12, 18]}',
    keys=(
        Key('section', 'int', lo=1, hi=99),
        Key('id', 'str', lo=1, hi=40, required=True),
        Key('floors', 'int', lo=1, hi=11),
        Key('size', 'obj', sub=SIZE),
        Key('rooms', 'pair', lo=6, hi=40),
        Key('tiles', 'glyphs'),
        Key('fog', 'obj', sub=FOG),
        Key('families', 'list', sub=FAMILY, required=True),
        Key('pattern', 'enums', choices=PATTERN_SLOTS,
            say={'wrong-type': ('{path} must be a list of "entry", "n", '
                                '"special", "landing" and "warden"')}),
        Key('specials', 'enums', choices=SPECIAL_KINDS,
            say={'wrong-type': ('{path} must be a list of "treasure", '
                                '"infested" and "hub"')}),
        Key('elites', 'obj'),
        Key('groups', 'obj'),
        Key('curve', 'obj', sub=CURVE),
        Key('loot', 'obj', sub=LOOT),
        Key('stamps', 'ids',
            say={'wrong-type': '{path} must be a list of stamp ids, such as '
                               '["cellar"]',
                 'wrong-element': '{path} must be a stamp id, such as '
                                  '"cellar"'}),
        Key('pois', 'ids',
            say={'wrong-type': '{path} must be a list of point-of-interest '
                               'names, such as ["the rusted grate"]',
                 'wrong-element': '{path} must be a point of interest, such '
                                  'as "the rusted grate"'}),
        Key('warden', 'str-or-obj', lo=1, hi=40, sub=WARDEN,
            say={'wrong-type': ('{path} must be a family id, such as '
                                '"cellar-king", or a record, such as '
                                '{{"family": "cellar-king", "carries": "cellar-key"}}')}),
        Key('vault', 'str-or-obj', lo=1, hi=40, sub=VAULT,
            say={'wrong-type': ('{path} must be a stamp id, such as '
                                '"vault-cellar", or a record, such as '
                                '{{"stamp": "vault-cellar", '
                                '"sets": "vault-1-read"}}')}),
    ),
    say={'missing-key': '{name} must hold its {key}'},
)

# Town states (ADR 0015, "Town states", and Amendment 1 section 3): the
# regions whose look depends on a story flag. One block names one region
# and the states that region takes; `use` is an ordinary authored region,
# baked as it always was, and the LAST state whose `when` flag reads true
# is the one that loads. These are two records in one block name because
# the list form is the same record repeated - `check_town_states` walks
# both, and nothing else in the table has to know which shape it is on.
TOWN_STATE = Block(
    name='town state',
    example='{"id": "act-2", "when": "vault-1-read", "use": "town-act-2"}',
    keys=(
        Key('id', 'str', lo=1, hi=40, required=True),
        Key('when', 'str', lo=1, hi=64, required=True),
        Key('use', 'str', lo=1, hi=64, required=True),
    ),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

TOWN_STATES = Block(
    name='town states',
    example='{"region": "town", "states": [{"id": "act-2", '
            '"when": "vault-1-read", "use": "town-act-2"}]}',
    keys=(
        Key('region', 'str', lo=1, hi=64, required=True),
        Key('states', 'list', sub=TOWN_STATE, required=True),
    ),
    say={'missing-key': '{name} must hold its {key}, such as {example}'},
)

# A scenario is one pack file, `scenarios/<name>.json`: a named game state
# the dev tools open the woven game in (ADR 0016's Player Driver, slice P2).
# It is an authored Session Capsule - the same VEFR-owned save keys a
# capture would hold, written by hand - plus the place the hero stands.
# These rows speak for its shape; `vefr.scenarios` checks it against the
# pack (the region, the tile, the items) and writes the save keys.
SCENARIO_START = Block(
    name='scenario start',
    example='{"region": "town", "at": [4, 6]} or {"depth": 5}',
    keys=(
        Key('region', 'str', lo=1, hi=64),
        Key('at', 'pair', lo=0, hi=999,
            say={'wrong-type': '{path} must be an [x, y] tile, such as [4, 6]'}),
        Key('depth', 'int', lo=1, hi=9999),
    ),
)

SCENARIO = Block(
    name='scenario',
    example='{"start": {"depth": 5}, "gold": 120, "bag": ["potion"]}',
    keys=(
        Key('start', 'obj', required=True, sub=SCENARIO_START),
        Key('note', 'str', lo=1, hi=200),
        Key('gold', 'int', lo=0, hi=1_000_000_000),
        Key('bag', 'list'),
        Key('equipped', 'obj'),
        Key('xp', 'int', lo=0, hi=1_000_000_000),
        Key('hp', 'int', lo=1, hi=1_000_000),
    ),
)

BLOCKS = {
    'saves': SAVES,
    'sound': SOUND,
    'affix': AFFIX,
    'elites': ELITES,
    'groups': GROUPS,
    'descent': DESCENT,
    'descent entry': DESCENT_ENTRY,
    'section': SECTION,
    'town states': TOWN_STATES,
    'town state': TOWN_STATE,
    'scenario': SCENARIO,
    'scenario start': SCENARIO_START,
    'item': ITEM,
}


# ------------------------------------------------- the event vocabulary

# One row per event a rule - and a sticker - may fire on: the name the
# pack writes, the payload it carries, and for each field what kind of
# pack id it names. A field with no `ref` is a number the table bounds
# itself, and the bounds are the contract's.
#
# The six events a rule may fire on became thirteen: the first six are
# the original vocabulary; the next five are facts the player already
# performs (a fight won, a thing bought or sold, a book closed, the
# watch turned) so the world can notice them. `says` is deliberately
# absent: the woven player has nowhere to type words, so an event that
# waited on typed speech could never fire.
#
# The last two are the hero's own two facts: `falls` and `wakes` (vefr
# #365). `defeats` is the player killing something; its mirror did not
# exist, so death was indistinguishable from a bug and a pack had to
# fake it with `enters` - a line that then fires on every ordinary
# arrival. `falls` carries the enemy that did it (`what`, empty when
# nothing did) and the place the hero fell in (`where`); on a descent
# floor that place is the floor's own name, `<section>-<cycle>-<floor>`,
# so one id says how deep.
#
# This is the one place the vocabulary is typed on the Python side. The
# woven player holds a JavaScript twin of it today (the `EVENTS` table
# in the rules engine); slice S3 generates that block from here, and
# until it does, `tests/test_event_table.py` fails if the two drift.
#
# The sentence each way of being wrong is spoken is NOT here: a rule's
# `when` and a sticker's `when` are read by two validators that speak in
# two different authors' words, and both read this table.
EVENTS = {
    'starts': (),
    'enters': (Key('place', 'ref', ref='place'),),
    'comes-near': (Key('who', 'ref', ref='thing'),
                   Key('distance', 'int', lo=0, hi=9)),
    'opens': (Key('what', 'ref', ref='thing'),),
    'picks-up': (Key('what', 'ref', ref='item'),),
    'uses-with': (Key('item', 'ref', ref='item'),
                  Key('with', 'ref', ref='thing')),
    'defeats': (Key('what', 'ref', ref='enemy'),),
    'buys': (Key('what', 'ref', ref='item'),),
    'sells': (Key('what', 'ref', ref='item'),),
    'reads': (Key('what', 'ref', ref='book'),),
    'phase-changes': (Key('to', 'ref', ref='phase'),),
    'falls': (Key('what', 'ref', ref='enemy'),
              Key('where', 'ref', ref='place')),
    'wakes': (Key('where', 'ref', ref='place'),),
}


# ------------------------------------------------- the checks that span records

def check_descent(block: dict) -> list[Problem]:
    """Every problem with a descent's own Sections, at their own pointers.

    One question two records cannot answer between them, so it lives here
    and not in the table: each Section is shaped like a Section. `block`
    is the resolved `descent` block - the Sections already read out of
    `sections/<id>.json` when the pack names them by id.
    """
    problems: list[Problem] = []
    listed = block.get('sections') if isinstance(block, dict) else None
    if not isinstance(listed, list):
        return problems
    for i, record in enumerate(listed):
        if not isinstance(record, dict):
            problems.append(Problem(
                'wrong-type', f'/sections/{i}',
                f'every Section must be a record, such as {SECTION.example}'))
            continue
        for problem in check(SECTION, record):
            problems.append(Problem(
                problem.code, f'/sections/{i}{problem.pointer[len("/section"):]}',
                problem.sentence))
    return problems


def check_town_states(block) -> list[Problem]:
    """Every problem with a pack's `town_states`, in either of its shapes.

    ADR 0015 wrote one block for the town; Amendment 1 section 3 added a
    list of them, one per region that changes. Both are `TOWN_STATES`
    records and this walks both, so the table above never has to know
    which shape it is on. A region may appear once: two blocks for one
    region are two answers to "what does this town look like now", and
    only one of them would ever load, so the second is a sentence rather
    than a silent winner.
    """
    if isinstance(block, list):
        listed, stems = list(block), [f'/town states/{i}'
                                      for i in range(len(block))]
    elif isinstance(block, dict):
        listed, stems = [block], ['/town states']
    else:
        return [Problem(
            'not-a-block-or-list', '/town states',
            _DEFAULTS['not-a-block-or-list'].format(
                path='town_states', example=TOWN_STATES.example))]

    problems: list[Problem] = []
    seen: set[str] = set()
    for stem, entry in zip(stems, listed):
        for problem in check(TOWN_STATES, entry):
            problems.append(Problem(
                problem.code,
                f'{stem}{problem.pointer[len("/town states"):]}',
                problem.sentence))
        region = entry.get('region') if isinstance(entry, dict) else None
        if not isinstance(region, str) or not region:
            continue
        if region in seen:
            problems.append(Problem(
                'duplicate-region', f'{stem}/region',
                _DEFAULTS['duplicate-region'].format(region=region)))
        seen.add(region)
    return problems


def check_town_regions(block, declared) -> list[Problem]:
    """Every town-state `region` and `use` the pack does not declare.

    Two records the table cannot compare: this block's names and the
    pack's own region list. A `use` naming no region is a state that could
    never load - the town would stay its base and say nothing - so it is a
    sentence here rather than a silence in play. A pack that declares no
    regions at all (`declared` empty) is not asked: the caller reads the
    acts, and a pack with none has nothing to compare against."""
    if not declared:
        return []
    listed = block if isinstance(block, list) else [block]
    problems: list[Problem] = []
    for i, entry in enumerate(listed):
        if not isinstance(entry, dict):
            continue
        stem = f'/town states/{i}' if isinstance(block, list) else '/town states'
        named = [(f'{stem}/region', entry.get('region'))]
        states = entry.get('states')
        if isinstance(states, list):
            named += [(f'{stem}/states/{j}/use', state.get('use'))
                      for j, state in enumerate(states)
                      if isinstance(state, dict)]
        for pointer, name in named:
            if isinstance(name, str) and name and name not in declared:
                problems.append(Problem(
                    'unknown-region', pointer,
                    _DEFAULTS['unknown-region'].format(id=name)))
    return problems


def named_affix_ids(section: dict) -> list[str]:
    """The affix ids a Section's `elites` block names, in pack order.

    The rule the two affix checks share, and the one a caller needs on
    its own: `vefr.maplab` has to say WHICH ids a Section names when the
    pack has no affix list at all, which is a question about the pack's
    files rather than about the list, and `shapes` cannot see the files.
    Only ids that could name an affix are returned - a non-string or an
    empty string is the `ids` kind's own sentence to speak, and naming it
    here as well would say it twice.
    """
    elites = section.get('elites')
    if not isinstance(elites, dict):
        return []
    affixes = elites.get('affixes')
    if not isinstance(affixes, list):
        return []
    return [a for a in affixes if isinstance(a, str) and a]


def check_affixes(section: dict, affixes) -> list[Problem]:
    """Every problem with the pack's affix list read against `section`.

    Three things only two records can say between them: that each
    record is the shape an affix is, that every id is its own, and that
    every id a Section names is one the pack defines. A record that is
    not a record stops it there, because an affix list that cannot be
    read cannot be searched for an id either.
    """
    if not isinstance(affixes, list):
        return [Problem('not-a-list', '/affixes', _DEFAULTS['not-a-list'])]

    problems: list[Problem] = []
    ids: list[str] = []
    for i, record in enumerate(affixes):
        for problem in check(AFFIX, record):
            problems.append(_moved(problem, f'affixes/{i}'))
        if isinstance(record, dict) and isinstance(record.get('id'), str):
            ids.append(record['id'])
    if problems or len(ids) != len(affixes):
        return problems

    # Every id against every id that came before it, not just the one
    # beside it: "ids are unique" (ADR 0014, "Affix") is a claim about
    # the whole list, and `[big, quick, big]` repeats an id exactly as
    # much as `[big, big]` does. The pointer is the SECOND record to
    # carry the id, so the pair that collides is named in one sentence.
    seen: set[str] = set()
    for i, aid in enumerate(ids):
        if aid in seen:
            return [Problem('duplicate-id', f'/affixes/{i}/id',
                             _DEFAULTS['duplicate-id'].format(id=aid))]
        seen.add(aid)

    defined = set(ids)
    for i, aid in enumerate(named_affix_ids(section)):
        if aid not in defined:
            return [Problem('undefined-affix', f'/elites/affixes/{i}',
                             _DEFAULTS['undefined-affix'].format(id=aid))]
    return []


def check_section(section: dict, affixes=None, resolve=None) -> list[Problem]:
    """Every problem with one Section pack, in stable order.

    `section` is a Section pack, `affixes` its pack's affix list, and
    `resolve` a callable taking a family id and returning the base
    record it resolves to, or None for a family the Blueprint does not
    have (`vefr.blueprint.resolve_family` behind that one wrapper -
    `shapes` may not import it). A caller with no `resolve` gets the
    family checks skipped rather than wrong.

    The order is the one ADR 0014's tests pinned, and the Section table
    comes first without disturbing it: the whole Section, then the two
    blocks it holds whose pointers are the Section's own (`elites`,
    `groups`), then the affix list, then the families, then the groups an
    elite leads, then the pattern.
    """
    problems: list[Problem] = []
    problems.extend(check(SECTION, section))
    if not isinstance(section, dict):
        # A Section pack that is not an object is one `not-object`
        # sentence and nothing else: the checks below all read it as a
        # table and there is nothing to read.
        return problems
    for name, block in (('elites', ELITES), ('groups', GROUPS)):
        if name in section:
            problems.extend(check(block, section[name]))

    if affixes is not None:
        problems.extend(check_affixes(section, affixes))

    families = section.get('families')
    if resolve is not None and isinstance(families, list):
        for i, entry in enumerate(families):
            if not isinstance(entry, dict):
                continue
            family = entry.get('family')
            if not isinstance(family, str) or not family:
                continue
            record = resolve(family)
            if record is None:
                return problems + [Problem(
                    'unknown-family', f'/families/{i}/family',
                    _DEFAULTS['unknown-family'].format(id=family))]
            missing = [stat for stat in ('hp', 'atk') if stat not in record]
            if missing:
                return problems + [Problem(
                    'no-stat', f'/families/{i}/family',
                    _DEFAULTS['no-stat'].format(stat=missing[0], id=family))]

    # A record names its family outright, so that family must resolve. A bare
    # string is checked by nothing here: packs write it both as a family id
    # (Cottage's "cellar-king") and as ADR 0015's warden id ("ashwing"), and
    # refusing either would break a pack that validates today.
    warden = section.get('warden')
    family = warden.get('family') if isinstance(warden, dict) else None
    if resolve is not None and isinstance(family, str) and family \
            and resolve(family) is None:
        problems.append(Problem(
            'unknown-family', '/warden/family',
            _DEFAULTS['unknown-family'].format(id=family)))

    problems.extend(_elite_leader_problems(section))
    problems.extend(_pattern_problems(section))
    return problems


def _pattern_problems(section: dict) -> list[Problem]:
    """Every way one Section's pattern contradicts the Section around it.

    A pattern is a list of slots, one for each floor, and three facts sit
    beside it: how many floors there are, what the last slot is, and what
    the specials list holds. None of those can be read off a single slot,
    so all three checks live here rather than in the table - the same
    reason the affix and family checks do.

    A Section that names no pattern is not one of these: it takes the
    default pattern in `vefr.sections`, which is the one PLAN.md section 4
    writes, and a pack that writes nothing is not a pack that got it
    wrong.
    """
    pattern = section.get('pattern')
    if not isinstance(pattern, list) or not pattern:
        return []
    problems: list[Problem] = []

    floors = section.get('floors')
    if isinstance(floors, int) and not isinstance(floors, bool) \
            and floors != len(pattern):
        problems.append(Problem(
            'pattern-length', '/pattern',
            _DEFAULTS['pattern-length'].format(
                floors=floors, given=len(pattern))))

    last = pattern[-1]
    if last != 'warden':
        problems.append(Problem(
            'no-warden', '/pattern',
            _DEFAULTS['no-warden'].format(slot=last)))

    named = sum(1 for slot in pattern if slot in ('entry', 'landing'))
    if named < 2:
        problems.append(Problem(
            'too-few-landings', '/pattern',
            _DEFAULTS['too-few-landings'].format(given=named)))

    if 'special' in pattern and not section.get('specials'):
        problems.append(Problem(
            'no-specials', '/specials', _DEFAULTS['no-specials']))
    return problems


def _elite_leader_problems(section: dict) -> list[Problem]:
    """A group led by an elite in a Section that names no affix.

    The leader would be a normal monster with a group around it, so the
    pack would get neither the monster it asked for nor the cap it
    spent. A Section with no `elites` block at all is not this: it asks
    for no elites, so its groups have nothing to be led by.
    """
    groups = section.get('groups')
    if not isinstance(groups, dict) or groups.get('leader') != 'elite':
        return []
    if not isinstance(section.get('elites'), dict):
        return []
    if named_affix_ids(section):
        return []
    return [Problem('no-affix-for-elite', '/groups/leader',
                    _DEFAULTS['no-affix-for-elite'])]
