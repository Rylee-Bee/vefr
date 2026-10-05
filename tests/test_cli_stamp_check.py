"""`vefr stamp check` - the gate a stamp pack has to pass before a floor uses it.

ADR 0013's Validation section names four kinds of check and two example
sentences, and this file pins both. The sentences are pinned as words
rather than as output, because the two examples are about numbers - a
room that places on 85 of 100 floors, a room 15 wide on floors that
start at 64 - and those numbers are the ones a check exists to produce.
The exit codes are pinned through the real command, on a real
temporary pack, because an exit code nobody calls is not an exit code.

The pack these tests build is a floor the generator can actually lay
out: three required roles, each a 5x5 room, and a 64x48 Section. It is
small on purpose - the sweep is the slow half and this file is about
what the check says, not about how long it takes.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import vefr.cli as cli
from vefr import delve_v3, stamp_check, stamps


# A 5x5 room per required role, each one a single component with a door
# in its west wall and a mouth outside the rectangle, which is the shape
# rule `stamps.read_v1` enforces.
LANDMARK = {
    "stamp": 1, "id": "test-alcove", "role": "landmark", "tags": ["cellar"],
    "weight": 2, "poi": "the test alcove",
    "rows": ["#####", "#...#", "+....", "#...#", "#####"],
}
HALL = {
    "stamp": 1, "id": "test-hall", "role": "warden-hall", "tags": ["cellar"],
    "weight": 1,
    "rows": ["#####", "#...#", "+W..#", "#...#", "#####"],
    "legend": {"W": {"anchor": "warden"}},
}
VAULT = {
    "stamp": 1, "id": "test-vault", "role": "vault", "tags": ["cellar"],
    "weight": 1,
    "rows": ["#####", "#CNH#", "+...#", "#####", "#####"],
    "legend": {"C": {"anchor": "chest"}, "N": {"anchor": "note"},
               "H": {"anchor": "home"}},
}
PACK = (LANDMARK, HALL, VAULT)

SECTION = {
    "section": 1, "id": "cellar", "floors": 2,
    "size": {"w": [64, 80], "h": [48, 56]}, "rooms": [12, 18],
    "families": [{"family": "rat", "weight": 5, "depth": [1, 6]}],
    "elites": {"per_floor": [1, 2], "affixes": ["big"]},
    "groups": {"per_floor": [1, 2], "minions": [2, 3]},
    "pois": ["the drowned well"], "warden": "ashwing", "vault": "vault-cellar",
    "stamps": ["cellar", "any"],
}


def _pack(tmp_path, records=PACK, section=SECTION) -> str:
    """A pack directory with `stamps/` and `sections/` in it."""
    (tmp_path / "stamps").mkdir(exist_ok=True)
    (tmp_path / "sections").mkdir(exist_ok=True)
    for record in records:
        (tmp_path / "stamps" / f"{record['id']}.json").write_text(
            json.dumps(record), encoding="utf-8")
    (tmp_path / "sections" / f"{section['id']}.json").write_text(
        json.dumps(section), encoding="utf-8")
    return str(tmp_path)


def _args(pack: str, seeds: int = 1) -> SimpleNamespace:
    return SimpleNamespace(pack=pack, seeds=seeds)


@pytest.fixture
def out(capsys):
    def _read() -> str:
        return capsys.readouterr().out

    return _read


# --------------------------------------------------------------- exit codes


def test_a_pack_that_holds_up_exits_zero(tmp_path, out):
    rc = cli.cmd_stamp_check(_args(_pack(tmp_path)))
    assert rc == cli.EXIT_OK
    text = out()
    assert "0 problems" in text


def test_a_stamp_with_no_door_is_reported_and_exits_one(tmp_path, out):
    """The first of the ADR's two example sentences, word for word.

    A room with no `+` is a room nothing can reach, and the sentence
    says what to do about it rather than only what is wrong.
    """
    broken = dict(LANDMARK, id="wine-alcove", poi="")
    broken["rows"] = ["#####", "#...#", ".....", "#...#", "#####"]
    rc = cli.cmd_stamp_check(_args(_pack(tmp_path, PACK[:1] + (broken, HALL, VAULT))))
    assert rc == cli.EXIT_ERROR
    assert ("stamp wine-alcove: no door socket (+) on its edge, so nothing can "
            "reach it; put a + in the outer wall. /rows") in out()


def test_a_pack_with_no_stamps_directory_is_a_usage_error(tmp_path, capsys):
    (tmp_path / "world.json").write_text("{}", encoding="utf-8")
    rc = cli.cmd_stamp_check(_args(str(tmp_path)))
    assert rc == cli.EXIT_USAGE
    assert "no stamps directory" in capsys.readouterr().out


def test_a_pack_with_no_sections_directory_is_a_usage_error(tmp_path, capsys):
    (tmp_path / "stamps").mkdir()
    rc = cli.cmd_stamp_check(_args(str(tmp_path)))
    assert rc == cli.EXIT_USAGE
    assert "no sections directory" in capsys.readouterr().out


def test_the_seeds_flag_is_the_number_of_seeds_swept(tmp_path, out):
    """`--seeds 1` and `--seeds 2` sweep one and two seeds, and say so.

    The flag is the only way an author can make this check quick, so
    the report has to carry the number it used.
    """
    cli.cmd_stamp_check(_args(_pack(tmp_path), 1))
    one = out()
    cli.cmd_stamp_check(_args(_pack(tmp_path), 2))
    two = out()
    assert "1 seed" in one
    assert "2 seeds" in two
    assert "8 floors" in one        # 1 seed x 2 floors x 4 kinds
    assert "16 floors" in two


# ------------------------------------------------------------ the two numbers


def test_the_placement_sentence_is_the_adrs_second_example():
    """`stamp crypt-hall: placed on 171 of 200 cellar floors (85%)...`

    Pinned with the ADR's own numbers rather than a sweep's, because
    the sentence is the author's only handle on how rare a room became
    and it has to say the share, the bar and the reason in one line.
    """
    line = stamp_check.placement_sentence(
        "crypt-hall", 171, 200, "cellar", 15, 64, 95)
    assert line == (
        "stamp crypt-hall: placed on 171 of 200 cellar floors (85%); it needs "
        "95%. It is 15 wide and cellar floors start at 64. /rows")


def test_a_required_room_is_told_it_needs_a_hundred_percent():
    """Required rooms must place on every eligible floor."""
    line = stamp_check.placement_sentence(
        "throne-hall", 199, 200, "cellar", 21, 64, 100)
    assert "it needs 100%" in line


def test_the_bar_is_a_ratio_for_a_required_room():
    """171/200 of a required room is reported; 200/200 is not."""
    below = stamp_check.rate_findings(
        {"a": {"placed": 171, "eligible": 200, "sections": ["cellar"],
               "width": 15, "min_width": 64}},
        {"a": {"role": "warden-hall"}})
    assert len(below) == 1
    assert "placed on 171 of 200" in below[0]
    assert stamp_check.rate_findings(
        {"a": {"placed": 200, "eligible": 200, "sections": ["cellar"],
               "width": 15, "min_width": 64}},
        {"a": {"role": "warden-hall"}}) == []


def test_a_required_room_below_a_hundred_percent_is_reported():
    """Required is 100%: one floor in a hundred that loses the room is
    a floor the hero walks into an empty hall."""
    findings = stamp_check.rate_findings(
        {"a": {"placed": 99, "eligible": 100, "sections": ["cellar"],
               "width": 5, "min_width": 64}},
        {"a": {"role": "landmark"}})
    assert len(findings) == 1
    assert "it needs 100%" in findings[0]


def test_an_optional_room_has_no_minimum():
    """Owner decision 4 (confirmed by Rylee 2026-10-04): optional rooms may be
    rare on purpose, so no placement rate ever fails the check."""
    for placed in (0, 1, 50, 94, 100):
        assert stamp_check.rate_findings(
            {"a": {"placed": placed, "eligible": 100, "sections": ["cellar"],
                   "width": 5, "min_width": 64}},
            {"a": {"role": "filler"}}) == []


def test_a_stamp_no_section_can_use_is_not_measured():
    """A pack may ship a stamp its own Sections never name.

    A rate over zero eligible floors is not a rate, and printing 0% for
    a stamp nobody asked for would be a complaint about the wrong thing.
    """
    assert stamp_check.rate_findings({}, {"a": {"role": "filler"}}) == []
    assert stamp_check.rate_findings(
        {"a": {"placed": 0, "eligible": 0, "sections": [], "width": 5,
               "min_width": 64}},
        {"a": {"role": "filler"}}) == []


def test_a_required_room_too_big_for_its_section_is_reported():
    """The fit check: a third of the floor, measured on the small side.

    A 15x20 room on a 64x48 floor is 3% of the area and looks fine,
    which is exactly why the rule is a third of the width and the
    height separately. The width is inside a third of 64 and the height
    is not inside a third of 48, so the height is what catches it.
    """
    big = dict(HALL, id="crypt-hall", rows=[
        "###############", "#W............#", "+.............#"] + [
        "#.............#"] * 16 + ["###############"])
    findings = stamp_check.fit_findings(
        {big["id"]: stamp_check.stamps.read_v1(big)}, [SECTION])
    assert len(findings) == 1
    assert findings[0].startswith("stamp crypt-hall: 15 wide and 20 tall")
    assert "cellar floors start at 64x48" in findings[0]


def test_a_required_room_that_fits_is_not_reported():
    small = stamp_check.stamps.read_v1(HALL)
    assert stamp_check.fit_findings({"test-hall": small}, [SECTION]) == []


# ------------------------------------------------------------- the fit sweep


def test_a_21_by_21_landmark_is_refused_on_a_small_section(tmp_path, out):
    """The cap is 21x21 and a Section has to be able to hold one.

    This is the check the size cap exists for: a hand-drawn throne room
    at the cap, on floors that start at 48 tall, is a room that can
    never be placed and the author hears about it here rather than in
    a hundred silent sweeps.
    """
    room = dict(LANDMARK, id="throne-hall", rows=[
        "#" * 21, "#" + "." * 19 + "#", "+" + "." * 19 + "#"] + [
            "#" + "." * 19 + "#"] * 17 + ["#" * 21])
    room["rows"][10] = "#" + "." * 9 + "P" + "." * 9 + "#"
    room.pop("poi")
    room["legend"] = {"P": {"anchor": "poi"}}
    small = dict(SECTION, size={"w": [48, 56], "h": [32, 40]})
    rc = cli.cmd_stamp_check(_args(_pack(tmp_path, (room, HALL, VAULT), small)))
    assert rc == cli.EXIT_ERROR
    assert "stamp throne-hall: 21 wide and 21 tall" in out()


def test_a_section_with_no_size_is_reported_and_skipped(tmp_path, out):
    """A Section that does not say how big its floors are cannot be swept."""
    shapeless = dict(SECTION)
    shapeless.pop("size")
    rc = cli.cmd_stamp_check(_args(_pack(tmp_path, PACK, shapeless)))
    assert rc == cli.EXIT_ERROR
    assert "section cellar: no size" in out()


# ------------------------------------------------------------ the defect


def test_a_floor_that_fell_back_over_a_stamp_reports_the_defect(tmp_path, out):
    """ADR 0013's Placement 4: the v2 floor carries the reason, so is it read.

    A 21x21 warden-hall cannot fit a 24x16 floor at any orientation, so
    every swept floor falls back to v2 and none of them carries a stamped
    room. The share findings say how often; the defect is what says the
    hall is the reason, and a check that counted those floors without
    naming the cause was reporting a rate about its own sweep.
    """
    hall = ["##+##" + "#" * 16] + ["#" + "." * 19 + "#"] * 19 + ["#" * 10 + "+" + "#" * 10]
    hall[1] = "#" + "W" + "." * 18 + "#"
    record = {
        "stamp": 1, "id": "too-big-hall", "role": "warden-hall", "tags": ["too-big"],
        "legend": {"W": {"anchor": "warden"}}, "rows": hall,
    }
    section = dict(SECTION, size={"w": [24, 24], "h": [16, 16]},
                   rooms=[6, 6], floors=1, stamps=["too-big"])
    section.pop("vault")
    rc = cli.cmd_stamp_check(_args(_pack(tmp_path, (record,), section), 1))
    text = out()
    assert rc == cli.EXIT_ERROR
    assert ("stamp warden-hall: did not place on 4 of 4 cellar floors the "
            "sweep laid, so each of them fell back to v2 and carries no "
            "stamped room at all /stamp_defect") in text
    # The share it explains is on the same report.
    assert "placed on 0 of 4 cellar floors" in text


# -------------------------------------------------------------- the graph


def _floor(rows: list[str], anchors: dict, stamps: list[dict],
           secrets: list[list[int]] | None = None) -> dict:
    """A FloorPlan shaped like the generator's, for the graph check."""
    return {
        "gen": 3, "w": len(rows[0]), "h": len(rows), "rows": rows,
        "rooms": [[0, 0, len(rows[0]), len(rows), "landmark"]],
        "anchors": anchors, "pois": [], "spawns": [], "chests": [],
        "secrets": secrets or [], "stamps": stamps,
    }


def test_a_placed_room_with_no_door_in_use_is_reported():
    """Graph check 1: a placed stamp has at least one used socket.

    A room the corridor never reached is a wall the hero cannot get
    past, and the placement record is the only place that knows.
    """
    plan = _floor(
        ["#####", "#...#", "#...#", "#...#", "#####"],
        {"up": [1, 1], "down": [3, 3]},
        [{"id": "test-alcove", "role": "landmark", "room": 0, "at": [1, 1],
          "size": [3, 3], "orientation": 0, "anchors": {"poi": [2, 2]}}])
    findings = stamp_check.graph_findings(plan)
    assert len(findings) == 1
    assert findings[0].startswith("stamp test-alcove: placed at 1,1 with no door in use")


def test_a_room_whose_anchor_is_behind_a_secret_is_reported():
    """Graph check 3: secrets count as passable, except to warden and vault.

    A chest you can only reach by opening a secret is a secret, not a
    chest, and the warden behind one is a floor the player cannot
    finish.
    """
    plan = _floor(
        ["#######", "#.....#", "###.###", "#.....#", "#######"],
        {"up": [3, 1], "down": [3, 3], "warden": [1, 1], "chest": None},
        [{"id": "test-alcove", "role": "landmark", "room": 0, "at": [1, 3],
          "size": [5, 1], "orientation": 0, "socket": [3, 2],
          "anchors": {"chest": [1, 3]}}],
        secrets=[[3, 2]])
    findings = stamp_check.graph_findings(plan)
    assert len(findings) == 1
    assert ("stamp test-alcove: its chest at 1,3 cannot be reached from up "
            "without opening a secret") in findings[0]


def test_a_room_whose_warden_is_behind_a_secret_is_reported():
    """The warden is the case the ADR names, so it is its own test."""
    plan = _floor(
        ["#######", "#.....#", "###.###", "#.....#", "#######"],
        {"up": [3, 1], "down": [3, 3], "warden": [1, 3]},
        [{"id": "test-hall", "role": "warden-hall", "room": 0, "at": [1, 3],
          "size": [5, 1], "orientation": 0, "socket": [3, 2],
          "anchors": {"warden": [1, 3]}}],
        secrets=[[3, 2]])
    findings = stamp_check.graph_findings(plan)
    assert len(findings) == 1
    assert "its warden at 1,3" in findings[0]


def test_a_room_reached_the_ordinary_way_is_not_reported():
    """The same floor with a door instead of a secret says nothing."""
    plan = _floor(
        ["#######", "#.....#", "###.###", "#.....#", "#######"],
        {"up": [3, 1], "down": [3, 3], "warden": [1, 3]},
        [{"id": "test-hall", "role": "warden-hall", "room": 0, "at": [1, 3],
          "size": [5, 1], "orientation": 0, "socket": [3, 2],
          "anchors": {"warden": [1, 3]}}])
    assert stamp_check.graph_findings(plan) == []


def test_a_room_behind_another_rooms_secret_is_not_reported():
    """Only the room's own secret is closed to that room's walk.

    The up-corridor runs along the top and the only way down to the
    hall is the secret at 3,2 - a secret that belongs to some other room
    on this floor, not to this one. The hall has its own ordinary socket
    at 7,2 and its warden is standing in it, so the hero walks in
    through a door the author drew; holding the room to a wall it does
    not own is how a pack full of secrets ends up with every room on the
    floor reported.
    """
    plan = _floor(
        ["##########", "#....u####", "###.###+##", "#........#", "##########"],
        {"up": [5, 1], "down": [1, 3], "warden": [7, 3]},
        [{"id": "test-hall", "role": "warden-hall", "room": 0, "at": [6, 2],
          "size": [3, 1], "orientation": 0, "socket": [7, 2],
          "anchors": {"warden": [7, 3]}}],
        secrets=[[3, 2]])
    assert stamp_check.graph_findings(plan) == []


def test_a_room_reached_through_a_secret_is_not_held_to_the_secret_rule():
    """The exemption the ADR's own secret rooms need.

    A `secret` stamp is found, not walked into, so its own anchors sit
    behind its own `?` by the author's drawing. Without the exemption
    every secret room in a pack is reported on every floor it appears
    in, and the check is a check nobody can pass.
    """
    plan = _floor(
        ["#######", "#.....#", "###.###", "#.....#", "#######"],
        {"up": [3, 1], "down": [3, 3], "warden": None},
        [{"id": "test-nook", "role": "secret", "room": 0, "at": [1, 3],
          "size": [5, 1], "orientation": 0, "socket": [3, 2],
          "secret": [3, 2], "anchors": {"chest": [1, 3]}}],
        secrets=[[3, 2]])
    assert stamp_check.graph_findings(plan) == []


def test_the_graph_check_ignores_a_floor_with_no_stamps():
    """Most floors have no stamps, and a check that complains about them
    would be a check that always fails."""
    plan = _floor(["#####", "#.u.#", "#####"],
                  {"up": [1, 1], "down": None}, [])
    assert stamp_check.graph_findings(plan) == []


# ------------------------------------------------------------ across Sections


def test_a_room_eligible_in_two_sections_names_both_of_them():
    """A rate over four Sections belongs to none of them.

    Naming the first one would give the author a sentence whose numbers
    and whose name disagree, which is the one thing the share sentence
    cannot be.
    """
    line = stamp_check.across_sentence(
        "cistern-nook", 99, 288, ["cellar-hub", "cellar-normal"], 5, 64, 95)
    assert line == (
        "stamp cistern-nook: placed on 99 of 288 floors across cellar-hub "
        "and cellar-normal (34%); it needs 95%. It is 5 wide and those "
        "floors start at 64. /rows")


def test_a_room_eligible_in_one_section_keeps_the_adrs_own_sentence():
    line = stamp_check.across_sentence(
        "cistern-nook", 99, 288, ["cellar"], 5, 64, 95)
    assert "of 288 cellar floors" in line
    assert "across" not in line


# ------------------------------------------------------------ what is eligible


def test_a_floor_reports_the_roles_it_wanted_a_stamped_room_for():
    """The trace is what makes "eligible" mean the ADR's three things.

    A floor that drew no secret has no slot for a secret room, and a
    rate that counted it anyway would be a rate about a floor that never
    asked for one.
    """
    records = [stamp_check.stamps.read_v1(record) for record in PACK]
    trace: dict = {}
    delve_v3.generate_floor_v3("check-0", (64, 48), SECTION, "normal",
                                records, 3, trace=trace)
    assert trace["floor_key"] == "check-0/cellar/normal"
    assert set(stamps.REQUIRED_ROLES) <= trace["slots"]


def test_a_trace_changes_nothing_about_the_floor():
    """The trace is a dict the floor writes into, and writes no draws.

    The whole check is measured against floors the generator would have
    drawn anyway, so a floor with a trace and a floor without one have
    to be the same floor.
    """
    records = [stamp_check.stamps.read_v1(record) for record in PACK]
    plain = delve_v3.generate_floor_v3("check-0", (64, 48), SECTION, "normal",
                                       records, 3)
    trace: dict = {}
    traced = delve_v3.generate_floor_v3("check-0", (64, 48), SECTION, "normal",
                                        records, 3, trace=trace)
    assert plain == traced


def test_a_sweep_never_measures_a_room_on_a_floor_its_role_was_not_wanted_on():
    """Every stamp's eligible count is a count of floors, and a subset."""
    records = [stamp_check.stamps.read_v1(record) for record in PACK]
    stats, findings, laid = stamp_check.sweep(records, [SECTION], seeds=2)
    assert laid == 2 * SECTION["floors"] * len(delve_v3.FLOOR_KINDS)
    for name, entry in stats.items():
        assert 0 < entry["eligible"] <= laid, name
        assert entry["placed"] <= entry["eligible"], name
    assert findings == []
