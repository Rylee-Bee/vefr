# Rules: "when this happens, do that"

Status: **proposed**. Decisions by Rylee on 2026-10-01: rules and flags live in `world.json`; *reaction* and *rule* are two names for one engine; no `says` event in the first slice; beliefs are in the first slice. Source: Rylee's twenty sentences (`design/named-edits-sentences.md`), the second named-edits run (`design/named-edits.md`), and a survey of
beginner game tools (below). No code yet. This adds a new pack surface, so it waits for Rylee's approval.

## Why

Seven of Rylee's twenty sentences describe behaviour, not content:
"an ominous fog rolls in when its name is spoken", "can the cat notice me?", "a sneaky surprise chest that's a bad guy",
"a split map with pieces you find as the story goes on", "a key to open the secret panel", "something that tells me where to go",
"a system for little treasures". Named edits can place a cat or a chest. They cannot say *when* something should happen.

## The idea

A **rule** is one sentence a person can read aloud, written as plain data:

> **When** the hero comes near the cat, **if** the cat has not noticed yet, **then** the cat looks up and says "Mrrp."

The sentence is the whole interface. Chat turns a request into that sentence and shows it as a preview. Drag-and-drop is three slots: *when*, *if*, *then*.
A person can also write it in a plain file. All three produce the same JSON.

```json
{
  "id": "cat-notices",
  "when": {"comes-near": {"who": "cat", "distance": 2}},
  "if":   [{"flag": "cat-noticed", "is": false}],
  "then": [{"set": "cat-noticed"}, {"say": {"who": "cat", "line": "Mrrp."}}],
  "once": true
}
```

## What a rule is made of (all small, all from a fixed list)

**Events** (what just happened). Each maps to something the woven player already knows:

| Event | Means | Where it already happens in the player |
| --- | --- | --- |
| `starts` | the game begins | the Begin button |
| `enters` | the hero arrives in a place | `enterRegion` |
| `comes-near` | the hero is within N tiles of a person, thing or tile | the talk reach (`tryNPC`, 2 tiles) |
| `opens` | a chest or door is used | `useHere` (chest, door) |
| `picks-up` | an item is taken | the floor pickup (`takeHere`) |
| `uses-with` | an item is used on a thing | the `use` verb (reward ruleset) |

`says` ("when a name is spoken") is **not** in the first set. **The woven player has no place for the player to type words** (its only text boxes are the model settings; Whisper is a button).
That needs a new input surface first. Until then, the same feelings come from `enters`, `comes-near`, `opens` and `uses-with`.

**Conditions** (only these): `has <item>`, `flag <name> is set / not set`, `<person> believes / does not believe <claim>`, `is in <place>`, `not`, `all of`.

**Actions** (only these): `say` (a line from a person, or a narrator line), `show` / `hide` a thing, `reveal` a thing (a chest becomes a monster, a panel appears),
`give <item>`, `set <flag>`, `believes` / `stops-believing` / `tells` (beliefs), `weather` (fog on or off, using the fog the player already has), `point-to <place>` (a plain hint: "The tavern is east of here").

## Two names, one engine: reactions first, rules later

- A **reaction** belongs to one thing: "the cat looks up when the hero comes near". One event, one response, attached to the cat. In drag-and-drop you click the cat and pick a reaction.
  This is what a player meets in the first hour.
- A **rule** is about the whole game: "when all three map pieces are found, show the full map". It uses flags and conditions across rooms. This comes with the tenth hour.
- Underneath, a reaction is a small rule that carries an `on` (the thing it belongs to). The same checker, the same log, the same preview card.

```json
{"id": "cat-notices", "on": "cat", "when": {"comes-near": {"distance": 2}}, "then": [{"say": "Mrrp."}]}
```

## Beliefs: reactions that follow what a character thinks, not what is true

The world has **flags**: what is true. Each character may also hold **beliefs**: their own flags, which can be wrong or out of date. A reaction can read either.
This is Rylee's "mistaken assumption": the guard thinks the hero opened the chest, but it was the cat, so he scolds the hero anyway.

- **Claims are declared**, like flags, in `world.json`, with a plain meaning and the truth. A belief is a claim a character holds as `true` or `false`.
  Beliefs may start wrong in the file (a mistaken assumption written by the author), or change through the same events as everything else.
- **A belief changes only through a listed action:** `believes` (the character sees or is told it), `stops-believing`, or `tells` (a character passes a belief to another when they meet).
  There is no randomness and no drifting.
- **Conditions** gain `<person> believes <claim>` and `<person> does not believe <claim>`.
- **The "why?" log** says where a belief came from: *"Stern glared because he believes 'hero-took-key'; he heard it from the fisher."* (The source is recorded when a belief is set.)
- **The validator** checks that every claim and person exists, warns when a claim is believed but can never be true or false in play, and warns about a belief nothing can ever read.

```json
"claims": {"hero-took-key": {"meaning": "The hero took the cellar key.", "true": false}},
"people": {"stern": {"believes": ["hero-took-key"]}}
```
```json
{"id": "stern-glares", "on": "stern", "when": {"comes-near": {"distance": 2}},
 "if": [{"believes": {"who": "stern", "claim": "hero-took-key"}}],
 "then": [{"say": "I know what you did."}], "once": true}
```

This also separates two layers the Archives already hint at: **canon** is what is true in the game; **beliefs** are what its people hold, and they can be wrong.

## Flags are declared and visible

Every flag has a plain name and a one-line meaning in the game's file. A rule may only use a declared flag, so the validator catches a typo.
The studio shows a **flags list** with which rules read and which write each one. There are no numbers, only on and off.

```json
"flags": {"cat-noticed": "The cat has looked up at the hero once."}
```

## How rules run (the three traps, avoided on purpose)

1. **No hidden state.** Declared flags only; the list is always visible.
2. **No fighting rules.** There are no priorities. Rules run in the order written, and the studio shows that order.
   The validator warns when two rules share an event and can both pass with conflicting actions (for example two different weathers).
3. **A "why?" answer.** Each rule that fires leaves one line in the play journal: *"rule 'cat-notices' fired: the hero came near the cat, and 'cat-noticed' was off."*
   A **Why did that happen?** button (and `vefr why`) prints the last few. The same log is what tests assert.

**Limits (v1):** a rule fires at most once per event; a rule cannot cause another rule's event (no chains); `once: true` is the default; at most 40 rules per game;
no numbers or maths, no randomness, no timers, no loops, no free-form scripting. These can be relaxed later without breaking the shape.

## What it checks (the validator, in plain sentences)

Unknown flag, item, person, place or event; a rule whose `then` names a thing that does not exist; two rules that conflict; a rule that can never fire
(its place is unreachable, its item can never be found); more than 40 rules; a `say` line longer than the speech box can show. Every error names the rule id.

## How Rylee's seven behaviour sentences map

| Sentence | As a rule |
| --- | --- |
| "Can the cat notice me?" | `comes-near` the cat, then `say` |
| "A sneaky surprise chest that's a bad guy" | `opens` the chest, then `reveal` a monster (needs `place_enemy`) |
| "An ominous fog when its name is spoken" | v1: `enters` the harbour, then `weather` fog. The spoken name needs the future input surface. |
| "A split map with pieces you find" | `picks-up` each piece, then `set` a flag; when all flags are on, `show` the whole map |
| "A key to open the secret panel" | `uses-with` the key on the panel, then `reveal` the panel and `set` a flag |
| "Something that tells me where to go" | `starts` or `enters`, then `point-to` the next place |
| "A system for little treasures" | each treasure `picks-up` sets a flag; the shelf shows what is found. A collection is a pack of rules, not a new engine feature. |

## How it joins the rest

- **Named edits** (`design/named-edits.md`): `add_rule` and `remove_rule` are edits. Chat proposes the sentence; the player keeps, changes or bins it.
- **Equipment** (`design/equipment.md`) and **items**: `has` and `give` use the same item ids.
- **Stickers:** a first rule can earn one ("your game reacted to you"); teaching that this is called a **rule** comes after they have seen one work.
- **Glossary:** noun **rule**, verbs **write a rule** and **ask why**; Norse name to be chosen by Rylee.

## What the tool survey says (sources)

Checked against the real pages:
- **Twine** ([cookbook](https://twinery.org/cookbook/)): state is variables; invisible, typo-prone variables are a known problem.
- **Ink** ([docs](https://github.com/inkle/ink/blob/master/Documentation/WritingWithInk.md)): content without a label is not "remembered"; the compiler warns about loose ends.
- **PuzzleScript** ([rules](https://www.puzzlescript.net/Documentation/rules.html)): a rule is a pattern and a replacement; order matters.
- **RPG Maker MZ** ([help](https://rpgmakerofficial.com/product/MZ_help-en/01_09_03.html)): a page appears only if all its conditions pass; triggers are separate (Action Button, Player Touch, Event Touch, Autorun, Parallel); when several pages qualify, the highest-numbered wins.
- **Construct 3** ([how events work](https://www.construct.net/en/make-games/manuals/construct-3/project-primitives/events/how-events-work)): conditions plus actions, with sub-events; the sheet runs top to bottom every tick.
- **Bitsy** (community docs, e.g. [Bitsy Variables: A Tutorial](https://ayolland.itch.io/trevor/devlog/29520/bitsy-variables-a-tutorial); not the official docs): curly-brace code blocks with variables and conditionals; `(exit)` and `(end)` run at the end of a dialogue.

**Not checked:** Scratch, Inform 7, and the claim that RPG Maker autorun events can lock a game (the official page does not say so; it is community lore).

## What it refuses to build at first

Numbers and arithmetic, loops, randomness, timers, parallel or autorun rules, rules that trigger rules, free-form scripting, per-page conditions, and a priority system.

## Decided and still open

**Decided (Rylee, 2026-10-01):** rules and flags live in `world.json`; *reaction* and *rule* are two names for one engine; `says` is not in the first slice
(the woven player has no typed input; the studio has a builder chat, and a future "play it here" pane could share it); beliefs are in the first slice.

**Decided (Rylee, 2026-10-01):** beliefs are visible **only in the "why?" log at first**, not on a resident's page.

**Still open:** a Norse name for each of reaction, rule and belief (Rylee chooses).

## Build order (about two to three weeks, foreman-sized)

| # | Task | Tag |
| --- | --- | --- |
| 1 | Approve the shape (this note) | **keep** (Rylee) |
| 2 | Validator for `flags`, `claims`, `people`, `rules` (shape, unknown ids, conflicts, limits, belief checks) with plain errors | offloadable |
| 3 | Engine as pure functions with a node harness: events in, actions out, once, no chains, beliefs set and read, the source recorded | offloadable |
| 4 | Wire six events and the actions into the woven player; one journal line per fired rule with its reason | offloadable, then **keep** (review) |
| 5 | **Why did that happen?** button and `vefr why` (including where a belief came from) | offloadable |
| 6 | A demo in Cottage: the cat notices you; the harbour fog on entering; map pieces; Stern believing the wrong thing | offloadable |
| 7 | `add_reaction` and `add_rule` as named edits: chat preview, and three-slot drag-and-drop | offloadable after 1 to 4 |
