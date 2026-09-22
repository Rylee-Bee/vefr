"""Phase 0 boundary pins - the engine speaks in references, packs speak in fiction.

These tests are the CI-enforced half of the neutrality guard: the
canon-string list is local-only by design (it never ships), so the
patterns below pin the *shape* of the boundary in public code:

  - no pack phase names in engine behavior (CSS, lines dicts, sightings)
  - no private-game taglines in engine surfaces
  - starred letters route to their own heading, never a phase
  - the act's verbs are the action vocabulary when declared
  - pack law (floor/tone/ruleset) validates loudly and defaults quietly
  - the storyteller prompt carries the act's tone dial position
"""

import copy
from pathlib import Path

import pytest

from vefr import combat, maplab, saga, starred
from vefr.world import load_world

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


# --- the web shells carry no pack phase names in behavior ---------

def test_town_js_has_no_phase_keyed_behavior():
    src = (WEB / "town.js").read_text(encoding="utf-8")
    assert "checkSighting" not in src
    assert "sighted" not in src
    assert "phase() !== '" not in src


def test_live_shell_has_no_name_keyed_phase_css_or_lines():
    src = (WEB / "index.html").read_text(encoding="utf-8")
    for needle in (
        'data-phase="awed"',
        'data-bond="attuned"',
        'data-bond="assigned"',
        "'awed':",
        "hellos that never happened",
        "memory &amp; longing",
    ):
        assert needle not in src, f"index.html must not carry {needle!r}"
    # The accent is positional now: the pack's culminating phase.
    assert 'data-culm="true"' in src


def test_packaged_shell_renders_verbs_from_the_act():
    src = (WEB / "packaged.html").read_text(encoding="utf-8")
    assert '<button type="button" data-verb="attack">' not in src
    assert "VEFR_WORLD.acts" in src
    assert "['attack', 'Strike']" in src


# --- starred letters are their own beat, not a phase ---------------

def test_starred_fallbacks_are_phase_agnostic():
    assert set(starred.FALLBACK_PHASE.values()) == {"kept-items", "letters"}


# --- the act's verbs are the action vocabulary ---------------------

def test_combat_verbs_come_from_the_act():
    world = {
        "acts": [{"verbs": ["plate", "flip", "serve"]}],
        "_current_act": 0,
    }
    verbs = combat.verbs_for_pack(world)
    assert verbs == ("plate", "flip", "serve")
    entry = combat.record_combat_action(
        kind="plate", phase="dusk", allowed=verbs
    )
    assert entry["verb"] == "plate"
    with pytest.raises(ValueError):
        combat.record_combat_action(kind="attack", phase="dusk", allowed=verbs)


def test_combat_verbs_default_keeps_the_old_costume():
    world = {"acts": [{"verbs": []}], "_current_act": 0}
    assert combat.verbs_for_pack(world) == combat.DEFAULT_VERBS
    entry = combat.record_combat_action(kind="attack", phase="dusk")
    assert entry["verb"] == "attack"


# --- pack law validates loudly, defaults quietly -------------------

def test_pack_law_defaults_load_on_the_canary():
    w = load_world("sample-world")
    act = w["acts"][0]
    assert act["floor"] == "costume"
    assert act["tone"] == ""
    assert act["ruleset"] == "ambient"
    assert act["verbs"] == []


def test_pack_law_bad_values_fail_validation():
    w = copy.deepcopy(load_world("sample-world"))
    act = w["acts"][0]
    act["floor"] = "salty"
    act["tone"] = "noir"
    act["ruleset"] = ""
    act["verbs"] = "plate"
    errors = " ".join(maplab.validate(w))
    assert "floor" in errors
    assert "tone" in errors
    assert "ruleset" in errors
    assert "verbs" in errors


def test_pack_law_good_values_pass_validation():
    w = copy.deepcopy(load_world("sample-world"))
    act = w["acts"][0]
    act["floor"] = "stakes"
    act["tone"] = "absurd"
    act["ruleset"] = "cooking"
    act["verbs"] = ["plate", "flip"]
    act["transitions"] = ["the road east"]
    errors = " ".join(maplab.validate(w))
    for word in ("floor", "tone", "ruleset", "verbs", "transitions"):
        assert word not in errors, errors


# --- the storyteller carries the act's tone dial -------------------

def test_saga_prompt_carries_the_tone_dial(monkeypatch):
    monkeypatch.setattr(
        "vefr.world.current_act", lambda *a, **k: {"tone": "ridiculous"}
    )
    prompt = saga.system_prompt("dusk")
    assert "ACT TONE: ridiculous" in prompt


def test_saga_prompt_is_silent_without_a_tone(monkeypatch):
    monkeypatch.setattr(
        "vefr.world.current_act", lambda *a, **k: {}
    )
    prompt = saga.system_prompt("dusk")
    assert "ACT TONE" not in prompt
