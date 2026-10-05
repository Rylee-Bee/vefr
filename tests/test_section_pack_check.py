"""`vefr check` reads the affix list and the Sections (ADR 0014).

`shapes.check_section` - and `check_affixes` inside it - is the engine's
own read of a Section pack and of the one `affixes.json` every Section
shares, and it is the whole of ADR 0014's "Validator rejects" list. It was
never called from a path a pack goes through, so a duplicate affix id, an
affix a Section names and the pack never defines, a malformed affix
record, a group led by an elite in a Section with no affix to lead it, and
a family the Blueprint does not have all validated green: the pack passed
`vefr check` and the first floor of a run found out instead.

These tests are the door itself. Every fixture is a real pack built the
shipped way - `make_blueprint_pack` plus a real `vefr normalize` for the
lock - with `affixes.json` at its root and one `sections/<id>.json` inside
it, and every assertion is on the sentences `vefr check` prints: the
sentence AND the pointer, because the pointer is what says which record
of a list is wrong.

Run with:

    bash tests/run.sh tests/test_section_pack_check.py
"""

import json

from blueprint_helpers import mk, normalized_pack, vefr

import vefr.maplab as maplab

# A Section pack that is legal by `shapes.check_section`: `elites` and
# `groups` inside their ranges, an elite-led group with affixes to lead
# it, and one family `STD_BLUEPRINT` below defines.
GOOD_SECTION = {
    "section": 1, "id": "cellar", "floors": 9,
    "rooms": [12, 18],
    "families": [{"family": "beetle", "weight": 5}],
    "elites": {"per_floor": [1, 2], "affixes": ["broad", "quick"]},
    "groups": {"per_floor": [1, 2], "minions": [2, 3], "leader": "elite",
               "same_family": True, "wake": "all", "leash": 6},
}

# The two affixes `GOOD_SECTION` names, each a legal record.
GOOD_AFFIXES = [
    {"id": "broad", "label": "Broad {name}", "hp": 1.5, "atk": 1.0,
     "xp": 1.5, "scale": 1.3, "extra_drops": 1},
    {"id": "quick", "label": "Quick {name}", "sight": 1},
]


def a_pack(tmp_path, sections=None, affixes=None, blueprint=None):
    """A pack that already validates, carrying the two E7 files.

    `sections` is `{file name: section pack}` written under `sections/`,
    and `affixes` the list at the pack root; either left off, the file is
    absent - which is what every pack in the tree looks like today. The
    base is a Blueprint pack (`vefr normalize` and all), because a
    Section names its families by id and the family checks need one.
    """
    built = normalized_pack(tmp_path,
                            blueprint=mk.STD_BLUEPRINT if blueprint is None
                            else blueprint)
    if affixes is not None:
        (built / "affixes.json").write_text(
            json.dumps(affixes, indent=2) + "\n", encoding="utf-8")
    for name, section in (sections or {}).items():
        (built / "sections").mkdir(exist_ok=True)
        (built / "sections" / name).write_text(
            json.dumps(section, indent=2) + "\n", encoding="utf-8")
    return built


def check(built):
    """The problems `validate` reports for a pack, as a list of sentences."""
    return maplab.validate(maplab.load_pack(built), pack_dir=built)


# ---- the door: a good pack says nothing ----

def test_a_pack_with_good_sections_and_affixes_validates(tmp_path):
    """The wiring costs a legal pack nothing.

    Every fixture here is otherwise a pack that has always validated, and
    the two E7 files are legal by the ADR, so this has to stay green: a
    check that refused its own shape would be worse than no check.
    """
    assert check(a_pack(tmp_path, {"cellar.json": GOOD_SECTION},
                        GOOD_AFFIXES)) == []


def test_a_pack_with_neither_file_validates_unchanged(tmp_path):
    """Both files are E7 additions and neither is required.

    A pack that ships no `affixes.json` and no `sections/` reads nothing
    new here: an empty list, not a problem about what it does not have.
    """
    assert check(a_pack(tmp_path)) == []


# ---- the affix list, on its own ----

def test_a_duplicate_affix_id_is_reported(tmp_path):
    """`quick` used twice, named at the SECOND record.

    ADR 0014: "Ids are unique." The pointer is the second record, so the
    pair that collides is named in one sentence. The run used to place an
    elite whose affix the second `quick` also claims.
    """
    affixes = GOOD_AFFIXES + [
        {"id": "quick", "label": "Quick {name}", "sight": 2}]
    assert check(a_pack(tmp_path, affixes=affixes)) == [
        "affixes.json: /affixes/2/id every affix id must be its own, "
        "and 'quick' is used twice"]


def test_a_malformed_affix_record_is_reported(tmp_path):
    """A record that is not a record, with the pointer at the record.

    `moves` is reserved (ADR 0014, "Affix") and refused as the unknown
    key it is, and the pointer says which record of the list carries it.
    """
    affixes = [GOOD_AFFIXES[0], {"id": "quick", "label": "Quick {name}",
                                 "moves": 1}]
    assert check(a_pack(tmp_path, affixes=affixes)) == [
        "affixes.json: /affixes/1/moves affix has an unknown key 'moves'; "
        "it may only hold id, label, hp, atk, xp, sight, scale and "
        "extra_drops"]


def test_an_affix_list_that_is_not_a_list_is_reported(tmp_path):
    """The list itself, not a record in it: one sentence at `/affixes`."""
    built = a_pack(tmp_path)
    (built / "affixes.json").write_text('{"big": true}', encoding="utf-8")
    assert check(built) == [
        "affixes.json: /affixes affixes must be a list of affix records"]


# ---- what a Section names ----

def test_an_affix_the_pack_never_defines_is_reported(tmp_path):
    """`elites.affixes` names an id the list does not carry.

    The pointer is the entry in `elites.affixes`, not the record that is
    missing - there is no record to point at.
    """
    section = dict(GOOD_SECTION,
                   elites={"per_floor": [1, 2], "affixes": ["broad", "vast"]})
    assert check(a_pack(tmp_path, {"cellar.json": section}, GOOD_AFFIXES)) == [
        "sections/cellar.json: /elites/affixes/1 every affix a section "
        "names must be defined by the pack, and 'vast' is not"]


def test_a_group_led_by_an_elite_with_no_affix_is_reported(tmp_path):
    """The pack asks for a monster it cannot build.

    A group led by an elite in a Section whose `elites.affixes` is empty
    is a normal monster with a ring around it: neither the monster the
    pack asked for nor the cap it spent.
    """
    section = dict(GOOD_SECTION, elites={"per_floor": [1, 2], "affixes": []})
    assert check(a_pack(tmp_path, {"cellar.json": section}, GOOD_AFFIXES)) == [
        "sections/cellar.json: /groups/leader a group led by an elite needs "
        "at least one affix, and the section names none"]


def test_a_group_block_out_of_range_is_reported(tmp_path):
    """`groups.leash` is 3 to 12; the sentence quotes the pair."""
    section = dict(GOOD_SECTION,
                   groups=dict(GOOD_SECTION["groups"], leash=2))
    assert check(a_pack(tmp_path, {"cellar.json": section}, GOOD_AFFIXES)) == [
        "sections/cellar.json: /groups/leash groups.leash must be between "
        "3 and 12"]


def test_a_section_that_is_not_json_is_reported(tmp_path):
    """A file the author is still editing, said once and plainly."""
    built = a_pack(tmp_path, {"cellar.json": GOOD_SECTION}, GOOD_AFFIXES)
    (built / "sections" / "cellar.json").write_text("{", encoding="utf-8")
    assert check(built) == [
        "sections/cellar.json: cellar.json is not valid JSON"]


def test_a_section_pack_that_is_not_an_object_is_reported(tmp_path):
    """A list where a Section pack goes is not a Section pack."""
    built = a_pack(tmp_path)
    (built / "sections").mkdir()
    (built / "sections" / "cellar.json").write_text("[]", encoding="utf-8")
    assert check(built) == [
        "sections/cellar.json: a Section pack must be a JSON object"]


# ---- the families a Section names ----

def test_a_family_the_blueprint_does_not_have_is_reported(tmp_path):
    """A Section names Blueprint families by id and carries no records.

    ADR 0014's "Validator rejects": a family not in the Blueprint is
    refused, and the pointer is the entry in `families`. This is the one
    question `shapes` cannot answer for itself, so it is asked through
    `blueprint.resolve_family`.
    """
    section = dict(GOOD_SECTION, families=[{"family": "wyrm", "weight": 1}])
    assert check(a_pack(tmp_path, {"cellar.json": section}, GOOD_AFFIXES)) == [
        "sections/cellar.json: /families/0/family unknown family 'wyrm'"]


def test_a_family_with_no_stats_is_reported(tmp_path):
    """A family the Blueprint has, resolving without `hp` or `atk`.

    The Blueprint is the only record of what a family is, so a family
    with no stats gives the pop stage nothing to scale - and the pointer
    still names the Section entry, which is the pack's own mistake.
    """
    blueprint = json.loads(json.dumps(mk.STD_BLUEPRINT))
    blueprint["families"]["hollow"] = {"defaults": {"name": "a hollow"}}
    section = dict(GOOD_SECTION, families=[{"family": "hollow", "weight": 1}])
    assert check(a_pack(tmp_path, {"cellar.json": section}, GOOD_AFFIXES,
                         blueprint=blueprint)) == [
        "sections/cellar.json: /families/0/family every family a section "
        "names needs an hp in the blueprint, and 'hollow' has none"]


def test_a_pack_with_no_blueprint_skips_the_family_checks(tmp_path):
    """No Blueprint, no families to resolve: skipped, not answered wrongly.

    A pack may carry its families somewhere this check has not been taught
    to read yet, so the families are left alone rather than told they are
    unknown: a false refusal is worse than a check that waits.
    """
    built = a_pack(tmp_path, {"cellar.json": GOOD_SECTION}, GOOD_AFFIXES)
    (built / "blueprint.json").unlink()
    (built / "blueprint.lock.json").unlink()
    assert check(built) == []


# ---- the sentence, through the front door ----

def test_vefr_check_fails_and_prints_the_affix_pointer(tmp_path):
    """`vefr check` is the door; this is the whole way round.

    The exit code is non-zero and the sentence and the pointer are on the
    output, because an author who reads one line of a failed check has to
    be able to find the record it names.
    """
    built = a_pack(tmp_path, {"cellar.json": GOOD_SECTION},
                   GOOD_AFFIXES + [{"id": "broad", "label": "Broad {name}"}])
    rc, out = vefr("check", "--pack", built)
    assert rc != 0
    assert ("FAIL: affixes.json: /affixes/2/id every affix id must be its "
            "own, and 'broad' is used twice") in out


def test_vefr_check_passes_a_good_pack(tmp_path):
    """And the other half: the door is not stuck shut."""
    built = a_pack(tmp_path, {"cellar.json": GOOD_SECTION}, GOOD_AFFIXES)
    rc, out = vefr("check", "--pack", built)
    assert rc == 0, out
