"""mob_stats - a monster's whole-number stats, from a base, an affix and a floor.

ADR 0014's "Stats, in whole numbers only" section is the spec, and this
module is its whole Python half. The formula it writes:

    pct(m)    = round(m * 100)
    curve pct = lo + (hi - lo) * (k - 1) // (n - 1)
    cycle pct = min(100 + 20 * c, 160)
    hp        = max(1, base_hp * curve_pct * affix_pct * cycle_pct // 1_000_000)
    atk       = max(1, base_atk * curve_pct * affix_pct * cycle_pct // 1_000_000)

`lo` and `hi` in the curve line are HUNDREDTHS, not multipliers: the
pack's `1.4` enters the arithmetic as `pct(1.4) == 140`. Three pct
terms multiply out to a divisor of 1_000_000, which is why the stat
lines divide by a million and not by a hundred.

Nothing here draws, and nothing here is random. The determinism rule of
PLAN.md section 2 is satisfied by construction: no `Math.random`, no
clock, no global, and no dictionary is ever iterated while a value is
produced. `mob_stats` is a pure function of its five arguments, which is
what makes the JavaScript twin a line-for-line twin and what makes the
balance report reproducible.

**No float ever leaves this module.** `pct` is the one place a float is
touched at all, and it exists because a Section pack writes `1.4` where
a hundredth is meant. Every value `mob_stats` returns is an `int`.

The JavaScript twin (owned by the slice after this one) writes the same
line at the same place; each formula below carries a note saying what
the twin must write there.
"""

from __future__ import annotations

import math

# The divisor the stat lines use: three pct terms, each 1/100, so
# 100 * 100 * 100. JS twin: `const SCALE = 1_000_000;`
_SCALE = 1_000_000

# The cycle pct's ceiling. A cycle adds 20 hundredths, and the endless
# ramp stops here, so monster numbers stay bounded however deep the run
# goes (PLAN.md section 1.3). JS twin: `const CYCLE_CAP = 160;`
_CYCLE_CAP = 160

# What a Section with no `curve` and no `floors` means: no ramp inside
# the Section, and the 8-11 floors of PLAN.md section 1 collapsed to the
# middle of that range. JS twin: the same two literals.
_DEFAULT_FLOORS = 9
_DEFAULT_CURVE = (1.0, 1.0)


# ------------------------------------------------------------------ pct


def pct(multiplier) -> int:
    """A multiplier as whole hundredths: `pct(1.4) == 140`.

    This is the ONLY line in the module that touches a float, and it is
    allowed to, because a Section pack writes a decimal multiplier
    where an integer hundredth is meant.

    The rounding is half-UP, which is what the JavaScript twin's
    `Math.round` does. Python's built-in `round` is half-to-EVEN, so
    `round(12.5)` answers 12 there and 13 in a browser; this function
    does not use it, and the twin does not use `Math.round` alone
    either - it writes `Math.floor(m * 100 + 0.5)`, the same line as
    here, so the two agree on every input including a tie. In practice
    the tie never fires: ADR 0014 requires every multiplier to be whole
    hundredths, and the test suite proves that range is exact.

    JS twin: `const pct = (m) => Math.floor(m * 100 + 0.5);`
    """
    return math.floor(float(multiplier) * 100.0 + 0.5)


# ------------------------------------------------------------- curve_pct


def curve_pct(lo, hi, k, n) -> int:
    """The depth ramp for floor `k` of `n`, in whole hundredths.

    `lo` and `hi` are already hundredths. The step is an integer floor
    divide and never a rounded one, so the ramp is monotonic: it rises
    by at most one hundredth per floor and never falls.

    **The degenerate case: `n <= 1` returns `lo`.** There is no step
    to interpolate over, so a one-floor Section sits at the bottom of
    its own curve whatever high end the pack asked for. That is the
    documented answer, and the test suite pins it.

    JS twin: `const curvePct = (lo, hi, k, n) => n <= 1 ? lo
      : lo + Math.floor((hi - lo) * (k - 1) / (n - 1));`
    """
    if n <= 1:
        # No step to interpolate over: the curve IS its low end.
        return lo
    # JS twin: `lo + Math.floor((hi - lo) * (k - 1) / (n - 1))`.
    return lo + (hi - lo) * (k - 1) // (n - 1)


# ------------------------------------------------------------- cycle_pct


def cycle_pct(c) -> int:
    """The endless-mode ramp for cycle `c`, in whole hundredths.

    `min(100 + 20 * c, 160)`. Cycle 0 is the story and is exactly the
    neutral 100; the ramp adds 20 hundredths a cycle and stops at 160,
    so a hundredth-deep run is no harder in numbers than a tenth-deep
    one. Difficulty past that comes from omens (PLAN.md section 1.3).

    JS twin: `const cyclePct = (c) => Math.min(100 + 20 * c, 160);`
    """
    return min(100 + 20 * c, _CYCLE_CAP)


# ------------------------------------------------------------ pack reads
# Every read here defaults, because a missing key must never raise: the
# packs in the wild are older than the ADR and a floor with no curve is
# a floor whose curve is flat.


def _pct_pair(value, fallback: tuple[int, int]) -> tuple[int, int]:
    """A `[lo, hi]` multiplier pair as two whole hundredths, low first.

    The pair is SORTED, so a pack that writes `[1.4, 1.0]` means a curve
    that rises rather than one that falls. That is what makes the
    monotonicity property hold for any pair that reaches here, and it
    is a decision the JavaScript twin has to make in the same place.

    JS twin: read the pair, sort it, then `pct` each end.
    """
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            lo, hi = pct(value[0]), pct(value[1])
        except (TypeError, ValueError):
            return fallback
        return (lo, hi) if lo <= hi else (hi, lo)
    return fallback


def _curve_of(section, stat: str) -> tuple[int, int]:
    """One stat's `[lo, hi]` hundredths from a Section pack, defaulted.

    Reads `section["curve"][stat]`, where `stat` is `"hp"` or `"atk"`.
    A pack with no `curve`, a curve with no `hp`, or a curve carrying
    something that is not a pair all answer `pct(1.0), pct(1.0)`: the
    neutral 100, which multiplies out of a stat and leaves the base
    alone.

    JS twin: the same three levels of default, the same two literals.
    """
    curve = section.get("curve") if isinstance(section, dict) else None
    value = curve.get(stat) if isinstance(curve, dict) else None
    return _pct_pair(value, (pct(_DEFAULT_CURVE[0]), pct(_DEFAULT_CURVE[1])))


def _floors_of(section) -> int:
    """How many floors the Section has: `section["floors"]`, else 9."""
    if isinstance(section, dict):
        try:
            floors = int(section.get("floors", _DEFAULT_FLOORS))
        except (TypeError, ValueError):
            return _DEFAULT_FLOORS
        return floors
    return _DEFAULT_FLOORS


def _whole(value, default: int) -> int:
    """A whole number out of a pack record, or `default`."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ------------------------------------------------------------- mob_stats


def mob_stats(base, affix, section, k, c) -> dict:
    """A monster's stats on floor `k` of `section` in cycle `c`.

    `base` is a Blueprint family base record - the `name, sprite, hp,
    atk, xp, sight, drops` dict that `vefr.blueprint.resolve_family`
    returns. `affix` is an affix record (`id`, `label`, `hp`, `atk`,
    `xp`, `sight`, `scale`, `extra_drops`) or `None` for a normal
    monster; every key on it is optional, and a missing key means NO
    CHANGE - multiplier 1.0 (pct 100), `sight` 0, `extra_drops` 0.
    `section` is the Section pack dict, read for `curve` and `floors`.
    `k` is the floor's 1-based position inside the Section and `c` is
    the cycle, 0 for the story.

    **The return shape, closed, every value an `int`:**

    - `hp`  - `max(1, base_hp * curve_hp * affix_hp * cycle // 1_000_000)`
    - `atk` - `max(1, base_atk * curve_atk * affix_atk * cycle // 1_000_000)`
    - `xp`  - `max(0, base_xp * affix_xp // 100)`: the reward curve is
      the affix alone, because a Section's `curve` block carries `hp`
      and `atk` and no `xp`, and because a deeper floor paying more
      reward than its difficulty is the wrong direction for an
      endless run.
    - `sight` - the base's `sight` plus the affix's `sight`, ADDED and
      never multiplied, since the affix field is a tile count.
    - `scale` - the affix's `scale` in whole hundredths, 100 when the
      affix carries none.
    - `extra_drops` - the affix's whole `extra_drops`, 0 when absent.

    The function is pure: the same five arguments return the same dict
    every time, no draws are consumed, and no input is mutated. It
    reads no clock, no global and no environment.

    JS twin: same five arguments, same six keys, same order of
    operations. `Math.floor` and Python's `//` agree on every operand
    here because all of them are non-negative, which is the contract
    that makes the two languages' rounding identical.
    """
    hp_lo, hp_hi = _curve_of(section, "hp")
    atk_lo, atk_hi = _curve_of(section, "atk")
    floors = _floors_of(section)
    cycle = cycle_pct(c)

    # The affix term: an absent key is a pct of 100, a monster with no
    # affix at all is every term at neutral.
    aff = affix if isinstance(affix, dict) else {}
    aff_hp = pct(aff.get("hp", 1.0))
    aff_atk = pct(aff.get("atk", 1.0))
    aff_xp = pct(aff.get("xp", 1.0))

    base_hp = _whole(base.get("hp"), 0) if isinstance(base, dict) else 0
    base_atk = _whole(base.get("atk"), 0) if isinstance(base, dict) else 0
    base_xp = _whole(base.get("xp"), 0) if isinstance(base, dict) else 0

    # JS twin, hp:
    #   Math.max(1, Math.floor(baseHp * curvePct(...) * pct(affHp) * cycle / 1e6))
    # The curve is asked twice, once per stat, because the pack's curve
    # block carries a separate pair for each.
    hp = max(1, base_hp * curve_pct(hp_lo, hp_hi, k, floors) * aff_hp * cycle // _SCALE)
    # JS twin, atk: the same line with the `atk` curve pair.
    atk = max(1, base_atk * curve_pct(atk_lo, atk_hi, k, floors) * aff_atk * cycle // _SCALE)
    # JS twin, xp: `Math.floor(baseXp * pct(affXp) / 100)`, clamped at 0.
    # No curve and no cycle: the ADR's xp line is the affix's own term.
    xp = max(0, base_xp * aff_xp // 100)

    sight = _whole(base.get("sight"), 0) + _whole(aff.get("sight"), 0)
    scale = pct(aff.get("scale", 1.0))
    extra_drops = max(0, _whole(aff.get("extra_drops"), 0))

    return {
        "hp": int(hp),
        "atk": int(atk),
        "xp": int(xp),
        "sight": int(sight),
        "scale": int(scale),
        "extra_drops": int(extra_drops),
    }
