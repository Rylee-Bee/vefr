"""E8c part 2: town states (ADR 0015, and Amendment 1 section 3).

A pack names the regions whose look follows a story flag. The single block
ADR 0015 wrote first stays valid and must keep working unchanged; the list
of blocks Amendment 1 added is one per region, and each is the same
record. On entering a region with states the LAST state whose `when` is
true loads, else the region's own base - derived on every entry and never
stored, because each `use` is an ordinary authored region baked as it
always was.

All of a region's states share that region's save identity. A dropped item
that is standing on a wall in the state being loaded moves to the nearest
floor tile, scanning row-major, rather than becoming something the player
can never walk onto.
"""

import copy
import sys
from pathlib import Path

import pytest

from vefr import cli, delve, locks, maplab, shapes
from vefr.maplab import load_pack, validate

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
import make_town_pack  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "worlds" / "sample-world"

ONE = {"region": "town", "states": [
    {"id": "act-2", "when": "vault-1-read", "use": "town-act-2"},
    {"id": "after-the-end", "when": "king-slain", "use": "town-after"}]}


@pytest.fixture()
def pack(tmp_path):
    """The town-states fixture pack: a town with three states and a tavern."""
    return make_town_pack.build(tmp_path)


def _say(pack, states):
    """Every `validate` sentence for a pack carrying `states`."""
    world = dict(load_pack(pack))
    world["town_states"] = copy.deepcopy(states)
    return [e for e in validate(world, pack_dir=pack)
            if e.startswith("world.json: /town states")]


# ---- the two shapes -------------------------------------------------------

def test_the_single_block_form_is_still_valid_and_still_means_itself():
    assert shapes.check_town_states(ONE) == []
    assert delve.town_states_of({"town_states": ONE}) == [ONE]
    assert delve.town_state_of(delve.town_states_of({"town_states": ONE}),
                               "town", {"vault-1-read": True}) == "town-act-2"


def test_the_list_form_is_one_block_per_region():
    blocks = [{"region": "town", "states": ONE["states"]},
              {"region": "tavern", "states": [
                  {"id": "full", "when": "vault-1-read", "use": "tavern"}]}]
    assert shapes.check_town_states(blocks) == []
    listed = delve.town_states_of({"town_states": blocks})
    assert [b["region"] for b in listed] == ["town", "tavern"]
    assert delve.town_state_of(listed, "tavern", {}) == "tavern"
    assert delve.town_state_of(listed, "tavern", {"vault-1-read": True}) \
        == "tavern"


def test_a_pack_that_names_none_has_no_blocks_and_no_changes():
    assert delve.town_states_of({}) == []
    assert delve.town_state_of([], "town", {"vault-1-read": True}) == "town"


def test_the_fixture_pack_validates_with_both_regions_declaring_states(pack):
    assert validate(load_pack(pack), pack_dir=pack) == []


# ---- which state loads ----------------------------------------------------

def test_the_last_true_state_wins():
    blocks = delve.town_states_of({"town_states": ONE})
    assert delve.town_state_of(blocks, "town", {}) == "town"
    assert delve.town_state_of(blocks, "town", {"vault-1-read": True}) \
        == "town-act-2"
    # Both true: the LATER state is the one that shows.
    assert delve.town_state_of(
        blocks, "town", {"vault-1-read": True, "king-slain": True}) \
        == "town-after"


def test_no_true_flag_gives_the_regions_own_base():
    blocks = delve.town_states_of({"town_states": ONE})
    assert delve.town_state_of(blocks, "town", {"something-else": True}) \
        == "town"
    assert delve.town_state_of(blocks, "town", {"vault-1-read": False}) \
        == "town"


def test_a_flag_that_is_true_but_not_a_string_changes_nothing():
    """The check is a flag, and a flag is a name: `{"vault-1-read": 1}` is
    not a flag that is true, and neither is a state with no `use`."""
    blocks = [{"region": "town", "states": [
        {"id": "broken", "when": "vault-1-read"},
        {"id": "no-flag", "use": "town-act-2"}]}]
    assert delve.town_state_of(blocks, "town", {"vault-1-read": True}) == "town"
    assert delve.town_state_of(blocks, "town", {"vault-1-read": 1}) == "town"


def test_the_state_is_derived_from_the_flags_right_now_and_never_stored():
    """Two reads of the same block, two different flags, two answers: there
    is no pointer to go stale because there is no pointer."""
    blocks = delve.town_states_of({"town_states": ONE})
    assert delve.town_state_of(blocks, "town", {"king-slain": True}) == \
        delve.town_state_of(blocks, "town", {"king-slain": True})
    assert delve.town_state_of(blocks, "town", {"king-slain": True}) == \
        "town-after"
    assert delve.town_state_of(blocks, "town", {}) == "town"


def test_a_region_with_no_block_keeps_its_own_face():
    blocks = delve.town_states_of({"town_states": ONE})
    assert delve.town_state_of(blocks, "cellar-entrance", {"king-slain": True}) \
        == "cellar-entrance"


# ---- the refusal sentences ------------------------------------------------

def test_a_use_naming_no_region_is_refused_in_one_sentence(pack):
    assert _say(pack, {"region": "town", "states": [
        {"id": "act-2", "when": "vault-1-read", "use": "nowhere"}]}) == [
        "world.json: /town states/states/0/use every region a town state "
        "names must be one the pack declares, and 'nowhere' is not"]


def test_a_block_for_a_region_the_pack_does_not_have_is_refused(pack):
    assert _say(pack, {"region": "somewhere-else", "states": []}) == [
        "world.json: /town states/region every region a town state names "
        "must be one the pack declares, and 'somewhere-else' is not"]


def test_a_list_block_is_pointed_at_by_its_own_index(pack):
    assert _say(pack, [{"region": "town", "states": []},
                       {"region": "tavern", "states": [
                           {"id": "x", "when": "f", "use": "nowhere"}]}]) == [
        "world.json: /town states/1/states/0/use every region a town state "
        "names must be one the pack declares, and 'nowhere' is not"]


def test_two_blocks_for_one_region_are_refused_in_one_sentence():
    twice = [{"region": "town", "states": []}, {"region": "town", "states": []}]
    assert [p.sentence for p in shapes.check_town_states(twice)] == [
        "every region may name its town states once, and 'town' names them "
        "twice"]


def test_a_block_that_is_not_a_block_or_a_list_is_refused_in_one_sentence():
    said = shapes.check_town_states("town")
    assert said[0].code == "not-a-block-or-list"
    assert said[0].sentence.startswith("town_states must be one "
                                        "town-states block, such as {")


def test_a_state_missing_its_use_is_refused_in_one_sentence():
    assert [p.sentence for p in shapes.check_town_states(
        {"region": "town", "states": [{"id": "a", "when": "f"}]})] == [
        'town state must hold its use, such as {"id": "act-2", '
        '"when": "vault-1-read", "use": "town-act-2"}']


def test_an_unknown_key_is_refused_and_names_the_keys_the_block_may_hold():
    said = shapes.check_town_states(
        {"region": "town", "states": [], "patch": 1})
    assert said[0].code == "unknown-key"
    assert "'patch'" in said[0].sentence and "region and states" in \
        said[0].sentence


# ---- the bake -------------------------------------------------------------

def test_the_weave_carries_the_block_and_a_pack_without_one_carries_null(pack):
    with_states = cli.weave_html(pack)
    assert 'window.VEFR_TOWN_STATES = [' in with_states
    assert '"town-act-2"' in with_states
    plain = cli.weave_html(SAMPLE)
    assert "window.VEFR_TOWN_STATES = null;" in plain


# ---- every state is an ordinary authored region --------------------------

def test_every_state_is_one_ordinary_authored_region_of_the_same_pack(pack):
    """The whole claim of `town_states`: each `use` names a region the pack
    baked like any other. A state is not a patch and not a variant - it is
    another region, and the ADR's "all states share `region`'s save
    identity" is what keeps them one town to the save rather than four."""
    world = load_pack(pack)
    blocks = delve.town_states_of(world)
    used = {s["use"] for b in blocks for s in b["states"]}
    assert used <= {"town-act-2", "town-after", "tavern"}
    act = pack / "acts" / "act-1"
    for region in sorted(used | {"town"}):
        assert (act / region / "map.md").is_file()
        assert (act / region / "contract.json").is_file()
    # `town-act-2` is the sample's own town copied: the same map, the same
    # hero_start, a different colour. Nothing about it is special to the
    # engine, which is exactly the point.
    base = (act / "town" / "map.md").read_text(encoding="utf-8")
    for region in sorted(used):
        assert (act / region / "map.md").read_text(encoding="utf-8") == base


# ---- nothing today changes ------------------------------------------------

def test_the_shipped_pack_declares_no_town_states_and_validates():
    world = load_pack(SAMPLE)
    assert "town_states" not in world
    assert maplab.town_states_errors(world) == []
    assert validate(world, pack_dir=SAMPLE) == []


def test_a_pack_with_states_that_no_rule_can_reach_is_asked_about(tmp_path):
    """ADR 0015 check 4: every `when` a town state waits on has a setter."""
    pack = make_town_pack.build(tmp_path, town_states={
        "region": "town", "states": [
            {"id": "never", "when": "never-set", "use": "town-act-2"}]})
    assert locks.progress_findings(pack) == [
        "town states: the region 'town' waits on the flag 'never-set', "
        "which no rule sets"]


def test_a_state_whose_flag_a_vault_note_sets_is_not_asked_about(pack):
    assert locks.progress_findings(pack) == []