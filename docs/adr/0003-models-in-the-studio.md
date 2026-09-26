# Models help in the studio; games are finished artifacts

Date: 2026-09-26
Decided by: Rylee (owner)

## Decision

**Language models work in the studio. A shared game is a finished
artifact, like a book.**

- In the studio, the residents use models to help make the game:
  drafting, sketching, suggesting. They work inside templates and
  structure, so each next time is easier, and the author approves what
  they draft before it becomes part of the game.
- A woven game plays completely without a model. Its rules and numbers
  are fixed, and its lines were written or approved in the studio, then
  baked into the file.
- **By default a game offers no model at all**: Begin goes straight into
  the game, and nothing asks about models. A model is heavy, and most
  players won't have one.
- **A game may opt in** with `"player": {"model": "optional"}` in
  `world.json`. Its pause menu then offers Model settings, so a player
  who runs their own model can switch on fresh lines. The game still
  never asks up front and still plays fully without one.

## Why

- Everyone gets the same, complete game, offline, forever.
- Local models answer in 13–35 seconds (ADR 0002's benchmark); that
  suits drafting in the studio, not a turn-based game waiting on every
  step.
- Fixed rules keep games fair and bugs reproducible.

## Consequences

- The woven player no longer shows a setup screen on first run.
- `ratatoskr weave --pool N` (generating lines at build time, in the
  studio) is how model-written lines reach a game.
- New rulesets (the Delve first) keep every rule and number in the
  engine; models never decide outcomes.
