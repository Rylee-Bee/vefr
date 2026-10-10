"""E8c part 1: the per-game `story_end` flag (ADR 0015 Amendment 1, section 1).

A pack's `descent` names the flag whose being true ends its story, and
`king-slain` is the default - so a final boss behind its own door keeps
working exactly as ADR 0015 describes, and a pack whose story ends in a
quiet room instead names its own flag and sets it with any rule. The
unknown-key refusal for `descent` accepts it; a value that is not a flag
name is one sentence naming the file, the key and the bad value.

The act is a derived read, never a stored pointer: one plus the number of
story vault flags actually true. That is ADR 0015 rescoping ADR 0006, and
it needs the Sections to say which flag their vault's note records - the
`sets` of the vault record, which the bare stamp id E8b shipped names no
flag and so changes nothing.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

from vefr import cli, delve, locks, maplab, shapes
from vefr.maplab import load_pack, validate

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
import make_town_pack  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "worlds" / "sample-world"

A_DESCENT = {"run_seed": "ember", "entry": {"region": "town", "at": [7, 5]},
             "sections": [{"id": "cellar", "floors": 9}]}


@pytest.fixture()
def pack(tmp_path):
    """The town-states fixture pack: two Sections, two vault notes."""
    return make_town_pack.build(tmp_path)


def _say(pack, **changes):
    """Every `validate` sentence over the fixture pack with `changes`."""
    world = dict(load_pack(pack))
    world.update(copy.deepcopy(changes))
    return validate(world, pack_dir=pack)


# ---- the shape ------------------------------------------------------------

def test_a_descent_block_that_names_no_story_end_is_fine():
    assert shapes.check(shapes.BLOCKS['descent'], A_DESCENT) == []


def test_the_unknown_key_refusal_for_a_descent_accepts_story_end():
    """The point of the sentence: a pack that names one is not refused for
    naming it. Before E8c this key was an unknown key and the refusal was
    correct; now it is part of the block."""
    problems = shapes.check(shapes.BLOCKS['descent'],
                            dict(A_DESCENT, story_end="the-quiet-room-is-reached"))
    assert problems == [], problems


def test_a_story_end_that_is_not_a_flag_name_is_refused_in_one_sentence(pack):
    assert _say(pack, descent=dict(load_pack(pack)["descent"],
                                   story_end=7)) == [
        'world.json: /descent/story_end descent.story_end must be the name '
        'of a flag, such as "king-slain"']


def test_a_story_end_naming_nothing_is_refused_in_one_sentence(pack):
    assert _say(pack, descent=dict(load_pack(pack)["descent"],
                                   story_end="")) == [
        'world.json: /descent/story_end descent.story_end must be between 1 '
        'and 64']


# ---- the read -------------------------------------------------------------

def test_a_pack_that_names_none_reads_the_default():
    assert delve.STORY_END_FLAG == "king-slain"
    assert delve.story_end_of(dict(A_DESCENT)) == "king-slain"


def test_a_pack_that_names_one_gets_its_own_flag():
    block = dict(A_DESCENT, story_end="the-quiet-room-is-reached")
    assert delve.story_end_of(block) == "the-quiet-room-is-reached"


def test_the_read_is_the_same_through_the_block_and_through_the_pack():
    """Both shapes a caller holds: the block on its own, and the block the
    weave carries inside the pack (`{"descent": {...}}`)."""
    block = dict(A_DESCENT, story_end="the-quiet-room-is-reached")
    assert delve.story_end_of(block) == delve.story_end_of({"descent": block})


def test_the_fixture_pack_ends_on_its_last_vaults_note(pack):
    assert delve.story_end_of(load_pack(pack)["descent"]) == "king-slain"


# ---- the act, which is a derived read and never stored --------------------

def test_the_act_is_one_plus_the_vault_notes_that_have_been_read(pack):
    listed = delve.descent_of(load_pack(pack), pack)["sections"]
    assert delve.vault_flags_of(listed) == ["vault-1-read", "king-slain"]
    assert delve.act_number(listed, {}) == 1
    assert delve.act_number(listed, {"vault-1-read": True}) == 2
    assert delve.act_number(
        listed, {"vault-1-read": True, "king-slain": True}) == 3
    # A flag that is not one of this pack's vaults moves nothing, and one
    # that is false is not read.
    assert delve.act_number(
        listed, {"vault-1-read": False, "other": True}) == 1


def test_a_flag_two_sections_share_is_one_vault():
    both = [{"vault": {"stamp": "v", "sets": "read"}},
            {"vault": {"stamp": "v", "sets": "read"}}]
    assert delve.vault_flags_of(both) == ["read"]
    assert delve.act_number(both, {"read": True}) == 2


def test_a_section_whose_vault_is_the_bare_stamp_id_names_no_flag():
    """The shape E8b shipped, still a stamp and nothing else: no flag, no
    gate, and the act never moves for it."""
    assert delve.vault_of({"vault": "vault-cellar"}) == \
        {"stamp": "vault-cellar", "sets": None}
    assert delve.vault_flag({"vault": "vault-cellar"}) is None
    assert delve.act_number([{"vault": "vault-cellar"}], {}) == 1


# ---- the progress walk reaches it -----------------------------------------

def test_the_walk_reaches_the_default_story_end(pack):
    assert locks.progress_findings(pack) == []


def test_the_walk_reaches_a_story_end_no_vault_note_records(tmp_path):
    """Amendment 1's ending: no boss, a rule. The walk proves the Sections
    open; the rule is what finishes the story, and its flag is a setter."""
    pack = make_town_pack.build(
        tmp_path, story_end="the-quiet-room-is-reached",
        rules=make_town_pack.RULES + [{
            "id": "arriving-ends-it",
            "when": {"enters": {"place": "town"}},
            "then": [{"set": "the-quiet-room-is-reached"}], "once": True}])
    assert delve.story_end_of(load_pack(pack)["descent"]) == \
        "the-quiet-room-is-reached"
    assert locks.progress_findings(pack) == []


def test_a_story_end_nothing_sets_is_refused_in_one_sentence(tmp_path):
    pack = make_town_pack.build(tmp_path, story_end="never-set")
    assert locks.progress_findings(pack) == [
        "the descent: its story_end flag 'never-set' is never set - no "
        "Section's vault note records it and no rule sets it"]


# ---- the vault record that carries the flag --------------------------------

def test_a_vault_record_naming_no_sets_is_refused_in_one_sentence(pack):
    (pack / "sections" / "cellar.json").write_text(json.dumps(
        {**make_town_pack.SECTIONS["cellar"],
         "vault": {"stamp": "vault-cellar"}}, indent=2), encoding="utf-8")
    said = [e for e in validate(load_pack(pack), pack_dir=pack)
            if e.startswith("world.json:")]
    assert said == [
        'world.json: /sections/0/vault/sets vault must hold its sets, such '
        'as {"stamp": "vault-cellar", "sets": "vault-1-read"}']


def test_the_bare_stamp_id_is_still_a_whole_vault(tmp_path):
    """The shape every Section in the tree writes, and the one E8b shipped:
    it validates, it draws a vault, and it gates nothing."""
    pack = make_town_pack.build(tmp_path)
    (pack / "sections" / "cellar.json").write_text(json.dumps(
        {**make_town_pack.SECTIONS["cellar"], "vault": "vault-cellar"},
        indent=2), encoding="utf-8")
    assert validate(load_pack(pack), pack_dir=pack) == []
    assert delve.vault_flag(load_pack(pack)["descent"]["sections"][0]) is None \
        or delve.vault_flag({"vault": "vault-cellar"}) is None


def test_the_vaults_note_flag_rides_the_floor_plan_in_both_languages(pack):
    """The plan's own `vault` record carries `sets`, which is the flag the
    town gate is guarded by. `tests/test_descent_parity.py` is what holds
    the two languages equal; this is the record it compares."""
    descent = delve.descent_of(load_pack(pack), pack)
    plan = delve.floor_plan(
        {**descent, "stamps": make_town_pack.stamp_records(pack)}, 3)
    assert plan["vault"]["sets"] == "vault-1-read"


def test_the_check_draws_the_vault_books_the_weave_will(pack):
    """A note pinned to the vault can only be checked against the floor the
    player will draw, so `vefr check` reads the same descent the weave
    carries, stamps and all (ADR 0013)."""
    assert (pack / "stamps" / "vault-cellar.json").is_file()
    assert validate(load_pack(pack), pack_dir=pack) == []


# ---- nothing today changes ------------------------------------------------

def test_the_shipped_pack_declares_no_descent_and_no_town_states():
    world = load_pack(SAMPLE)
    assert "descent" not in world and "town_states" not in world
    assert maplab.descent_errors(world, SAMPLE) == []
    assert maplab.town_states_errors(world) == []


def test_the_shipped_pack_still_validates_and_has_no_story_to_walk():
    assert locks.progress_findings(SAMPLE) == []
    assert locks.section_findings(SAMPLE) == []
    assert validate(load_pack(SAMPLE), pack_dir=SAMPLE) == []


def test_a_pack_with_no_descent_is_asked_for_no_story(tmp_path):
    """Only a descent has a story to end: a pack with none is not asked."""
    pack = make_town_pack.build(tmp_path, descent={"run_seed": "run-a"})
    assert locks.progress_findings(pack) == []


def test_the_fixture_pack_weaves_with_its_town_states_baked(pack):
    html = cli.weave_html(pack)
    assert '"region": "town"' in html and '"town-act-2"' in html
    assert delve.story_end_of(load_pack(pack)["descent"]) == "king-slain"