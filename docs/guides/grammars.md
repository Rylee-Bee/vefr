# Grammars - a pack that keeps its voice with no model

A woven game with a baked pool speaks offline, in the pack's own
voice, from lines a model wrote at weave time.
A pack with no pool - or one whose pool the player has drained - falls
back further: the composer's re-sewn cloth, then the author's
fragment banks, then honest silence.

A **grammar** is the last stop before silence, and the cheapest one to
write: a few lines of JSON in your own `world.json`, expanded by the
engine (and by the woven file itself) with no model, no network, and
no clock. It is not a phrase bank and it is not generated. It is you,
writing the world's own words, once.

## What a grammar is

A grammar is an object mapping a **rule name** to a non-empty list of
**strings**. One rule is required: `origin`, where expansion starts.
Inside a string, `#rule#` expands to one entry of that rule. Every
other character is kept exactly as you wrote it.

```jsonc
// a fragment of world.json - the whole block, in one pack
"grammars": {
  "whisper": {
    "origin": ["#who# says #news#."],
    "who": ["the innkeeper", "the ferryman", "the watch"],
    "news": ["the road east is watched",
             "the ford is out",
             "nobody has crossed in three nights"]
  },
  "weather": {
    "origin": ["#sky# over #place#."],
    "sky": ["Rain", "Hard frost", "A wind off the water"],
    "place": ["the town", "the ridge", "the long bridge"]
  },
  "name": {
    "origin": ["#adj# #noun#"],
    "adj": ["Grey", "Still", "Low"],
    "noun": ["Hollow", "Reach", "Cellar"]
  }
}
```

That block goes at the **top level** of your pack's `world.json`,
beside `title` and `phases`. Every part is optional: a pack with no
`grammars` behaves exactly as it always has, and a pack with only a
`whisper` grammar gets whispers and nothing else.

A worked example, end to end. Given the `whisper` grammar above:

| step | what the expander does |
|---|---|
| start | picks one `origin` entry: `#who# says #news#.` |
| first reference | `#who#` -> draws `the ferryman` |
| second reference | `#news#` -> draws `the ford is out` |
| literal text | ` says ` and `.` are kept as written |
| result | `the ferryman says the ford is out.` |

The three engines that read a grammar:

| grammar | read by | when |
|---|---|---|
| `whisper` | the woven player | a whisper is asked for, and there is no endpoint, no pool, and no fragment bank to draw from |
| `weather` | the woven player | the hero enters a region - once per arrival, never per step |
| `name` | `norns delve` | a generated dungeon floor is written, and the drawn name rides in that region's `contract.json` |

Two implementations of the same algorithm exist, one per side of the
engine: `expand()` in `src/vefr/grammar.py`, and `grammarExpand()` in
`web/packaged.html` (the woven file carries its own copy, so it needs
no Python at all). They behave identically. They do not promise the
same sentence for the same seed, because each side's random stream is
its own.

## The three laws

1. **`origin` is required.** Expansion starts there; a grammar
   without one expands to nothing.
2. **Every `#rule#` names a rule in the same grammar.** A reference
   that names nothing expands to nothing.
3. **One expansion draws at most 200 entries.** A grammar that points
   at itself stops at the cap rather than looping.

When any of the three is broken, the expansion returns the empty
string - never a line with a hole where a word should be. The engine
prefers honest silence to half a sentence, the same way the composer
does.

`norns validate` checks the block up front, so a typo is a message at
authoring time rather than a silence at play time:

```
FAIL: grammar 'whisper' needs an 'origin' rule - expansion starts there
FAIL: grammar 'whisper' rule 'origin' references 'townsfolk', which is not a rule in that grammar
FAIL: grammar 'name' rule 'adj' must be a non-empty list of strings
```

## The seed rule

Every draw comes from a random stream the caller passes in, and
nothing else - no clock, no global random, no network. That is the
whole seed rule:

- **The engine** (`norns delve`): the seed is the delve seed plus the
  floor's name, so the same `--seed` always names the same floor.
- **The woven file**: the seed is the player's own save seed
  (`localStorage['vefr-save-seed']`) plus a draw counter that ticks
  once per draw. The save seed is written once, on first play, and kept.

So a pack is deterministic in the way that matters: the same save and
the same draw say the same thing, every playthrough, on every machine.
A whisper is not "random" in the sense of being unowned - it is a
draw from your words, and the draw is the save's.

## Writing a good one

- **Write the fragments, not the sentences.** Rules that hold single
  words or short phrases compose into lines you did not write
  yourself; a rule per full sentence means you have written the line.
- **Keep the tone in the rule, not the shape.** `who` and `news` can
  carry the register; `origin` should stay the frame.
- **Three or four entries per rule** reads well. One makes every draw
  the same; forty makes the world feel unrelated to itself.
- **Name what the world calls things** (`#place#`, `#noun#`) rather
  than hardcoding them, so a rule can be reused across grammars.

## Related

- The pack contract: the `grammars` block in `src/vefr/world.py`'s docstring.
- The expander: `src/vefr/grammar.py`.
- The validator: `grammar_errors()` in `src/vefr/maplab.py`.
- Offline play (pool, composer, fragment banks): `README.md`, the
  "Package a single HTML file" section.
