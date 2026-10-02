"""Growth, T4: the words exist where a person looks (design/growth.md,
build order step 4)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8").lower()


def test_glossary_names_the_new_words():
    g = read("docs/guides/glossary.md")
    for word in ("experience", "level", "practice"):
        assert word in g, word


def test_rulesets_guide_documents_the_growth_block():
    r = read("docs/guides/rulesets.md")
    for needle in ('"growth"', "levels", "practice", "xp"):
        assert needle in r, needle


def test_design_note_is_marked_built():
    assert "status: **built**" in read("design/growth.md")
