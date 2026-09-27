"""The studio as a person uses it, in a real browser (no model needed)."""
from .steps import ask_resident, fake_reply, fake_teach, open_book, open_studio

CARD = {"term": "sanctuary", "stage": "first", "plain": "A safe square where nothing can hurt you.",
        "why": "Safe places let players breathe.", "context": "the tavern", "local": "safe squares"}


def test_tour_off_hides_the_first_walk_only_when_asked(page, studio):
    open_studio(page, studio, "library", tour=True)
    assert page.locator(".walk-rail").count() == 1
    open_studio(page, studio, "library")
    assert page.locator(".walk-rail").count() == 0


def test_library_shelves_and_tap_a_word(page, studio):
    open_studio(page, studio, "library")
    titles = page.locator(".lib-shelf__title").all_inner_texts()
    assert "How games are made" in titles and "How VEFR works" in titles
    open_book(page, "How Maps Work")
    page.locator(".lib-term").first.click()
    card = page.locator(".lib-term-card")
    assert card.is_visible() and "One square of a map." in card.inner_text()


def test_library_fits_a_phone(phone, studio):
    open_studio(phone, studio, "library")
    open_book(phone, "How Maps Work")
    assert not phone.evaluate("document.documentElement.scrollWidth > innerWidth")


def test_frodi_holds_up_a_note_after_the_reply(page, studio):
    fake_reply(page, "A tavern it is.")
    calls = fake_teach(page, CARD)
    got_it = []
    page.route("**/api/teach/got-it", lambda r: (got_it.append(r.request.post_data_json),
                                                 r.fulfill(status=200, body="{}")))
    open_studio(page, studio, "map")
    ask_resident(page, "Ask the Cartographer", "The tavern should be a safe place.")
    note = page.locator(".paddle-note")
    note.wait_for()
    assert calls and calls[0]["message"] == "The tavern should be a safe place."
    text = note.inner_text()
    assert "Sanctuary" in text and "In VEFR: safe squares." in text and "Here: the tavern." in text
    page.get_by_role("button", name="Why designers use this").click()
    assert page.locator(".paddle-note__why").is_visible()
    page.get_by_role("button", name="Got it").click()
    assert note.count() == 0 and got_it == [{"term": "sanctuary"}]


def test_just_plain_words_means_no_note_and_no_check(page, studio):
    fake_reply(page, "A tavern it is.")
    calls = fake_teach(page, CARD)
    open_studio(page, studio, "map")
    page.evaluate("window.VEFR_PREFS.set({teach: 'off'})")
    ask_resident(page, "Ask the Cartographer", "The tavern should be a safe place.")
    page.locator(".folio__msg--resident", has_text="A tavern it is.").wait_for()
    page.wait_for_timeout(500)
    assert calls == [] and page.locator(".paddle-note").count() == 0


ROOMS = ["launcher", "floor", "workshop", "map", "characters", "items", "library",
         "journal", "runes", "evidence", "hall", "settings"]


def test_every_room_opens_without_a_script_error(page, studio):
    """The safety net for moving code around: each room renders, and nothing throws."""
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text
            and errors.append(m.text))
    open_studio(page, studio, "launcher")
    for room in ROOMS:
        page.evaluate(f"location.hash = '#{room}'")
        page.wait_for_timeout(700)
        screen = page.locator(f"#screen-{room}")
        assert screen.count() == 1 and screen.is_visible(), f"{room} didn't render"
        assert len(screen.inner_text().strip()) > 20, f"{room} rendered empty"
    assert errors == [], errors
