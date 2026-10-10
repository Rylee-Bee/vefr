"""E8c part 3: the progress walk (ADR 0015, checks 4 and 5).

A flag-only simulation: it starts with no flags at all and walks the
Sections in order, three steps each - complete the warden's challenge, read
the note, enter town - and asks whether the pack's story can actually be
finished. Only flags move; no floor is drawn, no rule is fired and no seed
is read, so the whole walk is the same sentence every time.

It runs inside `section_findings`, the same door `vefr check` opens onto the
Sections, and it is the check that a missing setter fails with ONE clear
sentence naming the flag and the Section.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

from vefr import delve, locks
from vefr.maplab import load_pack

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
import make_town_pack  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "worlds" / "sample-world"


@pytest.fixture()
def pack(tmp_path):
    """The town-states fixture pack: two Sections, two vault notes, two
    rules that record them, and a story that ends on the second note."""
    return make_town_pack.build(tmp_path)


def _without(pack, flag):
    """The same pack with the rule that records `flag` taken away."""
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    world["rules"] = [r for r in world["rules"]
                      if not any(e.get("set") == flag for e in r.get("then") or [])]
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")
    return pack


# ---- the walk passes ------------------------------------------------------

def test_a_pack_whose_story_can_be_finished_walks_clean(pack):
    assert locks.progress_findings(pack) == []


def test_the_walk_is_the_same_sentence_every_time(pack):
    """It reads no clock, no seed and no storage: twice is the same answer,
    which is what makes it something a check can rely on."""
    assert locks.progress_findings(pack) == locks.progress_findings(pack)


# ---- the three steps ------------------------------------------------------

def test_the_walk_sets_the_wardens_flag_and_reads_the_note(pack):
    """The steps are the ADR's, in the ADR's order, and the flags they set
    are the ones ADR 0015 names: `warden:<id>:c<cycle>`, the vault's own
    `sets` flag, and `town-seen:<section>:c<cycle>`."""
    listed = delve.descent_of(load_pack(pack), pack)["sections"]
    assert [delve.warden_flag(delve.warden_of(s)["id"], 0) for s in listed] == \
        ["warden:cellar-boss:c0", "warden:hollow-warden:c0"]
    assert delve.vault_flags_of(listed) == ["vault-1-read", "king-slain"]


def test_a_section_with_no_warden_is_not_asked_about_one(tmp_path):
    """Three steps and no warden: the first has nothing to do, and the
    Section is not one of the walk's problems."""
    sections = {"cellar": {**make_town_pack.SECTIONS["cellar"],
                           "vault": {"stamp": "vault-cellar",
                                     "sets": "vault-1-read"}}}
    pack = make_town_pack.build(tmp_path, sections=sections)
    assert locks.progress_findings(pack) == []


def test_a_section_whose_vault_names_no_flag_gates_nothing(tmp_path):
    """The shape E8b shipped - a bare stamp id - names no flag, so it has
    no gate and nothing for the walk to prove about it. The Sections open
    freely, and the story still ends on the rule that sets it."""
    sections = {k: {**v, "vault": "vault-cellar"}
                for k, v in make_town_pack.SECTIONS.items()}
    pack = make_town_pack.build(tmp_path, sections=sections)
    listed = delve.descent_of(load_pack(pack), pack)["sections"]
    assert [delve.vault_flag(s) for s in listed] == [None, None]
    assert locks.progress_findings(pack) == []


# ---- a missing setter -----------------------------------------------------

def test_a_flag_nothing_sets_is_refused_in_one_sentence(pack):
    _without(pack, "vault-1-read")
    assert locks.progress_findings(pack) == [
        "section cellar: the flag 'vault-1-read' has no setter - no rule "
        "sets it and no vault note records it, so the gate "
        "'town-seen:cellar:c0' can never open"]


def test_the_missing_setter_is_named_once_even_when_it_is_the_story_end(
        tmp_path):
    """One fact, one sentence. The story ends on that same note, so saying
    it again as "the story can never be finished" would be the same fault
    in a second coat of paint."""
    pack = make_town_pack.build(tmp_path)
    _without(pack, "king-slain")
    assert locks.progress_findings(pack) == [
        "section hollow: the flag 'king-slain' has no setter - no rule sets "
        "it and no vault note records it, so the gate "
        "'town-seen:hollow:c0' can never open"]


def test_both_sections_missing_their_setters_say_one_thing_each(tmp_path):
    pack = make_town_pack.build(tmp_path)
    _without(pack, "vault-1-read")
    _without(pack, "king-slain")
    assert [f.split(": ")[0] + ": " + f.split(": ")[1]
            for f in locks.progress_findings(pack)] == [
        "section cellar: the flag 'vault-1-read' has no setter - no rule "
        "sets it and no vault note records it, so the gate "
        "'town-seen:cellar:c0' can never open",
        "section hollow: the flag 'king-slain' has no setter - no rule sets "
        "it and no vault note records it, so the gate "
        "'town-seen:hollow:c0' can never open"]


# ---- what a setter is -----------------------------------------------------

def test_a_setter_is_any_rule_that_sets_the_flag():
    assert locks._rule_setters({"rules": [
        {"id": "r", "when": {"starts": {}}, "then": [{"set": "lit"}]}]}) == \
        {"lit"}


def test_a_rule_that_gives_an_item_sets_nothing():
    assert locks._rule_setters({"rules": [
        {"id": "r", "then": [{"give": "pebble"}, {"say": "here"}]}]}) == set()


def test_a_pack_with_no_rules_has_no_setters():
    assert locks._rule_setters({}) == set()
    assert locks._rule_setters({"rules": "nonsense"}) == set()


# ---- the door `vefr check` opens ------------------------------------------

def test_the_walk_runs_inside_the_section_sweep(pack):
    """`vefr check` calls `section_findings`, so the walk is part of the
    same 200-seed gate and a missing setter is a non-zero exit."""
    findings = locks.section_findings(pack, seeds=1)
    assert findings == []
    _without(pack, "vault-1-read")
    assert locks.section_findings(pack, seeds=1) == [
        "section cellar: the flag 'vault-1-read' has no setter - no rule "
        "sets it and no vault note records it, so the gate "
        "'town-seen:cellar:c0' can never open"]


def test_the_whole_two_hundred_seed_gate_is_green_for_the_fixture(pack):
    """Acceptance: the walk sits inside the same sweep every Section of a
    pack is held to, and a pack that holds passes both."""
    assert locks.section_findings(pack) == []


def test_a_bad_fixture_fails_the_check_where_the_author_looks(tmp_path):
    """The sentence at the door itself: `vefr check` prints these findings
    and exits non-zero on them, so a story nobody can finish is a failed
    check rather than a note in a design document."""
    import contextlib
    import io
    import types
    from vefr import cli

    def check(pack):
        buf = io.StringIO()
        args = types.SimpleNamespace(map_cmd="validate", pack=str(pack))
        with contextlib.redirect_stdout(buf):
            code = cli.cmd_map(args)
        return code, buf.getvalue()

    good = make_town_pack.build(tmp_path / "good")
    code, out = check(good)
    assert code == cli.EXIT_OK and "no setter" not in out, out

    bad = make_town_pack.build(tmp_path / "bad")
    _without(bad, "vault-1-read")
    code, out = check(bad)
    assert code == cli.EXIT_ERROR, out
    assert ("section cellar: the flag 'vault-1-read' has no setter"
            in out), out


# ---- nothing today changes ------------------------------------------------

def test_a_pack_with_no_descent_has_no_story_to_walk():
    """Every pack in the tree today, the shipped one included: no descent,
    so no story, so nothing to ask."""
    assert locks.progress_findings(SAMPLE) == []
    assert locks.section_findings(SAMPLE) == []


def test_a_descent_with_no_sections_has_nothing_to_walk(tmp_path):
    pack = make_town_pack.build(tmp_path, descent={
        "run_seed": "run-a", "entry": {"region": "town", "at": [7, 5]},
        "sections": []})
    assert locks.progress_findings(pack) == []


def test_a_directory_that_is_not_a_pack_is_not_asked(tmp_path):
    assert locks.progress_findings(tmp_path) == []


def test_a_pack_whose_descent_names_a_section_it_does_not_ship(tmp_path):
    """`descent_of` says so out loud, and the walk does not then invent a
    story over Sections that are not there."""
    pack = make_town_pack.build(tmp_path)
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    world["descent"] = dict(world["descent"], sections=["nowhere"])
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")
    assert locks.progress_findings(pack) == []


def test_a_copy_of_the_fixture_pack_is_still_a_pack(tmp_path):
    """A guard on the guard: the fixture is what every test here walks, so
    it is worth knowing it is a real, loadable pack."""
    pack = make_town_pack.build(tmp_path)
    listed = delve.descent_of(load_pack(pack), pack)["sections"]
    assert [s["id"] for s in listed] == ["cellar", "hollow"]
    assert copy.deepcopy(listed) == listed