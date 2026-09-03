# Follow the Thread - design probe

> Exploratory, exploratory only. Nothing here is implemented. This is
> the open question from the 2026-09-03 free-dock review: from
> something visible in the world, follow the provenance of why it
> is true. The review explicitly said "do not build another giant
> inspector" and "produce a short design note only if the current
> data model actually supports it." So no prototype - just the data
> shape and where the joins already exist.

## What the concept wants

From a single selection (an NPC, a journal entry, a forged item, a
whisper, a recent generation call) one click should reveal:

1. the originating source (prompt section + lore pack fragment
   that produced the line)
2. the generation trace (which model call, which route, how long,
   which phase input)
3. the state delta (what changed in the world after the line)
4. the joins that already existed across journal / wiki / trace /
   weave before this was asked for

## What joins already exist in the current data

**Without a single schema change**, the engine today can already
be queried in dev mode along most of those axes:

| Want                                | Already have                                                              |
| ----------------------------------- | ------------------------------------------------------------------------- |
| NPC -> recent dialogue              | `/api/wiki` returns `speakers[key].recent[]`                              |
| NPC -> last known location          | `world.pois` plus `current_poi` in `/api/journal/move` return value       |
| Journal entry -> kind/source/phase  | `journal.list_entries()` returns full entry dicts; `/api/journal` exposes |
| Trace events -> generation calls    | `/api/trace` returns `{at, route, ms, ok, phase, speaker}` per call       |
| Trace events -> pack load facts     | `/api/weave` returns `{event: 'pack.load.end', pack, acts, shape}`        |
| World entity -> engine phase/seed   | `/api/builder/aspects` returns `rune_cast {phase, seed, iso_minute}`      |
| Forged item -> source forge call    | `/api/vault` items carry `bond`, `lore`, `kind`, `name` (no upstream id)   |
| Whisper -> speaker/phase            | `/api/rumor` returns `{speaker, whisper, is_true, hook}`                   |

**Stable IDs that already exist across these joins:**

- `phase` (single string) joins everywhere
- `pack.name` (single string) joins wiki, trace, weave
- `speaker.key` (string) joins wiki + npc recent
- `at` (ISO timestamp) joins journal + trace at the second-resolution
- `rune.iso_minute` (truncated timestamp) joins rune cast + any
  later entry by minute

**What is missing - real holes, not imaginary:**

| Wanted join                         | Status                                                                          |
| ----------------------------------- | ------------------------------------------------------------------------------- |
| A whisper back to its exact trace   | Rumor + trace both carry `phase`; no trace carries the whisper's text or seed    |
| A forged item to the forge call     | No `forge_call_id` exists; the kept item only carries the *result*, not the call |
| A journal entry to the originating  | `kind` is free-form; no `trace_event_id` on journal entries                       |
| Lore pack fragment -> generated line| `prompt_block` in `/api/runes/cast` returns the assembly but the wiki doesn't carry a trace id |
| Determinism: same seed -> same line | `rune_cast.seed` exists but `/api/rumor` doesn't echo it back                    |

## What would require data-model / API changes

Strictly to wire stable IDs end-to-end (no functional behavior
change), you'd want:

1. `JournalEntry` gets an optional `trace_event_id: str`
   generated on the server, persisted, exposed via `/api/journal`.
2. `/api/rumor`, `/api/stefna`, `/api/forge`, `/api/npc` return
   `trace_event_id` alongside their existing payload.
3. `/api/runes/cast` returns a `cast_id`; subsequent rumor/stefna/
   forge calls echo it so client can group "this was the cast
   that produced these lines."
4. `WikiSpeakers[].recent[]` entries get `trace_event_id` mirroring
   journal.

None of these touches pack contracts (`world.py` is unchanged).

## What can be done entirely in client today

The wiki page's NPC row already links `name -> recent dialogue`;
the journal's `when` field shows the timestamp; pressing `Enter`
on a selected trace event could already scroll the wiki/wiki
NPCs to the matching `speaker.key` row. The dev drawer's filter
already does substring matching across sections. A minimal client-
only "Follow the Thread" affordance would be:

- a shared selection state in `state.js` (single string, e.g.
  `selectedContextId`)
- the `Trace` list calls `state.set('selectedContextId', trace.id)`
- the `Journal` list renders the selected trace id as a highlight
- a small `state.subscribe` in `wiki.js` that scrolls the
  matching NPC row into view

No server work needed for that minimum-viable version. It is the
shape of the Ask, the Where, and the When without inventing a new
inspector panel.

## Where this belongs

**Dev UI, not player UI.** The player lives in the world; the
provenance graph is the author/buddy/debug view (matches the
existing dev drawer / builder tab pattern). Trying to surface it in
player-facing chrome adds a second inspector that competes with
the world for attention. The `state.js` shared selection could
still *survive* across player/dev switches without being drawn in
the player view.

## Why this is a probe, not a plan

The instruction was "produce a short design note only if the
current data model actually supports it." It does, partially. The
`phase` / `at` / `speaker.key` triple already joins four of the
five views; the missing link is a stable `trace_event_id`. Adding
that field is the smallest schema delta that would unlock a
client-only Follow the Thread without another inspector build.
Anything beyond that (lore pack fragment hashing, deterministic
echo of seeds on output) is a larger exploration the author should
sponsor explicitly.
