"""S1 (tighten-shapes plan section 4). FROZEN CONTRACT for src/vefr/shapes.py (stdlib only).

check(block, value) -> list[Problem]; Problem is a namedtuple (code, pointer, sentence). Codes are stable:
not-object, unknown-key, missing-key, not-in-choices, out-of-range, wrong-type, unknown-ref (this slice emits the
first five and wrong-type). Emission order: stop at not-object; then unknown keys in the value's own order; then each
table key in table order (missing, else value). BLOCKS maps a block name to its Block; saves and sound are the first
two. maplab.saves_errors and maplab.sound_errors become `[p.sentence for p in shapes.check(...)]`, byte-identical
(tests/test_validator_golden.py proves it).
"""
import inspect

from vefr import maplab, shapes


def test_the_table_holds_saves_and_sound():
    assert {"saves", "sound"} <= set(shapes.BLOCKS)


def test_a_good_value_has_no_problems():
    assert shapes.check(shapes.BLOCKS["saves"], {"rules": "persist"}) == []
    assert shapes.check(shapes.BLOCKS["sound"], {"theme": "soft"}) == []


def test_not_an_object_stops_at_one_problem_with_the_block_example():
    (p,) = shapes.check(shapes.BLOCKS["saves"], [1])
    assert (p.code, p.pointer) == ("not-object", "/saves")
    assert p.sentence == 'saves must be an object such as {"rules": "persist"}'


def test_codes_and_pointers_are_stable():
    ps = shapes.check(shapes.BLOCKS["saves"], {"zeta": 1, "rules": "x", "legacy": "y", "alpha": 2})
    assert [(p.code, p.pointer) for p in ps] == [
        ("unknown-key", "/saves/zeta"), ("unknown-key", "/saves/alpha"),
        ("not-in-choices", "/saves/rules"), ("not-in-choices", "/saves/legacy")]


def test_a_missing_required_key_is_missing_key():
    (p,) = shapes.check(shapes.BLOCKS["sound"], {})
    assert (p.code, p.pointer) == ("missing-key", "/sound/theme")


def test_problems_are_namedtuples():
    p = shapes.check(shapes.BLOCKS["sound"], 5)[0]
    assert p._fields == ("code", "pointer", "sentence")


def test_the_validators_are_now_table_driven_not_hand_written():
    for fn in (maplab.saves_errors, maplab.sound_errors):
        assert "shapes.check" in inspect.getsource(fn)
        assert "errors.append" not in inspect.getsource(fn)


def test_shapes_is_stdlib_only():
    import ast
    tree = ast.parse(inspect.getsource(shapes))
    import sys
    for n in ast.walk(tree):
        names = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""] if isinstance(n, ast.ImportFrom) and not n.level else []
        for m in names:
            assert m.split(".")[0] in sys.stdlib_module_names, m
