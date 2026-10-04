# Blueprints: a small source for repeated monsters

A pack often repeats the same creature: a beetle in one cave, a
slightly tougher beetle in the next. A **Blueprint** lets you write the
family once and let VEFR build the records.

## What is a Blueprint?

A Blueprint is one file at a pack root, `blueprint.json`. It holds a
few small families of enemy values and a list of regions. `vefr
normalize` expands it into the `enemies` list of every region it names.
The Blueprint is the edited truth for the regions it owns. The records
it writes are generated, not hand-written.

The word is "Blueprint". It is not `grammar.py`, which is text
expansion, and it has nothing to do with rules or events.

## When should I use one?

Use a Blueprint when the same monster repeats across regions and only a
few numbers change. Use it when you want one place to change a family
and have every region follow.

Do not use one for a single, hand-written enemy. A pack with no
`blueprint.json` is completely unchanged.

A Blueprint needs the acts shape. A flat pack (one `world.json`, no
`acts/`) cannot carry one.

## How do I run it?

First write `blueprint.json` at the pack root. Then run:

```sh
uv run vefr normalize --pack worlds/<name>
```

With no `--out` this is read-only: it prints one line per owned region
and says `fresh` when the committed output already matches. Add `--out`
to write the generated records and the lock:

```sh
uv run vefr normalize --pack worlds/<name> --out worlds/<name>
```

`--pack PACK --out PACK` refreshes the pack in place. `--out` may also
name a new or empty directory outside the pack; the pack is copied
there, refreshed and validated there, and the original is never
touched.

`normalize` exits `0` when the output is fresh or was written (or the pack has no Blueprint, which it says), and `1`
when there are errors or the committed output is stale.

Then check the whole pack:

```sh
uv run vefr check --pack worlds/<name>
```

`vefr check` validates the pack geometry and also refuses stale
Blueprint output.

## The file format

The version field `blueprint` is required. It must be the integer `1`
or the integer `3`.

- `1` is enemies: `regions` carry `enemies` and nothing else.
- `3` is places: `regions` may also carry `places`.
- `2` is reserved for things. It does not exist yet and nothing reads
  it, so a `"blueprint": 3` file is complete on its own and never
  waits for format 2.

A pack on `1` expands exactly as it did before, byte for byte.

This is a full example on format 1 (a synthetic pack, not real
content):

```json
{
  "blueprint": 1,
  "families": {
    "beetle": {"defaults": {"name": "a beetle", "sprite": "beetle",
                            "hp": 3, "atk": 1, "xp": 2}},
    "deep-beetle": {"extends": "beetle", "defaults": {"hp": 4}},
    "moth": {"defaults": {"name": "a moth", "sprite": "moth",
                          "hp": 2, "atk": 1, "xp": 1, "sight": 3}}
  },
  "regions": {
    "act-1/cave-2": {"enemies": [
      {"id": "b1", "family": "beetle", "at": [3, 4]},
      {"id": "b2", "family": "beetle", "at": [6, 4],
       "properties": {"drops": ["shell"]}},
      {"id": "m1", "family": "moth", "at": [4, 2]},
      {"id": "odd1", "family": "beetle", "at": [5, 5],
       "properties": {"hp": 9}}
    ]},
    "act-1/cave-3": {"enemies": [
      {"id": "d1", "family": "deep-beetle", "at": [3, 4]},
      {"id": "d2", "family": "deep-beetle", "at": [6, 4]}
    ]}
  }
}
```

A region key is `<act>/<region>` and must name a real region directory
inside the pack. An instance needs an `id` and a `family`, and it needs
`at` (a `[x, y]` pair of whole numbers) unless a `properties` or family
value already provides one.

Values are merged in this order: parent family defaults first (root
first), then the family's own defaults, then the instance's
`properties`. A later value replaces an earlier one whole. Lists are
never merged. A family may extend at most one parent.

### The closed key sets

Every object may use only these keys. Anything else fails with a plain
sentence and a JSON pointer.

| Top level | |
|---|---|
| `blueprint` | the format version, `1` or `3` |
| `families` | the named families |
| `regions` | the regions this Blueprint owns |

<!-- TOP_KEYS: blueprint, families, regions -->

| A family | |
|---|---|
| `defaults` | the values this family contributes |
| `extends` | the one parent family, or absent |

<!-- FAMILY_KEYS: defaults, extends -->

| A field value (in `defaults` or `properties`) | |
|---|---|
| `name` | the monster's name |
| `sprite` | the picture key |
| `hp` | health |
| `atk` | attack |
| `xp` | experience |
| `sight` | how far it notices the hero |
| `drops` | a list of item ids the pack declares |

<!-- FIELD_KEYS: name, sprite, hp, atk, xp, sight, drops -->

| A region entry | |
|---|---|
| `enemies` | the instances for this region |
| `places` | the doors, stairs and signs for this region (format 3) |

<!-- REGION_KEYS: enemies, places -->

| An instance | |
|---|---|
| `id` | a unique id within the region |
| `family` | the family to start from |
| `at` | the `[x, y]` position |
| `properties` | values that override the family for this one |

<!-- INSTANCE_KEYS: id, family, at, properties -->

Unknown keys, unknown families, unknown parents, cycles, duplicate
ids, a missing `at`, an absent region, a region path outside the pack,
and an unknown `drops` item all fail. Generated records are written in
this key order: `id, name, sprite, at, hp, atk, xp, sight, drops`. A family nothing uses is checked too: a broken parent or a cycle there is rejected, so a typo cannot hide until the family is first used. An error about a `drops` list points at the declaration that supplied it (the family's `defaults`, an ancestor's, or the instance's `properties`).

## Places (format 3)

A **place** is one thing built into the floor: a door, a stair or a
sign. A door goes from six edits in four files to one. Written as a
place, it is one entry, and `vefr normalize` writes the rest.

```json
{
  "blueprint": 3,
  "families": {},
  "regions": {
    "act-1/cave-2": {"places": [
      {"id": "down", "kind": "stair", "at": [2, 7], "glyph": ">",
       "tile": "stair-down", "to": "cave-3", "to_at": [3, 1]},
      {"id": "keeper-door", "kind": "door", "at": "far:down off:down>up",
       "glyph": "D", "base": ["#332e26"], "to": "cave-3",
       "to_at": [3, 1], "needs": "shell", "locked_text": "It will not open yet."},
      {"id": "warning", "kind": "sign", "at": "near:down", "glyph": "!",
       "label": "the cracked sign", "text": "The cave breathes here."}
    ]}
  }
}
```

| A place | |
|---|---|
| `id` | a unique id within the region (required) |
| `kind` | `door`, `stair` or `sign` (required) |
| `at` | where it stands (required): a `[x, y]` pair or a sentence |
| `glyph` | the one character it paints on the map (required) |
| `tile` | the tile picture for that character |
| `base` | the legend colours; defaults to the region's `.` |
| `label` | the name of the poi, a sign only |
| `text` | what the sign says, a sign only |
| `to` | the region of the same act it leads to, with `to_at` |
| `to_at` | the tile it lands on, with `to` |
| `needs` | the item that opens it, a door only, with `to` |
| `locked_text` | what the door says while it is shut, a door only |

<!-- PLACE_KEYS: id, kind, at, glyph, tile, base, label, text, to, to_at, needs, locked_text -->

`id`, `kind`, `at` and `glyph` are always required. A `door` and a
`stair` must name `to` and `to_at`, and they come together: one
without the other fails. `needs` and `locked_text` are a door's alone,
and a door with either one must have `to`. `label` and `text` are a
sign's alone. `chest` is not a kind yet; the engine has no chest place
to point at.

### Where a place stands

`at` is a sentence read left to right, and its words are ANDed. The
whole language is five words:

- `x,y` is a coordinate, and the only form format 1 has.
- `far:ANCHOR` is the tile farthest from the anchor.
- `near:ANCHOR` is the tile nearest to the anchor.
- `off:A>B` is a tile that is not on any shortest route from anchor
  `A` to anchor `B`.
- `dead-end` is a tile that leads nowhere.

An **anchor** is a name the region already has: `up`, `down`, a place
id, a poi name, or `start`. One real sentence:

```json
{"id": "guardian", "kind": "sign", "at": "far:up off:up>down",
 "glyph": "!", "label": "the guardian", "text": "It watches the stair."}
```

Read it: the farthest tile from the arrival stair, on no route from
that stair to the stair down.

`room:N` is not in this version. It is reserved, the same way format 2
is reserved.

### What one place writes

A place writes into the files a hand-written door would have touched:

- `contract.json` gets one legend entry for the `glyph`:
  `{base, solid: no, tile}`, with `base` defaulting to the region's
  `.` entry;
- `contract.json` gets a `pois` entry for the place's tile, holding
  `label`, and a `poi_text` entry, holding `text`;
- the act's `world.json` gets one `transitions` entry
  `{from, at, to, to_at, requires: {item: needs}, locked_text}`,
  appended after the hand-written ones so the hand transitions keep
  their `transition {i}` numbers;
- the character is written **into `map.md`**.

That last one is why deleting `blueprint.json` still leaves a working
pack. The glyph is a real character in the real file the bot and the
studio read, not an overlay drawn at weave time. Delete the
Blueprint, delete the lock, and the doors, stairs and signs are still
there, still walkable, in the ordinary hand-written shape.

## The stale rule

The output is **stale** when any of these is true:

- the lock's `source_sha256` differs from the current Blueprint's
  hash, or
- any owned `enemies` list on disk is not structurally equal to what
  this VEFR expands now, or
- an owned `map.md` cell does not hold the character its place names.

Structural equality compares the parsed JSON: key order is ignored,
list order matters. It is not byte equality. The third clause is the
map cell: a cell a place owns is stale when someone drew a different
character there by hand.

One stale check compares the Blueprint to its lock. The other compares
the committed records to a fresh expansion. A newer normalizer or
format than this VEFR knows also fails, clearly, instead of guessing.

The one command that fixes stale output is:

```sh
uv run vefr normalize --pack PACK --out PACK
```

## The lock file

`vefr normalize --out` writes `blueprint.lock.json` beside the
Blueprint. It records:

- `source_sha256`, the hash of the canonical Blueprint,
- the `normalizer` and `blueprint` (format) versions, and
- `outputs`, the provenance of every generated record (source pointer,
  family chain, overridden keys).

The lock is how `check`, `normalize` and the weave know the output is
fresh. It is generated; do not hand-edit it.

## Generated records are read-only

The `enemies` lists of the regions a Blueprint owns are generated by
`vefr normalize`. Do not hand-edit them: the next stale check compares
them to a fresh expansion, and a hand edit reads as stale. Change the
Blueprint, then run `normalize` again. Regions the Blueprint does not
name are untouched.

The same holds for everything a place writes: the legend entry, the
poi and its text, the transition and the `map.md` cell. Do not hand
edit those either.

## Leaving a Blueprint behind

If the Blueprint does not earn its keep, use the exit ramp: delete
`blueprint.json` and `blueprint.lock.json`. The generated records are
already in the old `enemies` shape, so nothing else changes. The pack
is a normal hand-written pack again. A place is already written in the
hand-written shape too, glyph and all, so a pack with places leaves
the same way.

## What it will not do

- It adds no rules and no events. A Blueprint word grants no authority
  at play time.
- It adds no effect vocabulary.
- It does not inherit beyond one parent.
- It does not change a pack that opts out.
- Hand-written enemy records stay fully supported.

Format changes are an ADR amendment with a new reader and fixtures. See
[ADR 0008](../adr/0008-blueprint-format.md).
