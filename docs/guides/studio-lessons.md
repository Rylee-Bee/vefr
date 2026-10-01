# Studio lessons

What making a real game by hand taught us, and where each lesson belongs
in the studio. Every workaround here is a feature the studio still owes
the next person. Add to it as you go; newest first.

## 2026-10-01: the night the helpers fell over

Two `offload` helper crews were building vefr in parallel, and both crashed:
their run summaries were 0 bytes and their worker agents were orphaned (parent
PID 1). A third crew finished on its own. The unlanded work lived only in
throwaway clones under `~/worktrees/offload/`, which `offload clean` deletes.

What saved it, and what to do again:

- **A throwaway clone is not a home.** Land or copy the commits out before
  anything cleans up. `offload clean` removes worker clones; a branch in the
  real repo does not.
- **Recover by content, not by trust.** Each clone's branch was fetched into the
  real repo and compared against `main`; only the unlanded work was kept
  (`recovered/vefr-*`), kept as safety refs, and the stale clones were deleted
  (41 directories, about 10 GB).
- **The parallel design worked.** Both crews were told to keep changes in new
  functions plus a few call sites; `web/packaged.html` auto-merged and only two
  files needed a hand (`ROADMAP.md`, `src/vefr/maplab.py`).
- **CI caught what review would have missed.** CodeQL failed the rules PR with
  two high "uncontrolled data used in path expression" alerts; the fix is the
  repo's own guard, `os.path.realpath` plus `startswith(base + sep)`.
- **The honest failure is the useful part.** The interact crew's own report said
  it changed no test to fit code, and that 3 of 6 workers failed (two
  provider-rejected, one timeout); its two unfinished tasks were finished by
  hand rather than pretending they shipped.
- **A stale line is a bug.** The pause menu's "How to play" still said "Talk
  with E, Space" after `E` became Interact; it is fixed.

Landed that evening: the rules engine (a world can react when something
happens) and one-button Interact (one key does what fits, plus Start over).
The shorter, player-facing version is on the studio's own shelf, as the book
*The Night the Helpers Fell Over* (`web/library/26-the-night-the-helpers-fell-over.md`).

## 2026-09-30: the engine grew by being used

A long stretch of building the engine *through* the game. What it taught.

- **The north star (owner, 2026-09-30): anyone can make their own game, their
  own way - and it is documented and taught.** Every choice below answers to it.
- **Delegation needs review, and the review earns its keep.** Two builds from a
  cheap worker looked finished and were not: the schema-to-grammar converter
  emitted *optional* commas (so the grammar could produce invalid JSON) and
  sent its constraint alongside the one it was meant to replace (so it could
  break a backend that already worked). Reading the diff caught both. The
  worker is fast; the review is the craft.
- **Small, interactive decisions beat a plan dump.** One question at a time
  (2-3 options) kept the owner in the loop and caught course corrections a
  single big plan would have missed.
- **A test can catch a coupling you forgot.** Adding one book to a shelf broke
  the "whole shelf" achievement count; the test said so before a player could.
  Add a book - check the achievement.
- **Document the contract where it lives.** `world.py` carries the pack
  contract, `docs/uat/` carries "what good means", `docs/guides/` carries the
  how-to. A capability with no home has no documentation.
- **Name the honest silence.** The woven player says plainly when it has
  nothing to say; the grammar work turned that silence into a last-resort
  voice rather than a bug.

## 2026-09-29: building Act 1 through the studio

Made with the studio for the first time: accepted the Cartographer's commission,
drew the town in the Map Room, and let the engine write it. Four things it
taught us.

- **The shipped file lagged the studio - three times.** The Map Room drew
  picture tiles while the woven player drew flat colour; then the studio drew
  a figure for each speaker and the woven player drew none; then sprites.
  Each time, the room that made a thing could draw more than the file that
  shipped it.
  *In the studio:* one renderer shared by the room that makes a thing and the
  file that ships it, so the two cannot drift. Until then, every new drawing
  feature lands in both players in the same change.
- **Saving a map ate the maker's own settings.** The write path rebuilt
  `world.json` from a fixed list of fields, so the game's `player` block (its
  title picture and accent colour) vanished the first time a map was saved -
  and the studio reported success.
  *In the studio:* a writer owns only the fields it models; every other key is
  the maker's and must survive a save. Now guarded by `tests/test_write_pack.py`
  (every shipped pack written back, its keys checked) on top of the one-field
  regression in `test_map_build.py`.
- **A rule the room can't satisfy is a trap.** The first map commission asked
  for a named landmark (`pois`), but no builder route can *set* a `pois` entry -
  the Map Room only paints the grid - so the job could never be finished in the
  studio. Caught before merge, but the next module will meet it too.
  *In the studio:* a module's done-rule may only read what its own room can
  write. The landmark became a square the Map Room can paint.
- **A backup beside a pack file dirties the pack.** The map build keeps
  `<file>.bak-<time>` beside the map, inside a git repo that never expected it.
  *In the studio:* either the engine keeps its backups where packs already
  ignore them, or every pack needs the pattern (`*.bak-*`).

## 2026-09-26 (evening): pictures

- **One reference set can't serve thirteen worlds.** Painting every genre with the same few reference
  pictures pulled them all toward our wood floor and rune pebble (a cyberpunk street painted as
  floorboards). *In the studio:* each theme gets its own **anchors**, a ground and a wall painted from
  words first; everything else in that theme uses those as references. Consistent within a theme,
  still in one family through a written style guide.
- **A reference is the strongest instruction.** "Match only the style" doesn't stop a model copying the
  reference's objects and clothes; choose references that share nothing but the style.
- **Keep the house style; offer others.** VEFR's own look stays storybook; other styles (pixel, flat,
  watercolour, woodcut, low-poly) are options for other people's games, each with its own anchors and
  add-on, never mixed in.
- **Know where training art came from.** Every picture keeps its prompt and references beside it, so a
  training set can be built from art we're free to train on (and never from outputs whose terms forbid it).
- **A big local painter can follow one example.** FLUX.2-klein on a 16 GB GPU painted a new tile on our
  own floorboards from one reference in 10 seconds: good for the studio's "Refine", and as a teacher
  for the small painter.

## 2026-09-26: the first game, day one

Made by hand with Rylee: the brief, a title picture, a colour, stickers,
a town character, Ratatoskr's voice. Then a live walkthrough of the
studio found what got in the way.

### What made it fun and easy

- **One question at a time, in the author's own words.** Filling the brief
  ("the game in two sentences", the verb, the feel) worked as a gentle
  interview, not a form: one question, a short reflection back, then save
  their exact words. The author said it was the structure they'd been
  missing.
  *In the studio:* an **Interview** template the residents run (the Desk
  for the brief, the Folks for a character): one question per turn, the
  author's words kept verbatim, a recap to approve before anything is
  saved.
- **Pick from three, then nudge.** Every picture landed through rounds:
  three options, then "2 but at night like 3", "only exactly one tunnel",
  "a complete redraw". Nobody wrote a prompt.
  *In the studio:* every picture module offers three, then **Keep /
  Refine / Redo**, with the refine box taking plain words ("at night",
  "fewer rooms") and "Redo" meaning a fresh drawing, not an edit.
- **Show choices where they'll live.** The accent colour was chosen from
  four real title screens, not four swatches.
  *In the studio:* previews in place (the button, the title, the room),
  never a bare colour chip or a file name.
- **Nothing goes to waste.** "Don't you waste that scroll": the options
  not picked became spare stickers.
  *In the studio:* a **spare parts shelf** in the Hall for unpicked
  options, so a no is never a loss.
- **Ideas are not decisions.** Hidden rooms and a teleport hard mode were
  noted as ideas, in the author's words, separate from what's decided.
  *In the studio:* the Archives keep two lists, **Decided** and **Ideas**,
  and a resident never promotes an idea on its own.
- **Celebrate the gates.** The brief being done, the title picture, the
  colour: each got a moment (a gold stop on the status page).
  *In the studio:* passing a stage gate (the handbook's greenlight)
  earns a milestone sticker in the Hall.
- **Confirm with pictures when a pick is ambiguous.** "2" could mean two
  different pictures; a one-tap question with both shown settled it.
  *In the studio:* when a reply could mean two things, show both and ask,
  never guess.

### What got in the way

- **A switch that said yes and did nothing.** Choosing a world on the page
  was overridden by a server setting, yet reported success, so every room
  kept showing the old world. Fixed (#62): the studio now says what pins it.
  *Lesson:* never report success the engine didn't deliver.
- **History bled between worlds.** One shared journal meant Emberfield's
  whispers showed up in Cottage and "keep" wrote into the shared pile.
  Fixed (#63): each world keeps its own.
  *Lesson:* everything a person makes is scoped to the world they're in.
- **Template leftovers felt like someone else's game.** A new world
  started with Emberfield's tagline, map and keeper, and they read as
  real content.
  *In the studio:* **Begin a new world** starts blank, with gentle
  "yours to write" placeholders, not another world's words.
- **Slow answers without a reason.** The assistant took 10 to 30 seconds
  while its machine was busy with benchmarks.
  *In the studio:* when a model is slow, say why ("the brain is busy,
  about 20 seconds"), and offer the no-model path.
- **Examples get copied.** Given whole example lines, models stitched them
  together; given an empty starter page, a tiny model handed it back.
  *In the templates:* give the author's **words** and rules, not finished
  lines to imitate, and check outputs (the design and story cups do).

### Ideas from the author, for the studio's shape

- Each room's assistant has **only that room's tools and templates**, and
  can "send you down the hall" to another room.
- **Ratatoskr as the executive assistant**: routes, carries a hand-off
  note, keeps the agenda; cocky, frantic, flexible, never mean, fond of
  acorns, in love with stories.
- Story help as **Keep / Refine / Redo** in the UI, keeping what you keep
  in the pack's structure; a writer's-block breaker that nudges (a
  question, a word from your word-hoard, a next beat) and never writes
  for you.
- Characters chat freely but **inside game rules**: one legal action per
  turn, enforced by the game.
- **The release is made in VEFR.** Hand-made work is draft and template;
  the shipped game comes out of the studio.
