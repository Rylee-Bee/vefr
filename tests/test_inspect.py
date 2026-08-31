"""The visible engine: weave log, resolved-world view, handoff bundle.

These three endpoints are the engine's mirrors - they show the
author what the loader did, what the engine sees, and package
the whole context for an AI-buddy debugging handoff. They are
the antidote to 'magic happened' when authoring a pack.
"""

import json
from pathlib import Path

import pytest


def test_weave_log_round_trips(tmp_path, monkeypatch):
    """A weave event written by the engine is readable from the
    ring AND from the on-disk JSONL file."""
    from vefr import weave as weave_mod

    log_path = tmp_path / "weave.jsonl"
    weave_mod.reset_path_for_testing(log_path)
    try:
        weave_mod.weave("test.event", foo="bar", n=42)
        from_disk = weave_mod.from_disk(limit=10)
        from_ring = weave_mod.recent(limit=10)
        assert any(e.get("event") == "test.event" for e in from_disk)
        assert any(e.get("foo") == "bar" and e.get("n") == 42
                   for e in from_ring)
    finally:
        weave_mod.reset_path_for_testing(None)


def test_resolved_world_returns_acts_shape(sample_pack, monkeypatch):
    """The resolved-world view reflects the always-array shape,
    with the current act's regions and speakers surfaced clearly.
    Forces the sample-world (acts-shape) so the test isn't
    sensitive to which pack happens to be alphabetically first."""
    from vefr import inspect, world as world_mod
    monkeypatch.setenv("VEFR_WORLD", "sample-world")
    world_mod.load_world.cache_clear()
    try:
        resolved = inspect.resolved_world()
        assert "acts" in resolved
        assert resolved["_current_act"] == 0
        assert resolved["acts"][0]["id"] == "act-1"
        assert "town" in resolved["acts"][0]["regions"]
        # Surface, name, title are surfaced for the author.
        assert "surface" in resolved
        assert "name" in resolved
        assert "title" in resolved
    finally:
        world_mod.load_world.cache_clear()


def test_handoff_writes_a_readable_bundle(tmp_path, monkeypatch):
    """The handoff bundle is a markdown file the author can fill
    in and paste anywhere. Auto-filled sections are present;
    open sections are marked."""
    from vefr import inspect, weave as weave_mod
    from vefr.paths import app_home

    # Re-point the weave log to a tmp file so we can assert on it.
    log_path = tmp_path / "weave.jsonl"
    weave_mod.reset_path_for_testing(log_path)
    weave_mod.weave("handoff.test", sample="line")

    out_dir = tmp_path / "handoffs"
    path = inspect.build_handoff(out_dir)
    try:
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        # Three sections the author fills in.
        assert "What I was trying to do" in text
        assert "What I saw instead" in text
        assert "What I've already tried" in text
        # Auto-filled context: the resolved world JSON, the
        # recent weave events, and the four-step task.
        assert "resolved world" in text.lower()
        assert "```json" in text
        assert "handoff.test" in text  # our event is in the bundle
        assert "The task" in text
    finally:
        weave_mod.reset_path_for_testing(None)


@pytest.fixture
def sample_pack():
    """The canary acts-shape pack (sample-world)."""
    return Path(__file__).resolve().parents[1] / "worlds" / "sample-world"
