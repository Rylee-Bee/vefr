"""E8b part 2: what is inside the vault (ADR 0015).

A library book with `place: vault-note` or `place: vault-chest` lies on the vault stamp's note or chest anchor on
the Section's warden floor - a fixed tile, not a draw, so it moves no other book. A chest book there is the vault
chest: the library's own found-list makes it open once, for good. The vault's home anchor is a stair to the
descent's entry. Reading the note fires the shipped `opens`, so a pack rule can set the vault's story flag.
"""
import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import play_kit
from vefr import cli, delve, library, stamps
from test_descent_deltas import TOWN, TOWN_HERO, _go, _go_fight, _path
from test_descent_floors import DESCENT

ROOT = Path(__file__).resolve().parents[1]
STAMPS = ROOT / "tests" / "fixtures" / "stamps"
RECORDS = json.loads(json.dumps(stamps.load(STAMPS)))
HARNESS = ROOT / "tests" / "fixtures" / "descent_parity_harness.mjs"
BOOKS = [{"id": "a-chest", "place": "vault-chest"}, {"id": "the-note", "place": "vault-note"},
         {"id": "z-loose", "place": "anywhere"}]


def _descent(stamped=True):
    out = copy.deepcopy(DESCENT)
    cellar = out["sections"][0]
    cellar.update({"pattern": ["entry", "n", "warden"], "stamps": ["cellar"], "vault": "vault-cellar",
                   "warden": "cellar-boss"})
    for section in out["sections"]:
        section["families"] = []
    if stamped:
        out["stamps"] = RECORDS
    return out


def test_vault_books_lie_on_the_vaults_note_and_chest():
    plan = delve.floor_plan(_descent(), 3)
    got = delve.place_books(plan, BOOKS)
    assert got["the-note"] == plan["vault"]["note"] and got["a-chest"] == plan["vault"]["chest"]
    assert "z-loose" in got and got["z-loose"] not in (plan["vault"]["note"], plan["vault"]["chest"])


def test_a_vault_book_moves_no_other_book():
    plan = delve.floor_plan(_descent(), 3)
    alone = delve.place_books(plan, [BOOKS[2]])
    assert delve.place_books(plan, BOOKS)["z-loose"] == alone["z-loose"]


def test_off_the_vault_floor_a_vault_book_has_no_tile():
    assert delve.place_books(delve.floor_plan(_descent(), 2), BOOKS[:2]) == {}


def test_vefr_check_says_when_a_floor_has_no_vault():
    said = library._sweep_pins("cellar-0-2", 2, [{"id": "the-note", "place": "vault-note"}], _descent())
    assert said == ["library book 'the-note': place vault-note needs the vault on its Section's warden floor, "
                    "and cellar-0-2 has none"]
    assert library._sweep_pins("cellar-0-3", 3, [{"id": "the-note", "place": "vault-note"}], _descent()) == []


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_both_languages_put_vault_books_in_the_same_place(tmp_path):
    html = tmp_path / "p.html"
    html.write_text(cli.weave_html(ROOT / "worlds" / "sample-world"), encoding="utf-8")
    cases = tmp_path / "cases.json"
    pins = [{"depth": 3, "run": run, "books": BOOKS} for run in (0, 1, 2)]
    cases.write_text(json.dumps({"descent": _descent(), "depths": [], "runs": [], "pins": pins}))
    run = subprocess.run(["node", str(HARNESS), str(html), str(cases)], capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr + run.stdout
    got = json.loads(run.stdout)["pins"]
    for case, js in zip(pins, got):
        assert js == delve.place_books(delve.floor_plan(_descent(), 3, case["run"]), BOOKS)


# ---- the whole warden floor, played (jsdom) -------------------------------------------------------------

def _pack(tmp_path):
    descent = _descent(stamped=False)
    patch = {"world.json": {"descent": descent,
                            "items": {"cellar-gem": {"name": "a cellar gem", "sprite": "gem", "value": 10}}}}
    pack = Path(play_kit.pack(tmp_path / "pack", "descent", patch=patch))
    shutil.copytree(STAMPS, pack / "stamps")
    lib = pack / "library"
    lib.mkdir(exist_ok=True)
    (lib / "the-note.md").write_text("---\ntitle: A note in the vault\nfound: map\nregion: cellar-0-3\n"
                                     "place: vault-note\n---\nThe vault was never empty.\n")
    (lib / "a-chest.md").write_text("---\ntitle: The vault chest\nfound: map\nregion: cellar-0-3\nplace: vault-chest\n"
                                    "chest: yes\ndrops: cellar-gem\n---\nA list of what was kept.\n")
    return descent, pack


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_beat_the_warden_read_the_note_open_the_chest_and_climb_home(tmp_path):
    descent, pack = _pack(tmp_path)
    html = play_kit.weave(pack, tmp_path)
    woven = {**descent, "stamps": RECORDS}
    plan = delve.floor_plan(woven, 3)
    vault = plan["vault"]
    (warden,) = [m for m in plan["mobs"] if m.get("warden")]
    down = ["begin", _go(TOWN, TOWN_HERO, descent["entry"]["at"]), "click:#interact", "wait:150"]
    for d in (1, 2):
        p = delve.floor_plan(woven, d)
        down += [_go(p, p["anchors"]["up"], p["anchors"]["down"]), "click:#interact", "wait:150"]

    fought = play_kit.play(html, {"steps": down + [_go_fight(plan, warden)] + ["wait:100"] * 6, "read": ["store"]})
    assert fought["errors"] == [], fought["errors"]

    # From that save: walk to the note (stepping on it finds it), then beside the chest, open it, then home.
    chest, home = vault["chest"], vault["home"]
    beside = next(t for t in ([chest[0] + 1, chest[1]], [chest[0] - 1, chest[1]],
                              [chest[0], chest[1] + 1], [chest[0], chest[1] - 1])
                  if plan["rows"][t[1]][t[0]] != "#" and abs(t[0] - home[0]) + abs(t[1] - home[1]) > 1
                  and t != vault["note"])
    to_note = _path(plan, plan["anchors"]["up"], vault["note"], [chest])   # in over the home stair: only Interact takes it
    to_chest = _path(plan, vault["note"], beside, [chest])
    to_home = _path(plan, beside, home, [chest])
    steps = down + ["walk:" + ",".join(to_note), "wait:300", "walk:" + ",".join(to_chest),
                    "click:#interact", "wait:300", "walk:" + ",".join(to_home), "click:#interact", "wait:200"]
    done = play_kit.play(html, {"steps": steps, "store": fought["store"],
                                "read": ["store", "VEFR_COMBAT.region"]})
    assert done["errors"] == [], done["errors"]
    found = json.loads(done["store"].get("vefr-library-descent-test") or "[]")
    assert "the-note" in found and "a-chest" in found, found
    assert "cellar-gem" in json.loads(done["store"].get("vefr-bag-descent-test") or "[]")
    assert done["reads"]["VEFR_COMBAT.region"] == descent["entry"]["region"], "the stair home did not lead home"
