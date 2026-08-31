"""The export - deterministic templating, proven with the model absent.

Runs against worlds/sample-world/ explicitly (never whichever pack
happens to be first alphabetically), with the journal and the vault
redirected into tmp_path.
"""

import pytest

from norn import forge, journal
from norn.export import export_story

WORLD = "sample-world"


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr(forge, "VAULT", tmp_path / "vault.json")


def _play():
    journal.log("rumor", phase="whispers", speaker="Katla", whisper="the mill ran dry", is_true=False)
    journal.log("npc_line", phase="whispers", speaker="the ferryman", line="stay off the reeds")
    journal.log("item_forged", name="The Ledger-Ribbon", bond="attuned", lore="Tied once to a door.")
    journal.log("bell_letter", letter="For you.\n\nbring the pail in")


def test_empty_journal_and_vault_still_export(tmp_path):
    out = export_story(WORLD)
    assert out.startswith("# Emberfield")
    assert "## What happened" in out
    assert "Nothing has happened here yet." in out
    assert "## What was carried" not in out
    assert out.endswith("\n")


def test_export_includes_the_bible_canon():
    out = export_story(WORLD)
    assert "Never explain. Never label. Show only." in out


def test_every_kind_renders_readably():
    _play()
    out = export_story(WORLD)

    # rumor: attributed whisper, plus the lie marker
    assert "Katla whispered: \u201cthe mill ran dry\u201d" in out
    assert "It was not true, or not true yet." in out

    # npc_line: attributed spoken line
    assert "the ferryman said: \u201cstay off the reeds\u201d" in out

    # item_forged: a found-item line carrying its lore
    assert "The Ledger-Ribbon came to hand \u2014 attuned." in out
    assert "Tied once to a door." in out

    # bell_letter: a blockquote, every line prefixed
    assert "> For you." in out
    assert "> bring the pail in" in out

    # order is the order it happened in
    assert out.index("Katla whispered") < out.index("the ferryman said") < out.index("For you.")


def test_a_true_rumor_carries_no_lie_marker():
    journal.log("rumor", phase="whispers", speaker="Katla", whisper="the bell is owed", is_true=True)
    out = export_story(WORLD)
    assert "the bell is owed" in out
    assert "It was not true" not in out


def test_vault_items_appear_when_kept():
    item = forge.ItemCard(
        name="The Ledger-Ribbon",
        kind="ribbon",
        bond="attuned",
        lore="Tied once to a door that had forgotten how to open.",
    )
    forge.keep_item(item)
    out = export_story(WORLD)
    assert "## What was carried" in out
    assert "- **The Ledger-Ribbon** (attuned)" in out
    assert "forgotten how to open" in out


def test_an_unknown_kind_does_not_crash_the_export():
    journal.log("weather_turned", note="a newer engine wrote this")
    out = export_story(WORLD)
    assert "a newer engine wrote this" in out


def test_missing_fields_never_raise():
    journal.log("rumor")
    journal.log("npc_line")
    journal.log("item_forged")
    journal.log("bell_letter")
    out = export_story(WORLD)
    assert "## What happened" in out
    assert "A letter was found, and said nothing." in out


def test_the_document_has_exactly_one_h1():
    _play()
    out = export_story(WORLD)
    h1s = [ln for ln in out.splitlines() if ln.startswith("# ")]
    assert h1s == ["# Emberfield"]
    # the bible's own heading is nested under it, not competing with it
    assert "## Emberfield - the world bible" in out
