"""The album, slice 1 (design/album.md; Cottage release 1, plan A1). FROZEN CONTRACT.

A pack may declare `"album": [ {id, name, kind, when, riddle?, shine?} ]` in world.json.
  - id: unique, plain; name: 1-60 chars; kind: "open" | "riddle" | "secret";
    riddle: required (a plain sentence) for kind "riddle", refused otherwise;
    shine: optional "paper" | "foil" | "holo"; default paper.
  - when: ONE rules event, same vocabulary as rules: {"defeats": {"what": "<enemy id>"}}, {"starts": {}},
    {"picks-up": {"what": "<item>"}}, ... Everything it names must be declared (the rules identity model).
    An unknown event key, an unknown thing, or more than one key is one plain sentence naming the sticker id.
  - Rewards only add: nothing is ever taken away.
Player:
  - A sticker is earned the first time its event fires. window.VEFR_ALBUM = {found: [ids], total: N}.
  - The live line #combat-live says "You found a sticker: <name>" once, when earned.
  - Menu > Album (button [data-panel="album"]) exists only when the pack declares an album. Its panel
    #album-panel says "N of M found" in plain text. A found sticker shows its name. An unfound "open" sticker
    shows its name as not yet found; an unfound "riddle" shows only its riddle (never its name); an unfound
    "secret" appears only in a count ("1 secret").
  - It persists in this browser (store passed back in) and a reload does not announce it again.
  - A pack with no album has no Album button and no VEFR_ALBUM.
Neutral fixtures only.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli, maplab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_lock_pack as mk  # noqa: E402

HARNESS = ROOT / "tests" / "fixtures" / "album_harness.mjs"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

ALBUM = [
    {"id": "first-steps", "name": "First steps", "kind": "open", "when": {"starts": {}}},
    {"id": "the-ring", "name": "A plain ring", "kind": "riddle",
     "riddle": "Something small and round waits in a ledger.", "when": {"picks-up": {"what": "brass-ring"}}},
    {"id": "rat-friend", "name": "Rat friend", "kind": "secret", "shine": "holo",
     "when": {"defeats": {"what": "storeroom-rat"}}},
]


def build(tmp_path, album=ALBUM):
    pack = mk.build(tmp_path)
    p = pack / "world.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    if album is not None:
        cfg["album"] = album
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return pack


def extra_errors(tmp_path, album):
    base = build(tmp_path / "b", None)
    base_errs = maplab.validate(maplab.load_pack(base), pack_dir=base)
    pack = build(tmp_path / "x", album)
    return [e for e in maplab.validate(maplab.load_pack(pack), pack_dir=pack) if e not in base_errs]


def sticker(**over):
    s = {"id": "s1", "name": "A sticker", "kind": "open", "when": {"starts": {}}}
    s.update(over)
    return s


# --- validator -------------------------------------------------------------------------------

def test_a_good_album_validates(tmp_path):
    assert extra_errors(tmp_path, ALBUM) == []


def test_a_pack_without_an_album_is_unchanged(tmp_path):
    assert extra_errors(tmp_path, None) == []


@pytest.mark.parametrize("bad,needle", [
    ([sticker(), sticker(name="Another")], "s1"),                       # duplicate id
    ([sticker(kind="legendary")], "s1"),                                 # unknown kind
    ([sticker(kind="riddle")], "s1"),                                    # riddle without riddle
    ([sticker(riddle="Why?")], "s1"),                                    # riddle on a non-riddle
    ([sticker(shine="neon")], "s1"),                                     # unknown shine
    ([sticker(when={"flies": {}})], "s1"),                               # unknown event
    ([sticker(when={"defeats": {"what": "no-such-enemy"}})], "no-such-enemy"),
    ([sticker(when={"starts": {}, "enters": {"place": "cellar"}})], "s1"),  # two keys
    ([sticker(name="")], "s1"),
])
def test_bad_stickers_are_named(tmp_path, bad, needle):
    errs = extra_errors(tmp_path, bad)
    assert any(needle in e for e in errs), errs


# --- player ------------------------------------------------------------------------------------

def play(tmp_path, spec=None, album=ALBUM):
    pack = build(tmp_path, album)
    html = tmp_path / "album.html"
    html.write_text(cli.weave_html(pack), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(html), json.dumps(spec or {})],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_the_first_event_earns_its_sticker_once(tmp_path):
    r = play(tmp_path)
    assert r["errors"] == []
    assert r["album"] == {"found": ["first-steps"], "total": 3}
    assert "You found a sticker: First steps" in r["live"]


def test_the_panel_speaks_plainly_and_hides_what_it_should(tmp_path):
    r = play(tmp_path)
    assert r["button"]["present"] and r["button"]["visible"]
    p = r["panel"]
    assert "1 of 3 found" in p
    assert "First steps" in p
    assert "Something small and round waits in a ledger." in p
    assert "A plain ring" not in p and "Rat friend" not in p
    assert "1 secret" in p


def test_it_persists_and_a_reload_does_not_announce_again(tmp_path):
    first = play(tmp_path / "one")
    second = play(tmp_path / "two", {"store": first["store"]})
    assert second["album"]["found"] == ["first-steps"]
    assert "You found a sticker" not in second["live"]


def test_a_pack_without_an_album_has_no_album(tmp_path):
    r = play(tmp_path, album=None)
    assert r["album"] is None
    assert not (r["button"]["present"] and r["button"]["visible"])
    assert r["errors"] == []
