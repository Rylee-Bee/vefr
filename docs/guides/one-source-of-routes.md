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

## The habit

Any time a session renames or removes an API route, the web layer
is part of the rename - grep `web/` for the old name before
calling it done. The guide-level lesson: a rename is not complete
when the Python side is green; it is complete when nothing
anywhere still says the old name - including the test doubles.
