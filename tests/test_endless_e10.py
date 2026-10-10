"""E10 (endless dungeon): the endless cycles, the omens, and the caps.

PLAN.md section 5 row E10 is the spec, and its acceptance line is what
this file is written from:

    "Depth 1-300 sweep: multiplier <= cap, loot tier <= cap; every omen
     changes only its stated field (golden diff)."

Three things are therefore pinned here, and the third is the one that
matters most:

| what | where in this file |
|---|---|
| `cycle_locate` past the story, and its agreement with `delve.locate` | "cycle locate" |
| the multiplier and the loot tier, at every depth 1 to 300 | "the caps" |
| one golden diff per omen: one key moves, and no other | "omens as modifiers" |

The golden diffs are read, not written: `modifier(section, cycle,
chosen)` is the whole record an omen can move, and each test below
asserts that the DIFFERENCE between "no omen" and "this omen" is one
key with the delta the omen's own field says. A fourth omen that moved
two fields would have to be caught here, and `test_an_omen_that_names_two_fields_is_refused`
is the schema half of the same rule.

Two numbers are the plan's and are not this file's to soften:
`min(1 + 0.2*c, 1.6)` and "the loot tier caps at Section 3's tier + 1".
They are asserted against the ENGINE (`vefr.mob_stats.cycle_pct` and
`vefr.sections`), not against constants written here, because a test
that agrees with itself proves nothing.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import delve, mob_stats, sections, shapes

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sections" / "cellar"

# The two caps, in the units the engine uses: whole hundredths for the
# multiplier, whole tiers for the loot.
MULTIPLIER_CAP = 160      # 1.6, PLAN.md section 4
LOOT_TIER_STEP = 1        # "Section 3's tier + 1", PLAN.md section 4

# The three Sections of the story the plan writes about, with the tiers
# that step up across them. Deepest is Section 3, so the endless cap is
# 3 + 1 = 4.
STORY = [
    {"section": 1, "id": "cellar", "floors": 9, "loot": {"tier": 1},
     "families": [{"family": "rat", "weight": 5}]},
    {"section": 2, "id": "hollows", "floors": 9, "loot": {"tier": 2},
     "families": [{"family": "rat", "weight": 5}]},
    {"section": 3, "id": "undercroft", "floors": 9, "loot": {"tier": 3},
     "families": [{"family": "rat", "weight": 5}]},
]

# One Section with every field an omen can move, and the three omens
# PLAN.md section 4's table names that this engine can actually change.
ARMED = {
    "section": 1, "id": "cellar", "floors": 9,
    "fog": {"radius": 4},
    "groups": {"per_floor": [1, 3]},
    "loot": {"tier": 1},
    "warden": {"family": "rat", "endless": {"affixes": 1}},
    "families": [{"family": "rat", "weight": 5}],
    "endless": {"picks": 3, "omens": [
        {"id": "darker", "label": "Darker", "fog_radius": -1},
        {"id": "crowded", "label": "Crowded", "groups_per_floor": 1},
        {"id": "proud", "label": "Proud", "warden_affixes": 1},
    ]},
}


def _diff(before, after):
    """The keys of two records that differ, as `{key: (before, after)}`."""
    return {k: (before[k], after[k]) for k in before if before[k] != after[k]}


# ------------------------------------------------------------ cycle locate


def test_the_story_is_cycle_zero_and_reads_exactly_as_locate_reads_it():
    """Every depth `locate` accepts, `cycle_locate` answers the same.

    E4 froze `locate`'s answer for every depth of the story, so E10 does
    not touch it: a second read of the depth curve that disagreed with
    the first would be two depth curves and one save.
    """
    for depth in range(1, 28):
        assert sections.cycle_locate(depth, STORY) == sections.locate(depth, STORY)


def test_the_descent_begins_again_in_cycle_one():
    """Twenty-seven floors of story, then cycle 1 starts at the first floor."""
    cycle, section, k = sections.cycle_locate(28, STORY)
    assert (cycle, section['id'], k) == (1, 'cellar', 1)
    cycle, section, k = sections.cycle_locate(54, STORY)
    assert (cycle, section['id'], k) == (1, 'undercroft', 9)
    cycle, section, k = sections.cycle_locate(55, STORY)
    assert (cycle, section['id'], k) == (2, 'cellar', 1)


def test_cycle_locate_is_the_same_curve_delve_locates():
    """Two reads of one depth curve must agree, at every depth.

    `vefr.delve.locate` is what the runtime asks and `vefr.sections` is
    what the pack sweep asks, so a pack whose floors the two disagreed
    about would generate one floor and validate another.
    """
    descent = {"descent": {"run_seed": "ember", "sections": STORY}}
    for depth in range(1, 300):
        mine = sections.cycle_locate(depth, STORY)
        theirs = delve.locate(depth, descent)
        assert (mine[0], mine[1]['id'], mine[2]) == \
               (theirs[0], theirs[1]['id'], theirs[2]), depth


def test_locate_still_refuses_a_depth_it_cannot_name():
    """The E4 refusal stands, and it now says where the endless read is.

    `test_locate_is_refused_a_depth_it_cannot_name` in the E4 file pins
    that it raises. This pins that the sentence points at the read that
    does answer, so the failure is a signpost rather than a dead end.
    """
    with pytest.raises(ValueError) as caught:
        sections.locate(28, STORY)
    assert 'cycle_locate' in str(caught.value)
    with pytest.raises(ValueError):
        sections.locate(0, STORY)


def test_cycle_locate_refuses_a_depth_or_a_pack_it_cannot_name():
    with pytest.raises(ValueError):
        sections.cycle_locate(0, STORY)
    with pytest.raises(ValueError):
        sections.cycle_locate("1", STORY)
    with pytest.raises(ValueError):
        sections.cycle_locate(1, [])


def test_cycle_locate_never_mutates_the_pack_it_is_handed():
    before = json.dumps(STORY, sort_keys=True)
    for depth in range(1, 60):
        sections.cycle_locate(depth, STORY)
    assert json.dumps(STORY, sort_keys=True) == before


# ----------------------------------------------------------------- the caps


def test_the_caps_are_one_number_in_every_place_they_are_written():
    """Three copies of 160, and this test is what keeps them one number.

    `sections.MULTIPLIER_CAP` is what the engine's own read is checked
    against in the tests above, the arithmetic in `mob_stats` is what
    actually computes it, and the report holds the PLAN's number on its
    own so that a raised engine cap is caught rather than agreed with.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "balance_report", ROOT / "scripts" / "balance_report.py")
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    assert sections.MULTIPLIER_CAP == 160
    assert mob_stats.cycle_pct(100_000) == sections.MULTIPLIER_CAP
    assert report.PLAN_MULTIPLIER_CAP == sections.MULTIPLIER_CAP
    assert sections.LOOT_TIER_STEP == report.PLAN_LOOT_TIER_STEP == 1


def test_the_multiplier_is_the_plan_s_and_nothing_deeper_than_it():
    """`min(1 + 0.2*c, 1.6)`, asserted against `mob_stats` itself.

    Cycle 3 is the cap and cycle 300 is the same number: that identity
    is the whole promise of PLAN.md section 1.3, "Endless at higher
    scaling is the power-creep failure".
    """
    assert [mob_stats.cycle_pct(c) for c in range(0, 5)] == [100, 120, 140, 160, 160]
    assert mob_stats.cycle_pct(100_000) == MULTIPLIER_CAP
    for cycle in range(0, 1001):
        assert sections.monster_multiplier(cycle) <= MULTIPLIER_CAP
    assert sections.monster_multiplier(3) == sections.monster_multiplier(300)


def test_the_loot_tier_cap_is_the_deepest_section_tier_plus_one():
    """PLAN.md section 4, read off the pack rather than written down.

    The three Section story of the plan has Section 3 deepest, so the cap
    is its tier plus one - and a pack whose deepest Section declares a
    higher tier moves the cap with it, which is the same line rather
    than a second rule.
    """
    assert sections.loot_tier_cap(STORY) == 3 + LOOT_TIER_STEP
    assert sections.cycle_loot_tier(STORY[2], 1, STORY) == 3


def test_an_endless_cycle_drops_no_loot_deeper_than_the_cap():
    """The cap is held in code, so a Section asking for more gets the cap.

    `cycle_loot_tier` is where the guarantee lives: a Section 1 that
    declares tier 9 in a three-Section story still drops tier 4 from
    cycle 1 onwards. The pack asking for it is the balance report's
    finding, not the player's.
    """
    greedy = dict(STORY[0], loot={"tier": 9})
    assert sections.cycle_loot_tier(greedy, 0, STORY) == 9      # the story asks for it
    assert sections.cycle_loot_tier(greedy, 1, STORY) == 4      # endless does not
    assert sections.cycle_loot_tier(greedy, 999, STORY) == 4


def test_depth_one_to_three_hundred_never_breaches_either_cap():
    """The acceptance sweep, over the plan's own three-Section story.

    Every depth of every cycle, all the way to 300 - which on this pack is
    cycle 11, far past the multiplier's cap at cycle 3. A cap that only
    holds to depth 27 is a cap that holds to the end of the story.
    """
    cap = sections.loot_tier_cap(STORY)
    assert cap == 4
    for depth in range(1, 301):
        cycle, section, k = sections.cycle_locate(depth, STORY)
        assert sections.monster_multiplier(cycle) <= MULTIPLIER_CAP, depth
        assert sections.cycle_loot_tier(section, cycle, STORY) <= cap, depth
        # And the stats the multiplier actually reaches, through ADR
        # 0014's own formula rather than around it.
        base = {"hp": 10, "atk": 2, "xp": 1, "sight": 0}
        assert mob_stats.mob_stats(base, None, section, k, cycle)["hp"] <= 22


def test_a_pack_that_names_no_endless_keeps_its_own_numbers():
    """Cycle 0 is not clamped, and a pack with no omens is untouched.

    The backward-compatibility promise, in both halves: the story drops
    what it always dropped, and `modifier` on a Section with no `endless`
    answers the Section's own data and nothing else.
    """
    plain = {"section": 1, "id": "cellar", "floors": 9,
             "fog": {"radius": 4}, "groups": {"per_floor": [1, 2], "minions": [2, 3]},
             "loot": {"tier": 1}, "families": [{"family": "rat"}]}
    assert sections.modifier(plain, 0) == {
        "fog_radius": 4, "groups_per_floor": [1, 2], "warden_affixes": 0}
    assert sections.omens(plain) == []
    assert shapes.check_section(plain) == []


# ------------------------------------------------------- omens as modifiers


@pytest.mark.parametrize("omen, field, before, after", [
    ("darker", "fog_radius", 4, 3),
    ("crowded", "groups_per_floor", [1, 3], [2, 3]),
    ("proud", "warden_affixes", 1, 2),
])
def test_every_omen_moves_its_own_field_and_nothing_else(omen, field, before, after):
    """THE GOLDEN DIFF, one per omen: exactly one key moves.

    `modifier` is the whole record an omen can touch, so the difference
    between "no omen" and "this omen" is the acceptance test in three
    lines. An omen that moved a second field - or a field it did not
    name - would show up here as a second key, which is why the loop is
    over the WHOLE record rather than over the one field the omen says.
    """
    plain = sections.modifier(ARMED, 1, [])
    with_omen = sections.modifier(ARMED, 1, [omen])
    assert _diff(plain, with_omen) == {field: (before, after)}


@pytest.mark.parametrize("omen", ["darker", "crowded", "proud"])
def test_an_omen_a_section_does_not_offer_changes_nothing(omen):
    """An id from another Section's table is not one of this Section's."""
    other = {"section": 1, "id": "hollows",
             "families": [{"family": "rat"}]}
    assert sections.chosen_omens(other, [omen]) == []
    assert sections.modifier(other, 1, [omen]) == sections.modifier(other, 1, [])


def test_an_omen_that_names_two_fields_is_refused_by_name():
    """The schema half of "each omen changes only its stated field".

    `vefr check` says it, and `omen_field` answers None so the engine
    cannot pick one for the player. A guess would be the one way an omen
    could change a field nobody chose.
    """
    two = {"section": 1, "id": "cellar",
           "families": [{"family": "rat"}],
           "endless": {"omens": [
               {"id": "greedy", "fog_radius": -1, "warden_affixes": 1}]}}
    problems = shapes.check_section(two)
    assert [(p.code, p.pointer) for p in problems] == [
        ('no-omen-field', '/endless/omens/0')]
    assert 'exactly one field' in problems[0].sentence
    assert sections.omen_field({"id": "greedy", "fog_radius": -1,
                                "warden_affixes": 1}) is None
    assert sections.chosen_omens(two, ["greedy"]) != []   # offered...
    assert sections.omen_delta(two, ["greedy"], "fog_radius") == 0   # ...and inert


def test_the_validator_reads_the_endless_block_off_disk(tmp_path):
    """The door `vefr check` opens, on a real pack directory.

    `shapes.check_section` is the table; this is the path that turns it
    into the lines `vefr check` prints, which is the only proof that a
    pack file on disk is what the engine reads.
    """
    from vefr import maplab
    _write_pack(tmp_path, {"cellar": {
        "section": 1, "id": "cellar", "floors": 9,
        "loot": {"tier": 1}, "families": [{"family": "rat", "weight": 5}],
        "endless": {"omens": [{"id": "greedy", "fog_radius": -1,
                               "warden_affixes": 1}]}}})
    assert maplab.section_errors(tmp_path) == [
        'sections/cellar.json: /endless/omens/0 every omen changes exactly '
        'one field, and omen 0 names 2']


def test_an_omen_that_names_no_field_is_refused_too():
    none = {"section": 1, "id": "cellar",
            "families": [{"family": "rat"}],
            "endless": {"omens": [{"id": "empty"}]}}
    assert [p.code for p in shapes.check_section(none)] == ['no-omen-field']
    assert sections.omen_field({"id": "empty"}) is None


def test_omens_stack_and_two_on_one_field_add():
    """Three picks is the plan's number, and nothing forbids a double.

    Two DIFFERENT omens may name the same field - a pack is free to offer
    two kinds of Darker - and their deltas add, which is the only way two
    omens ever touch one field. An id repeated is one omen: the player
    picks omens off a list, not copies of one.
    """
    twice = dict(ARMED, endless={"picks": 3, "omens": [
        {"id": "darker", "fog_radius": -1},
        {"id": "darker-still", "fog_radius": -1},
        {"id": "proud", "warden_affixes": 1}]})
    assert sections.modifier(twice, 1, ["darker", "darker-still"])["fog_radius"] == 2
    assert sections.modifier(ARMED, 1, ["darker", "darker"])["fog_radius"] == 3
    mixed = sections.modifier(ARMED, 1, ["darker", "crowded", "proud"])
    assert mixed == {"fog_radius": 3, "groups_per_floor": [2, 3],
                     "warden_affixes": 2}


def test_an_omen_cannot_move_a_number_below_its_own_floor():
    """Darker stops at the fog's low end, and Crowded at the group cap.

    PLAN.md section 1.4 caps a floor's groups, and section 4's fog has a
    low end in the `fog` block. An omen may not be the thing that breaks
    either, and three Darkers on a Section that asks for 2 leave it at 2.
    """
    tight = dict(ARMED, fog={"radius": 2})
    assert sections.fog_radius(tight, ["darker"] * 3) == 2
    packed = dict(ARMED, groups={"per_floor": [3, 3]})
    assert sections.groups_per_floor(packed, ["crowded"]) == (3, 3)
    proud = dict(ARMED, warden={"family": "rat", "endless": {"affixes": 2}})
    assert sections.warden_affixes(proud, 1, ["proud"]) == \
        shapes.AFFIXES_MAX == 2


def test_a_warden_draws_no_endless_affixes_in_the_story():
    """ADR 0015: "In cycles `c >= 1` it draws `endless.affixes` affixes"."""
    assert sections.warden_affixes(ARMED, 0) == 0
    assert sections.warden_affixes(ARMED, 1) == 1
    plain = dict(ARMED, warden={"family": "rat"})
    assert sections.warden_affixes(plain, 5) == 0


def test_the_omen_fields_are_the_ones_the_table_allows():
    """One list, in both modules, or the pack and the engine disagree.

    `shapes.OMEN_FIELDS` is what the schema refuses anything outside of,
    and `sections.MODIFIER_FIELDS` is what the engine hands back in
    `modifier`. A field in one and not the other would be an omen a pack
    could write that the engine would not answer for - or the reverse.
    """
    table_keys = {key.name for key in shapes.OMEN.keys}
    assert shapes.OMEN_FIELDS == sections.MODIFIER_FIELDS
    assert set(sections.MODIFIER_FIELDS) <= table_keys
    assert set(sections.MODIFIER_FIELDS) <= set(shapes.OMEN_FIELDS)
    assert len(shapes.OMEN_FIELDS) == 3


def test_a_player_may_pick_at_most_three_omens():
    """PLAN.md section 4: "the player picks 0-3 omens"."""
    assert shapes.OMEN_PICKS_MAX == 3
    assert sections.picks({"endless": {"picks": 9}}) == 3
    assert sections.picks({"endless": {"picks": 2}}) == 2
    assert sections.picks({}) == 3
    over = dict(ARMED, endless={"picks": 4})
    assert any('between 0 and 3' in p.sentence for p in shapes.check_section(over))


# --------------------------------------------------------------- the board


def test_the_board_opens_on_the_story_end_and_nothing_else():
    """ADR 0015 Amendment 1: "Endless mode opens on `story_end`."

    E8c wrote the flag; this is the question that reads it. A hero who
    has not killed the King is on the story's last cycle however deep a
    depth says they are - which is why this is a gate and not a fact
    about the depth.
    """
    ended = {"descent": {"run_seed": "ember", "story_end": "the-king-falls"}}
    assert delve.board_open(ended, {}) is False
    assert delve.board_open(ended, {"the-king-falls": True}) is True
    assert delve.board_open(ended, {"the-king-falls": "yes"}) is False
    assert delve.board_open({"descent": {}}, {"king-slain": True}) is True


def test_the_board_offers_each_omen_with_the_one_field_it_moves():
    """The hook, as data: id, label, field, delta - and nothing else."""
    offer = sections.board_offer(ARMED)
    assert offer["section"] == "cellar"
    assert offer["picks"] == 3
    assert offer["stars"] == 3          # one star per omen, PLAN.md §4
    assert [o["id"] for o in offer["omens"]] == ["darker", "crowded", "proud"]
    assert offer["omens"][0] == {"id": "darker", "label": "Darker",
                                 "field": "fog_radius", "delta": -1}
    # An omen with no label of its own is shown by its id, so the board
    # never prints an empty row.
    unlabelled = dict(ARMED, endless={"omens": [{"id": "proud",
                                                "warden_affixes": 1}]})
    assert sections.board_offer(unlabelled)["omens"][0]["label"] == "proud"


def test_a_section_with_no_omens_has_no_board():
    """None, not an empty offer: no omens and no board are different facts."""
    assert sections.board_offer({"id": "cellar", "families": []}) is None
    assert sections.board_offer(dict(ARMED, endless={"omens": []})) is None


def test_the_board_does_not_offer_an_omen_it_cannot_honour():
    """An omen naming two fields is refused by `vefr check`, so it is not
    offered either - a choice the board shows and then ignores is worse
    than no choice at all."""
    broken = dict(ARMED, endless={"omens": [
        {"id": "darker", "fog_radius": -1},
        {"id": "greedy", "fog_radius": -1, "warden_affixes": 1}]})
    offer = sections.board_offer(broken)
    assert [o["id"] for o in offer["omens"]] == ["darker"]


# ------------------------------------------------------------ the gate itself


def _report(pack_dir, *extra):
    """Run `scripts/balance_report.py` and return `(code, stdout)`."""
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "balance_report.py"),
         "--pack", str(pack_dir), *extra],
        capture_output=True, text=True, cwd=str(ROOT))
    return done.returncode, done.stdout + done.stderr


def _write_pack(root: Path, records):
    (root / "sections").mkdir(parents=True, exist_ok=True)
    for name, record in records.items():
        (root / "sections" / f"{name}.json").write_text(
            json.dumps(record), encoding="utf-8")
    return root


def test_the_balance_report_passes_a_conforming_pack(tmp_path):
    pack = _write_pack(tmp_path / "good", {s['id']: s for s in STORY})
    code, out = _report(pack)
    assert code == 0, out
    assert 'every depth holds to both caps' in out


def test_the_balance_report_fails_a_pack_that_breaches_a_cap(tmp_path):
    """Exit 1, not a printed warning: a report that only prints is not a gate."""
    greedy = dict(STORY[0], loot={"tier": 9})
    two_fields = dict(
        STORY[1],
        endless={"omens": [{"id": "greedy", "fog_radius": -1,
                            "warden_affixes": 1}]})
    pack = _write_pack(tmp_path / "bad", {
        "cellar": greedy, "hollows": two_fields, "undercroft": STORY[2]})
    code, out = _report(pack)
    assert code == 1, out
    assert 'FAIL' in out
    assert "loot tier 9" in out
    assert 'does not change exactly one field' in out


def test_the_balance_report_fails_on_a_pack_it_cannot_read(tmp_path):
    assert _report(tmp_path / "nowhere")[0] == 2


def test_the_fixture_pack_the_report_sweeps_holds_to_both_caps():
    """The Section pack E4 froze, swept by the gate that watches E10."""
    code, out = _report(FIXTURE)
    assert code == 0, out
    assert 'max multiplier over the sweep  160' in out