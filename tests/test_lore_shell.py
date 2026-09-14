"""Focused tests for the Lorekeeper slice (vefr-lore).

The embed service is faked for every unit test: no live network, no
generative model, deterministic vectors. Live-service smoke stays
out of the pytest suite (see the handoff: do not let unit tests
depend on the live service).
"""

import json

import pytest

from vefr.lore_shell import (
    EmbedMalformed,
    EmbedUnavailable,
    LoreFact,
    add_fact,
    ask,
    facts_path,
    list_facts,
    rebuild,
    status,
    vectors_path,
    _cos,
)


@pytest.fixture
def lore_home(tmp_path, monkeypatch):
    """Point VEFR_LORE_DIR at a tmp dir so tests never touch real lore."""
    root = tmp_path / "lore"
    monkeypatch.setenv("VEFR_LORE_DIR", str(root))
    monkeypatch.setenv("VEFR_EMBED_URL", "http://127.0.0.1:9")
    return root


def _fixed_vectors(texts: list[str]) -> list[list[float]]:
    """Deterministic 4-dim vectors so cosine math is hand-checkable."""
    return [[float(len(t)), 1.0, 0.0, 0.0] for t in texts]


def test_add_persists_structured_fact(lore_home, monkeypatch):
    monkeypatch.setattr("vefr.lore_shell.embed_texts", _fixed_vectors)
    fact = add_fact("The western gate was destroyed.", source="owner")
    assert fact.id
    assert fact.text == "The western gate was destroyed."
    assert fact.source == "owner"
    lines = facts_path().read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    stored = LoreFact(**json.loads(lines[0]))
    assert stored.id == fact.id
    assert stored.created_at
    assert stored.metadata == {}
    assert stored.tags == []


def test_index_is_derived_not_authoritative(lore_home, monkeypatch):
    monkeypatch.setattr("vefr.lore_shell.embed_texts", _fixed_vectors)
    add_fact("The western gate was destroyed.")
    assert vectors_path().exists()
    # Deleting the derived index must not touch the authoritative facts.
    vectors_path().unlink()
    assert len(list_facts()) == 1
    assert facts_path().exists()
    # A stale index is regenerable from the facts.
    rebuild()
    assert vectors_path().exists()


def test_rebuild_preserves_facts(lore_home, monkeypatch):
    monkeypatch.setattr("vefr.lore_shell.embed_texts", _fixed_vectors)
    add_fact("Fact one.")
    add_fact("Fact two.")
    before = [f.text for f in list_facts()]
    rebuild()
    assert [f.text for f in list_facts()] == before
    # Index now covers all facts.
    s = status()
    assert s["fact_count"] == 2
    assert s["indexed_count"] == 2


def test_ask_returns_relevant_stored_facts(lore_home, monkeypatch):
    def _vec(texts: list[str]) -> list[list[float]]:
        return [{
            "The western gate was destroyed.": [0.95, 0.1, 0.0, 0.0],
            "The northern tower stands tall.": [0.1, 0.95, 0.0, 0.0],
            "western gate": [0.9, 0.0, 0.0, 0.0],
        }[texts[0]]]

    monkeypatch.setattr("vefr.lore_shell.embed_texts", _vec)
    add_fact("The western gate was destroyed.")
    add_fact("The northern tower stands tall.")
    result = ask("western gate", k=3)
    assert result["matches"][0]["text"] == "The western gate was destroyed."
    assert result["matches"][0]["score"] > 0.9
    assert result["matches"][0]["source"] == "owner"


def test_empty_lore_returns_honest_empty(lore_home, monkeypatch):
    monkeypatch.setattr("vefr.lore_shell.embed_texts", _fixed_vectors)
    result = ask("anything")
    assert result["matches"] == []
    assert result["query"] == "anything"


def test_embed_unavailable_is_explicit(lore_home, monkeypatch):
    monkeypatch.setattr("vefr.lore_shell.embed_texts", _fixed_vectors)
    add_fact("A fact so index exists before the outage.")

    def _boom(texts: list[str]) -> list[list[float]]:
        raise EmbedUnavailable("refused")

    monkeypatch.setattr("vefr.lore_shell.embed_texts", _boom)
    with pytest.raises(EmbedUnavailable):
        ask("query")
    s = status()
    assert s["embed_ok"] is False
    assert "refused" in s["embed_error"]


def test_embed_down_adds_with_explicit_warning(lore_home, monkeypatch, capsys):
    def _boom(texts: list[str]) -> list[list[float]]:
        raise EmbedUnavailable("down")

    monkeypatch.setattr("vefr.lore_shell.embed_texts", _boom)
    fact = add_fact("A fact stored without a vector.")
    assert fact.text == "A fact stored without a vector."
    err = capsys.readouterr().err
    assert "embed unavailable" in err
    # Fact survived; index simply isn't populated.
    assert len(list_facts()) == 1
    assert not vectors_path().exists()


def test_malformed_embed_response_fails_honestly(lore_home, monkeypatch):
    monkeypatch.setattr("vefr.lore_shell.embed_texts", _fixed_vectors)
    add_fact("Fact one.")
    add_fact("Fact two.")

    def _junk(texts: list[str]) -> list[list[float]]:
        raise EmbedMalformed("no embedding field")

    monkeypatch.setattr("vefr.lore_shell.embed_texts", _junk)
    # ask and rebuild refuse to guess on a malformed contract.
    with pytest.raises(EmbedMalformed):
        ask("query")
    with pytest.raises(EmbedMalformed):
        rebuild()


def test_duplicate_add_is_deliberate(lore_home, monkeypatch):
    calls: list[int] = []

    def _counting(texts: list[str]) -> list[list[float]]:
        calls.append(len(texts))
        return _fixed_vectors(texts)

    monkeypatch.setattr("vefr.lore_shell.embed_texts", _counting)
    first = add_fact("Same text twice.")
    second = add_fact("Same text twice.")
    assert first.id == second.id
    assert len(list_facts()) == 1
    assert calls == [1]


def test_gitignore_covers_runtime_lore(lore_home, repo_root):
    rules = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert "/data/lore/" in rules


def test_no_chat_or_generation_path(lore_home, repo_root):
    """The Lorekeeper must never call a generative model: the only
    HTTP path is the /v1/embeddings embed route, and nothing ever
    posts a chat payload. Probing the module source keeps this an
    honest structural check rather than a mocked-away behavior."""
    src = (repo_root / "src" / "vefr" / "lore_shell.py").read_text(encoding="utf-8")
    import re
    assert not re.search(r"/v1/chat/completions", src)
    assert not re.search(r"messages.*role.*content", src, re.S)
    assert re.search(r"/v1/embeddings", src)


# --- helpers / fixtures ---------------------------------------------

@pytest.fixture
def repo_root():
    import pathlib
    return pathlib.Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("a,b,expected", [
    ([1.0, 0.0], [1.0, 0.0], 1.0),
    ([1.0, 0.0], [-1.0, 0.0], -1.0),
    ([], [1.0], 0.0),
])
def test_cosine(a, b, expected):
    got = _cos(a, b)
    assert got == pytest.approx(expected)