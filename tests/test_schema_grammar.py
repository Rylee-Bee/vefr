"""Tests for the JSON Schema -> GBNF converter and its generator wiring.

The converter is pure (no model, no network); the wiring tests stub
httpx so nothing leaves the process.
"""

import re
from types import SimpleNamespace

import pytest

from vefr import generator, storyteller
from vefr.schema_grammar import SchemaGrammarError, grammar_from_schema


def _openai_stub(monkeypatch):
    """Make generator._completion take the OpenAI-compatible branch."""
    st = SimpleNamespace(model_provider=storyteller.Provider.OPENAI_COMPATIBLE)
    monkeypatch.setattr(storyteller, "resolve_active", lambda: st)
    monkeypatch.setattr(generator, "LLAMACPP_URL", "http://stub")


def _capture_post(monkeypatch) -> list[dict]:
    sent: list[dict] = []

    class _Resp:
        text = '{"choices": [{"message": {"content": "ok"}}]}'

        def raise_for_status(self):
            pass

    def fake_post(url, json, timeout):
        sent.append(json)
        return _Resp()

    monkeypatch.setattr(generator.httpx, "post", fake_post)
    return sent


def _root_rule(grammar: str) -> str:
    return next(
        line for line in grammar.splitlines() if line.startswith("root ::=")
    )


def _identifiers(rhs: str) -> list[str]:
    """Rule names referenced by a GBNF right-hand side (strings and
    character classes removed first)."""
    cleaned = re.sub(r'"(?:[^"\\]|\\.)*"', " ", rhs)
    cleaned = re.sub(r"\[(?:\\.|[^\]])*\]", " ", cleaned)
    return re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", cleaned)


# --- the converter ---------------------------------------------------

def test_rumor_schema_has_root_and_property_rules():
    grammar = grammar_from_schema(generator.SCHEMA)
    assert "root ::=" in grammar
    for prop in ("speaker", "whisper", "is_true", "hook"):
        assert f"root_{prop} ::=" in grammar
    assert "string ::=" in grammar
    assert "boolean ::=" in grammar


def test_object_commas_are_exact_not_optional():
    grammar = grammar_from_schema(generator.SCHEMA)
    # The over-permissive construct that admits `{"a":1,}` must not exist.
    assert '(ws "," ws)?' not in grammar
    root = _root_rule(grammar)
    # An optional property becomes alternative whole-object shapes.
    assert "root_hook" in root
    assert "|" in root


def test_optional_property_expands_to_present_and_absent():
    schema = {
        "type": "object",
        "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
        "required": ["a"],
    }
    root = _root_rule(grammar_from_schema(schema))
    assert "root_a" in root and "root_b" in root
    assert "|" in root


def test_required_only_object_has_one_shape():
    schema = {
        "type": "object",
        "properties": {"a": {"type": "string"}},
        "required": ["a"],
    }
    root = _root_rule(grammar_from_schema(schema))
    assert "|" not in root
    assert "root_a" in root


def test_every_referenced_rule_is_defined():
    grammar = grammar_from_schema(generator.SCHEMA)
    defined = {
        line.split(" ::= ", 1)[0].strip()
        for line in grammar.splitlines()
        if " ::= " in line
    }
    for line in grammar.splitlines():
        if " ::= " not in line:
            continue
        rhs = line.split(" ::= ", 1)[1]
        for ref in _identifiers(rhs):
            assert ref in defined, f"{ref!r} referenced but never defined"


def test_enum_alternatives():
    grammar = grammar_from_schema({"type": "string", "enum": ["red", "green"]})
    assert '"red"' in grammar and '"green"' in grammar


def test_array_rule():
    grammar = grammar_from_schema({"type": "array", "items": {"type": "string"}})
    assert "root_items ::=" in grammar
    assert '"["' in grammar and '"]"' in grammar


def test_nullable_and_explicit_null():
    assert '"null"' in grammar_from_schema({"type": ["string", "null"]})
    assert '"null"' in grammar_from_schema({"type": "null"})


def test_optional_property_flood_raises():
    props = {f"p{i}": {"type": "string"} for i in range(8)}
    with pytest.raises(SchemaGrammarError, match="optional"):
        grammar_from_schema({"type": "object", "properties": props})


@pytest.mark.parametrize("schema, needle", [
    ({"oneOf": [{"type": "string"}]}, "oneOf"),
    ({"$ref": "#/x"}, r"\$ref"),
    ({"type": "string", "pattern": "^a$"}, "pattern"),
])
def test_unsupported_raises(schema, needle):
    with pytest.raises(SchemaGrammarError, match=needle):
        grammar_from_schema(schema)


# --- the generator wiring --------------------------------------------

def test_default_completion_is_unchanged(monkeypatch):
    """No opt-in: response_format as before, no grammar."""
    _openai_stub(monkeypatch)
    sent = _capture_post(monkeypatch)
    assert generator._completion({
        "model": "m", "system": "s", "prompt": "p", "format": generator.SCHEMA,
    }) == "ok"
    body = sent[0]
    assert "response_format" in body
    assert "grammar" not in body


def test_opt_in_grammar_replaces_response_format(monkeypatch):
    _openai_stub(monkeypatch)
    sent = _capture_post(monkeypatch)
    generator._completion({
        "model": "m", "system": "s", "prompt": "p",
        "format": generator.SCHEMA, "grammar": True,
    })
    body = sent[0]
    assert "root ::=" in body["grammar"]
    # One constraint, not two that might conflict server-side.
    assert "response_format" not in body


def test_opt_in_grammar_falls_back_when_unconvertible(monkeypatch):
    _openai_stub(monkeypatch)
    sent = _capture_post(monkeypatch)
    generator._completion({
        "model": "m", "system": "s", "prompt": "p",
        "format": {"oneOf": [{"type": "string"}]}, "grammar": True,
    })
    body = sent[0]
    assert "grammar" not in body
    assert "response_format" in body


def test_generate_rumor_retries_with_grammar(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(
        generator, "build_payload",
        lambda phase, theme, sid=None: {"model": "m", "format": generator.SCHEMA},
    )

    def fake_completion(payload, max_tokens=1024):
        calls.append(payload)
        if len(calls) == 1:
            return "not json at all"
        return '{"speaker": "s", "whisper": "w", "is_true": true}'

    monkeypatch.setattr(generator, "_completion", fake_completion)
    card = generator.generate_rumor()
    assert card.whisper == "w"
    assert len(calls) == 2
    assert not calls[0].get("grammar")
    assert calls[1].get("grammar") is True
