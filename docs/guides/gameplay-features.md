# Gameplay features

VEFR uses one small vocabulary at three levels.

```text
GAME
characters · maps · art · story · one-off rules
        ↓
GAMEPLAY FEATURES
reusable ways to play
        ↓
VEFR CORE
things · places · state · rules · input · UI · audio · saves
```

## The words

| Where | Say | Meaning |
|---|---|---|
| Studio UI and Library books | **gameplay feature** | a reusable way to play |
| Creator / engineering docs | **gameplay feature (gameplay system / mechanic)** | the same concept, with the common industry words beside it |
| Code | use the narrow domain name | `equipment`, `rules`, `delve`, not a new generic framework |

Do not use **bundle** for this. In VEFR, a bundle is the one-file game you send
to someone. Do not teach **module** as the creator word either; it already meant
a Studio room in older VEFR material and is too broad to explain the idea.

## What goes where

| Put it in | Ask | Examples |
|---|---|---|
| **game** | Does only this game or chapter need it? | story, characters, maps, art, a one-off boss rule |
| **gameplay feature** | Could unrelated games reuse this way of playing? | dialogue, turns, detection, scoring, cards, timers |
| **VEFR core** | Is this small machinery that several games or gameplay features need underneath? | things, places, state, rules, input, UI, audio, saves |

The examples name the boundary, not a promised feature list. Some current VEFR
capabilities already resemble gameplay features; this decision does not move
files or create a loader.

## Promotion rule

### Game -> gameplay feature

Keep a mechanic in the game until a **second real game** independently needs the
same behavior and invariants.

Then promote the smallest reusable shape only when all of these are true:

1. it uses VEFR's public creator/runtime surface instead of private engine hooks;
2. it contains no game names, canon or special cases;
3. a game that does not use it behaves exactly as before;
4. its public surface is smaller than the implementation it replaces;
5. validation, tests and a small example cover the contract;
6. the normal repo gate is clean and the change adds no warnings.

### Gameplay feature -> core

Move something into core only when multiple real uses need the same primitive
and extracting it either removes duplicated facts or makes an invariant
enforceable. "This would be convenient someday" is not evidence.

This is the existing second-consumer rule applied to gameplay.

## Compose before you grow core

A different-feeling chapter does not require a different engine.

Examples of the intended thinking:

```text
stealth      = detection + state + consequence
photography  = targeting + detection + scoring
driving      = movement + lanes + hazards + scoring
fishing      = timing + input window + scoring
```

These are examples, not approved VEFR APIs. The rule is: try existing pieces
first, add one reusable gameplay feature second, change core last.

## The overnight loop

Independent games are tests of the creator surface.

For each overnight "idea to playable game" run, record only:

- **complete?** did a playable game ship;
- **game work** what was content or game-specific code;
- **feature work** what reusable gameplay capability was missing;
- **core work** what fundamental VEFR primitive was missing;
- **friction** workaround, unclear docs or repeated error.

One odd request stays in its game. The same friction in unrelated games is
evidence.

### A working "done enough" signal

Use ten consecutive independent overnight runs as a rolling window:

- at least **8/10** finish as complete playable games;
- at least **7/10** need **no VEFR core change**;
- the same creator-surface failure does not keep recurring unresolved.

At that point proactive engine design should mostly stop. Games pull the next
change from VEFR instead.

## Engineering bar

Gameplay features do **not** earn a second language.

- one creator vocabulary;
- one deterministic build path;
- schemas and validation at boundaries;
- useful errors, not tolerated warning noise;
- tests for the public behavior;
- accessible player surfaces;
- game-specific data stays out of the engine;
- no plugin loader, marketplace or new runtime until real evidence earns one.

See [ADR 0012](../adr/0012-gameplay-features.md) for the decision and industry
references.
