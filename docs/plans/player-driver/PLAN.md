# Player Driver campaign

Owner: Rylee  
Co-design: Rylee + Sol, 2026-10-06  
Epic: [#317](https://github.com/Rylee-Bee/vefr/issues/317)  
ADR: [0016](../../adr/0016-player-driver-and-session-capsules.md)  
Research: [player-driver-session-capsules.md](../../research/player-driver-session-capsules.md)

## Goal

Make a real player run portable and reproducible without adding a second runtime.

A person, deterministic bot, UAT runner or model-backed player should be able to operate the same logical player actions, while VEFR remains the only authority that changes world state.

## Non-goals

- online multiplayer;
- cloud saves/accounts;
- an agent framework;
- a new database;
- a model requirement;
- direct save mutation by autoplay;
- replacing Playwright/browser evidence;
- solving save migration in the first version.

## Shape

```text
                         ┌─ human keyboard/touch
                         ├─ replay tape
scenario/capsule ───────>├─ deterministic autoplay
                         ├─ model-backed player
                         └─ UAT fidelity runner
                                   │
                                   v
                         logical Player Driver
                                   │
                                   v
                           VEFR validates/applies
                                   │
                                   v
                                world
```

Browser UAT remains a wrapper around that loop, not part of the game authority.

## Slice P0 - design

**This PR.**

Deliver:

- research record;
- ADR 0016;
- this implementation plan;
- durable epic #317;
- companion uat-harness design issue/PR.

No runtime behavior changes.

## Slice P1 - one logical player action seam

### Purpose

Stop keyboard, touch and tests from each being their own way into game behavior.

### Work

1. Inventory every player action currently produced by keyboard/touch/UI.
2. Name the smallest closed logical action vocabulary that can express current play.
3. Add one dispatcher below physical input decoding.
4. Route existing keyboard/touch controls through it without changing behavior.
5. Add a bounded player-visible observation facade.
6. Add a test-only/documented driver entry point using the same dispatcher.

Do not expose a state setter.

### Candidate action families

Only add actions current play needs. Likely families:

- move/turn;
- interact/confirm/cancel;
- menu open/close;
- panel selection;
- item/equipment operation;
- conversation/choice when a game actually has one.

The implementation decides exact names after inventory. Do not design unused future verbs.

### Proof

- existing browser/player tests unchanged;
- keyboard and touch tests assert the logical action observed;
- direct test-driver action reaches the same resulting state;
- observation excludes a fixture's known hidden fact/undiscovered region;
- no model/runtime dependency.

### Gate

VEFR full gate + browser gate because this changes the player input path.

## Slice P2 - scenarios and strict session capsules

### Scenario

Add a validated authored scenario shape that can express the existing Release-1 need:

- region/position;
- player stats/growth;
- bag/equipment/currency;
- flags/rule state;
- album/record/library state;
- generated-run identity/deltas when applicable.

Reuse current save keys/shapes rather than inventing parallel state.

A scenario lives with a pack and is dev/test data.

### Capsule

Add capture/import of normalized VEFR-owned persistence.

Requirements:

- ordinary JSON schema/version;
- pack/build/engine/generator identity;
- storage whitelist, never origin-wide enumeration;
- deterministic ordering for stable hashing/diffs;
- clear strict-compatibility refusal;
- round-trip test: capture -> fresh browser -> import -> same normalized digest.

### CLI/tooling

Prefer extending existing `vefr look` / `vefr probe` / developer tooling over adding a second tool family.

The exact verbs are chosen after inspecting those implementations in the slice.

### Proof

- #260's deep-start use case works from a scenario;
- generated-floor state round-trips;
- a foreign origin key planted beside VEFR keys is not exported;
- an incompatible build is refused;
- blocked browser storage leaves ordinary play alive and reports capture unavailable.

## Slice P3 - action tape and replay

### Record

Record logical actions after input decoding.

Each entry has:

- sequence number;
- logical action;
- optional physical source metadata;
- optional relative timing metadata for observation/debug only.

Do not put timing into world semantics.

### Checkpoint

Record bounded checkpoint digests at useful boundaries:

- region change;
- save-worthy progression;
- configurable every N logical actions for debug runs.

A checkpoint is a digest + small summary, not a full browser snapshot.

### Replay

Replay from a known scenario/capsule.

Features:

- play;
- pause;
- step;
- stop;
- take control.

On divergence:

- stop at the first proven mismatched checkpoint;
- report expected/actual summary;
- do not continue and produce misleading downstream noise unless an explicit diagnostic mode asks for it.

### Proof

- record a real keyboard route;
- replay semantically in a fresh context;
- final/checkpoint digests match;
- pause and manual continuation work;
- a deliberately changed fixture reports the first divergence.

## Slice P4 - autoplay and UAT consumers

### Deterministic autoplay first

Add strategies outside world authority:

- route/critical-path driver where a route exists;
- explorer;
- bounded random/fuzz driver.

They consume `observe/actions/act`.

A strategy cannot call internal save setters.

### Model adapter second

A model adapter receives only the player-visible observation and legal action schema.

The model proposes one action. VEFR accepts/refuses it through the same driver.

Debug omniscience is a separately named test mode.

### UAT fidelity

The VEFR UAT runner may:

1. load a scenario/capsule;
2. read a tape;
3. use the tape's optional physical source to press/tap a real control in Chromium;
4. verify the logical action/checkpoint;
5. write the capsule/tape/divergence report under the normal UAT output directory.

Playwright screenshots/video/trace remain external evidence.

No uat-harness game logic.

### Proof

- the same tape succeeds via semantic replay and at least one browser-real input replay;
- desktop and phone runs produce useful artifacts;
- reduced-motion run stays usable;
- model adapter is unable to see a seeded hidden fact in ordinary mode.

## Slice P5 - matrix and player-facing polish

Only after the primitives prove useful.

Candidate matrix axes:

- viewport;
- keyboard/touch;
- reduced motion;
- seed set;
- reload checkpoint;
- save policy;
- strategy.

Player-facing affordances:

- **Pass the Controller**;
- **Watch this run**;
- pause/step/take over;
- **Save for someone else**.

A self-contained woven HTML with an embedded capsule is optional convenience work. The small JSON artifact remains the primitive.

## Artifact budgets

Set measured limits before finalizing P2/P3. Initial design target:

- capsule: proportional to current save state, not game assets;
- tape: O(number of actions), compact logical records;
- checkpoints: sparse and bounded;
- no screenshots/video/DOM in either portable format.

If size is a real problem, measure first. Do not preemptively invent compression/container machinery.

## Cross-repo boundary

### Cottage

Cottage is the first proving game because its existing bot and 1,651-keypress deep route supply concrete acceptance cases.

Cottage supplies pack/scenario/tape fixtures only. Engine machinery stays in VEFR.

### uat-harness

uat-harness remains the generic browser evidence collector.

For the first implementation, VEFR writes its extra artifacts under the normal UAT output directory. `ci-harness` already uploads that directory, so no CI API change is required.

Only add a generic uat-harness adapter after a second domain proves it needs the same shape.

## Contracts

| Contract | P0 | Later expectation |
| --- | --- | --- |
| Accessibility | N/A docs only | PASS for replay/share UI and browser runs |
| Human reliability | PASS: explicit refusal/UNKNOWN rules | PASS |
| Security/privacy | PASS: artifact boundaries specified | PASS with canary tests |
| World authority | PASS: no direct model/save mutation | PASS |
| Pack neutrality | PASS | PASS |
| Runtime recovery | N/A | PASS for capture/import/replay interruption |
| Asset provenance | N/A | N/A |

## Stop conditions

Stop and return to Rylee if a slice requires any of these to make the basic use case work:

- a server;
- a database;
- raw browser-profile export;
- model-specific state in the capsule;
- full event sourcing of the world;
- a second input/action engine beside the current player;
- exposing hidden world truth to ordinary autoplay.

Those mean the slice has grown past the problem.
