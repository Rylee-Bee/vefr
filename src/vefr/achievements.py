"""Achievements for using the studio: Ratatoskr's sticker book in the Hall.

Not the games you make: these reward exploring VEFR itself (open a room, paint a
square, finish a book, poke the tree). Definitions live in
web/achievements/achievements.json; each has a painted sticker in
web/art/stickers/<id>.webp.

The page reports small events (`visit`, `room_visit`, `map_paint`, ...) with the
person's local time; this module keeps the tally in data/achievements.json and
says which stickers were just earned. Rules:

  {"count": [event, n]}                    event happened n times
  {"count": [event, n, {"k": "v"}]}        ...with data matching those fields
  {"distinct": [event, field, n]}          n different values of data[field]
  {"distinct": [event, field, n, "k", v]}  ...counting only events where data[k] == v
  {"after": [a, b]}                        b happened after an a
  {"burst": [event, n, seconds]}           n of event within that many seconds
  {"days": n} / {"streak": n}              used on n days / n days in a row
  {"hour": [h1, h2]} (+ "minute": [m1, m2]) any event in that local time window
  {"weekdays": [5, 6]}                     used on each of those weekdays (Mon=0)
  {"earned": n | "half" | "all"}           stickers found (counting all the non-book ones)

Kinds follow the shared album rules (Worlds' sticker album, Play-Nice stickers/0):
open stickers show what they are; riddles show only a riddle until found (and a
riddle with a `whisper` stays hidden until its neighbour is found); secrets show
only as a count. Shine is paper, foil (learning milestones) or holo (deepest).
No streaks, no day-counting, no late-night bait, nothing to lose.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .paths import app_home, data_dir

_lock = threading.Lock()
MAX_KEEP = 200            # distinct values / burst timestamps kept per achievement
SAFE = re.compile(r"^[A-Za-z0-9 ._'’:-]{0,80}$")


def definitions() -> list[dict]:
    path = app_home() / "web" / "achievements" / "achievements.json"
    defs = json.loads(path.read_text(encoding="utf-8"))["achievements"]
    # A rule can be parked until its sticker art is chosen: `"disabled": true`
    # keeps it out of the book, the tally, the album and the art tests until
    # the art exists and the flag is cleared. TODO(T5) rules use this.
    return [d for d in defs if not d.get("disabled")]


def vocabulary(defs: list[dict]) -> set[str]:
    # Events the page may report. Most come from the enabled rules below;
    # these two come from the first walk's play/place loop, so they are
    # accepted even while their stickers wait on art (see definitions()).
    events = {"visit", "play_here", "character_placed"}
    for d in defs:
        r = d["rule"]
        for key in ("count", "distinct", "burst"):
            if key in r:
                events.add(r[key][0])
        if "after" in r:
            events.update(r["after"])
    return events


def _store() -> Path:
    return data_dir() / "achievements.json"


def load() -> dict:
    try:
        s = json.loads(_store().read_text())
        if isinstance(s, dict) and isinstance(s.get("earned"), dict):
            return s
    except (OSError, ValueError):
        pass
    return {"earned": {}, "progress": {}, "seen": {}, "flags": {}, "times": {}, "dates": [], "weekdays": []}


def _save(s: dict) -> None:
    p = _store()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False))
    os.replace(tmp, p)


def _clean(data) -> dict:
    """Only short, plain scalar fields travel with an event."""
    out = {}
    if isinstance(data, dict):
        for k, v in list(data.items())[:8]:
            if isinstance(k, str) and SAFE.match(k) and isinstance(v, (str, int, bool)) and SAFE.match(str(v)):
                out[k] = v
    return out


def _streak(dates: list[str]) -> int:
    days = sorted({date.fromisoformat(d) for d in dates})
    best = run = 0
    prev = None
    for d in days:
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        best, prev = max(best, run), d
    return best


def _matches(want: dict, data: dict) -> bool:
    return all(str(data.get(k)) == str(v) for k, v in want.items())


def record(event: str, data: dict | None = None, local: dict | None = None, *, now: float | None = None) -> dict:
    """Tally one event; return {"earned": [newly earned definitions], "total": n earned}."""
    defs = definitions()
    if event not in vocabulary(defs):
        raise ValueError(f"unknown event {event!r}")
    data = _clean(data)
    local = local if isinstance(local, dict) else {}
    now = time.time() if now is None else now
    with _lock:
        s = load()
        for key in ("progress", "seen", "flags", "times"):
            s.setdefault(key, {})
        today = str(local.get("date") or date.today().isoformat())
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", today) and today not in s["dates"]:
            s["dates"] = (s["dates"] + [today])[-400:]
        wd = local.get("weekday")
        if isinstance(wd, int) and 0 <= wd <= 6 and wd not in s["weekdays"]:
            s["weekdays"].append(wd)
        hour, minute = local.get("hour"), local.get("minute")
        new = []

        def earn(d):
            if d["id"] not in s["earned"]:
                s["earned"][d["id"]] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                new.append(d)

        for d in defs:
            if d["id"] in s["earned"]:
                continue
            r, i = d["rule"], d["id"]
            if "count" in r and r["count"][0] == event:
                if len(r["count"]) < 3 or _matches(r["count"][2], data):
                    s["progress"][i] = s["progress"].get(i, 0) + 1
                    if s["progress"][i] >= r["count"][1]:
                        earn(d)
            elif "distinct" in r and r["distinct"][0] == event:
                ev, field, n, *filt = r["distinct"]
                if field in data and (not filt or str(data.get(filt[0])) == str(filt[1])):
                    seen = s["seen"].setdefault(i, [])
                    if data[field] not in seen:
                        seen.append(data[field])
                        del seen[:-MAX_KEEP]
                    s["progress"][i] = len(seen)
                    if len(seen) >= n:
                        earn(d)
            elif "after" in r:
                a, b = r["after"]
                if event == a:
                    s["flags"][i] = True
                elif event == b and s["flags"].get(i):
                    earn(d)
            elif "burst" in r and r["burst"][0] == event:
                _, n, secs = r["burst"]
                t = [x for x in s["times"].get(i, []) if now - x <= secs] + [now]
                s["times"][i] = t[-MAX_KEEP:]
                if len(t) >= n:
                    earn(d)
            elif "days" in r:
                s["progress"][i] = len(s["dates"])
                if len(s["dates"]) >= r["days"]:
                    earn(d)
            elif "streak" in r:
                s["progress"][i] = _streak(s["dates"])
                if s["progress"][i] >= r["streak"]:
                    earn(d)
            elif "hour" in r and isinstance(hour, int):
                h1, h2 = r["hour"]
                ok = h1 <= hour <= h2
                if ok and "minute" in r:
                    ok = isinstance(minute, int) and r["minute"][0] <= minute <= r["minute"][1]
                if ok:
                    earn(d)
            elif "weekdays" in r:
                s["progress"][i] = sum(w in s["weekdays"] for w in r["weekdays"])
                if all(w in s["weekdays"] for w in r["weekdays"]):
                    earn(d)
        # stickers about the sticker book itself, checked after the rest
        others = [d for d in defs if "earned" not in d["rule"]]
        for d in defs:
            want = d["rule"].get("earned")
            if want is None or d["id"] in s["earned"]:
                continue
            got = sum(o["id"] in s["earned"] for o in others)
            s["progress"][d["id"]] = got
            goal = {"all": len(others), "half": (len(others) + 1) // 2}.get(want, want)
            if got >= goal:
                earn(d)
        _save(s)
        pending = [i for i in s["earned"] if i not in s.get("sent", [])]
    if pending:
        threading.Thread(target=send_to_album, args=(pending,), daemon=True).start()
    return {"earned": new, "total": len(s["earned"])}


# --- Rylee's album in Worlds (Play-Nice stickers/0) --------------------------
# Every sticker found here is also told to Worlds, which keeps one album across the
# owner's apps. VEFR's own record stays the truth: anything not sent yet is retried on
# the next event, repeats are harmless, and nothing waits on Worlds.

def album_post(sticker: str, context: str) -> bool:
    import urllib.request

    base, token = os.environ.get("VEFR_WORLDS_URL", ""), os.environ.get("VEFR_WORLDS_STICKERS_TOKEN", "")
    if not base or not token:
        return False
    body = json.dumps({"app": "vefr", "sticker": sticker, "context": context[:120]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/api/stickers/found", data=body, method="POST",
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=4) as r:
            return 200 <= r.status < 300
    except Exception:  # noqa: BLE001 - Worlds away is normal; the next event retries
        return False


def send_to_album(ids: list[str], post=None) -> list[str]:
    """Tell Worlds about found stickers; returns the ids it accepted (and remembers them)."""
    post = post or album_post
    how = {d["id"]: d["how"] for d in definitions()}
    sent = [i for i in ids if i in how and post(i, how[i].rstrip("."))]
    if sent:
        with _lock:
            s = load()
            s["sent"] = sorted(set(s.get("sent", [])) | set(sent))
            _save(s)
    return sent


def target(rule: dict, defs: list[dict]) -> int | None:
    for key, pos in (("count", 1), ("distinct", 2)):
        if key in rule:
            return rule[key][pos]
    for key in ("days", "streak"):
        if key in rule:
            return rule[key]
    if "weekdays" in rule:
        return len(rule["weekdays"])
    if "earned" in rule:
        n = len([d for d in defs if "earned" not in d["rule"]])
        return {"all": n, "half": (n + 1) // 2}.get(rule["earned"], rule["earned"])
    return None


def visible(d: dict, earned: dict) -> bool:
    """Open stickers always show; riddles once their whisper (if any) is found; secrets only when found."""
    if d["id"] in earned:
        return True
    if d["kind"] == "secret":
        return False
    return not d.get("whisper") or d["whisper"] in earned


def book() -> dict:
    """The sticker book as the page shows it: open ones, riddles as riddles, secrets as a count."""
    defs, s = definitions(), load()
    earned = s["earned"]
    rows, hidden = [], 0
    for d in defs:
        if not visible(d, earned):
            hidden += 1
            continue
        at = earned.get(d["id"])
        riddle = d["kind"] == "riddle" and not at
        goal = target(d["rule"], defs)
        rows.append({
            "id": d["id"], "group": d["group"], "kind": d["kind"], "shine": d["shine"],
            "name": "A riddle" if riddle else d["name"],
            "how": d["riddle"] if riddle else d["how"],
            "earned_at": at,
            "progress": None if riddle or goal is None else [min(s.get("progress", {}).get(d["id"], 0), goal), goal],
        })
    return {"achievements": rows, "earned": len(earned), "total": len(defs), "hidden": hidden}


def room_view() -> dict:
    """VEFR's page for the Worlds album (Play-Nice stickers/0): secrets as a count only."""
    SECTIONS = {"start": "Starting out", "make": "Making things", "learn": "Learning", "comfort": "Comfort",
                "silly": "Just for fun", "secret": "Secrets", "book": "The book itself"}
    out, secrets = [], 0
    for d in definitions():
        if d["kind"] == "secret":
            secrets += 1
            continue
        row = {"id": d["id"], "kind": d["kind"], "shine": d["shine"], "section": SECTIONS.get(d["group"], d["group"]),
               "art": f"art/stickers-{d['id']}.webp"}
        if d["kind"] == "riddle":
            row["riddle"] = d["riddle"]
            if d.get("whisper"):
                row["whisper"] = d["whisper"]
        else:
            row["name"], row["earn"] = d["name"], d["how"]
        out.append(row)
    return {"contract": "stickers/0", "app": "vefr", "page": {"title": "VEFR", "look": "vefr"},
            "stickers": out, "secrets": secrets}
