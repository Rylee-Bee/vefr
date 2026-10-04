# 0011 - Gameplay features: one vocabulary, three layers

Date: 2026-10-04

## Status

Accepted. Rylee chose the learner-facing name **gameplay feature** on
2026-10-04 while refining how VEFR should grow from independent games.

This ADR is a vocabulary and architecture boundary. It does **not** authorize a
plugin loader, package manager, new runtime, new DSL, broad pack migration or a
new public pack contract.

## Context

Cottage of the Breeze proved that VEFR can carry a substantial polished game,
then exposed authoring and contract friction to tighten. Lanternwake, built as an
independent consumer without engine edits, exposed different seams. The next
planned experiment repeats that pressure with rotating models making complete,
unrelated games overnight.

The repository already has the second-consumer rule: extract shared machinery
only when two actual consumers independently need the same operation and
invariants. The language-architecture decision also explicitly rejected a plugin
system without that evidence.

We need plain words that learners can understand without creating a second
technical vocabulary.

## Decision

VEFR has three logical layers:

```text
game
  ↓
gameplay feature
  ↓
VEFR core
```

- **Game** owns characters, maps, story, art and game-specific rules.
- **Gameplay feature** is the learner-facing term for a reusable way to play.
  In engineering prose, **gameplay system** and **game mechanic** are acceptable
  clarifiers for the same idea.
- **VEFR core** owns the small common machinery used underneath many games and
  gameplay features: things, places, state, rules, input, presentation, audio,
  saves and similar primitives.

The layers share one public VEFR vocabulary. A gameplay feature is not a new
authoring language and does not bypass the normal validator, build or player.

### Promotion

1. A need starts in the game.
2. After a second real, unrelated game needs the same behavior and invariants,
   the smallest reusable shape may become a gameplay feature.
3. A primitive moves into core only when several real uses need it and the move
   removes duplicated facts or makes an invariant enforceable.

A gameplay feature must be optional, game-neutral, documented, validated where
it accepts data, tested through public behavior and clean under the normal repo
gate. Absence must preserve existing behavior.

### Names we are not using

- **bundle** stays the one-file game produced for sharing;
- **module** stays a generic code word / older Studio-room word, not the learner
  term for gameplay;
- **plugin** implies loading and lifecycle machinery VEFR has not earned.

## Why this shape

The goal is not to collect genre engines. It is to make a small set of reusable
ways to play compose over one stable core. A stealth chapter, for example, may
be a composition of detection, state and consequence rather than a new
"stealth engine".

This preserves a small creator vocabulary while allowing implementation
complexity to stay behind tested public surfaces.

## Industry check (2026-10-04)

This decision borrows established vocabulary and the composition principle
without copying larger engines' machinery:

- Epic's Unreal Engine documentation calls standalone activatable capabilities
  **Game Features**, and says modular features help keep projects readable and
  reduce accidental dependencies:
  https://dev.epicgames.com/documentation/unreal-engine/game-features-and-modular-gameplay-in-unreal-engine
- Epic groups high-level mechanics, behaviors and conditions under
  **Gameplay Systems**:
  https://dev.epicgames.com/documentation/unreal-engine/gameplay-systems-in-unreal-engine
- Godot teaches that small nodes with different jobs can be combined into more
  complex behavior, and that composed scenes can become reusable building
  blocks:
  https://docs.godotengine.org/en/stable/getting_started/step_by_step/nodes_and_scenes.html
- Unity uses **packages** as containers for features/assets and **feature sets**
  as collections of packages. VEFR deliberately does not use "package" or
  "bundle" for this concept because those words already describe packaging
  jobs in VEFR:
  https://docs.unity3d.com/Manual/Packages.html

## Consequences

- UI and Library teaching use **gameplay feature** first.
- Engineering docs may add "gameplay system" or "mechanic" in parentheses.
- No generic gameplay-feature framework is built by this ADR.
- Existing systems do not need to be reorganized merely to match the diagram.
- Independent games and Burrito Journalism provide the evidence for future
  promotion.
- Repeated engine work across unrelated games is a signal to improve VEFR;
  one unusual game's request is not.

The creator guide is [Gameplay features](../guides/gameplay-features.md).
