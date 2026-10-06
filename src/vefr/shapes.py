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
table order (a missing required key, else its wrong value).

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

A wrong element of a `pair` or an `ids` is reported at that element's
pointer, and the first wrong element is the one reported, so a key earns
one sentence however wrong its value is.

Three checks cannot live in that table, because each spans records
rather than one value: an affix id the pack does not define, a repeated
id, a family a Section names that the Blueprint does not have, and a
group led by an elite in a Section that names no affix. They are
`check_affixes` and `check_section`, and they return the same
`list[Problem]` and speak the same plain sentences.

The module is standard-library only: `shapes.py` must never import from
`vefr`, or `maplab` would import itself into a cycle. So the one
question `shapes` cannot answer for itself - does this family exist in
the Blueprint, and what does it resolve to - is asked through a
`resolve` callable the caller passes in.
"""

from collections import namedtuple
from dataclasses import dataclass, field
from typing import Mapping


Problem = namedtuple('Problem', 'code pointer sentence')


@dataclass(frozen=True)
class Key:
    name: str
    kind: str               # 'str' | 'int' | 'bool' | 'enum' | 'obj' | 'list' | 'ref'
                             # | 'hundredths' | 'pair' | 'ids' | 'name-label'
    choices: tuple = ()     # enum values, in sentence order
    lo: int | None = None   # int bounds, str length bounds, or hundredths
    hi: int | None = None
    ref: str | None = None  # unused in this slice
    required: bool = False


@dataclass(frozen=True)
class Block:
    name: str               # 'saves'
    example: str            # '{"rules": "persist"}'
    keys: tuple             # tuple[Key, ...] in table order
    say: Mapping[str, str] = field(default_factory=dict)  # code -> sentence override


# The default sentence per error code. A block's `say` overrides
# individual codes; where it does not, these are the bytes.
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
}

# The kinds whose wrong values need a sentence of their own. A block's
# `say` still wins over these.
_KIND_SAY = {
    'str': {'wrong-type': '{path} must be a string'},
    'int': {'wrong-type': '{path} must be a whole number'},
    'bool': {'wrong-type': '{path} must be a yes or a no'},
    'hundredths': {
        'wrong-type': '{path} must be a number, such as 1.5',
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
}

# What a `wrong-element` names, per kind.
_ELEMENT_NOUN = {
    'pair': 'a whole number',
    'ids': 'an affix id',
    'hundredths': 'a whole number',
}


def _render_choices(choices) -> str:
    return ' or '.join(f'"{choice}"' for choice in choices)


def _join_keys(block) -> str:
    names = [key.name for key in block.keys]
    if len(names) == 1:
        return names[0]
    return ', '.join(names[:-1]) + ' and ' + names[-1]


def _say(block, key, code) -> str:
    """The sentence for one code about one key: the default, the kind's
    own wording, then the block's. The block has the last word.

    Resolved per key rather than per block, because a block may hold
    two kinds that need different words for the same code - `sight` is
    a whole number and `hp` is a number in hundredths, and one block
    saying both wrong ways would be one of them wrong.
    """
    kind = _KIND_SAY.get(key.kind, {}) if key is not None else {}
    return block.say.get(code) or kind.get(code) or _DEFAULTS[code]


def _as_hundredths(n) -> str:
    """A bound in hundredths as the pack writes it: 100 -> `1.0`."""
    text = f'{n / 100:.2f}'
    return text[:-1] if text.endswith('0') else text


def _type_ok(kind: str, value) -> bool:
    if kind in ('str', 'name-label'):
        return isinstance(value, str)
    if kind == 'int':
        # bool is not an int here, and vice versa.
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == 'bool':
        return isinstance(value, bool)
    if kind == 'obj':
        return isinstance(value, dict)
    if kind in ('list', 'ids'):
        return isinstance(value, list)
    if kind == 'ref':
        return isinstance(value, str)
    if kind == 'hundredths':
        return (isinstance(value, (int, float))
                and not isinstance(value, bool))
    if kind == 'pair':
        return (isinstance(value, list) and len(value) == 2
                and all(isinstance(n, int) and not isinstance(n, bool)
                        for n in value))
    return True


def _whole_hundredths(value) -> bool:
    scaled = value * 100
    return abs(scaled - round(scaled)) < 1e-9


def _out_of_range(key: Key, value) -> bool:
    """Whether a value of this kind falls outside its bounds.

    A `pair` bounds each of its two halves rather than the pair as one
    number, so it answers for the list it is given and for either half
    of it.
    """
    if key.kind == 'pair' and isinstance(value, (list, tuple)):
        return any(_out_of_range(key, n) for n in value)
    if key.kind in ('int', 'pair'):
        return ((key.lo is not None and value < key.lo)
                or (key.hi is not None and value > key.hi))
    if key.kind in ('str', 'name-label'):
        n = len(value)
        return ((key.lo is not None and n < key.lo)
                or (key.hi is not None and n > key.hi))
    if key.kind == 'hundredths':
        return ((key.lo is not None and value * 100 < key.lo)
                or (key.hi is not None and value * 100 > key.hi))
    return False


def _bounds(key: Key):
    """The two numbers an `out-of-range` sentence quotes for `key`."""
    if key.kind == 'hundredths':
        return _as_hundredths(key.lo), _as_hundredths(key.hi)
    return key.lo, key.hi


def _range_problem(block, key, value, path, pointer):
    lo, hi = _bounds(key)
    return Problem('out-of-range', pointer,
                   _say(block, key, 'out-of-range').format(
                       path=path, lo=lo, hi=hi))


def _element_problem(block, key, value, index, path):
    """The one problem with element `index` of a `pair` or an `ids`."""
    pointer = f'/{block.name}/{key.name}/{index}'
    here = f'{path}[{index}]'
    if key.kind == 'pair':
        if _out_of_range(key, value):
            return _range_problem(block, key, value, here, pointer)
        return None
    if isinstance(value, str) and value:
        return None
    return Problem('wrong-element', pointer,
                   _say(block, key, 'wrong-element').format(
                       path=here, noun=_ELEMENT_NOUN.get(key.kind, 'a value')))


def _shape_problem(block, key, value, path):
    """The one problem with a value that is the right type and still
    cannot be read: a label that does not name its monster, a hundredth
    that is not whole, a wrong pair half, or a wrong list element."""
    pointer = f'/{block.name}/{key.name}'
    if key.kind == 'name-label':
        if '{name}' not in value:
            return Problem('no-name-slot', pointer,
                           _say(block, key, 'no-name-slot').format(path=path))
        return None
    if key.kind == 'hundredths':
        # Whole hundredths before range: a value that is not a hundredth
        # at all is reported as that, not as a bound it never met.
        if not _whole_hundredths(value):
            return Problem('not-hundredths', pointer,
                           _say(block, key, 'not-hundredths').format(path=path))
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
    if key.kind == 'pair':
        # A pair always reports at the half that is wrong, so it never
        # answers as one value: `groups.minions[1]` names the problem.
        return _shape_problem(block, key, value, path)
    if _out_of_range(key, value):
        return _range_problem(block, key, value, path, pointer)
    if key.kind in ('name-label', 'ids'):
        return _shape_problem(block, key, value, path)
    return None


def check(block, value, known=None) -> list[Problem]:
    """Every problem with `value` against `block`, in stable order.

    A non-object value stops at one `not-object` problem. Otherwise the
    value's unknown keys come first, in the value's own order, then
    each table key in table order. `known` is accepted and ignored (the
    id checks are the validators' own; see `EVENTS`).
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
        path = f'{block.name}.{key.name}'
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
    return problems


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

BLOCKS = {
    'saves': SAVES,
    'sound': SOUND,
    'affix': AFFIX,
    'elites': ELITES,
    'groups': GROUPS,
}


# ------------------------------------------------- the event vocabulary

# One row per event a rule - and a sticker - may fire on: the name the
# pack writes, the payload it carries, and for each field what kind of
# pack id it names. A field with no `ref` is a number the table bounds
# itself, and the bounds are the contract's.
#
# The six events a rule may fire on became eleven: the first six are
# the original vocabulary; the last five are facts the player already
# performs (a fight won, a thing bought or sold, a book closed, the
# watch turned) so the world can notice them. `says` is deliberately
# absent: the woven player has nowhere to type words, so an event that
# waited on typed speech could never fire.
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
}


# ------------------------------------------------- the checks that span records

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
    """Every problem with one Section pack's elites and groups.

    `section` is a Section pack, `affixes` its pack's affix list, and
    `resolve` a callable taking a family id and returning the base
    record it resolves to, or None for a family the Blueprint does not
    have (`vefr.blueprint.resolve_family` behind that one wrapper -
    `shapes` may not import it). A caller with no `resolve` gets the
    family checks skipped rather than wrong.
    """
    problems: list[Problem] = []
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

    problems.extend(_elite_leader_problems(section))
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
