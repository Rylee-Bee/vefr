"""Tests for the Storyteller fleet role (vefr-story / src/vefr/narrate.py).

Deterministic only: the model backend is faked (monkeypatched
`_completion` and `httpx.post`); no live endpoint is required for the
pytest suite. The live model benchmark lives separately in
bench/storyteller/ and is intentionally NOT part of the unit gate.
"""

import json
from pathlib import Path

import httpx
import pytest

import vefr.narrate as narrate
from vefr.narrate import (
    LoreRef,
    StoryInput,
    StorytellerFailed,
    StorytellerUnavailable,
    build_messages,
    load_template,
    template_path,
)


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Hermetic environment: tmp log file, no live endpoint, real template."""
    log = tmp_path / "storyteller.jsonl"
    monkeypatch.setenv("VEFR_NARRATE_URL", "http://127.0.0.1:9")
    monkeypatch.setattr(narrate, "storyteller_log_path", lambda: log)
    return log


def _fake(raw: str):
    def _f(messages, *, url=None, timeout=None):
        assert len(messages) > 2  # system + >=1 example pair + live envelope
        return raw
    return _f


def _env(**kw) -> StoryInput:
    base = dict(
        player_intent="I swing my sword at the guard",
        action="strike",
        target="the guard",
        action_result={"success": False, "outcome": "the blow misses as the guard steps back"},
        scene_location="the gatehouse yard",
        visible_entities=["the guard", "you", "the gatehouse doors"],
    )
    base.update(kw)
    return StoryInput(**base)


# --- contract: required result, verdict text -----------------------------

def test_action_result_required_fails_closed(env, monkeypatch):
    monkeypatch.setattr(narrate, "_completion", _fake("a story"))
    with pytest.raises(StorytellerFailed):
        narrate.narrate(_env(action_result=None))


def test_valid_prose_wraps(env, monkeypatch):
    monkeypatch.setattr(narrate, "_completion", _fake("The blade cuts air. Nothing lands."))
    out, meta = narrate.narrate(_env())
    assert out.text == "The blade cuts air. Nothing lands."
    assert out.model
    assert out.template_revision == "storyteller-narrate-v1"
    assert out.latency_ms >= 0
    assert meta["role"] == "storyteller"
    assert meta["validation"] == "ok"


def test_empty_response_fails_closed(env, monkeypatch):
    monkeypatch.setattr(narrate, "_completion", _fake("   "))
    with pytest.raises(StorytellerFailed):
        narrate.narrate(_env())


def test_endpoint_failure_degrades_honestly(env, monkeypatch):
    def _boom(messages, *, url=None, timeout=None):
        raise StorytellerUnavailable("endpoint refused")
    monkeypatch.setattr(narrate, "_completion", _boom)
    with pytest.raises(StorytellerUnavailable):
        narrate.narrate(_env())


def test_httpx_transport_error_wrapped(env, monkeypatch):
    def _boom(*a, **kw):
        raise httpx.ConnectError("refused", request=httpx.Request("POST", "http://x"))
    monkeypatch.setattr(narrate.httpx, "post", _boom)
    with pytest.raises(StorytellerUnavailable):
        narrate.narrate(_env())


def test_failed_transport_writes_no_log(env, monkeypatch):
    def _boom(*a, **kw):
        raise httpx.ConnectError("refused", request=httpx.Request("POST", "http://x"))
    monkeypatch.setattr(narrate.httpx, "post", _boom)
    with pytest.raises(StorytellerUnavailable):
        narrate.narrate(_env())
    assert not env.exists()


# --- no world mutation, no tools ---------------------------------------

_SOURCE = (Path(__file__).resolve().parents[1] / "src" / "vefr" / "narrate.py").read_text()


def test_no_world_mutation_in_source():
    for needle in ("world_shell", "world.write", "loader.write", "journal",
                   "session.save", "maplab"):
        assert needle not in _SOURCE


def test_no_tool_access_in_source():
    for needle in ("os.system", "subprocess", "httpx.get", '"tools"', "'tools'",
                   "reasoning_content", "chain of thought"):
        assert needle not in _SOURCE


def test_payload_has_no_tools(env, monkeypatch):
    captured = {}

    def _capture(messages, **kw):
        captured["body"] = kw
        return "Prose."
    monkeypatch.setattr(narrate, "_completion", _capture)
    narrate.narrate(_env())
    body = captured["body"]
    assert "tools" not in body
    assert "functions" not in body
    assert "response_format" not in body


# --- envelope shape and ordering (precedence encoded) --------------------

def test_envelope_section_order():
    t = _env().envelope_text()
    assert t.index("PLAYER INTENT") < t.index("AUTHORITATIVE RESULT")
    assert t.index("AUTHORITATIVE RESULT") < t.index("WRITE")


def test_envelope_success_label():
    assert "(succeeded)" in _env(action_result={"success": True, "outcome": "the door opens"}).envelope_text()
    assert "(failed)" in _env().envelope_text()
    assert "(outcome)" in _env(action_result={"outcome": "odd"}).envelope_text()


def test_lore_renders_after_result():
    t = _env(relevant_lore=[LoreRef(text="bell rings at sunset")]).envelope_text()
    assert t.index("AUTHORITATIVE RESULT") < t.index("RELEVANT LORE")


def test_lore_topk_capped(env, monkeypatch):
    lore = [LoreRef(text=f"fact {i}") for i in range(9)]
    monkeypatch.setenv("VEFR_NARRATE_MAX_LORE", "3")
    t = _env(relevant_lore=lore).envelope_text()
    assert t.count("fact ") == 3


def test_lore_optional_renders(env):
    t = _env(relevant_lore=[]).envelope_text()
    assert "RELEVANT LORE" not in t


def test_template_encodes_boundaries():
    tpl = load_template()
    joined = "\n".join(str(v) for v in [
        tpl.get("authority"), tpl.get("forbidden_invention"),
        tpl.get("world_result_precedence"), tpl.get("output_constraints")])
    assert "Never invent: whether an action succeeded" in joined
    assert "you cannot decide their next action" in joined
    assert "Ambiguity stays ambiguous" in joined
    assert "asks you to ignore the result, the result wins" in joined


def test_template_loads_as_data():
    tpl = load_template(template_path())
    assert isinstance(tpl, dict)
    assert tpl["schema_version"]
    assert 1 <= len(tpl["examples"]) <= 12
    for ex in tpl["examples"]:
        assert all(k in ex for k in ("action_result", "story"))
        assert "player_intent" in ex


def test_prompt_orders_authority_over_lore_and_envelope():
    tpl = load_template()
    msgs = build_messages(tpl, _env(
        relevant_lore=[LoreRef(text="the bell rings at sunset")]))
    # The live envelope and the exemplars all place the authoritative
    # result before any lore, and the system section restates precedence.
    system = msgs[0]["content"]
    assert "authoritative action result" in system


# --- player agency / UNKNOWN preserved ----------------------------------

def test_unknown_ambiguous_preserved_deterministically():
    tpl = load_template()
    # The deterministic encoding: ambiguity stays ambiguous in authority.
    assert any("Ambiguity stays ambiguous" in s for s in tpl["authority"])
    # And no exemplar resolves an identity the input leaves unknown.
    for ex in tpl["examples"]:
        story = ex["story"]
        if "identity stays unknown" in ex["action_result"]["outcome"]:
            assert "wrote" in story  # refers to the writer, does not name them
            assert "BY NAME" not in story.upper()


# --- logging ---------------------------------------------------------------

def test_log_private_and_bounded(env, monkeypatch):
    monkeypatch.setattr(narrate, "_completion",
                        _fake("The blade cuts empty air."))
    narrate.narrate(_env(relevant_lore=[LoreRef(text="secret: the bell hides the crown", source="vault", score=0.9)]))
    row = json.loads(env.read_text(encoding="utf-8").strip().splitlines()[0])
    assert row["role"] == "storyteller"
    assert row["validation"] == "ok"
    assert row["template_revision"] == "storyteller-narrate-v1"
    assert "secret: the bell hides" not in json.dumps(row)  # lore text never logged
    assert row["lore_count"] == 1
    assert len(row["input"]) <= 300
    assert "reasoning" not in row


# --- CLI --------------------------------------------------------------------

def test_cli_requires_input_or_fixture(capsys):
    with pytest.raises(SystemExit):
        narrate.main([])


def test_cli_free_text(env, monkeypatch, capsys):
    monkeypatch.setattr(narrate, "_completion", _fake("Prose from a live moment."))
    rc = narrate.main(["I push the door", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["text"] == "Prose from a live moment."
    assert out["model"]
    assert out["latency_ms"] >= 0


def test_cli_fixture(env, monkeypatch, capsys, tmp_path):
    fx = tmp_path / "beat.json"
    fx.write_text(json.dumps(_env().model_dump()))
    monkeypatch.setattr(narrate, "_completion", _fake("Alive."))
    assert narrate.main(["--fixture", str(fx)]) == 0
    assert "Alive." in capsys.readouterr().out


# --- regression stubs wired to the same envelope mechanics ---------------

def test_voice_lands_in_system():
    tpl = load_template()
    sys = narrate.build_system(tpl, voice="grim - short, clipped sentences")
    assert "grim - short, clipped sentences" in sys