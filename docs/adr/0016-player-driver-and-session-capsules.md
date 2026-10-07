# 0016 - Player Driver, session capsules and replayable play

Date: 2026-10-06

## Status

**Proposed.** Becomes Accepted when the first Player Driver slice lands with tests proving existing keyboard/touch play is unchanged.

Tracks [#317](https://github.com/Rylee-Bee/vefr/issues/317).

## Decision

Rylee and Sol developed this direction together in chat on 2026-10-06.

VEFR will grow one game-neutral **Player Driver** seam and two portable data shapes:

- a **Session Capsule** for captured VEFR-owned persistent state;
- an **Action Tape** for logical player actions from a known start.

Scenarios, Pass the Controller, replay, autoplay, debugging, UAT and agent play are consumers of those primitives, not separate runtimes.

## Why

Cottage Release 1 already produced the evidence:

- deep visual QA required a 1,651-keypress playthrough;
- `vefr look` cannot start in a chosen deep state (#260);
- the pack-specific bot re-derived route information VEFR already knows;
- the bot reads multiple ad-hoc globals instead of one stable player-facing observation;
- a creator currently has to describe a real play route from memory if she wants an agent to reproduce it.

The same missing seam causes all five problems.

Research: `docs/research/player-driver-session-capsules.md`.

Plan: `docs/plans/player-driver/PLAN.md`.

## The contract

### Player Driver

The driver has one job:

> accept a legal logical player action and expose the player-visible result.

Keyboard and touch remain normal first-class inputs. They decode into the same logical actions that replay and agents use.

The first driver contract has the conceptual operations:

- `observe()` — player-visible observation only;
- `actions()` — the legal logical action vocabulary/capabilities in the current state;
- `act(action)` — submit one logical player action and receive accepted/refused plus a bounded result.

The implementation may combine `observe` and `actions` if that is smaller. The concept is the constraint, not these exact JavaScript names.

### Session Capsule

A capsule is a strict, versioned snapshot of **VEFR-owned** persistent state plus enough identity to decide whether the run can be reproduced.

It is not:

- a raw `localStorage` dump;
- a browser profile;
- a DOM snapshot;
- a screenshot/video bundle;
- an agent transcript.

The first serialization is ordinary inspectable JSON. A friendly file extension is optional presentation, not a new binary format.

Import is strict by default. Unsupported schema/build/generator identity is a clear refusal, not a best-effort guess.

### Action Tape

A tape records **logical actions**, for example:

- move north;
- interact;
- open bag;
- equip an item;
- choose a visible conversation/interaction option.

It may carry optional physical-source evidence (`keyboard ArrowUp`, `touch dpad north`) so a UAT fidelity replay can exercise the original binding.

It may carry sparse checkpoint digests so a replay can stop at the first proven divergence.

It does not store a full save or DOM snapshot after every action.

### Scenario

A scenario is an authored test/demo starting state validated against a pack.

A scenario is not a captured player session.

This ADR generalizes #260: `vefr look --at` may be a convenience, but the durable capability is "start from a validated scenario/capsule".

## Authority

The existing brain-socket rule remains unchanged:

> VEFR owns reality. Brains interpret and propose actions; they do not define truth.

An autoplay/model player receives the same **player-visible observation** boundary a human is entitled to.

Full internal inspection is a separate explicit debug/UAT capability. It is never silently added to ordinary autoplay.

The driver does not expose a "set state" or "teleport" operation to ordinary play.

## Input fidelity

There are two legitimate replay paths:

1. **Semantic replay**: feed the recorded logical action to the Player Driver. This is the stable, input-device-independent replay.
2. **Fidelity UAT**: use recorded input-source metadata to press/tap the actual control in a real browser, then verify that it produces the same logical action/checkpoint.

The first proves game behavior. The second also proves the binding/surface.

Both converge on the same logical action path.

## Persistence boundary

`web/player/parts/065-store.js` remains the single browser-storage seam.

Session capture reads a whitelist/registry of VEFR-owned save state. It never walks every browser storage key.

A blocked-storage browser remains playable under today's graceful-degradation rule; capture may truthfully be unavailable.

## Security and privacy

A capsule/tape may contain player-authored game text in future games. Treat exported artifacts as user content.

Do not include:

- credentials;
- unrelated origin storage;
- provider configuration;
- model/API secrets;
- absolute local paths;
- hidden browser data.

No network service is part of this ADR.

## Compatibility

The first implementation prefers refusal over migration.

A capsule carries:

- session schema version;
- world/pack identity;
- world/build fingerprint;
- engine compatibility identity;
- generator/version cards needed by generated content.

If VEFR cannot prove it can load the artifact faithfully, it says so.

## Accessibility

Pass-the-Controller/replay UI, when built, must obey the existing player accessibility contract:

- keyboard operable;
- 44 px targets;
- text state, not color-only state;
- reduced motion respected;
- replay has pause/stop and never forces continuous motion.

The core artifact/driver work is useful before the UI exists.

## What does not belong here

- a cloud save service;
- accounts;
- multiplayer synchronization;
- model selection/prompting;
- a second persistence engine;
- Playwright trace as the canonical save/replay format;
- a generic agent framework.

## Consequences

### Good

- a human play session can become reproducible QA evidence;
- the same run can be watched, continued or debugged;
- pack-specific bots can shrink over time;
- agents can play without direct save mutation or omniscience;
- UAT can compare browser-real input with logical game actions;
- deep-state tests stop paying the full 1,651-keypress setup cost unless the journey itself is what is under test.

### Cost

- VEFR must finally name one stable player-facing observation/action seam;
- exported state needs explicit version/compatibility rules;
- replay divergence has to be reported honestly;
- hidden/player-visible state boundaries must be reviewed whenever observation grows.

## Acceptance boundary

This ADR becomes Accepted with P1, not with the entire feature.

P1 must prove:

1. keyboard and touch still produce the same behavior;
2. their behavior converges through one logical action dispatcher;
3. a test driver can submit those same logical actions;
4. the observation contains only player-visible state;
5. a pack with no new feature declaration is unchanged.

Capsules/tapes remain later slices of the accepted direction.
