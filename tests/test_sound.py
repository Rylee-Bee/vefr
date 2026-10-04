"""Sound, slice 1 (Cottage release 1, plan S1). FROZEN CONTRACT.
Played through the shared tests/play_kit.py.

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

import shutil
import sys
from pathlib import Path

import pytest

from vefr import maplab

import play_kit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_lock_pack as mk  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
STORE_KEY = f"vefr-sound-{mk.NAME}"

SOUND = "VEFR_SOUND"
TOGGLE = "exists:#sound-toggle"
TOGGLE_CHECKED = "exists:#sound-toggle:checked"
TO_DOOR = "walk:down,down,right,right,up,right,right,right,right,down,down,right,right"


def build(tmp_path, sound=None, requires=None, extra=None):
    world = dict(extra or {})
    if sound is not None:
        world["sound"] = sound
    patch = {"world.json": world} if world else None
    return play_kit.pack(tmp_path, "lock", patch, requires=requires)


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

def run(tmp_path, spec=None, **kw):
    html = play_kit.weave(build(tmp_path, **kw), tmp_path)
    return play_kit.play(html, spec or {})


def test_the_snapshot_and_toggle_exist_when_opted_in(tmp_path):
    out = run(tmp_path, {"steps": ["begin"], "read": [SOUND, TOGGLE, TOGGLE_CHECKED]},
              sound={"theme": "soft"})
    assert out["errors"] == []
    assert out["reads"][SOUND] == {"theme": "soft", "on": True, "played": []}
    assert out["reads"][TOGGLE] is True and out["reads"][TOGGLE_CHECKED] is True


def test_a_door_makes_its_cue(tmp_path):
    out = run(tmp_path, {"steps": ["begin", TO_DOOR, "key:e", "wait:200"], "read": [SOUND]},
              sound={"theme": "soft"})
    assert out["errors"] == []
    assert out["reads"][SOUND]["played"] == ["door"]


def test_a_locked_door_makes_the_locked_cue(tmp_path):
    out = run(tmp_path, {"steps": ["begin", TO_DOOR, "key:e", "wait:200"], "read": [SOUND]},
              sound={"theme": "soft"}, requires=mk.RING)
    assert out["reads"][SOUND]["played"] == ["locked"]


def test_a_sticker_and_the_end_have_cues(tmp_path):
    extra = {"flags": {}, "claims": {}, "people": {},
             "rules": [{"id": "the-end", "when": {"starts": {}}, "once": True,
                        "then": [{"complete-act": "act-1"}]}],
             "album": [{"id": "begin", "name": "Begin", "kind": "open", "when": {"starts": {}}}]}
    out = run(tmp_path, {"steps": ["begin"], "read": [SOUND]}, sound={"theme": "soft"}, extra=extra)
    assert sorted(out["reads"][SOUND]["played"]) == ["end", "sticker"]


def test_off_is_remembered_and_silences_everything(tmp_path):
    out = run(tmp_path, {"steps": ["begin", TO_DOOR, "key:e", "wait:200"],
                         "read": [SOUND, TOGGLE, TOGGLE_CHECKED], "store": {STORE_KEY: "off"}},
              sound={"theme": "soft"})
    assert out["reads"][SOUND] == {"theme": "soft", "on": False, "played": []}
    assert out["reads"][TOGGLE] is True and out["reads"][TOGGLE_CHECKED] is False


def test_a_pack_without_sound_has_none(tmp_path):
    out = run(tmp_path, {"steps": ["begin", TO_DOOR, "key:e", "wait:200"], "read": [SOUND, TOGGLE]})
    assert out["reads"][SOUND] is None
    assert out["reads"][TOGGLE] is False
    assert out["errors"] == []
