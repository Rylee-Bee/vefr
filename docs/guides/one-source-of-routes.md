# One source of truth for routes

Why the Stefna tab 404'd while every test stayed green - and the
guard that closes the whole class.

## The incident

The rename pass moved `/api/bell` to `/api/stefna` on the server.
The web layer was never told:

- the server served `/api/stefna`
- `web/index.html` still POSTed `/api/bell`
- the DOM harness's fetch stub happily answered `/api/bell`

Result: 121 tests green, harness green, and the live dev UI's
letter tab returning 404 on every strike. The bug sat in mainline
until a human clicked the tab.

## The gap

The same route name was written by hand in three places, in two
languages, with nothing checking them against each other. Renames
passed every gate because the harness - the thing that *looks*
like it exercises the UI's HTTP - faked the stale URL instead of
refusing it.

A stub that answers a route the server no longer serves is not a
stub, it is a false witness.

## The rule

The server's route table is the only list of routes. Everything
else derives from it, or gets tested against it.

## The guard (shipped)

`tests/test_web_routes.py` scans every `/api/...` string literal in
`web/*.js` and `web/index.html`, and asserts each one is a path
FastAPI actually serves (`app.routes`). A renamed route now fails
the suite the moment the web layer is not updated with it.

What it catches:

- renames that missed the web layer
- typos in fetch URLs
- fetches of routes that no longer exist

What it cannot catch (known limits, stated honestly):

- URLs assembled at runtime from pieces - `'/api/' + target +
  '/undo'` appears in source only as the bare prefix `/api/`. The
  harness-level fix (derive the stub routes from the server's
  table instead of hand-writing them) is the follow-up that covers
  those; it is in ROADMAP, not yet built.

## The route inventory (regenerated from `app.routes`, 2026-09-01)

42 routes. This table is derived from the server's route table, not
maintained by hand where it can be derived - the drift below happened
once already.

| Verb | Path | Description |
|---|---|---|
| GET | /api/builder/aspects | Aspect inspector: live pack state |
| POST | /api/builder/chat | Chat with builder AI |
| POST | /api/builder/enhance/item | Contextual AI enhance: item |
| POST | /api/builder/enhance/map | Contextual AI enhance: map/POI |
| POST | /api/builder/enhance/voice | Contextual AI enhance: voice |
| POST | /api/builder/import | Import / clone pack into worlds |
| POST | /api/builder/lore | Generate lore mood text |
| POST | /api/builder/lore/list | List available lore packs |
| GET | /api/builder/resolved | Resolved raw pack payload |
| POST | /api/builder/validate | Offline pack validation |
| POST | /api/builder/verify | Live endpoint verification |
| GET | /api/builder/worlds | List discovered world packs |
| POST | /api/combat/action | Execute combat surface action |
| GET | /api/export | Export full playthrough markdown |
| GET | /api/export/tabs | List available exportable tabs |
| GET | /api/export/tabs/{name} | Export single tab markdown |
| POST | /api/forge | Generate and roll an item |
| POST | /api/handoff | AI-buddy debugging handoff bundle |
| GET | /api/health | Health probe (ok + purpose) |
| GET | /api/journal | Read session journal entries |
| POST | /api/journal/clear | Clear session journal |
| POST | /api/journal/fork | Fork journal state |
| POST | /api/journal/move | Journal one town arrival (no model call) |
| POST | /api/journal/remove/{index} | Remove a journal entry |
| POST | /api/journal/rewind | Rewind journal state |
| POST | /api/journal/rewind/undo | Undo journal rewind |
| POST | /api/journal/star/{index} | Star a journal entry |
| POST | /api/journal/undo | Undo journal entry removal |
| POST | /api/npc | Generate a speaker whisper line |
| POST | /api/rumor | Generate a rumor for current phase |
| GET | /api/runes | Full rune registry |
| GET | /api/runes/cast | Seeded rune cast for current minute |
| GET | /api/starred | Read starred favorite lines (no POST - starring is `/api/journal/star/{index}` or `/api/vault/star/{index}`) |
| POST | /api/stefna | Generate sealed bell letter |
| GET | /api/trace | Live model call trace events |
| GET / POST | /api/vault | Read / persist kept items |
| POST | /api/vault/remove/{index} | Drop a kept vault item (undoable 60s) |
| POST | /api/vault/star/{index} | Star a kept vault item |
| POST | /api/vault/undo | Restore the last removed vault item |
| GET | /api/weave | Live loader weave event log |
| GET | /api/wiki | World knowledge summary (characters, relics) |
| GET | /api/world | Active world pack state (geometry, phases, speakers) |

## The habit

Any time a session renames or removes an API route, the web layer
is part of the rename - grep `web/` for the old name before
calling it done. The guide-level lesson: a rename is not complete
when the Python side is green; it is complete when nothing
anywhere still says the old name - including the test doubles.
