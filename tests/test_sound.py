"""Sound, slice 1 (Cottage release 1, plan S1). FROZEN CONTRACT.

A small synthesized sound set, no audio files. A pack opts in with `"sound": {"theme": "soft"}` in world.json.
  - validator: `sound` must be an object with exactly one key `theme`, whose value is "soft" (the only theme in this
    slice). Anything else is one plain sentence naming `sound`. A pack without `sound` is unchanged.
  - player: cues are named moments: "hit", "hurt", "defeat", "pickup", "door", "locked", "level", "sticker", "end".
    window.VEFR_SOUND = {theme, on, played: [cue names in order]} is the harness snapshot and exists ONLY when the
    pack opts in. `played` records a cue whenever it would sound and sound is on, even where no audio device exists
    (jsdom has none; the player must never throw without AudioContext).
  - Menu > Display holds a checkbox #sound-toggle labelled "Sound", present only when the pack opts in, checked
    when on. Turning it off is remembered in this browser (localStorage 'vefr-sound-<world>' = "off"); then no
    cue is recorded or played. On by default.
  - the sound is a convenience, never the only signal: every cue already has its text in the live line.
  - A pack without `sound` has no VEFR_SOUND and no toggle.
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

HARNESS = ROOT / "tests" / "fixtures" / "sound_harness.mjs"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
STORE_KEY = f"vefr-sound-{mk.NAME}"


def build(tmp_path, sound=None, requires=None, extra=None):
    pack = mk.build(tmp_path, requires=requires)
    p = pack / "world.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    if sound is not None:
        cfg["sound"] = sound
    cfg.update(extra or {})
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return pack


def extra_errors(tmp_path, sound):
    bpack = build(tmp_path / "b")
    base = maplab.validate(maplab.load_pack(bpack), pack_dir=bpack)
    pack = build(tmp_path / "x", sound)
    return [e for e in maplab.validate(maplab.load_pack(pack), pack_dir=pack) if e not in base]


# --- validator -------------------------------------------------------------------------------

def test_a_soft_theme_validates(tmp_path):
    assert extra_errors(tmp_path, {"theme": "soft"}) == []


def test_a_pack_without_sound_is_unchanged(tmp_path):
    assert extra_errors(tmp_path, None) == []


@pytest.mark.parametrize("bad", [{"theme": "loud"}, {"theme": "soft", "volume": 3}, {}, "soft", 3, ["soft"]])
def test_a_bad_sound_block_is_named(tmp_path, bad):
    errs = extra_errors(tmp_path, bad)
    assert any("sound" in e for e in errs), errs


# --- player ------------------------------------------------------------------------------------

def play(tmp_path, spec=None, **kw):
    pack = build(tmp_path, **kw)
    html = tmp_path / "sound.html"
    html.write_text(cli.weave_html(pack), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(html), json.dumps(spec or {})],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_the_snapshot_and_toggle_exist_when_opted_in(tmp_path):
    r = play(tmp_path, sound={"theme": "soft"})
    assert r["errors"] == []
    assert r["sound"] == {"theme": "soft", "on": True, "played": []}
    assert r["toggle"] == {"present": True, "checked": True}


def test_a_door_makes_its_cue(tmp_path):
    r = play(tmp_path, {"door": True}, sound={"theme": "soft"})
    assert r["errors"] == []
    assert r["sound"]["played"] == ["door"]


def test_a_locked_door_makes_the_locked_cue(tmp_path):
    r = play(tmp_path, {"door": True}, sound={"theme": "soft"}, requires=mk.RING)
    assert r["sound"]["played"] == ["locked"]


def test_a_sticker_and_the_end_have_cues(tmp_path):
    extra = {"flags": {}, "claims": {}, "people": {},
             "rules": [{"id": "the-end", "when": {"starts": {}}, "once": True,
                        "then": [{"complete-act": "act-1"}]}],
             "album": [{"id": "begin", "name": "Begin", "kind": "open", "when": {"starts": {}}}]}
    r = play(tmp_path, sound={"theme": "soft"}, extra=extra)
    assert sorted(r["sound"]["played"]) == ["end", "sticker"]


def test_off_is_remembered_and_silences_everything(tmp_path):
    r = play(tmp_path, {"door": True, "store": {STORE_KEY: "off"}}, sound={"theme": "soft"})
    assert r["sound"] == {"theme": "soft", "on": False, "played": []}
    assert r["toggle"] == {"present": True, "checked": False}


def test_a_pack_without_sound_has_none(tmp_path):
    r = play(tmp_path, {"door": True})
    assert r["sound"] is None
    assert r["toggle"]["present"] is False
    assert r["errors"] == []
