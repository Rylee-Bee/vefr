"""Reusable steps for browser tests, in the words a person would use."""
import json


def open_studio(page, base, room="", *, tour=False):
    """Open a room (library, map, ...). The first-walk tour is off unless asked for."""
    page.goto(f"{base}/{'' if tour else '?tour=off'}#{room}")
    page.wait_for_load_state("networkidle")


def open_book(page, title):
    page.get_by_role("button", name=title).click()
    page.locator(".lib-page").wait_for()


def fake_reply(page, text):
    """Answer the builder chat without a model."""
    page.route("**/api/builder/chat", lambda r: r.fulfill(
        status=200, content_type="application/json", body=json.dumps({"reply": text})))


def fake_teach(page, card):
    """Make Fróði's recognizer return this card (or None); returns the list of calls."""
    calls = []

    def handle(route):
        calls.append(route.request.post_data_json)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"teach": card, "why_not": "" if card else "none"}))
    page.route("**/api/teach/recognize", handle)
    return calls


def ask_resident(page, button_name, text):
    """Open a resident's folio with its Ask button, type, and send."""
    page.get_by_role("button", name=button_name).first.click()
    box = page.get_by_role("dialog", name="Ask a resident").locator("#folio-input")
    box.fill(text)
    box.press("Enter")
