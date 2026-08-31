"""Lore packs - the wandering-poets shape + journey/rune map.

The engine has two pieces of *structural identity* that aren't
flavor toggles:

  1. The Hero's Journey - four phases the engine runs through
     (call / threshold / tests / return), anchored to four Elder
     Futhark runes. Packs can rename their phase keys but the
     engine maps them by position.

  2. The lore packs - data, not code. worlds/lore/<name>/ is a
     directory with textures.md, names.md, questions.md, prompt.md,
     LICENSE.md. The engine reads the first three; the author copies
     the fourth. lore is mood, not canon.
"""

import json
from pathlib import Path

import pytest

from vefr import journey, lore, world
from vefr.journey import (
    DEFAULT_PHASES,
    PHASE_JOURNEY_RUNE,
    all_phases_with_journey,
    journey_for,
    journey_prose_for,
)


# ---- journey.py ----

def test_default_phases_are_four():
    assert len(DEFAULT_PHASES) == 4


def test_every_default_phase_has_a_rune():
    for phase in DEFAULT_PHASES:
        entry = journey_for(phase)
        assert entry["rune"], f"{phase} has no rune"
        assert entry["stage"], f"{phase} has no stage"
        assert entry["rune_meaning"], f"{phase} has no rune meaning"


def test_journey_for_unknown_phase_returns_generic():
    """Packs may add phases beyond the engine's four. The engine
    doesn't crash; it returns a generic record."""
    entry = journey_for("a custom seventh phase")
    assert entry["rune"] == "?"
    assert "outside the engine's bones" in entry["rune_meaning"]


def test_journey_prose_for_known_phase_is_substantial():
    """Every phase's prose should be a paragraph, not a sentence."""
    for phase in DEFAULT_PHASES:
        prose = journey_prose_for(phase)
        assert len(prose) > 80, f"{phase} prose too short: {prose!r}"


def test_all_phases_with_journey_preserves_canonical_order():
    phases = [p for p, _ in all_phases_with_journey()]
    assert phases == list(DEFAULT_PHASES)


# ---- lore packs: file shape ----

def test_lore_root_lists_all_shipped_packs():
    packs = [e.name for e in lore.list_lore()]
    assert "norse" in packs
    assert "historical-event" in packs
    assert "norse-runes" in packs


def test_every_shipped_pack_has_all_five_files():
    """A pack without LICENSE.md is a bug - we don't ship anything
    that doesn't declare its terms."""
    for entry in lore.list_lore():
        assert entry.has_textures, f"{entry.name} missing textures.md"
        assert entry.has_names, f"{entry.name} missing names.md"
        assert entry.has_questions, f"{entry.name} missing questions.md"
        assert entry.has_prompt, f"{entry.name} missing prompt.md"
        assert entry.has_license, f"{entry.name} missing LICENSE.md"


def test_every_shipped_pack_license_is_cc_by_sa():
    """The license terms are the same family - CC BY-SA 4.0 - even
    though each pack has its own attributions."""
    from vefr.paths import app_home
    for entry in lore.list_lore():
        lic_path = app_home() / "worlds" / "lore" / entry.name / "LICENSE.md"
        text = lic_path.read_text(encoding="utf-8")
        # All three ship with CC BY-SA 4.0 (Creative Commons
        # Attribution-ShareAlike 4.0 International). Different
        # phrasings; both 'BY-SA' and 'Attribution-ShareAlike' are
        # canonical.
        assert "BY-SA" in text or "Attribution-ShareAlike" in text, (
            f"{entry.name}: license does not declare CC BY-SA 4.0"
        )


# ---- lore preview route (smoke; the live test needs the model) ----

def test_preview_request_validates_lore_name():
    """An unknown lore name should surface as 404 from the route."""
    from fastapi.testclient import TestClient
    from vefr.main import app
    c = TestClient(app)
    r = c.post("/api/builder/lore", json={"lore": "no-such-pack", "seeds": []})
    # either 404 (missing pack files) or 502 (model call fails in
    # offline test); both are acceptable - the contract is "fail
    # cleanly, never 500 with a stack trace"
    assert r.status_code in (404, 502)


def test_preview_response_shape():
    """The wandering-poets shape: textures + names + questions."""
    # No model call - validate the schema in isolation.
    from vefr.lore import LorePreviewResponse
    payload = {
        "lore": "norse",
        "textures": "a short prose passage",
        "names": ["Bragi", "Lofn"],
        "questions": ["where does the road come from?"],
    }
    resp = LorePreviewResponse(**payload)
    assert resp.lore == "norse"
    assert isinstance(resp.textures, str)
    assert isinstance(resp.names, list)
    assert len(resp.names) >= 1
    assert isinstance(resp.questions, list)


# ---- world.py: journey attachment ----

def test_load_world_attaches_journey_to_each_phase_by_position(monkeypatch):
    """The engine maps pack phases to journey stages by position.

    A pack that renames its phases ('the ordinary day' instead of
    'whispers') still gets the engine's bones attached by order.
    """
    # Use the sample-world pack (which has 2 phases; we only need 4+
    # to test the mapping). Emberfield's `phases` dict has only two
    # keys, so we test on private-canon which has four.
    w = world.load_world("private-canon")
    assert "_journey" in w
    assert len(w["_journey"]) == 4
    # First phase in private-canon is whispers; engine should anchor
    # it to the first journey stage (Fehu, the call).
    assert w["_journey"][0]["pack_phase"] == "whispers"
    assert w["_journey"][0]["rune"] == "Fehu"
    # Last phase is awed; engine anchors it to Sowilo.
    assert w["_journey"][3]["pack_phase"] == "awed"
    assert w["_journey"][3]["rune"] == "Sowilo"


def test_pack_phase_to_journey_lookup():
    """The helper resolves a pack's phase key to its journey entry."""
    w = world.load_world("private-canon")
    entry = world.pack_phase_to_journey("awed")
    assert entry is not None
    assert entry["rune"] == "Sowilo"
    # An unknown phase returns None.
    assert world.pack_phase_to_journey("a phase private-canon doesn't have") is None


# ---- saga.py: the rune line in system prompts ----

def test_system_prompt_includes_rune_line():
    """Every whisper's system prompt carries the rune anchor for
    its current phase - the engine's bones threading through
    every generation."""
    from vefr.saga import system_prompt
    for phase in DEFAULT_PHASES:
        prompt = system_prompt(phase)
        expected_rune = PHASE_JOURNEY_RUNE[phase]["rune"]
        assert expected_rune in prompt, f"{phase} prompt missing rune {expected_rune}"
        assert "JOURNEY STAGE" in prompt