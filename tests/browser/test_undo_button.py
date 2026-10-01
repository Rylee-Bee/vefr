"""The Desk's "Undo last edit" button, in a real browser.

Press it on a studio that has kept no edits: POST
/api/builder/edits/undo answers 404 with "there is nothing to undo in
this world", and the Desk shows that as a friendly sentence in its own
polite live region (#ws-undo-status, reusing the weave status pattern
and its CSS class) - not an error, and no status code on screen.

The button is a real <button type="button"> in the Desk tools row, so
get_by_role("button", name="Undo last edit") finds it, and it is live
again for the next press.

Skips without Chromium exactly like the other browser tests.
"""
from .steps import open_studio


def test_undo_with_nothing_to_undo_is_a_friendly_sentence(page, studio):
    open_studio(page, studio, "workshop")
    page.locator("#screen-workshop").wait_for()

    # A real button, reachable by its accessible name alone.
    undo = page.get_by_role("button", name="Undo last edit")
    assert page.get_attribute("#ws-undo-edit", "type") == "button"
    undo.click()

    # The answer lands in the polite live region, in friendly words.
    status = page.locator("#ws-undo-status", has_text="nothing to undo")
    status.wait_for()
    assert page.get_attribute("#ws-undo-status", "role") == "status"
    assert page.get_attribute("#ws-undo-status", "aria-live") == "polite"
    text = page.locator("#ws-undo-status").inner_text()
    assert "nothing to undo" in text.lower(), text
    assert "404" not in text and "Error" not in text, text

    # Nothing to undo is not a failure: the button stays usable.
    assert undo.is_enabled()
