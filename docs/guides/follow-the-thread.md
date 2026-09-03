# Follow the Thread - design probe

> Exploratory, exploratory only. Nothing here is implemented. This is
> the open question from the 2026-09-03 free-dock review: from
> something visible in the world, follow the provenance of why it
> is true. The review explicitly said "do not build another giant
> inspector" and "produce a short design note only if the current
> data model actually supports it." So no prototype - just the data
> shape and where the joins already exist.
>
> **Bottom line:** the engine today has partial joins on
> `(phase, at, speaker.key)` and exactly zero stable trace identity.
> A complete Follow the Thread is blocked on a new `trace_event_id`
> field; a partial "near this moment" client-only tool could exist
> today and would say honestly what it cannot prove. See
> "What can be done entirely in client today" for the caveats.


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
the journal's `when` field shows the timestamp; today's data model
already supports partial joins via `(phase, at, speaker.key)` -

- `phase` is a single string on every rumor, trace event, NPC
  line, journal entry, and pack load
- `at` (ISO timestamp) appears on trace + journal at second
  resolution
- `speaker.key` joins wiki NPCs and npc recent dialogue

A minimal **partial** "Follow the Thread" affordance using only
what exists today, with its limits stated plainly:

- shared selection state in `state.js` keyed by the existing
  `(phase, at)` tuple (string, e.g. `"phase=whispers&at=2026-08-31T13:00:00Z"`)
- the Trace list calls `state.set('selectedContext', {phase, at})`
  on a row's keyboard activation
- the Journal list highlights entries whose `(phase, at)` matches
  the selection (a timestamp JOIN, not a stable id JOIN)
- a `state.subscribe` in `wiki.js` highlights NPC recent lines
  whose `(phase, at)` falls within a small window of the
  selection

**Limitations of the partial version, stated honestly:**

- `(phase, at)` is a *probabilistic* join, not a guaranteed one.
  Two unrelated events a second apart would collide.
- No exact "this NPC call produced this rumor" guarantee exists
  today; you can show "things near this moment" but not "this is
  what produced that."
- Selecting a forged item has no link back to the originating
  forge call at all (see "what would require data-model changes"
  above) - the partial version skips items.

A complete version (exact trace->rumor->journal join, forge
items linking back to their call, lore-pack fragments hashing
back to output) requires the `trace_event_id` field described
in the next section. The partial version is honest about what
it cannot prove.

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
