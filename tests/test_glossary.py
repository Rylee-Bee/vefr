"""The glossary stays well formed: every table row has a plain name, the retired words are listed
beside the plain ones, and the decided choices are written down."""

from __future__ import annotations

from pathlib import Path

GLOSSARY = Path(__file__).resolve().parents[1] / "docs" / "guides" / "glossary.md"


def _text() -> str:
    return GLOSSARY.read_text(encoding="utf-8")


def _rows(heading: str) -> list[list[str]]:
    section = _text().split(f"## {heading}", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        if line.startswith("|") and not line.startswith("|---") and "**" in line:
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def test_every_noun_verb_and_state_row_has_a_status():
    for heading in ("Things (nouns)", "Actions (verbs)", "States (adjectives)"):
        rows = _rows(heading)
        assert rows, heading
        for r in rows:
            assert r[-1].split(";")[0].strip() in {"decided", "proposed", "in use", "in use after the pack-tiles change lands"} \
                or r[-1].startswith(("decided", "proposed", "in use")), (heading, r)


def test_the_decided_choices_are_written_down():
    text = _text()
    assert "**game**" in text and '"pack"' in text           # the game folder
    assert "**level**" in text and "**chamber**" in text and "**stakes**" in text and "**room**" in text
    assert "**achievement**" in text and "**sticker**" in text
    assert "keep working" in text                              # old setting names keep working


def test_old_setting_names_are_listed_beside_the_plain_ones():
    section = _text().split("## Settings (environment variables)", 1)[1].split("\n## ", 1)[0]
    for old in ("VEFR_LLAMACPP_URL", "VEFR_VAULT", "VEFR_JOURNAL", "VEFR_STORYTELLER"):
        assert old in section
