"""EA cup: can a tiny model be Ratatoskr, the studio's executive assistant?

Ratatoskr doesn't do the work; he walks you to the room whose resident
does, with a short hand-off note so you never repeat yourself, and he says
so when a request isn't the studio's job. 30 plain requests; checks: right
room, note keeps the request's key facts, note short, no invented names.
Rooms and their jobs come from the studio's own "How the studio works" sheet.

    python3 -m bench.story.ea <participant> [...]
"""
import json
import re
import sys
import time
from pathlib import Path

from bench.design.run import ENDPOINTS, _chat
from bench.olympics.participants import PARTICIPANTS
from bench.olympics.runtime import ModelServer
from .cup import ALLOWED, NO_THINK, _invented_names, parse

ROOT = Path(__file__).resolve().parents[2]
ROOMS = {  # id: (name, the studio sheet's own line)
    "desk": ("The Desk", "where the Storyteller works: ask what happens next."),
    "map-room": ("The Map Room", "where the Cartographer keeps the map: sketch new land and save it."),
    "folks": ("The Folks", "where the Keeper of Faces keeps the people: meet someone, or invite a new character."),
    "chronicle": ("The Chronicle", "where Urðr writes down what happened: keep the moments that matter."),
    "hall": ("The Hall", "everything you kept, carried up by Ratatoskr."),
    "vault": ("The Vault", "where the Hoard-Keeper keeps items: draft one, or grow an item's story."),
    "casting": ("The Casting Table", "where the Rune-Carver keeps the runes: cast three when you're stuck."),
    "archives": ("The Archives", "where Skuld keeps the story bible: read what is true."),
    "boiler-room": ("The Boiler Room", "the settings: look, sound, motion and the local model."),
}
# (request, acceptable rooms, key facts the note must keep)
REQUESTS = [
    ("I'm stuck, I don't know what happens after she leaves the town.", {"desk", "casting"}, ["leave", "town"]),
    ("Can you cast some runes for me? I need an idea.", {"casting"}, ["rune"]),
    ("I want to add a new island to the east.", {"map-room"}, ["island", "east"]),
    ("Make a new character, a grumpy blacksmith.", {"folks"}, ["grumpy", "blacksmith"]),
    ("What did we decide about the bell last week?", {"archives", "chronicle"}, ["bell"]),
    ("Write down that the player finally met the keeper.", {"chronicle"}, ["met", "keeper"]),
    ("I need a cursed sword that belonged to someone else.", {"vault"}, ["curse", "sword"]),
    ("The music is too loud.", {"boiler-room"}, ["music"]),
    ("Turn off the animations please.", {"boiler-room"}, ["animation"]),
    ("Where's that picture of the lantern I kept?", {"hall"}, ["lantern"]),
    ("Is it canon that the keeper can't leave the stone?", {"archives"}, ["keeper", "stone"]),
    ("Give the blacksmith a better name.", {"folks"}, ["blacksmith", "name"]),
    ("Draw a path from the well to the threshold.", {"map-room"}, ["path", "well", "threshold"]),
    ("What should the next scene be?", {"desk"}, ["next"]),
    ("I want a potion that makes you forget.", {"vault"}, ["potion", "forget"]),
    ("Show me everything I've made so far.", {"hall"}, []),
    ("Switch the local model to a smaller one.", {"boiler-room"}, ["model", "small"]),
    ("Who is the keeper, exactly?", {"folks", "archives"}, ["keeper"]),
    ("Log that we playtested floor one today.", {"chronicle"}, ["playtest", "floor"]),
    ("Add a hidden room under the tavern.", {"map-room"}, ["hidden", "tavern"]),
    ("Book me a flight to Oslo.", {"none"}, []),
    ("What's the weather tomorrow?", {"none"}, []),
    ("Can you do my taxes?", {"none"}, []),
    ("hmm", {"none"}, []),
    ("The text is hard to read, can it be bigger?", {"boiler-room"}, ["text", "bigger"]),
    ("I have an idea for a villain.", {"folks"}, ["villain"]),
    ("Give the player a lantern at the start.", {"vault"}, ["lantern", "start"]),
    ("I keep writing the same thing, help me get unstuck.", {"casting", "desk"}, ["stuck"]),
    ("What are the rules of this world again?", {"archives"}, ["rule"]),
    ("Tell the storyteller to make the ending sadder.", {"desk"}, ["ending", "sad"]),
]
# the studio's own proper names: rooms, residents (from the sheet above and app.js's household)
STUDIO_NAMES = set(re.findall(r"[A-Z][a-zð]+", " ".join(n + " " + d for n, d in ROOMS.values()))) | {
    "Storyteller", "Cartographer", "Keeper", "Faces", "Urðr", "Skuld", "Hoard", "Rune", "Carver", "Ratatoskr", "Oslo"}
VOICE = (Path(__file__).resolve().parent / "ratatoskr.md").read_text()
MODES = ("plain", "template", "voice")
FMT = 'Reply with only JSON: {"room": "<room id or none>", "note": "<hand-off note for that room>", "say": "<what you say to the author>"}'


def prompts(mode, req):
    ids = ", ".join(list(ROOMS) + ["none"])
    if mode == "plain":
        return [{"role": "system", "content": f"You route requests in a game studio app. Rooms: {ids}."},
                {"role": "user", "content": f'Request: "{req}" {FMT}'}]
    rooms = "\n".join(f"- {k}: {n}, {d}" for k, (n, d) in ROOMS.items())
    if mode == "voice":  # the same job, in the author's own voice notes for him
        return [{"role": "system", "content":
                 VOICE + "\n\nYour job: you never do the work yourself. You take the author to the room whose resident "
                 "does it, with a short note so they never repeat themselves.\n\nRooms:\n" + rooms +
                 "\n- none: not the studio's job, or unclear. Joke, then offer something you can do.\n\n"
                 "The note: one plain sentence for the resident, keeping every specific the author gave. Never add details "
                 "they didn't give. 'say': one short line to the author, in your voice."},
                {"role": "user", "content": f'The author says: "{req}" {FMT}'}]
    return [{"role": "system", "content":
             "You are Ratatoskr, the squirrel who runs the studio's errands up and down the tree. You never do the work "
             "yourself: you take the author to the room whose resident does it, with a short note so they never repeat "
             "themselves.\n\nRooms:\n" + rooms + "\n- none: not the studio's job, or unclear. Say so kindly, or ask one short question.\n\n"
             "The note: one sentence for the resident, keeping every specific the author gave (names, places, things). "
             "Never add details they didn't give. 'say': one short, warm sentence to the author."},
            {"role": "user", "content": f'The author says: "{req}" {FMT}'}]


def check(out, case):
    if not isinstance(out, dict):
        return {"format": False}
    room, note = str(out.get("room", "")).strip().lower(), str(out.get("note", "")).strip()
    low = note.lower()
    return {
        "format": room in ROOMS or room == "none",
        "right_room": room in case[1],
        "keeps_facts": case[1] == {"none"} or all(re.search(r"\b" + f, low) for f in case[2]),
        "note_short": len(note.split()) <= 40,
        "no_invented_names": not _invented_names(note + " " + str(out.get("say", "")), ALLOWED | STUDIO_NAMES),
    }


def run(participants):
    rid = time.strftime("%Y%m%dT%H%M%S")
    out_root = ROOT / "bench" / "runs" / "ea" / rid
    out_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for key in participants:
        server = None
        if key.startswith("endpoint:"):
            url, model, api_key = ENDPOINTS[key.split(":", 1)[1]]()
        else:
            server = ModelServer(PARTICIPANTS[key])
            try:
                server.start(wait_timeout=420)
            except Exception as e:  # a model that won't load is a result, not a crash
                print(f"{key:<26} did not start: {str(e)[:120]}", flush=True)
                server.stop()
                continue
            url, model, api_key = server.url + "/v1", PARTICIPANTS[key].alias, None
        try:
            for mode in MODES:
                for i, case in enumerate(REQUESTS):
                    try:
                        text, secs, _ = _chat(url, model, api_key, prompts(mode, case[0]), max_tokens=300, extra=NO_THINK)
                    except Exception:
                        text, secs = "", None
                    out = parse(text)
                    c = check(out, case)
                    rows.append({"participant": key, "mode": mode, "case": i, "request": case[0], "output": out,
                                 "raw": text[:400], "checks": c, "score": sum(c.values()), "of": 5, "seconds": secs})
                sub = [r for r in rows if r["participant"] == key and r["mode"] == mode]
                secs = sorted(r["seconds"] or 0 for r in sub)
                print(f"{key:<26} {mode:<9} right room {sum(bool(r['checks'].get('right_room')) for r in sub)}/30  "
                      f"all checks {sum(r['score'] == r['of'] for r in sub)}/30  median {secs[15]}s", flush=True)
        finally:
            if server:
                server.stop()
        (out_root / "results.json").write_text(json.dumps(rows, indent=1))
    return out_root


if __name__ == "__main__":
    print("evidence:", run(sys.argv[1:]))
