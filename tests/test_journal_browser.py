"""Static guard for the 2026-09-03 Journal panel fix.

The earlier bug was that the Journal panel only re-rendered when its
own tab was clicked: ``renderJournal()`` was wired to a tab-visibility
event dispatched in ``announceView``. The fix dispatches
``vefr:journal`` from each gameplay outcome that lands a server-side
journal entry - so the panel listens at the session level, not the
tab level.

Companion to the DOM-harness regression (tests/test_web_dom.py +
dom_harness.mjs, which drives a full flow and asserts the journal
fetch count grows). This static guard is the cheap-and-fast
compliment that nails down the EXACT lines that must stay in place.
"""
from pathlib import Path

INDEX = Path("web/index.html").read_text(encoding="utf-8")
TOWN = Path("web/town.js").read_text(encoding="utf-8")


def _window(needle: str) -> bool:
    """Find a window.dispatchEvent(new Event('vefr:journal')) line within
    +/- 25 lines of any line mentioning `needle` (a fetch URL or a
    function declaration). Returns True iff the dispatch is present in
    the immediate neighborhood of every gameplay outcome that mutates
    the server-side journal.
    """
    for i, line in enumerate(INDEX.splitlines()):
        if needle in line and ("fetch" in line or "function" in line):
            nearby = "\n".join(INDEX.splitlines()[max(0, i - 2):i + 25])
            if "'vefr:journal'" in nearby:
                return True
    return False


def test_whisper_dispatches_journal_refresh():
    assert _window("/api/rumor"), (
        "the whisper click handler must dispatch vefr:journal so the "
        "Journal panel refetches when the player is on any tab. The "
        "comment header on the dispatch site explains the invariant."
    )


def test_combat_verb_dispatches_journal_refresh():
    assert _window("/api/combat/action"), (
        "combat verbs log to the server-side journal via /api/combat/action. "
        "Without a vefr:journal dispatch here, Journal panel freezes "
        "during combat."
    )


def test_forge_keep_dispatches_journal_refresh():
    assert _window("/api/vault"), (
        "the forge keep-via-vault path logs to the journal. Without a "
        "vefr:journal dispatch here, Journal panel freezes when the "
        "player keeps an item."
    )


def test_stefna_strike_dispatches_journal_refresh():
    assert _window("/api/stefna"), (
        "the bell strike logs to the journal via /api/stefna. Without "
        "a vefr:journal dispatch here, Journal panel freezes when the "
        "player sounds the bell from a non-Journal tab."
    )


def test_journal_visit_dispatches_journal_refresh():
    """town.js: the hero's journalVisit() is the move-path. The dispatch
    must be wired there because the move endpoint is the only journal-
    writing path that doesn't also touch the shared STATE patch
    subsystem."""
    assert "'vefr:journal'" in TOWN, (
        "town.js's journalVisit() must dispatch vefr:journal after a "
        "successful /api/journal/move POST. Without it, the Journal "
        "panel freezes while the player walks around town."
    )


def test_journal_listener_survives_without_tab_switch():
    """The original bug gated the listener on tab visibility. The fix
    keeps the listener global on `window` and lets gameplay events
    fire it. This guard asserts that the global listener is still
    bound on window (not on a panel-specific element)."""
    window_listener = "window.addEventListener('vefr:journal'"
    assert window_listener in INDEX, (
        "the Journal render listener must stay bound on `window` "
        "(session-level), not on a panel-local element (tab-level). "
        "The bug class returns immediately if this listener moves."
    )
    # And nothing should be tab-gating renderJournal() itself.
    assert "if (activeTab" not in INDEX.replace(" ", ""), (
        "renderJournal() must not be guarded on tab visibility (the "
        "original bug's root cause). If you see an activeTab check "
        "around renderJournal, that's the regression."
    )
