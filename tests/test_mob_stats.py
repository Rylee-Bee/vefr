"""`vefr.mob_stats` - whole-number monster stats, the acceptance tests.

These are the acceptance tests of ADR 0014's "Stats, in whole numbers
only" section, written BEFORE `src/vefr/mob_stats.py`, on purpose: the
formula is the contract and a test written after the code only records
what the code happened to do. The module is in the tree now and these
tests pass against it, unchanged: the contract was written down first
and the code was made to meet it, not the other way round.

The formula, as ADR 0014 writes it:

    pct(m)       = round(m * 100)
    curve pct    = lo + (hi - lo) * (k - 1) // (n - 1)
    cycle pct    = min(100 + 20 * c, 160)
    hp           = max(1, base_hp * curve_pct * affix_pct * cycle_pct // 1_000_000)
    atk          = max(1, base_atk * curve_pct * affix_pct * cycle_pct // 1_000_000)

`lo` and `hi` in the curve line are hundredths, not multipliers: the
multiplier `1.4` enters as `pct(1.4) == 140`. Every value this file
reads out of `mob_stats` is compared as an `int`, and the whole-number
property is asserted with `type(v) is int` rather than `isinstance`, so
a `bool` sneaking in would fail too.

Determinism (PLAN.md section 2) is tested directly: the same inputs
must return the same dict on every repeat, with no clock, no global
and no draw. The 200-seed matrix is what ADR 0014's Acceptance names
("the same whole numbers in both languages, for 200 seeds x curves x
affixes x cycles 0-5"); the JavaScript twin and the parity case belong
to the slice that follows this one, and this file is the Python half of
that matrix - same seeds, same curves, same affixes, same cycles.
"""

from __future__ import annotations

import inspect

import pytest

from vefr import mob_stats
from vefr.mob_stats import cycle_pct, curve_pct, mob_stats as stats, pct

# The matrix ADR 0014's Acceptance names.
SEED_COUNT = 200
SEEDS = [f"mobstats-{i}" for i in range(SEED_COUNT)]
CYCLES = list(range(6))  # 0-5, and cycle 0 is the story

# How many times the purity check calls `mob_stats` again on a case it
# has already called. Three: the matrix itself is the wide sweep, this
# is the repeat dimension of it, and 672k cases x 200 repeats was 134
# million calls of a six-argument function.
REPEATS = 3

# The curves the matrix crosses. Each is a real Section `curve` block:
# decimal multipliers, low then high, flat and sloped.
CURVES = [
    {"hp": [1.0, 1.0], "atk": [1.0, 1.0]},  # flat: the floor does not bite
    {"hp": [1.0, 1.4], "atk": [1.0, 1.3]},  # a gentle first Section
    {"hp": [1.2, 2.0], "atk": [1.1, 1.8]},  # a steep late Section
    {"hp": [1.0, 1.1], "atk": [1.0, 1.1]},  # a flat sloped one
]

# The affixes the matrix crosses. `None` is a normal monster, the `quick`
# one carries only a sight term (a missing key is no change), the `big`
# one is the full record, and the last one is deliberately out of the
# ordinary range on the low side to keep the matrix honest about floor
# clamps rather than only about big numbers.
AFFIXES = [
    None,
    {"id": "quick", "label": "Quick {name}", "sight": 1},
    {"id": "big", "label": "Big {name}", "hp": 1.5, "atk": 1.2, "xp": 1.5,
     "sight": 0, "scale": 1.3, "extra_drops": 1},
    {"id": "frail", "label": "Frail {name}", "hp": 0.5, "atk": 0.6, "xp": 0.5,
     "sight": 0, "scale": 0.9, "extra_drops": 0},
    {"id": "keen", "label": "Keen {name}", "hp": 1.1, "atk": 1.9, "xp": 1.2,
     "sight": 2, "scale": 1.0, "extra_drops": 2},
]

# The keys `mob_stats` returns, closed. A key added later is a contract
# change, and this tuple is where the change shows up.
RETURN_KEYS = ("hp", "atk", "xp", "sight", "scale", "extra_drops")


def base_record(hp: int = 10, atk: int = 4, xp: int = 3, sight: int = 5) -> dict:
    """A Blueprint family base record, in format 1's field order."""
    return {"name": "a family", "sprite": "m1", "hp": hp, "atk": atk, "xp": xp,
            "sight": sight, "drops": []}


def section_pack(curve: dict | None = None, floors: int = 9) -> dict:
    """A Section pack carrying only what `mob_stats` reads."""
    pack = {"section": 1, "id": "cellar", "floors": floors}
    if curve is not None:
        pack["curve"] = curve
    return pack


def draw(rng, lo: int, hi: int) -> int:
    """A whole number in [lo, hi] from one draw, the `delve_v3` twin."""
    return lo + int(rng() * (hi - lo + 1))


# ------------------------------------------------------------------ pct


def test_pct_neutral_and_boundaries():
    # 1.0 is the neutral multiplier: its pct is 100, which is what a
    # missing affix key and a flat curve both contribute.
    assert pct(1.0) == 100
    assert pct(1.4) == 140
    assert pct(1.5) == 150
    assert pct(2.0) == 200
    assert pct(1.01) == 101
    assert pct(0.5) == 50


def test_pct_is_always_an_int():
    # The forbidden-float rule ends here: whatever goes in, an `int`
    # comes out. `type(v) is int` and not `isinstance`, so `True`
    # would fail as well.
    for raw in (1.0, 1.4, 1.005, 0.5, 2.0, 1.999, 0.125):
        value = pct(raw)
        assert type(value) is int
    # A multiplier that lands exactly on half a hundredth rounds UP, the
    # way `Math.round` does in the JavaScript twin. Python's built-in
    # `round` is half-to-even and would answer 12 here, so `pct` does
    # not use it. No pack carries 0.125 - multipliers are whole
    # hundredths - and this is the test that says so out loud.
    assert pct(0.125) == 13


def test_pct_scales_whole_hundredths_exactly():
    # The range ADR 0014 puts on an affix multiplier is [1.0, 2.0] in
    # whole hundredths, so the multiply is exact and no rounding rule
    # is in play. This is the case that actually runs.
    for hundredths in range(100, 201):
        assert pct(hundredths / 100) == hundredths


# -------------------------------------------------------------- curve_pct


def test_curve_pct_endpoints():
    # k=1 is the low end, k=n is the high end. Every Section is flat at
    # its own floor 1 and at its own last floor.
    assert curve_pct(100, 140, 1, 9) == 100
    assert curve_pct(100, 140, 9, 9) == 140
    assert curve_pct(110, 180, 1, 5) == 110
    assert curve_pct(110, 180, 5, 5) == 180


def test_curve_pct_interpolates_on_integer_floor_division():
    # lo + (hi - lo) * (k - 1) // (n - 1), floor-divided, never rounded.
    # 100 + 40 * 4 // 8 == 120, and 100 + 30 * 4 // 8 == 115.
    assert curve_pct(100, 140, 5, 9) == 120
    assert curve_pct(100, 130, 5, 9) == 115
    # A division that does not come out even floors down, it does not
    # round to nearest: 100 + 40 * 1 // 3 == 113 (113.33 floors).
    assert curve_pct(100, 140, 2, 4) == 113
    assert curve_pct(100, 140, 3, 4) == 126
    assert curve_pct(100, 140, 4, 4) == 140


def test_curve_pct_is_always_an_int():
    for lo in (100, 113, 150):
        for hi in (100, 141, 200):
            for k in range(1, 12):
                assert type(curve_pct(lo, hi, k, 9)) is int


def test_curve_pct_single_floor_is_the_low_end():
    # n <= 1 has no step to interpolate over, so the curve is `lo`.
    # This is the degenerate case the docstring pins.
    assert curve_pct(100, 140, 1, 1) == 100
    assert curve_pct(100, 200, 1, 0) == 100
    assert curve_pct(100, 200, 1, -3) == 100


def test_curve_pct_flat_curve_is_flat():
    for k in range(1, 10):
        assert curve_pct(140, 140, k, 9) == 140


# -------------------------------------------------------------- cycle_pct


def test_cycle_pct_boundaries():
    # min(100 + 20 * c, 160): the story is 100, the cap lands on c=3.
    assert cycle_pct(0) == 100
    assert cycle_pct(1) == 120
    assert cycle_pct(2) == 140
    assert cycle_pct(3) == 160
    assert cycle_pct(4) == 160
    assert cycle_pct(9) == 160
    assert cycle_pct(1000) == 160
    assert type(cycle_pct(5)) is int


# ---------------------------------------------------------------- mob_stats


def test_returns_only_whole_numbers():
    out = stats(base_record(), {"id": "big", "label": "Big {name}", "hp": 1.5,
                                "atk": 1.2, "xp": 1.5, "sight": 1, "scale": 1.3,
                                "extra_drops": 1},
                section_pack(CURVES[1]), 4, 2)
    assert set(out) == set(RETURN_KEYS)
    for value in out.values():
        # `type(v) is int`, not `isinstance`: a bool is an int in
        # Python and would slip through a weaker assertion.
        assert type(value) is int, out


def test_neutral_affix_equals_the_base_at_neutral_terms():
    # ADR 0014: a missing affix key means no change - multiplier 1.0
    # (pct 100), sight 0, extra_drops 0. So `affix=None` and a
    # explicitly all-neutral affix are the same numbers, and both are
    # the base record under a flat curve on the story cycle.
    base = base_record()
    pack = section_pack(CURVES[0])
    neutral = {"id": "plain", "label": "Plain {name}", "hp": 1.0, "atk": 1.0,
               "xp": 1.0, "sight": 0, "scale": 1.0, "extra_drops": 0}
    from_none = stats(base, None, pack, 1, 0)
    from_neutral = stats(base, neutral, pack, 1, 0)
    assert from_none == from_neutral
    assert from_none == {"hp": 10, "atk": 4, "xp": 3, "sight": 5,
                         "scale": 100, "extra_drops": 0}


def test_empty_section_is_the_flat_default():
    # A Section with no `curve` and no `floors` is the defaults the
    # docstring names: hp [1.0, 1.0], atk [1.0, 1.0], 9 floors.
    out = stats(base_record(), None, {}, 5, 0)
    assert out["hp"] == 10
    assert out["atk"] == 4
    assert out["xp"] == 3


def test_missing_base_stat_clamps_to_one():
    # max(1, ...): a base record that carries nothing still gives a
    # monster with 1 hp and 1 atk, never 0.
    out = stats({"name": "a family", "sprite": "m1", "xp": 0}, None,
                section_pack(), 1, 0)
    assert out["hp"] == 1
    assert out["atk"] == 1
    assert out["xp"] == 0


def test_sight_and_extra_drops_are_whole_and_additive():
    out = stats(base_record(sight=5), {"id": "keen", "label": "Keen {name}",
                                        "sight": 2, "extra_drops": 2},
                section_pack(), 1, 0)
    # The affix's sight is ADDED to the base's, never multiplied.
    assert out["sight"] == 7
    assert out["extra_drops"] == 2
    assert out["scale"] == 100


def test_scale_is_hundredths_and_defaults_to_100():
    assert stats(base_record(), None, section_pack(), 1, 0)["scale"] == 100
    scaled = stats(base_record(), {"id": "big", "label": "Big {name}",
                                   "scale": 1.3}, section_pack(), 1, 0)
    assert scaled["scale"] == 130
    assert type(scaled["scale"]) is int


def test_single_floor_section_uses_the_low_end():
    # n <= 1: the curve is `lo`, so the high end never appears and the
    # numbers are the story's numbers whatever the pack asked for.
    steep = section_pack({"hp": [1.0, 2.0], "atk": [1.0, 2.0]}, floors=1)
    assert stats(base_record(), None, steep, 1, 0)["hp"] == 10
    # The cycle is a separate term and still applies: only the DEPTH
    # ramp degenerates. 10*100*100*160 // 1e6 == 16.
    assert stats(base_record(), None, steep, 1, 3)["hp"] == 16
    # The same pack given its 9 floors has a top step: 10*200*100*100
    # // 1e6 == 20... which is the high end 200 for hp. Checked as the
    # high end being reachable at all, not at k=1.
    deep = section_pack({"hp": [1.0, 2.0], "atk": [1.0, 2.0]}, floors=9)
    assert stats(base_record(), None, deep, 9, 0)["hp"] == 20


def test_reversed_curve_pair_is_normalised():
    # A pack that writes [1.4, 1.0] means a curve that rises, not one
    # that falls: the pair is read low-then-high. This is what makes the
    # monotonicity property hold for any pack that passes shapes.py.
    reversed_pack = section_pack({"hp": [1.4, 1.0], "atk": [1.3, 1.0]})
    assert stats(base_record(), None, reversed_pack, 9, 0)["hp"] == 14
    assert stats(base_record(), None, reversed_pack, 9, 0)["atk"] == 5


# ------------------------------------------------------------ the matrix


def _matrix_cases():
    """Every (base, affix, section, k, c) the ADR's matrix names.

    The seed drives the base record's numbers through `vefr.delve.prng`
    so the sweep is a real seed sweep and not a fixed table, and so a
    JavaScript twin can rebuild the identical matrix from the identical
    seed string. `mob_stats` itself draws nothing.
    """
    from vefr.delve import prng

    for seed in SEEDS:
        rng = prng(f"mobstats-matrix|{seed}")
        base = base_record(hp=draw(rng, 1, 120), atk=draw(rng, 1, 40),
                           xp=draw(rng, 0, 25), sight=draw(rng, 0, 9))
        for curve in CURVES:
            for floors in (1, 2, 5, 9, 11):
                pack = section_pack(curve, floors=floors)
                for affix in AFFIXES:
                    for k in range(1, floors + 1):
                        for c in CYCLES:
                            yield seed, base, affix, pack, k, c


def test_matrix_is_whole_and_clamped():
    # ADR 0014's Acceptance, Python half: 200 seeds x curves x affixes
    # x cycles 0-5. Every returned value is a whole number, and hp and
    # atk are never below 1.
    cases = 0
    for _seed, base, affix, pack, k, c in _matrix_cases():
        out = stats(base, affix, pack, k, c)
        assert set(out) == set(RETURN_KEYS)
        for value in out.values():
            assert type(value) is int, (out, base, affix, pack, k, c)
        assert out["hp"] >= 1, (out, base, affix, pack, k, c)
        assert out["atk"] >= 1, (out, base, affix, pack, k, c)
        assert out["xp"] >= 0
        assert out["sight"] >= 0
        assert out["scale"] >= 0
        assert out["extra_drops"] >= 0
        cases += 1
    assert cases > 50_000, cases


def test_matrix_is_a_pure_function_of_its_inputs():
    # The determinism rule of PLAN.md section 2, measured: the same
    # inputs return the same dict on every repeat. No clock, no
    # global, no draw, no dict iteration.
    #
    # Three repeats, not 200. The matrix already carries 672k cases, so
    # 200 repeats ran 134 million calls of a function that reads six
    # arguments and returns a dict - the fourth call already proves the
    # same thing the 200th would, and the extra minutes bought no
    # coverage. Purity has no warm-up: there is no cache to fill and no
    # first call that differs from the rest.
    for _seed, base, affix, pack, k, c in _matrix_cases():
        first = stats(base, affix, pack, k, c)
        for _ in range(REPEATS):
            assert stats(base, affix, pack, k, c) == first


def test_matrix_does_not_mutate_its_inputs():
    # A caller passes a pack it also reads from. `mob_stats` takes a
    # deep snapshot of what it needs on the first call and answers the
    # same for the rest, so it cannot be writing back into the pack.
    base = base_record()
    affix = {"id": "big", "label": "Big {name}", "hp": 1.5, "atk": 1.2,
             "xp": 1.5, "sight": 1, "scale": 1.3, "extra_drops": 1}
    pack = section_pack(CURVES[1])
    before = (dict(base), dict(affix), repr(sorted(pack.items())))
    stats(base, affix, pack, 3, 1)
    after = (dict(base), dict(affix), repr(sorted(pack.items())))
    assert before == after


# ------------------------------------------------------------- goldens
# Hand-computed, so a change to the formula shows up as a diff on this
# table rather than as a surprise at run time. Every line is worked out
# here, longhand.

GOLDENS = [
    # (base, affix, curve, floors, k, c, expected dict)
    # 1. Floor 1, story, no affix. curve hp pct 100, atk pct 100, cycle
    #    100, affix pct 100. 10*100*100*100 // 1_000_000 == 10.
    (base_record(), None, {"hp": [1.0, 1.4], "atk": [1.0, 1.3]}, 9, 1, 0,
     {"hp": 10, "atk": 4, "xp": 3, "sight": 5, "scale": 100, "extra_drops": 0}),
    # 2. Floor 5, story. curve hp = 100 + 40*4//8 = 120, atk = 100 + 30*4
    #    // 8 = 115. 10*120*100*100 // 1e6 == 12, 4*115*100*100 // 1e6 == 4.
    (base_record(), None, {"hp": [1.0, 1.4], "atk": [1.0, 1.3]}, 9, 5, 0,
     {"hp": 12, "atk": 4, "xp": 3, "sight": 5, "scale": 100, "extra_drops": 0}),
    # 3. Floor 9, cycle 2. curve hp 140, atk 130, cycle min(140,160) = 140.
    #    10*140*100*140 // 1e6 == 19 (19.6 floors), 4*130*100*140 // 1e6
    #    == 7 (7.28 floors).
    (base_record(), None, {"hp": [1.0, 1.4], "atk": [1.0, 1.3]}, 9, 9, 2,
     {"hp": 19, "atk": 7, "xp": 3, "sight": 5, "scale": 100, "extra_drops": 0}),
    # 4. The `big` affix on floor 1, story. affix hp pct 150, atk 120, xp
    #    150. 10*100*150*100 // 1e6 == 15, 4*100*120*100 // 1e6 == 4
    #    (4.8 floors), xp 3*150//100 == 4 (4.5 floors), sight 5+1 == 6,
    #    scale 130, extra_drops 1.
    (base_record(),
     {"id": "big", "label": "Big {name}", "hp": 1.5, "atk": 1.2, "xp": 1.5,
      "sight": 1, "scale": 1.3, "extra_drops": 1},
     {"hp": [1.0, 1.4], "atk": [1.0, 1.3]}, 9, 1, 0,
     {"hp": 15, "atk": 4, "xp": 4, "sight": 6, "scale": 130, "extra_drops": 1}),
    # 5. The `big` affix on floor 5 of a steep curve, cycle 1. curve hp =
    #    100 + 100*4//8 = 150, atk = 100 + 80*4//8 = 140, cycle 120.
    #    10*150*150*120 // 1e6 == 27, 4*140*120*120 // 1e6 == 8 (8.064).
    (base_record(),
     {"id": "big", "label": "Big {name}", "hp": 1.5, "atk": 1.2, "xp": 1.5,
      "sight": 1, "scale": 1.3, "extra_drops": 1},
     {"hp": [1.0, 2.0], "atk": [1.0, 1.8]}, 9, 5, 1,
     {"hp": 27, "atk": 8, "xp": 4, "sight": 6, "scale": 130, "extra_drops": 1}),
    # 6. A sight-only affix under the default section. No hp/atk/xp key
    #    means pct 100, so the stats are the base's and only sight moves.
    (base_record(sight=5), {"id": "quick", "label": "Quick {name}", "sight": 2},
     None, 9, 1, 0,
     {"hp": 10, "atk": 4, "xp": 3, "sight": 7, "scale": 100, "extra_drops": 0}),
    # 7. The cycle cap. curve flat, cycle 3 is the cap at 160, and cycle
    #    5 is still 160: 10*100*100*160 // 1e6 == 16, 4*... == 6 (6.4).
    (base_record(), None, {"hp": [1.0, 1.0], "atk": [1.0, 1.0]}, 9, 1, 3,
     {"hp": 16, "atk": 6, "xp": 3, "sight": 5, "scale": 100, "extra_drops": 0}),
    (base_record(), None, {"hp": [1.0, 1.0], "atk": [1.0, 1.0]}, 9, 1, 5,
     {"hp": 16, "atk": 6, "xp": 3, "sight": 5, "scale": 100, "extra_drops": 0}),
    # 8. A one-floor Section. n <= 1 is the low end: curve hp pct 100
    #    whatever the pack's high end says, so 10.
    (base_record(), None, {"hp": [1.0, 2.0], "atk": [1.0, 2.0]}, 1, 1, 0,
     {"hp": 10, "atk": 4, "xp": 3, "sight": 5, "scale": 100, "extra_drops": 0}),
    # 9. The 1-hp floor. A 1-hp base at neutral terms is exactly
    #    1*100*100*100 // 1e6 == 1, and a 0 base is clamped up to 1.
    (base_record(hp=1, atk=1, xp=0, sight=0), None, None, 9, 1, 0,
     {"hp": 1, "atk": 1, "xp": 0, "sight": 0, "scale": 100, "extra_drops": 0}),
    (base_record(hp=0, atk=0, xp=0, sight=0), None, None, 9, 9, 5,
     {"hp": 1, "atk": 1, "xp": 0, "sight": 0, "scale": 100, "extra_drops": 0}),
    # 10. A low-end `frail` affix on a late floor of a steep curve, cycle
    #     0. affix hp pct 50, atk 60, xp 50. curve hp 200, atk 180.
    #     10*200*50*100 // 1e6 == 10, 4*180*60*100 // 1e6 == 4 (4.32),
    #     xp 3*50//100 == 1 (1.5 floors).
    (base_record(),
     {"id": "frail", "label": "Frail {name}", "hp": 0.5, "atk": 0.6, "xp": 0.5,
      "sight": 0, "scale": 0.9, "extra_drops": 0},
     {"hp": [1.0, 2.0], "atk": [1.0, 1.8]}, 9, 9, 0,
     {"hp": 10, "atk": 4, "xp": 1, "sight": 5, "scale": 90, "extra_drops": 0}),
    # 11. A 9-floor Section where the division does not come out even.
    #     k=2 of 4: curve hp = 100 + 40*1//3 = 113, atk = 100 + 30*1//3
    #     = 110. 10*113*100*100 // 1e6 == 11, 4*110*100*100 // 1e6 == 4.
    (base_record(), None, {"hp": [1.0, 1.4], "atk": [1.0, 1.3]}, 4, 2, 0,
     {"hp": 11, "atk": 4, "xp": 3, "sight": 5, "scale": 100, "extra_drops": 0}),
]


@pytest.mark.parametrize("base,affix,curve,floors,k,c,expected", GOLDENS)
def test_golden_table(base, affix, curve, floors, k, c, expected):
    pack = section_pack(curve, floors=floors)
    assert stats(base, affix, pack, k, c) == expected


# --------------------------------------------------------- monotonicity


@pytest.mark.parametrize("curve", CURVES)
@pytest.mark.parametrize("affix", AFFIXES)
def test_hp_never_decreases_as_k_rises(curve, affix):
    # For everything else fixed, a deeper floor is never a weaker
    # monster. This is the property that makes a Section's curve safe to
    # hand to a player as a difficulty ramp.
    for c in CYCLES:
        previous = 0
        for k in range(1, 10):
            hp = stats(base_record(), affix, section_pack(curve), k, c)["hp"]
            assert hp >= previous, (curve, affix, c, k, hp, previous)
            previous = hp


@pytest.mark.parametrize("curve", CURVES)
@pytest.mark.parametrize("affix", AFFIXES)
def test_atk_never_decreases_as_k_rises(curve, affix):
    for c in CYCLES:
        previous = 0
        for k in range(1, 10):
            atk = stats(base_record(), affix, section_pack(curve), k, c)["atk"]
            assert atk >= previous, (curve, affix, c, k, atk, previous)
            previous = atk


@pytest.mark.parametrize("curve", CURVES)
@pytest.mark.parametrize("affix", AFFIXES)
def test_hp_never_decreases_as_c_rises(curve, affix):
    # Endless mode is harder, not softer. The cycle pct saturates at 160,
    # so the series flattens and never falls.
    for k in range(1, 10):
        previous = 0
        for c in CYCLES:
            hp = stats(base_record(), affix, section_pack(curve), k, c)["hp"]
            assert hp >= previous, (curve, affix, k, c, hp, previous)
            previous = hp


@pytest.mark.parametrize("curve", CURVES)
def test_atk_never_decreases_as_c_rises(curve):
    for k in range(1, 10):
        previous = 0
        for c in CYCLES:
            atk = stats(base_record(), None, section_pack(curve), k, c)["atk"]
            assert atk >= previous, (curve, k, c, atk, previous)
            previous = atk


def test_monotonicity_survives_a_reversed_curve_pair():
    # Read low-then-high, so a pack that writes its pair backwards
    # still gives a rising curve. This is what the reversed-pair
    # normalisation is for.
    pack = section_pack({"hp": [2.0, 1.0], "atk": [1.8, 1.0]})
    previous = 0
    for k in range(1, 10):
        hp = stats(base_record(), None, pack, k, 0)["hp"]
        assert hp >= previous
        previous = hp


# ------------------------------------------------------------- the surface


def test_public_surface_is_these_four_names():
    # The module's own public functions, closed. The balance report and
    # the JavaScript twin both call exactly these, and nothing else.
    public = {
        name for name, value in vars(mob_stats).items()
        if not name.startswith("_") and inspect.isfunction(value)
    }
    assert public == {"pct", "curve_pct", "cycle_pct", "mob_stats"}


def test_the_return_shape_is_documented():
    # The docstring names every key the function returns. A key added
    # later without a line here fails, and that is the point.
    doc = mob_stats.mob_stats.__doc__ or ""
    for key in RETURN_KEYS:
        assert key in doc, key
    assert "hp" in doc and "atk" in doc
