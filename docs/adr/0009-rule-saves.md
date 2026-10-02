# 0009 - Rule saves

Date: 2026-10-02

## Status

Proposed. Becomes Accepted when the player work (plan PR 2) merges. Decisions below were made by Rylee on 2026-10-02; the plan is `docs/plans/durable-rule-saves-plan.md`.

## Context

The player saves only the WHY log (`vefr-rules-<world>`). The rules engine's flags, fired markers, beliefs and items live in memory, so a reload makes a `once` rule fire again and a set flag read off. Games on this engine want different things: a roguelike wants a fresh run every time; a story game with gates and guardians needs the world to remember.

## Decision

A pack chooses, in an optional top-level `saves` block of `world.json`:

```json
"saves": { "rules": "persist" | "reset", "legacy": "fresh" | "from-log" }
```

- **`rules`**: `reset` (the default, and when the block or key is absent) is today's behavior exactly: no new storage key is read or written. `persist` keeps all four mutable engine parts (flags, fired markers, beliefs, items) across a reload and clears them on Start over.
- **`legacy`** (persist mode, saves made before the pack opted in): `fresh` (the default) starts rule state empty, so a `once` rule may repeat one time. `from-log` marks as fired the rules the WHY log proves fired; the log keeps only the last 20 entries, so older firings may still repeat once. It never marks a rule fired that did not fire.
- **`starts`** fires once per save in persist mode, and again after Start over. In reset mode it fires on every load, as today.

Storage: `vefr-rulestate-<world>`, value `{ "v": 1, "flags", "fired", "beliefs", "items" }`. Load drops anything the current bake does not know (removed flags, rules, people, claims, items) and never throws. An unreadable value gives a fresh state. A save with `v` greater than 1 gives a fresh state and is never overwritten. Every storage access is wrapped; a failed write is silent.

The pure engine block is unchanged. Load and save sit around `rulesStateNow` and `fireRule` in the player. Derived values are never stored.

## Why a block, not a flat field

Rylee wants many games on this engine, so save policy is a game's choice, like `growth`'s `levels` or `practice`. A block leaves room for later save settings without more top-level keys.

## Consequences

Packs without `saves` are unchanged. Persist mode adds one storage key per world. `docs/guides/rules.md` must say in which mode "one rule fires at most once" holds across a reload.

## Known gap, not part of this decision

When `window.localStorage` itself throws on access (a sandboxed iframe), today's player raises an uncaught error during Begin and `starts` never fires. That is a separate fix; the test is recorded as a strict xfail with that reason.
