"""shapes - the schema table for flat world-pack blocks.

One row per block: the keys it may hold, and the sentence each way a
value can be wrong is spoken in. The validators in `maplab.py` call
`check` and keep returning `list[str]`, so no caller changes.

`check(block, value)` returns a list of `Problem(code, pointer,
sentence)`. Emission order is stable: stop at `not-object`; then the
value's unknown keys in the value's own order; then each table key in
table order (a missing required key, else its wrong value).

`known` is reserved for slice S2's `unknown-ref`; it is accepted and
ignored here.

The module is standard-library only: `shapes.py` must never import
from `vefr`, or `maplab` would import itself into a cycle.
"""

from collections import namedtuple
from dataclasses import dataclass, field
from typing import Mapping


Problem = namedtuple('Problem', 'code pointer sentence')


@dataclass(frozen=True)
class Key:
    name: str
    kind: str               # 'str' | 'int' | 'bool' | 'enum' | 'obj' | 'list' | 'ref'
    choices: tuple = ()     # enum values, in sentence order
    lo: int | None = None   # int bounds, or str length bounds
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
}


def _render_choices(choices) -> str:
    return ' or '.join(f'"{choice}"' for choice in choices)


def _join_keys(block) -> str:
    return ' and '.join(key.name for key in block.keys)


def _type_ok(kind: str, value) -> bool:
    if kind == 'str':
        return isinstance(value, str)
    if kind == 'int':
        # bool is not an int here, and vice versa.
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == 'bool':
        return isinstance(value, bool)
    if kind == 'obj':
        return isinstance(value, dict)
    if kind == 'list':
        return isinstance(value, list)
    if kind == 'ref':
        return isinstance(value, str)
    return True


def _out_of_range(key: Key, value) -> bool:
    if key.kind == 'int':
        return ((key.lo is not None and value < key.lo)
                or (key.hi is not None and value > key.hi))
    if key.kind == 'str':
        n = len(value)
        return ((key.lo is not None and n < key.lo)
                or (key.hi is not None and n > key.hi))
    return False


def _value_problem(block, key, value, path, templates):
    pointer = f'/{block.name}/{key.name}'
    if key.kind == 'enum':
        if value not in key.choices:
            return Problem(
                'not-in-choices', pointer,
                templates['not-in-choices'].format(
                    name=block.name, key=key.name, path=path,
                    choices=_render_choices(key.choices)))
        return None
    if not _type_ok(key.kind, value):
        return Problem(
            'wrong-type', pointer,
            templates['wrong-type'].format(path=path, kind=key.kind))
    if _out_of_range(key, value):
        return Problem(
            'out-of-range', pointer,
            templates['out-of-range'].format(path=path, lo=key.lo, hi=key.hi))
    return None


def check(block, value, known=None) -> list[Problem]:
    """Every problem with `value` against `block`, in stable order.

    A non-object value stops at one `not-object` problem. Otherwise the
    value's unknown keys come first, in the value's own order, then
    each table key in table order. `known` is accepted and ignored
    (reserved for slice S2's `unknown-ref`).
    """
    templates = dict(_DEFAULTS)
    templates.update(block.say)

    if not isinstance(value, dict):
        return [Problem(
            'not-object', f'/{block.name}',
            templates['not-object'].format(
                name=block.name, example=block.example))]

    problems: list[Problem] = []
    table_names = {key.name for key in block.keys}
    for name in value:
        if name not in table_names:
            problems.append(Problem(
                'unknown-key', f'/{block.name}/{name}',
                templates['unknown-key'].format(
                    name=block.name, key=name, keys=_join_keys(block))))

    for key in block.keys:
        path = f'{block.name}.{key.name}'
        if key.required and key.name not in value:
            problems.append(Problem(
                'missing-key', f'/{block.name}/{key.name}',
                templates['missing-key'].format(
                    name=block.name, key=key.name, example=block.example)))
            continue
        if key.name not in value:
            continue
        problem = _value_problem(block, key, value[key.name], path, templates)
        if problem is not None:
            problems.append(problem)
    return problems


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

BLOCKS = {'saves': SAVES, 'sound': SOUND}
