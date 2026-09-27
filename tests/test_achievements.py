"""Ratatoskr's sticker book: achievements for using the studio."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vefr import achievements as A

WEB = Path(__file__).resolve().parents[1] / "web"
DEFS = A.definitions()


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "_store", lambda: tmp_path / "achievements.json")


def ids(out):
    return {d["id"] for d in out["earned"]}


def test_the_book_follows_the_album_rules():
    """Shared album rules (Worlds sticker album): ~40% open, ~30% riddles, ~30% secrets;
    no streaks or day-counting; no late-night bait; riddles have a riddle."""
    assert len(DEFS) >= 60 and len({d["id"] for d in DEFS}) == len(DEFS)
    share = {k: sum(d["kind"] == k for d in DEFS) / len(DEFS) for k in ("open", "riddle", "secret")}
    assert 0.35 <= share["open"] <= 0.5 and 0.25 <= share["riddle"] <= 0.35 and 0.25 <= share["secret"] <= 0.35, share
    known = {d["id"] for d in DEFS}
    for d in DEFS:
        assert d["id"].isascii() and d["name"] and d["how"] and d["sticker"], d["id"]
        assert d["kind"] in {"open", "riddle", "secret"} and d["shine"] in {"paper", "foil", "holo"}, d["id"]
        assert not {"streak", "days", "weekdays"} & set(d["rule"]), f"{d['id']}: no streaks or day-counting"
        r = d["rule"]
        filt = r["count"][2] if "count" in r and len(r["count"]) > 2 else {}
        hour = r["hour"][0] if "hour" in r else filt.get("hour")
        if hour is not None:
            assert 5 <= hour <= 22, f"{d['id']}: no late-night bait"
        if d["kind"] == "riddle":
            assert d.get("riddle"), d["id"]
        if d.get("whisper"):
            assert d["whisper"] in known, d["id"]


def test_every_sticker_has_art():
    missing = [d["id"] for d in DEFS if not (WEB / "art" / "stickers" / f"{d['id']}.webp").is_file()]
    assert not missing, missing


def test_shelf_goals_match_the_shelves():
    """'Whole Shelf' must mean every book on that shelf, even when books are added."""
    books = list((WEB / "library").glob("[0-9]*.md"))
    for d in DEFS:
        r = d["rule"].get("distinct")
        if r and r[0] == "book_finish":
            shelf = r[4]
            n = sum(f"shelf: {shelf}" in b.read_text() for b in books)
            assert r[2] == n, f"{d['id']} wants {r[2]} books but {shelf} has {n}"


def test_counting_and_a_first_sticker():
    assert ids(A.record("visit")) == {"hello-studio"}
    assert ids(A.record("visit")) == set()          # never earned twice


def test_filters_distinct_and_progress():
    for room in ["map", "library", "hall"]:
        A.record("room_visit", {"room": room})
    A.record("room_visit", {"room": "map"})
    tour = next(r for r in A.book()["achievements"] if r["id"] == "grand-tour")
    assert tour["progress"] == [3, 12] and tour["earned_at"] is None
    assert ids(A.record("setting_change", {"key": "workings", "value": "simple"})) == {"knob-twiddler"}
    assert ids(A.record("setting_change", {"key": "workings", "value": "show"})) == {"behind-the-curtain"}


def test_after_burst_and_gentle_hours():
    assert "broke-it-fixed-it" not in ids(A.record("map_check_ok"))
    A.record("map_check_fail")
    assert "broke-it-fixed-it" in ids(A.record("map_check_ok"))
    got = set()
    for k in range(5):
        got |= ids(A.record("room_visit", {"room": f"r{k}"}, now=1000 + k))
    assert "speedrunner" in got
    assert "sunrise" in ids(A.record("visit", local={"hour": 6, "minute": 10}))
    assert "noon-bell" in ids(A.record("bell", {"hour": 12}))


def test_secrets_riddles_and_whispers():
    book = A.book()
    assert "old-magic" not in {r["id"] for r in book["achievements"]} and book["hidden"] > 0
    A.record("konami")
    row = next(r for r in A.book()["achievements"] if r["id"] == "old-magic")
    assert row["name"] == "Old Magic" and row["earned_at"] and row["kind"] == "secret"
    riddle = next(r for r in A.book()["achievements"] if r["id"] == "island-maker")
    assert riddle["name"] == "A riddle" and "quiet place" in riddle["how"] and riddle["progress"] is None
    assert "got-it" not in {r["id"] for r in A.book()["achievements"]}      # whispers after its neighbour
    A.record("teach_note", {"term": "gating", "stage": "first"})
    assert "got-it" in {r["id"] for r in A.book()["achievements"]}


def test_the_worlds_album_view():
    view = A.room_view()
    assert view["contract"] == "stickers/0" and view["app"] == "vefr" and view["secrets"] == sum(
        d["kind"] == "secret" for d in DEFS)
    assert all(v["kind"] != "secret" for v in view["stickers"])
    assert "Old Magic" not in json.dumps(view)
    rid = next(v for v in view["stickers"] if v["id"] == "island-maker")
    assert "name" not in rid and rid["riddle"] and rid["section"] == "Making things"


def test_unknown_events_and_odd_data_are_refused():
    with pytest.raises(ValueError):
        A.record("delete_everything")
    A.record("room_visit", {"room": "<script>", "x" * 90: 1, "ok": "map"})
    seen = json.loads((A._store()).read_text())["seen"].get("grand-tour", [])
    assert "<script>" not in seen


def test_routes():
    from vefr.main import app
    c = TestClient(app)
    r = c.post("/api/achievements/event", json={"event": "bell", "local": {"hour": 10}})
    assert r.status_code == 200 and [e["id"] for e in r.json()["earned"]] == ["ding"]
    assert c.post("/api/achievements/event", json={"event": "nope"}).status_code == 422
    book = c.get("/api/achievements").json()
    assert book["earned"] == 1 and book["total"] == len(DEFS)


def test_every_group_has_a_place_in_the_hall():
    """A group the Hall doesn't list is silently never shown (the 'comfort' group was, once)."""
    import re
    hall = (WEB / "js" / "rooms" / "hall.js").read_text()
    shown = set(re.findall(r"\['([a-z]+)', '[^']+'\]", hall[hall.index("STICKER_GROUPS"):]))
    assert {d["group"] for d in DEFS} <= shown, {d["group"] for d in DEFS} - shown


def test_found_stickers_go_to_the_worlds_album_and_retry(monkeypatch):
    posted = []
    ok = {"up": False}

    def fake(sticker, context):
        posted.append((sticker, context))
        return ok["up"]
    monkeypatch.setattr(A, "album_post", fake)
    monkeypatch.setattr(A.threading, "Thread", lambda target, args, daemon: type(
        "T", (), {"start": lambda self: target(*args)})())
    A.record("bell")                                      # Worlds away: nothing marked sent
    assert ("ding", "Ring for the Storyteller") in posted
    assert "ding" not in json.loads(A._store().read_text()).get("sent", [])
    ok["up"] = True
    posted.clear()
    A.record("light_toggle")                              # next event retries the backlog
    assert {p[0] for p in posted} == {"ding", "day-and-night"}
    assert set(json.loads(A._store().read_text())["sent"]) == {"ding", "day-and-night"}


def test_no_key_means_no_album_call(monkeypatch):
    monkeypatch.delenv("VEFR_WORLDS_STICKERS_TOKEN", raising=False)
    assert A.album_post("ding", "x") is False
