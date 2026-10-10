# 0006 - Acts and surfaces

Date: 2026-10-02

## Status

Proposed. **Act advance is superseded in part (2026-10-09).** ADR 0015
rescopes it to **town states**: an act is no longer a surface the hero
moves to, it is a change to the town alone, and "the current act" is a
derived read (one plus the vault notes read) rather than a stored pointer.
Everything this ADR says about the *event* (`act-completes`) and about
per-act play surfaces is withdrawn rather than built; what survives is the
one identity question below, and ADR 0015's town states answer it by
giving every state of a region that region's own save identity. The
rescope is built in slice E8c of the endless dungeon.

## Context

Two seams showed up in the first independent pack (findings 15):

- **Only `acts[0]` plays.** `cli.weave_html` bakes the first act,
  `world["_current_act"]` is documented as "0 for now", and
  `current_act()` exists but nothing advances it. An act list is
  loaded, validated and echoed - then only the first entry runs.
- **One play surface per game.** `startPlaySurface()` picks one
  screen when the player starts. The cook, the desk and the town
  map are each fine alone; a game cannot open one, then the next.

Both are honest gaps, not bugs: the pack contract already carries
per-act `ruleset`, `floor`, `tone` and `verbs`, so the data shape
for more than one act exists. What does not exist is the advance
and the composition.

## Decision

**Acts advance through journal-marked milestones, and surfaces
compose per act rather than per game.** (Design only - not
implemented by this ADR, and superseded in part as noted above:
ADR 0015 replaces the act pointer with town states, and the hero stays
where they are.)

- A new rule event, `act-completes`, is declared by the pack (a
  rule fires it when the act's goal is met). Firing writes a
  milestone line to the play journal - the same journal the why-log
  and `vefr handbok` already read. No timers, no model, no
  inference: an authored rule decides, the journal records.
  **Withdrawn by ADR 0015:** acts no longer complete.
- The engine derives the current act from the journal: advance on
  the `act-completes` milestone, persist it with the save. The
  journal is the source of truth; `_current_act` becomes a derived
  read, not a hand-set field. **Replaced by ADR 0015:** the act is
  derived from the vault flags, on every read, and stored nowhere.
- The play surface resolves per act: each act's `ruleset` picks its
  screen when that act becomes current. A pack can be the cook in
  act 1, the desk in act 2, and the town in act 3. A pack whose
  acts declare no ruleset behaves as today (engine defaults).
  **Withdrawn by ADR 0015:** the hero stays in one place and the town
  is what changes.

Compatibility story:

- Existing packs are unchanged. A flat pack is one implicit act
  that never completes, so it plays exactly as now.
- The first act behaves exactly as today: same bake, same screen,
  same start. Nothing advances without an authored
  `act-completes` rule, and no shipped pack declares one.
- New fields are optional everywhere; validation of today's shape
  passes untouched.

Hard parts, named now so they are costed later:

- **Bake size.** Baking every act's regions, voices and sprites
  into one shareable HTML file grows the artifact; today only
  `acts[0]` is baked. Staged or lazy act payloads may be needed,
  and that changes `weave`.
- **Save identity.** Storage keys (`vefr-slain-<world>-<region>`,
  bag, gold) are per world, not per act. Act 2 needs its own (or a
  shared, deliberately chosen) identity without orphaning saves
  that exist today. **Answered by ADR 0015:** every state of a region
  shares that region's identity, so a save is never orphaned; a
  dropped item standing on a new state's wall moves to the nearest
  floor tile.
- **The current-act pointer.** It must be persisted, inspectable,
  and consistent between the live app and the woven player - and a
  save reset must reset it too. **Answered by ADR 0015:** there is no
  pointer. The act is derived from the flags on every read.

## Consequences

It costs:

- Real work later in `cli.weave_html`, `main.py`, the player's
  `startPlaySurface()`, save keys, and the validator - each with
  tests, and each touching the pack contract's consumers (ask-first
  per AGENTS.md).
- A migration rule for existing saves, written before any key
  changes.
- Docs to write when it lands: how an act completes, what the
  pointer means, how a surface is chosen.

It does NOT:

- Implement any of this now; this ADR fixes intent only.
- Auto-advance acts: without an authored `act-completes` rule an
  act is forever current, exactly as today.
- Add timers, pressure, or model calls to act transitions - the
  journal decides, offline.
- Change the pack contract today, or change what any shipped or
  independent pack plays.
- Force multi-act structure: one-act packs remain the normal case.
