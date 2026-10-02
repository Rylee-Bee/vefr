# Rules — when this happens, do that

One rule is one sentence a person can read aloud:

> **When** the hero comes near the keeper, **if** the hero has the
> key, **then** take the key and say "You found it."

Rules live in `world.json` (top level, beside `flags`, `claims` and
`people`). They are data, not code: no loops, no numbers, no
priorities - rules run in the order written, and the world's answer
is always the same. The design note behind them is
`design/rules-when-then.md`; this page is the contract.

```json
{
  "id": "the-stone-hums",
  "when": {"comes-near": {"who": "the stone", "distance": 0}},
  "if":   [{"flag": "lit", "is": false}],
  "then": [{"set": "lit"}, {"say": "The stone hums."}],
  "once": true
}
```

## The eleven events

Each fires from something the player already does. A pack may name
at most **40 rules** (see `docs/adr/0004-scoped-rules.md` for why).

| `when` | Means | Fires from |
|---|---|---|
| `{"starts": {}}` | the game begins | the Begin button |
| `{"enters": {"place": "X"}}` | the hero arrives in a region | crossing into it |
| `{"comes-near": {"who": "X", "distance": 0}}` | the hero is within N tiles of X (0 = standing on it) | Talk; walking onto a named place |
| `{"opens": {"what": "X"}}` | a chest or door is used | Interact on it |
| `{"picks-up": {"what": "X"}}` | the player takes an item | a floor drop, a chest's contents, a purchase |
| `{"uses-with": {"item": "X", "with": "Y"}}` | a carried item is used at a named place | Use in the bag |
| `{"defeats": {"what": "X"}}` | an enemy falls | the hit that ends it |
| `{"buys": {"what": "X"}}` | the player buys an item | the shop's Buy |
| `{"sells": {"what": "X"}}` | the player sells an item | the shop's Sell |
| `{"reads": {"what": "X"}}` | a book is closed having been read | the reader's Close |
| `{"phase-changes": {"to": "X"}}` | the watch turns to a phase | the Dusk/Dawn buttons (Menu > Display) |

## One identity model

A rule may name only what the pack declares - and everything the
pack declares is nameable:

| Kind | Where it is declared | Used for |
|---|---|---|
| item ids | `world.json` `items` | `has`, `give`, `takes`, `picks-up`… |
| speaker keys | the act's `speakers` | `who`, `say`'s voice |
| region names | the act's `regions` | `enters`, `point-to`, a door's `opens` |
| **POI labels** | the region contract's `pois` | `comes-near`, `uses-with` — the label *is* the id |
| **book ids** | `library/<id>.md` file names | `opens` (a chest), `reads` |
| **enemy ids** | the region contract's `enemies` | `defeats` |
| phase names | `world.json` `phases` | `phase-changes` |
| flags / claims | `world.json` `flags` / `claims` | `set`, `believes`… |

The validator names anything else. There is no need to register a
fake item for a landmark: the place's own label is its id.

## Conditions (`if`) and actions (`then`)

Conditions (all must pass): `{"has": "<item>"}`,
`{"flag": "<f>", "is": true|false}`,
`{"believes"|"not-believes": {"who", "claim"}}`,
`{"is-in": {"who", "place"}}`, `{"not": …}`, `{"all-of": [ … ]}`.

Actions: `say` (a narrator string, or `{"who", "line"}`),
`show` / `hide` / `reveal` (a thing on the floor),
`give` / **`takes`** (add / remove a carried item),
`set` / `unset` (a flag), `believes` / `stops-believing` / `tells`
(beliefs), `weather` (`"fog"` / `"clear"`), `point-to` (a direction
that is kept in the **Where next?** panel).

One rule fires at most once (`"once": true`, the default). In the
default `reset` mode that holds only until a reload: the fired markers
are forgotten, so a `once` rule may fire again. With `saves.rules` set
to `persist` the marker survives a reload and the rule fires at most
once per save. No rule ever triggers another: a `give` is not a
`picks-up`. That is the whole discipline - the world notices, remembers,
and changes in small understandable ways.

## Saves

A pack chooses how much of a run its rules remember, with an optional
top-level `saves` block in `world.json`:

```json
{ "saves": { "rules": "persist", "legacy": "from-log" } }
```

- `saves.rules` is `persist` or `reset`. The default is `reset`, today's
  behavior: each load starts the rules fresh, and no save key is read or
  written. `persist` keeps flags, fired markers, beliefs and the engine's
  items across a reload, and Start over clears them.
- `saves.legacy` chooses what a persist pack does with saves made before
  it opted in. `fresh` (the default) starts the rule state empty, so a
  `once` rule may repeat one time. `from-log` marks as fired the rules
  the **Why did that happen?** log proves fired; the log keeps only the
  last 20 entries, so older firings may still repeat once. It never marks
  a rule fired that did not fire.
- `starts` fires once per save in persist mode, and again after Start
  over. In reset mode it fires on every load, as today.

## Items: usable is not consumable

| Field | Means |
|---|---|
| `use` | a verb for the Bag's Use button ("drink", "turn") |
| `heal` | using restores health (and spends the copy) |
| `light` | using lights the dark (and spends the copy) |
| **`keep: true`** | using never spends it - a quest tool, a lantern |

A bare `use` with no `heal` and no `light` is a persistent tool: the
button appears, `uses-with` fires, nothing is spent.

## Why did that happen?

Every fired rule leaves one plain sentence in the player's menu
(**Why did that happen?**), and `point-to` hints are kept under
**Where next?**. Both are real records of what ran - nothing is
inferred. They are the first place to look when a rule does not do
what the sentence says.
