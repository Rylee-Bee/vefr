"""Books pinned to a generated floor: the floor chooses the tile, every run, the same in both languages.

A generated floor is redrawn every run ("New descent") and whenever its Section changes, so a
library book on one names `place: near-up | near-down | anywhere` instead of a tile. On
2026-10-08 Cottage's six story notes were re-homed by fixed tiles (cottage#113), which hold for
the first run only. `delve.place_books` chooses reachable ground off the stairs and monsters, one
book per tile, from the floor's own `book|<id>` stream; the descent part's `placeBooks` is its
twin, and `vefr check` proves every pinned book finds a tile in each of 200 runs.
"""

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli, delve, library, maplab

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
import make_descent_pack  # noqa: E402
from test_descent_floors import DESCENT  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "descent_parity_harness.mjs"
BOOKS = [{"id": "a-letter", "place": "near-up"}, {"id": "b-candle", "place": "near-down"},
         {"id": "c-coin", "place": "anywhere"}]


def plan(depth=1, run=0):
    return delve.floor_plan(DESCENT, depth, run)


# ---------------------------------------------------------------- where the floor puts them

@pytest.mark.parametrize("run", range(40))
def test_every_book_lies_on_reachable_floor_off_the_stairs_and_monsters_one_to_a_tile(run):
    p = plan(1 + run % 3, run)
    got = delve.place_books(p, BOOKS)
    assert set(got) == {b["id"] for b in BOOKS}
    up, down = tuple(p["anchors"]["up"]), tuple(p["anchors"]["down"])
    from_up = delve._floor_distances(p["rows"], up)
    from_down = delve._floor_distances(p["rows"], down)
    mobs = {tuple(m["at"]) for m in p["mobs"]}
    tiles = [tuple(xy) for xy in got.values()]
    assert len(set(tiles)) == len(tiles)
    for t in tiles:
        assert p["rows"][t[1]][t[0]] == "." and t in from_up and t not in mobs | {up, down}
    lo, hi = delve.BOOK_NEAR
    assert lo <= from_up[tuple(got["a-letter"])] <= hi
    assert lo <= from_down[tuple(got["b-candle"])] <= hi
    assert from_up[tuple(got["c-coin"])] >= lo


def test_the_same_run_always_puts_a_book_in_the_same_place_whatever_order_it_is_listed_in():
    shuffled = BOOKS[:]
    random.Random(7).shuffle(shuffled)
    assert delve.place_books(plan(), BOOKS) == delve.place_books(plan(), shuffled) == delve.place_books(plan(), BOOKS)


def test_a_new_run_moves_the_books():
    spots = {json.dumps(delve.place_books(plan(1, run), BOOKS), sort_keys=True) for run in range(20)}
    assert len(spots) > 15


def test_a_floor_with_no_tile_near_a_stair_falls_back_to_anywhere_reachable():
    tiny = {"key": "k", "rows": ["#####", "#u.d#", "#####"], "anchors": {"up": [1, 1], "down": [3, 1]},
            "mobs": []}
    assert delve.place_books(tiny, [{"id": "x", "place": "near-up"}]) == {"x": [2, 1]}
    assert delve.place_books(tiny, [{"id": "x", "place": "near-up"}, {"id": "y", "place": "anywhere"}]) == {"x": [2, 1]}


# ---------------------------------------------------------------- what the validator says

@pytest.fixture
def pack(tmp_path):
    return make_descent_pack.build(tmp_path)


def put(pack, name, front):
    folder = pack / "library"
    folder.mkdir(exist_ok=True)
    (folder / f"{name}.md").write_text("---\n" + "\n".join(f"{k}: {v}" for k, v in front.items())
                                       + "\nkind: note\n---\nA page.\n", encoding="utf-8")


def book_errors(pack):
    return [e for e in maplab.validate(maplab.load_pack(pack), pack_dir=pack) if e.startswith("library book")]


def test_pinned_books_on_generated_floors_check_clean(pack):
    put(pack, "a-letter", {"title": "A letter", "found": "map", "region": "cellar-0-1", "place": "near-up", "chest": "yes"})
    put(pack, "b-candle", {"title": "A candle", "found": "map", "region": "cellar-0-1", "place": "near-down"})
    put(pack, "c-coin", {"title": "A coin", "found": "map", "region": "cellar-0-3", "place": "anywhere"})
    assert book_errors(pack) == []


@pytest.mark.parametrize("front, says", [
    ({"region": "town", "place": "near-up"}, "place is for a book on a generated floor; town is drawn by hand, so give at: [x, y]"),
    ({"region": "cellar-0-1", "place": "somewhere"}, "place must be near-up, near-down, anywhere, vault-note or vault-chest"),
    ({"region": "cellar-0-1", "place": "near-up", "at": "[3, 4]"}, "a book with place takes no at"),
    ({"region": "cellar-0-9", "place": "near-up"}, "region 'cellar-0-9' is not a region of this pack"),
])
def test_a_place_the_pack_cannot_use_is_refused_with_a_sentence(pack, front, says):
    put(pack, "bad", {"title": "Bad", "found": "map", **front})
    found = book_errors(pack)
    assert any(says in e for e in found), found


def test_place_goes_with_a_map_book(pack):
    put(pack, "bad", {"title": "Bad", "found": "shelf", "place": "near-up"})
    assert any("place goes with found: map" in e for e in book_errors(pack))


def test_a_floor_that_has_no_room_for_a_book_in_some_run_is_named(pack, monkeypatch):
    put(pack, "a-letter", {"title": "A letter", "found": "map", "region": "cellar-0-1", "place": "near-up"})
    real = delve.place_books
    monkeypatch.setattr(delve, "place_books", lambda p, books: {} if p["key"].endswith("/run-7/cellar/0/1") else real(p, books))
    found = book_errors(pack)
    assert found == ["library book 'a-letter': cellar-0-1 has no free tile for it in run 7"], found


def test_the_woven_game_carries_a_books_place(pack):
    put(pack, "a-letter", {"title": "A letter", "found": "map", "region": "cellar-0-1", "place": "near-up"})
    html = cli.weave_html(pack)
    assert '"place": "near-up"' in html


def test_the_sweep_draws_two_hundred_runs():
    assert library.PIN_RUNS == 200


# ---------------------------------------------------------------- the JavaScript twin answers the same

@pytest.fixture(scope="module")
def replay(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    home = tmp_path_factory.mktemp("pins-parity")
    html = home / "p.html"
    html.write_text(cli.weave_html(ROOT / "worlds" / "sample-world"), encoding="utf-8")
    pins = [{"depth": depth, "run": run, "books": BOOKS} for depth in (1, 2, 3, 4, 5) for run in range(8)]
    cases = home / "cases.json"
    cases.write_text(json.dumps({"descent": DESCENT, "depths": [], "runs": [], "pins": pins}), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(html), str(cases)], capture_output=True, text=True, timeout=300)
    if run.returncode != 0 and "Cannot find package 'jsdom'" in run.stderr:
        pytest.skip("jsdom not installed (npm ci)")
    assert run.returncode == 0, run.stderr + run.stdout
    return pins, json.loads(run.stdout)["pins"]


def test_the_javascript_twin_places_every_book_where_python_does(replay):
    pins, answers = replay
    assert len(answers) == len(pins) == 40
    for case, answer in zip(pins, answers):
        want = delve.place_books(delve.floor_plan(DESCENT, case["depth"], case["run"]), case["books"])
        assert answer == want, (case["depth"], case["run"])
