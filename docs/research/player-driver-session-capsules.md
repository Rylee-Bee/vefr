# Player Driver and portable session capsules

Status: research for [#317](https://github.com/Rylee-Bee/vefr/issues/317)  
Date: 2026-10-06  
Origin: Rylee and Sol worked this through together in chat, starting from "Pass me the controller" and widening it only where the same primitive solved an observed testing problem.

## Question

Can VEFR let a player hand a real play session to another person or agent, replay how someone played, turn a human run into a regression test, and support autoplay/UAT without growing a second runtime?

## Short answer

Yes, if VEFR builds one small player-driving seam and keeps the artifacts boring.

The proposal is:

- one **Player Driver**: legal logical action in, player-visible observation out;
- one **Session Capsule**: a strict snapshot of VEFR-owned persistent state plus exact build identity;
- one **Action Tape**: ordered logical player actions with optional input-source metadata and bounded checkpoints.

Scenarios, replay, Pass the Controller, autoplay, debugging and agent play become different consumers of those three things.

Do not build separate "AI play", "UAT play", "shared save" and "debug replay" systems.

## Existing VEFR evidence

### Release 1 already found the missing seams

`docs/research/cottage-release-1-learnings.md` records two relevant findings:

1. **Scenarios: start the game in any state.** Reaching the King's room required a 1,651-keypress bot run because `vefr look` could not start deep in the game.
2. **A route through the pack, and one stable play-state API.** The Cottage bot had to reconstruct the region graph and read a collection of ad-hoc globals.

Issue #260 is the narrow symptom: `vefr look` cannot begin in a selected region.

The current Cottage bot is valuable proof, but it is pack-specific machinery. It reads `VEFR_COMBAT`, `VEFR_REGIONS` and other globals, then presses ordinary keys. The engine-side descent bot already demonstrates the right testing principle: a scripted player reaches generated floors through the same pad/Interact path a person uses.

### Persistence is already centralized enough

`web/player/parts/065-store.js` is now the one player storage wrapper. That makes capture practical without rewriting persistence first.

The capsule must **not** enumerate arbitrary browser storage. It should export a whitelist of VEFR-owned persistent state, normalized into a versioned shape.

### Random floors make reproducibility more important

The endless-dungeon work now has play-time generation, run seeds, generated-floor deltas and generator versioning. A useful session artifact therefore needs enough identity to answer:

> "Can this exact run be reproduced with this engine/game/generator?"

A seed alone is not a save. A save without build identity is not a reliable reproduction artifact.

## External patterns

### Chrome DevTools Recorder: portable flows are useful bug evidence

Chrome Recorder records user flows, can export them as JSON, import them, replay them, step them, and explicitly describes exported flows as useful for bug reporting.

Source: Chrome for Developers, "Recorder features reference"  
https://developer.chrome.com/docs/devtools/recorder/reference/  
Accessed 2026-10-06.

**Lesson for VEFR:** a small portable sequence of user actions is a proven debugging primitive. VEFR should record game-meaningful actions instead of DOM selectors.

### Playwright: trace is excellent evidence, not the game contract

Playwright Trace Viewer preserves actions, before/action/after DOM snapshots, screenshots, logs and network detail. Playwright codegen can record real browser interactions into tests.

Sources:

- https://playwright.dev/docs/trace-viewer
- https://playwright.dev/docs/codegen

Accessed 2026-10-06.

**Lesson for VEFR:** keep Playwright trace/video as browser evidence around a run. Do not use a Playwright trace as the portable game session format: it is browser-specific, larger, and speaks in browser operations rather than VEFR actions.

### Unity Input System: separate logical actions from physical controls

Unity documents `InputAction` as an abstraction for logical concepts such as "jump" rather than physical inputs such as a space-bar press. Its Input System also supports recording, persisting and replaying input event traces.

Sources:

- https://docs.unity3d.com/Packages/com.unity.inputsystem@1.4/api/UnityEngine.InputSystem.InputAction.html
- https://docs.unity3d.com/Packages/com.unity.inputsystem@1.4/api/UnityEngine.InputSystem.LowLevel.InputEventTrace.ReplayController.html

Accessed 2026-10-06.

**Lesson for VEFR:** the durable tape should prefer logical actions (`move north`, `interact`, `equip X`) while optionally remembering which physical input produced them. Keyboard, touch and replay should converge after input decoding.

### Gymnasium: a small action/observation boundary scales to agents

Gymnasium's environment contract is deliberately small: an agent supplies an action and receives the next observation plus outcome metadata.

Source: Gymnasium `Env` API  
https://gymnasium.farama.org/api/env/  
Accessed 2026-10-06.

**Lesson for VEFR:** an agent does not need direct access to saves or internal mutation. It needs a bounded observation and a legal action surface.

## Refined model

### 1. Scenario

An authored development/test starting state.

- checked into a game repo when useful;
- validated against the pack;
- names intentional setup, not player history;
- may be used by `vefr look`, tests and demos.

Example purpose:

> "level 8, bell key, floor 5, album half full"

This is the generalized form of #260.

### 2. Session Capsule

A captured real session state.

The first format should be ordinary JSON, even if its filename later uses a friendly extension such as `.vefrplay`.

Minimum envelope:

```json
{
  "schema": "vefr/session-v1",
  "world": {
    "id": "pack-id",
    "build": "content fingerprint",
    "engine": "engine revision or compatible build id"
  },
  "created_at": "ISO-8601",
  "state": {}
}
```

The state is normalized VEFR-owned persistence, not a raw `localStorage` dump.

It may include private/internal state required to resume truthfully. That does **not** mean an autoplay brain gets to see it.

Default import behavior is strict:

- exact schema understood;
- compatible world/build identity;
- compatible generator cards for generated content;
- otherwise refuse in a plain sentence.

Automatic migration is future work.

### 3. Action Tape

A bounded sequence of logical player intents from a known start.

Example:

```json
{
  "schema": "vefr/tape-v1",
  "start": {"capsule": "sha256:..."},
  "actions": [
    {"n": 1, "do": "move", "dir": "north", "via": {"kind": "keyboard", "key": "ArrowUp"}},
    {"n": 2, "do": "interact", "via": {"kind": "keyboard", "key": "e"}},
    {"n": 3, "do": "equip", "item": "ring"}
  ],
  "checkpoints": [
    {"after": 3, "digest": "sha256:..."}
  ]
}
```

Rules:

- logical action is authoritative;
- physical-source metadata is optional evidence;
- timings are optional and not part of world semantics;
- checkpoints are bounded, not one full save per turn;
- no screenshots or art are embedded.

The tape can remain tiny while Playwright/UAT separately keeps screenshots/video/trace when desired.

### 4. Player Driver

The Player Driver is the seam all inputs converge on.

Conceptually:

```text
keyboard ─┐
touch ────┤
replay ───┼──> logical player action ──> VEFR validates/applies ──> world
agent ────┤
UAT ──────┘
```

A first public-in-the-player shape can be small:

```text
observe() -> player-visible observation
actions() -> legal logical actions/capabilities
act(action) -> accepted/refused + resulting observation summary
```

The exact JavaScript name is an implementation detail for slice P1.

### Player-visible observation vs debug inspection

This distinction is required.

**Ordinary player/agent mode** exposes only what the player may legitimately know:

- current location and visible geometry;
- visible entities;
- carried/equipped items;
- player stats shown by the game;
- current UI/overlay state;
- journal/record facts the player has earned;
- currently legal interactions.

It must not expose sealed character knowledge, undiscovered rooms, hidden rules, future generated floors or other omniscient state.

**Debug/UAT inspection** is explicit and separate. It may read internal state for assertions and divergence reports, but it is not what the autoplay strategy sees unless the caller deliberately chooses debug mode.

This preserves the brain-socket rule: more intelligence does not grant more authority.

## What this unlocks

### Pass the Controller

Export capsule; another person imports it; they continue; they export the updated capsule.

No server or account is required.

### Watch, pause, take over

Replay a tape from its start capsule. Pause on any action and continue manually.

### "Use my last run"

A creator can hand an agent the actual session artifact rather than narrating remembered steps.

The agent can inspect the allowed observation stream or replay the tape and see where the run diverges.

### Human run -> regression fixture

A useful real session can be promoted deliberately into a checked-in scenario+tape fixture.

This is better than rewriting the route from memory.

### Debug matrix

One runner may vary conditions around the same start/tape:

- desktop / phone;
- keyboard / touch;
- reduced motion on/off;
- original seed / bounded seed sweep;
- reload at named checkpoints;
- fresh vs persisted rule-save modes.

The matrix is runner configuration, not part of the session format.

### Autoplay

Autoplay is a strategy over the driver, not engine authority.

Possible strategies:

- critical-path runner;
- explorer;
- bounded random/fuzz player;
- model-backed player.

All receive the same legal action surface. No strategy edits saves directly.

## UAT boundary

VEFR owns game semantics, session capture, logical actions and replay.

`uat-harness` owns browser-real evidence:

- Chromium contexts;
- real keyboard/touch fidelity runs;
- screenshots/video;
- Playwright trace;
- console/network evidence;
- axe checks;
- redaction/finalization.

For the first slice, no new generic UAT API is required. A VEFR-owned UAT command can place its capsule/tape/divergence artifacts under the normal UAT output directory, and the existing `ci-harness` reusable UAT workflow already uploads that directory.

A generic adapter should wait for a second non-VEFR consumer.

## Size budget

The feature stays small by refusing to capture the wrong things.

Capsule contains:

- normalized persistent state;
- compact fog bitsets / generated-floor deltas already used by the player;
- build identity.

Tape contains:

- logical actions;
- sparse checkpoints/digests;
- optional input-source metadata.

Neither contains:

- game art;
- HTML;
- browser profile;
- DOM snapshots;
- video;
- model transcripts.

A self-contained woven HTML with an embedded capsule can be a later convenience export, not the primitive.

## Failure and honesty rules

- If a capsule does not match a compatible build, say so.
- If a replay diverges, stop at the first proven divergence and report expected/actual checkpoint facts.
- If a tape uses an action the current player does not support, refuse that action; do not guess.
- If debug inspection is unavailable, report UNKNOWN rather than silently giving autoplay omniscience.
- If storage is blocked, ordinary play continues under the existing graceful-degradation rule; capture says unavailable.

## Recommendation

**GO, in slices, with the Player Driver as the root primitive.**

Do not begin with sharing UI or model autoplay.

Build in this order:

1. one logical action seam and player-visible observation;
2. scenarios + strict session capture/import;
3. logical tape record/replay + checkpoint digests;
4. UAT/autoplay consumers;
5. optional sharing polish and self-contained embedded sessions.

That order turns existing QA pain into the proof of the player-facing feature instead of building a speculative sharing system first.
