"""A map book names a region the pack has, and on a generated floor a tile the hero can reach.

2026-10-08: Cottage removed its hand-built cellar and six books went on naming `floor-1` and
`king-room`. Nothing could find them, and `vefr check` stayed green, because a map book's region
was only ever checked when it was the town. A map book now names a declared region or a floor of
the generated descent (`<section>-<cycle>-<floor>`), and on a generated floor its tile must be
ground joined to the stairs on the floor a new game draws.
"""

import json
import sys
from pathlib import Path

import pytest

from vefr import delve, maplab
from vefr.library import load_library, validate_books

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
import make_descent_pack  # noqa: E402


def book(pack, name, region, at, chest=False):
    folder = pack / "library"
    folder.mkdir(exist_ok=True)
    front = [f"title: {name}", "found: map", f"region: {region}", f"at: [{at[0]}, {at[1]}]", "kind: note"]
    if chest:
        front.append("chest: yes")
    (folder / f"{name}.md").write_text("---\n" + "\n".join(front) + "\n---\nA page.\n", encoding="utf-8")


def region_errors(pack):
    return [e for e in maplab.validate(maplab.load_pack(pack), pack_dir=pack) if e.startswith("library book")]


@pytest.fixture
def pack(tmp_path):
    return make_descent_pack.build(tmp_path)


def floor(pack, depth):
    w = maplab.load_pack(pack)
    return delve.floor_plan(delve.descent_of(w, pack), depth)


def test_a_book_on_a_region_the_pack_lost_is_refused_with_a_sentence(pack):
    book(pack, "lost-note", "floor-1", [3, 4])
    found = region_errors(pack)
    assert found == ["library book 'lost-note': region 'floor-1' is not a region of this pack; "
                     "it has town, or a generated floor such as cellar-0-1"]


def test_a_fixed_tile_on_a_generated_floor_is_refused_even_when_it_is_reachable_today(pack):
    # The floor is redrawn every run (New descent) and whenever its Section changes: a
    # tile that is floor in this run can be wall in the next. Pinned books name a place.
    plan = floor(pack, 2)
    book(pack, "deep-note", plan["name"], plan["anchors"]["up"])
    found = region_errors(pack)
    assert len(found) == 1 and "is a generated floor, redrawn every run" in found[0]
    assert "give place: near-up, near-down or anywhere instead of at" in found[0]


def test_a_floor_past_the_end_of_its_section_is_not_a_region(pack):
    book(pack, "too-deep", "cellar-0-9", [3, 4])              # the fixture's cellar has 3 floors
    assert "region 'cellar-0-9' is not a region of this pack" in region_errors(pack)[0]


def test_without_a_descent_a_floor_name_is_just_an_unknown_region(pack):
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    del world["descent"]
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")
    book(pack, "deep-note", "cellar-0-1", [3, 4])
    assert region_errors(pack) == ["library book 'deep-note': region 'cellar-0-1' is not a region "
                                   "of this pack; it has town"]


def test_a_caller_that_names_no_regions_checks_exactly_as_before(pack):
    book(pack, "lost-note", "floor-1", [3, 4])
    assert validate_books(load_library(pack)) == []
