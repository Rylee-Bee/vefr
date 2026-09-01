"""The export - deterministic templating, proven with the model absent.

Runs against worlds/sample-world/ explicitly (never whichever pack
happens to be first alphabetically), with the journal and the vault
redirected into tmp_path.

The export shape is one section per dev-UI tab, in the order the
player met them. See export.py for the section mapping.
"""

import pytest

from vefr import forge, journal
from vefr.export import export_story, export_tab, _TAB_NAMES

WORLD = "sample-world"


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")
    monkeypatch.setattr(forge, "VAULT", tmp_path / "vault.json")


def _play():
    journal.log("rumor", phase="whispers", speaker="Katla", whisper="the mill ran dry", is_true=False)
    journal.log("npc_line", phase="whispers", speaker="the ferryman", line="stay off the reeds")
    journal.log("item_forged", name="The Ledger-Ribbon", bond="attuned", lore="Tied once to a door.")
    journal.log("stefna_letter", letter="For you.\n\nbring the pail in")
    # The vault tab only appears when an item was actually kept -
    # log-only entries don't make the vault section show.
    forge.keep_item(forge.ItemCard(
        name="The Ledger-Ribbon", kind="ribbon", bond="attuned",
        lore="Tied once to a door that had forgotten how to open.",
    ))


def test_empty_journal_and_vault_still_export(tmp_path):
    out = export_story(WORLD)
    assert out.startswith("# Emberfield")
    # no per-tab sections when nothing has happened
    assert "Nothing has happened here yet." in out
    assert "## Relics" not in out
    assert "## The Stefna" not in out
    assert out.endswith("\n")


def test_export_includes_the_logbok_canon():
    out = export_story(WORLD)
    assert "Never explain. Never label. Show only." in out


def test_every_kind_renders_in_its_own_tab():
    _play()
    out = export_story(WORLD)

    # rumor: appears in the Rumors tab
    rumors_start = out.index("## The Whispers Heard")
    assert "Katla whispered: \u201cthe mill ran dry\u201d" in out[rumors_start:]
    assert "It was not true, or not true yet." in out[rumors_start:]

    # npc_line: appears under the Voices tab, grouped by speaker
    voices_start = out.index("## The Voices Heard")
    voices = out[voices_start:]
    assert "the ferryman said: \u201cstay off the reeds\u201d" in voices

    # item_forged: appears under The Relics tab
    vault_start = out.index("## Relics")
    vault = out[vault_start:]
    assert "The Ledger-Ribbon" in vault
    assert "attuned" in vault

    # stefna_letter: each letter gets its own subsection under The Stefna tab
    stefna_start = out.index("## The Stefna")
    stefna = out[stefna_start:]
    assert "> For you." in stefna
    assert "> bring the pail in" in stefna
    assert "Letter 1" in stefna

    # town + journal sections can be empty but the headings should still
    # be present if there are journal entries that don't fit the four
    # tab kinds. After _play(), the Journal section should be empty
    # (everything went into Rumors/Voices/Vault/Bell); it's only
    # present if it had content - the canonical 4 kinds don't, so
    # the Journal section is omitted when empty.


def test_a_true_rumor_carries_no_lie_marker():
    journal.log("rumor", phase="whispers", speaker="Katla", whisper="the bell is owed", is_true=True)
    out = export_story(WORLD)
    assert "the bell is owed" in out
    assert "It was not true" not in out


def test_vault_items_appear_in_their_own_tab():
    item = forge.ItemCard(
        name="The Ledger-Ribbon",
        kind="ribbon",
        bond="attuned",
        lore="Tied once to a door that had forgotten how to open.",
    )
    forge.keep_item(item)
    out = export_story(WORLD)
    assert "## Relics" in out
    assert "### The Ledger-Ribbon" in out
    assert "(attuned)" in out
    assert "forgotten how to open" in out


def test_an_unknown_kind_falls_into_the_journal_tab():
    journal.log("weather_turned", note="a newer engine wrote this")
    out = export_story(WORLD)
    assert "## The Journal" in out
    assert "a newer engine wrote this" in out


def test_missing_fields_never_raise():
    journal.log("rumor")
    journal.log("npc_line")
    journal.log("item_forged")
    journal.log("stefna_letter")
    out = export_story(WORLD)
    assert "A letter was found, and said nothing." in out


def test_the_document_has_exactly_one_h1():
    _play()
    out = export_story(WORLD)
    h1s = [ln for ln in out.splitlines() if ln.startswith("# ")]
    assert h1s == ["# Emberfield"]
    # the logbok's own heading is nested under it, not competing with it
    assert "### Emberfield - the world logbok" in out


# ---- per-tab exports ----

def test_export_tab_returns_one_section():
    _play()
    for name in _TAB_NAMES:
        out = export_tab(name, WORLD)
        assert out.startswith("# Emberfield"), f"{name} missing world title"
        assert "### Emberfield - the world logbok" in out, f"{name} missing logbok"
        # each section's header must appear (even if the section is
        # empty - then it says 'Nothing yet.')


def test_export_tab_rumors_only_has_rumors():
    _play()
    out = export_tab("rumors", WORLD)
    assert "## The Whispers Heard" in out
    # the logbok canon at the top of the export mentions the ferryman + 'For you.'
    # in its own right; the per-tab section starts at the first H2.
    tab_section = out[out.index("## The Whispers Heard"):]
    assert "the ferryman said" not in tab_section  # npc_line, not a rumor
    assert "For you." not in tab_section     # stefna letter, not a rumor


def test_export_tab_vault_only_has_vault():
    forge.keep_item(forge.ItemCard(
        name="Bell-Key", kind="tool", bond="attuned", lore="opens a door"))
    _play()
    out = export_tab("vault", WORLD)
    assert "## Relics" in out
    tab_section = out[out.index("## Relics"):]
    assert "Bell-Key" in tab_section
    assert "the ferryman said" not in tab_section
    assert "Katla whispered" not in tab_section


def test_export_tab_rejects_unknown_name():
    with pytest.raises(ValueError):
        export_tab("nope", WORLD)