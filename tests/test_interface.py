"""Tests for the Interface Translator (vefr-interface).

Deterministic only: the model backend is faked (monkeypatched
`_completion` and `httpx.post`); no live endpoint is required for the
pytest suite. The live model benchmark lives separately in
bench/interface/ and is intentionally NOT part of the unit gate.
"""

import json
from pathlib import Path

import httpx
import pytest

import vefr.interface as interface
from vefr.interface import (
    ACTIONS,
    Intent,
    InterfaceMalformed,
    InterfaceUnavailable,
    interface_log_path,
    load_template,
    translate,
)


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Hermetic environment: tmp log file, no live endpoint, real template."""
    log = tmp_path / "interface.jsonl"
    monkeypatch.setenv("VEFR_INTERFACE_URL", "http://127.0.0.1:9")
    monkeypatch.setattr(interface, "interface_log_path", lambda: log)
    return log


def _fake(raw: str):
    def _f(messages, *, url=None, timeout=None, temperature=0.0, max_tokens=200):
        return raw
    return _f


def test_valid_structured_response_parses(env, monkeypatch):
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "observe", "confidence": 0.9, "needs_clarification": false}'))
    intent, meta = translate("look around")
    assert intent.action == "observe"
    assert intent.needs_clarification is False
    assert meta["validation"] == "ok"
    assert meta["role"] == "interface"
    assert meta["template_revision"] == "interface-intent-v1"
    assert meta["latency_ms"] >= 0


def test_malformed_response_rejected(env, monkeypatch):
    monkeypatch.setattr(interface, "_completion", _fake("definitely not json"))
    with pytest.raises(InterfaceMalformed):
        translate("look around")


def test_unknown_action_rejected(env, monkeypatch):
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "dance", "confidence": 0.9, "needs_clarification": false}'))
    # "dance" is not in the engine vocabulary - fail closed.
    with pytest.raises(InterfaceMalformed):
        translate("dance at midnight")


def test_missing_required_argument_rejected(env, monkeypatch):
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "move", "confidence": 0.8, "needs_clarification": false}'))
    # move requires a direction; speak/attack/strike/console/hurl require
    # a target. An action without its required argument is discarded.
    with pytest.raises(InterfaceMalformed):
        translate("move")


def test_clarification_accepted(env, monkeypatch):
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "observe", "confidence": 0.5, "needs_clarification": true, '
        '"clarification": "Which door do you mean?"}'))
    intent, meta = translate("do the thing with that one")
    assert intent.needs_clarification is True
    assert intent.clarification == "Which door do you mean?"
    # Even if the model left a routed action, the deterministic cleanup
    # nulls it - a clarification never smuggles an action.
    assert intent.action is None
    assert meta["validation"] == "clarification"


def test_speak_intent_carries_topic(env, monkeypatch):
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "speak", "target": "the innkeeper", "topic": "the caravan", '
        '"confidence": 0.95, "needs_clarification": false}'))
    intent, _ = translate("ask the innkeeper about the caravan")
    assert intent.action == "speak"
    assert intent.target == "the innkeeper"
    assert intent.topic == "the caravan"


def test_confidence_out_of_bounds_rejected(env, monkeypatch):
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "observe", "confidence": 12.0, "needs_clarification": false}'))
    with pytest.raises(InterfaceMalformed):
        translate("look around")


def test_additional_properties_rejected(env, monkeypatch):
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "observe", "confidence": 0.9, "needs_clarification": false, '
        '"world_state_damage": "now it is destroyed"}'))
    with pytest.raises(InterfaceMalformed):
        translate("look around")


def test_endpoint_unavailable_fails_honestly(env, monkeypatch):
    def _dead(messages, *, url=None, timeout=None, temperature=0.0, max_tokens=200):
        raise InterfaceUnavailable("connection refused")
    monkeypatch.setattr(interface, "_completion", _dead)
    with pytest.raises(InterfaceUnavailable):
        translate("look around")


def test_http_transport_error_is_unavailable(env, monkeypatch):
    def _boom(*a, **k):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(interface.httpx, "post", _boom)
    with pytest.raises(InterfaceUnavailable):
        translate("look around")


def test_timeout_fails_honestly(env, monkeypatch):
    def _slow(*a, **k):
        raise httpx.TimeoutException("timed out")
    monkeypatch.setattr(interface.httpx, "post", _slow)
    with pytest.raises(InterfaceUnavailable):
        translate("look around")


def test_template_loads_as_data(env):
    tpl = load_template()
    assert tpl["schema_version"] == "interface-intent-v1"
    assert 5 <= len(tpl["examples"]) <= 12
    inputs = [e["input"] for e in tpl["examples"]]
    assert any("go north" in s for s in inputs)  # move exemplar present
    assert any("attack" in s for s in inputs)    # attack exemplar present
    assert {a["name"] for a in tpl["actions"]} == set(ACTIONS)
    from vefr.interface import build_fewshot
    assert len(build_fewshot(tpl)) == 2 * len(tpl["examples"])


def test_template_missing_fails_loudly(env, monkeypatch):
    from vefr.interface import load_template
    with pytest.raises(InterfaceUnavailable):
        load_template(Path("/nonexistent/intent.json"))


def test_template_malformed_fails_loudly(env, tmp_path, monkeypatch):
    bad = tmp_path / "intent.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(InterfaceUnavailable):
        load_template(bad)


def test_translator_cannot_mutate_world():
    src = Path(interface.__file__).read_text(encoding="utf-8")
    for forbidden in ("journal.log(", "world.load_world(", "forge.", "vault.",
                      "sessions.", "maplab.", ".write_text(", "os.system",
                      "subprocess", "exec(", "eval("):
        assert forbidden not in src, f"translator must not contain {forbidden!r}"
    # The result object is a plain validated intent, nothing more.
    intent = Intent(action="observe", confidence=0.9)
    assert set(intent.model_dump()) == {
        "action", "target", "topic", "direction", "confidence",
        "needs_clarification", "clarification"}


def test_no_direct_tool_execution_path():
    src = Path(interface.__file__).read_text(encoding="utf-8")
    for forbidden in ("subprocess", "os.system", "shlex", "Popen",
                      "function_calls", "tool_choice", "tool_use", "exec(",
                      "eval("):
        assert forbidden not in src, f"no tool path: {forbidden!r}"
    # The wire payload never carries a tools/functions block either.
    for m in interface.build_messages(load_template(), "look around"):
        assert set(m) == {"role", "content"}
        assert "tools" not in m["content"]
    assert "tools" not in json.dumps(load_template())


def test_logging_does_not_expose_config_or_secrets(env, monkeypatch):
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "observe", "confidence": 0.9, "needs_clarification": false}'))
    # A URL that would carry credentials if the logger were sloppy.
    monkeypatch.setenv("VEFR_INTERFACE_URL",
                       "http://op:s3cr3t-token@127.0.0.1:8085")
    long_input = ("go " * 2000) + "toward the square"
    translate(long_input)
    entries = env.read_text(encoding="utf-8").splitlines()
    assert len(entries) == 1
    line = entries[0]
    assert "s3cr3t-token" not in line
    # Truncated, not the full paste: the 3000-suffix "toward the square"
    # beyond the 300-char log cap is absent, and the tail chars are.
    assert "toward the square" not in line
    assert len(json.loads(line)["input"]) <= 300


def test_log_shape_and_runtime_private(env, tmp_path, monkeypatch):
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "speak", "target": "the guard", "confidence": 0.9, '
        '"needs_clarification": false}'))
    translate("tell the guard to stay")
    entry = json.loads(env.read_text(encoding="utf-8").splitlines()[0])
    assert set(entry) == {"at", "role", "model", "template_revision", "input",
                          "output", "validation", "latency_ms"}
    assert entry["role"] == "interface"
    assert entry["output"]["action"] == "speak"
    # Runtime private: the log path lives under app_home()/data.
    assert "/data/interface.jsonl" in str(interface_log_path())


def test_loopback_default_not_localhost(monkeypatch):
    monkeypatch.delenv("VEFR_INTERFACE_URL", raising=False)
    assert interface.interface_url() == "http://127.0.0.1:8085"
    assert "localhost" not in interface.interface_url()
    assert "::1" not in interface.interface_url()


def test_routed_intent_drops_commentary_clarification(env, monkeypatch):
    """A routed action may carry stray commentary in the clarification
    slot (the 1.5B model does this eagerly). The deterministic layer
    drops it - the flag is the only clarification authority, and prose
    never rides a routed action."""
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "observe", "confidence": 0.9, "needs_clarification": false, '
        '"clarification": "I can only observe the world as it is. What would '
        'you like to look at?"}'))
    intent, meta = translate("look around")
    assert intent.action == "observe"
    assert intent.needs_clarification is False
    assert intent.clarification is None
    assert meta["validation"] == "ok"


def test_empty_optional_strings_normalized_to_none(env, monkeypatch):
    """llama.cpp strict grammar can fill optional string slots with "" -
    the deterministic cleanup must read that as absent."""
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "speak", "target": "the innkeeper", "topic": "", '
        '"direction": "", "confidence": 0.9, "needs_clarification": false, '
        '"clarification": ""}'))
    intent, _ = translate("ask the innkeeper")
    assert intent.target == "the innkeeper"
    assert intent.topic is None
    assert intent.direction is None
    assert intent.clarification is None
    with pytest.raises(InterfaceMalformed):
        # Clarification with nothing to say is still rejected: a model
        # that needs clarification must actually say what it needs.
        monkeypatch.setattr(interface, "_completion", _fake(
            '{"action": "observe", "confidence": 0.5, '
            '"needs_clarification": true, "clarification": ""}'))
        translate("ambiguous")


def test_cli_clarification_demo(env, monkeypatch, capsys):
    import argparse
    from vefr.interface import _cmd_interface
    monkeypatch.setattr(interface, "_completion", _fake(
        '{"action": "observe", "confidence": 0.6, "needs_clarification": true, '
        '"clarification": "What would you like to do, and with which target?"}'))
    rc = _cmd_interface(argparse.Namespace(
        instruction="do the thing with that one", url=None, json=False))
    assert rc == 0
    out = capsys.readouterr().out
    assert "clarification required" in out
    assert "What would you like to do" in out