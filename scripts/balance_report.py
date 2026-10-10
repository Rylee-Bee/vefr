#!/usr/bin/env python3
"""balance_report - the endless-mode balance report, as a GATE.

PLAN.md section 4 is the spec, and the sentence that asks for this file
is unambiguous about what it is for:

    "Bounded numbers. The monster multiplier is `min(1 + 0.2*c, 1.6)`.
     The loot tier caps at Section 3's tier + 1. The hero's level cap
     does not move. So there is no stat creep. **That is enforced by the
     balance report in E10.**"

A report that prints a number is not enforcement, so this one EXITS
NON-ZERO when a cap is breached and exits 0 otherwise. Six things fail
it:

1. the engine's own multiplier cap is above the plan's 1.6 - the check
   on the CHECK, so raising `_CYCLE_CAP` in `vefr.mob_stats` is caught
   here rather than shipped;
2. any depth's multiplier is above 1.6 (defensive: `cycle_pct` clamps,
   so this fires only if the clamp is removed);
3. any Section asks for a loot tier above the cap - a pack CAN write
   `loot: {"tier": 9}` on its first Section, and the engine holds it at
   the cap at read time, but a pack that asks for power creep is a pack
   whose numbers somebody has to fix, so the pack fails here rather than
   quietly getting the clamped answer forever;
4. any depth's loot tier is above the cap;
5. an omen that does not move exactly one field (PLAN.md section 4:
   "each omen changes only its stated field");
6. an omen on a field the plan did not name for an omen at all - the
   three of `shapes.OMEN_FIELDS` and nothing else.

The sweep is depth 1 to `MAX_DEPTH` (300), which is the slice's
acceptance: at every one of those depths the multiplier is at most 1.6
and the loot tier is at most the cap. The report also carries the
`mob_stats` numbers for one reference monster per depth, because ADR
0014 says this is the file those numbers are computed in, and because a
multiplier is only legible as what it does to a monster.

Deterministic, like everything in the endless plan: no clock, no seed,
no draws. Two runs of this file on one pack print the same bytes and
exit the same code.

Usage:
    python3 scripts/balance_report.py
    python3 scripts/balance_report.py --pack worlds/sample-world
    python3 scripts/balance_report.py --pack tests/fixtures/sections/cellar --verbose
    python3 scripts/balance_report.py --json bench/runs/balance.json

Exit codes: 0 conforming, 1 a cap is breached, 2 the pack could not be
read at all.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make `vefr` importable from a bare `python3 scripts/balance_report.py`
# as well as from `uv run python ...`, the same line `bench_floors.py`
# opens with.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from vefr import mob_stats, sections, shapes  # noqa: E402

# PLAN.md section 5 row E10: "Depth 1-300 sweep". Inclusive at both ends.
MIN_DEPTH = 1
MAX_DEPTH = 300

# The multiplier ceiling, written HERE as the plan writes it rather than
# read from the engine: a gate that reads the number it is checking
# checks nothing. The engine's own cap is read from `mob_stats` and
# compared against this one - finding 1.
PLAN_MULTIPLIER_CAP = 160        # hundredths of 1.6

# PLAN.md section 4: "The loot tier caps at Section 3's tier + 1". The
# "+1" is the only half of that sentence the engine does not know, and
# `vefr.sections.LOOT_TIER_STEP` holds the other; this file states it so
# that a pack whose Sections disagree is a sentence rather than a clamp.
PLAN_LOOT_TIER_STEP = 1

# One monster's base record, so the report can show what the multiplier
# does rather than only that it is in range. It is a REFERENCE base: the
# report is about the shape of the curve, and a base chosen per pack
# would make the report's numbers move when a pack retunes one family.
# 10 hp and 2 atk put cycle 0 in the low hundreds, where the 1.6 cap is
# visible as a number a person can check in their head.
REFERENCE_BASE = {"hp": 10, "atk": 2, "xp": 1, "sight": 0}


def sweep(pack_dir, lo: int = MIN_DEPTH, hi: int = MAX_DEPTH) -> list[dict]:
    """One record per depth in `lo..hi`, in depth order.

    Every number here comes from `vefr.sections` and `vefr.mob_stats` -
    the engine's own reads - so the report is a report ON the engine and
    not a second implementation of it. A depth the pack cannot answer
    for raises here rather than being skipped: a pack with no Sections
    has nothing to sweep, which is finding 0 and not an empty table.
    """
    pack = sections.load(pack_dir)
    cap = sections.loot_tier_cap(pack)
    out: list[dict] = []
    for depth in range(lo, hi + 1):
        cycle, section, k = sections.cycle_locate(depth, pack)
        stats = mob_stats.mob_stats(REFERENCE_BASE, None, section, k, cycle)
        out.append({
            "depth": depth,
            "cycle": cycle,
            "section": sections.section_id(section) or "?",
            "k": k,
            "multiplier": sections.monster_multiplier(cycle),
            "loot_tier": sections.cycle_loot_tier(section, cycle, pack),
            "declared_tier": sections.loot_tier(section),
            "hp": stats["hp"],
            "atk": stats["atk"],
        })
    return out


def findings(pack_dir, rows) -> list[str]:
    """Every way this pack breaches a cap, as plain sentences.

    Empty is the only conforming answer, and the caller turns a non-empty
    list into a non-zero exit. Each sentence names the pack, the number
    and the cap it broke, because a gate that says "failed" is a gate
    somebody learns to ignore.
    """
    pack = sections.load(pack_dir)
    cap = sections.loot_tier_cap(pack)
    out: list[str] = []

    # 1. The engine's own cap against the plan's. Read here rather than
    #    from `sections`, because the point is that the ENGINE may not
    #    have moved past what the plan allows even if the pack is clean.
    engine_cap = mob_stats.cycle_pct(100_000)
    if engine_cap > PLAN_MULTIPLIER_CAP:
        out.append(
            f"the engine's monster multiplier caps at {engine_cap} hundredths "
            f"but PLAN.md section 4 caps it at {PLAN_MULTIPLIER_CAP} "
            f"(1.6); endless mode is the power-creep failure and the cap is "
            f"where it stops")

    # 2/4. The sweep itself. One line per cycle and per Section rather
    #    than per depth: a breach that repeats 300 times is one breach,
    #    and a gate that prints 300 sentences is a gate nobody reads.
    for cycle in sorted({row['cycle'] for row in rows}):
        worst = max(row['multiplier'] for row in rows
                    if row['cycle'] == cycle)
        if worst > PLAN_MULTIPLIER_CAP:
            out.append(
                f"cycle {cycle} has a multiplier of {worst}, above the cap "
                f"of {PLAN_MULTIPLIER_CAP} (1.6)")
    for name in sorted({row['section'] for row in rows}):
        worst = max(row['loot_tier'] for row in rows if row['section'] == name)
        if worst > cap:
            out.append(
                f"section {name!r} drops loot tier {worst} somewhere in the "
                f"sweep, above the cap of {cap}")

    # 3. What the pack ASKED for, which is the finding the clamp hides.
    #    A Section whose own tier is over the cap is a pack whose numbers
    #    are wrong, and the cap is what stops it being wrong in play -
    #    not a licence for it to be wrong on disk.
    for section in sections.ordered(pack):
        tier = sections.loot_tier(section)
        if tier > cap:
            out.append(
                f"section {sections.section_id(section) or '?'!r} asks for "
                f"loot tier {tier}, above the endless cap of {cap} "
                f"(the deepest Section's tier + 1); the engine holds it at "
                f"the cap, and the pack should say the cap")

    # 5/6. Omens: one field each, and only a field the plan named.
    for section in sections.ordered(pack):
        for i, omen in enumerate(sections.omens(section)):
            name = sections.section_id(section) or '?'
            if sections.omen_field(omen) is None:
                out.append(
                    f"section {name!r} omen {i} does not change exactly one "
                    f"field, so `vefr check` refuses the pack")
        for field in shapes.OMEN_FIELDS:
            if field in ('monster_multiplier', 'loot_tier'):
                out.append(
                    f"PLAN.md section 4 makes a stat cap not an omen: "
                    f"{field!r} may not be one")
    return out


def _span(rows, field: str) -> str:
    """One number, or `a-b` when a cycle's depths do not agree.

    A column of one value is a column a reader checks by eye; a column of
    two is a column a reader has to parse. Every value a cycle's depths
    share prints once.
    """
    values = sorted({row[field] for row in rows})
    return str(values[0]) if len(values) == 1 else f'{values[0]}-{values[-1]}'


def _runs(groups):
    """Consecutive groups of cycles that print identically, as one group.

    A group's signature is its four columns; a run is every consecutive
    group with the same one. Yields `(first cycle, last cycle, rows)`
    with the rows of the whole run, so the depth span covers all of it.
    """
    run: list = []
    start = 0
    signature = None
    for index, group in enumerate(groups):
        here = (_span(group, 'multiplier'), _span(group, 'loot_tier'),
                _span(group, 'hp'), _span(group, 'atk'))
        if run and here != signature:
            yield start, index - 1, run
            run = []
            start = index
        signature = here
        run.extend(group)
    if run:
        yield start, len(groups) - 1, run


def _print_table(rows, pack_dir, cap, verbose: bool) -> None:
    pack = sections.ordered(sections.load(pack_dir))
    print(f"balance report - {pack_dir}")
    print(f"  sections     {len(pack)}"
          f" ({', '.join(sections.section_id(s) for s in pack) or 'none'})")
    print(f"  depths       {rows[0]['depth']}-{rows[-1]['depth']}")
    print(f"  multiplier   cap {PLAN_MULTIPLIER_CAP} (1.6)"
          f", engine cap {mob_stats.cycle_pct(100_000)}")
    print(f"  loot tier    cap {cap}")
    print(f"  cycles       {min(r['cycle'] for r in rows)}"
          f"-{max(r['cycle'] for r in rows)}")
    print()
    if verbose:
        print("  depth  cycle  section    k  multiplier  loot  hp  atk")
        for row in rows:
            print(f"  {row['depth']:>5}  {row['cycle']:>5}  "
                  f"{row['section']:<9} {row['k']:>2}  "
                  f"{row['multiplier']:>10}  {row['loot_tier']:>4}  "
                  f"{row['hp']:>3}  {row['atk']:>3}")
    else:
        # The compact form is one line per CYCLE rather than per depth,
        # with the extremes named: 300 depths is 300 lines, and a report
        # nobody reads is not a gate.
        print("  cycle  depths        multiplier  loot      hp      atk")
        seen: dict[int, list] = {}
        for row in rows:
            seen.setdefault(row['cycle'], []).append(row)
        # Consecutive cycles whose columns all read the same are ONE
        # line, and the line says so with its cycle range. That is not a
        # summary - it is the finding: from the cap outwards, every
        # deeper cycle is the same row, which is what "no stat creep"
        # looks like in a table.
        for first, last, group in _runs([seen[c] for c in sorted(seen)]):
            lo, hi = group[0]['depth'], group[-1]['depth']
            span = (f'{first}' if first == last else f'{first}-{last}')
            print(f"  {span:>5}  {lo:>4}-{hi:<6}  "
                  f"{_span(group, 'multiplier'):>10}  "
                  f"{_span(group, 'loot_tier'):>6}  "
                  f"{_span(group, 'hp'):>6}  "
                  f"{_span(group, 'atk'):>6}")
    print()
    print(f"  max multiplier over the sweep  "
          f"{max(r['multiplier'] for r in rows)}")
    print(f"  max loot tier over the sweep    "
          f"{max(r['loot_tier'] for r in rows)}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="The endless-mode balance report. Exits 1 on a "
                    "breached cap; 0 on a conforming pack.")
    parser.add_argument('--pack', default=str(ROOT / 'worlds' / 'sample-world'),
                        help='the pack directory to report on '
                             '(default: worlds/sample-world)')
    parser.add_argument('--lo', type=int, default=MIN_DEPTH,
                        help=f'first depth of the sweep (default {MIN_DEPTH})')
    parser.add_argument('--hi', type=int, default=MAX_DEPTH,
                        help=f'last depth of the sweep (default {MAX_DEPTH})')
    parser.add_argument('--json', metavar='PATH', default=None,
                        help='also write the whole report as JSON here')
    parser.add_argument('--verbose', action='store_true',
                        help='print one line per depth rather than per cycle')
    args = parser.parse_args(argv)

    if args.lo < 1 or args.hi < args.lo:
        print('balance_report: the sweep runs from a depth of 1 upwards',
              file=sys.stderr)
        return 2
    if not Path(args.pack).is_dir():
        print(f'balance_report: {args.pack} is not a directory',
              file=sys.stderr)
        return 2

    loaded = sections.load(args.pack)
    if not loaded:
        # Not a failure and not a pass: there is nothing here to breach a
        # cap with, and saying "ok" would read as a clean sweep. The
        # engine's own caps are still checked, because those are about
        # the engine and not about the pack.
        report = findings(args.pack, [])
        if report:
            for line in report:
                print(f'  FINDING  {line}')
            return 1
        print(f'balance report - {args.pack}')
        print('  this pack ships no sections/, so there are no depths to '
              'sweep;')
        print('  the engine\'s own multiplier cap was still checked and '
              'holds.')
        return 0

    rows = sweep(args.pack, args.lo, args.hi)
    cap = sections.loot_tier_cap(loaded)
    _print_table(rows, args.pack, cap, args.verbose)
    print()

    if args.json:
        report = {
            "pack": args.pack,
            "depths": [args.lo, args.hi],
            "multiplier_cap": PLAN_MULTIPLIER_CAP,
            "loot_tier_cap": cap,
            "rows": rows,
        }
        report["findings"] = findings(args.pack, rows)
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(f'  wrote {path}')

    report = findings(args.pack, rows)
    if report:
        for line in report:
            print(f'  FINDING  {line}')
        print(f'\nFAIL: {len(report)} finding(s). The pack breaches a cap.')
        return 1
    print('  ok: every depth holds to both caps')
    return 0


if __name__ == '__main__':
    sys.exit(main())