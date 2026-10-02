"""Skin loader, K3: the words exist where a person looks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rulesets_guide_documents_the_skin_field():
    text = (ROOT / "docs/guides/rulesets.md").read_text(encoding="utf-8").lower()
    for needle in ('"skin"', "skin.json", "prefers-contrast", "nine-slice", "no skin"):
        assert needle in text, needle


def test_the_design_note_records_what_is_built():
    text = (ROOT / "design/ui-skin.md").read_text(encoding="utf-8")
    assert "Status: **loader built" in text
