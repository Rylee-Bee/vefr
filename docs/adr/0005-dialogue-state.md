# 0005 - Dialogue state

Date: 2026-10-02

## Status

Proposed

## Context

A speaker's standing line is a seed: `speakers[].seeds[phase]`, one
string per phase, and the validator requires every phase covered
(maplab.py). Offline play speaks the seed; a woven game has no model
(ADR 0003).

Flags exist and are declared in `world.json`; rules set them. But a
seed cannot notice a flag. The only reactive speech is a rule's
one-shot `say`. An independent pack wanted one line that changes
when a flag turns - before and after a story landmark - and the
contract had no seam for it (finding 14).

## Decision

**The smallest additive contract: a seed value may become a small
list of flag-conditioned entries plus one default line.**

```json
"seeds": {"dusk": [
  {"when": {"flag": "landmark-lit", "is": true},
   "line": "It is burning. I knew it would."},
  {"line": "The dark holds. Nothing has changed yet."}
]}
```

- A seed value stays a plain string (today's shape), or becomes a
  list of entries. Exactly one entry carries no `when` - the
  default - and it is required.
- Each `when` is one **declared** flag and one boolean (`true` or
  `false`). Nothing else: no and/or, no negation beyond `is:false`,
  no numbers. The validator rejects an undeclared flag.
- **Selection is deterministic:** first entry in written order
  whose `when` matches the current flag value; if none matches, the
  default. Same flags, same line, every time.
- The validator caps the list (at most 6 entries per phase) so a
  seed stays a handful of lines, not a decision tree.
- **Offline-first is non-negotiable:** selection reads flags the
  player's own session already stores. No model, no inference; it
  works in the woven file.
- Fragment banks (`voices/<name>.fragments.md`) stay static in v1.
  The same `when` shape could extend them later - noted as an
  option, not decided here.

Considered and rejected:

- **A dialogue scripting language** (many flags, order of events,
  arithmetic in text) - that is a second rules engine hidden inside
  prose, and the why-log could never explain it.
- **Per-line conditions everywhere** (books, whispers, pool lines) -
  every authored line becomes a truth table the author must audit.
  Conditions live only where a speaker already has a keyed entry:
  seeds.

## Consequences

It costs:

- A pack-contract change ("ask first" per AGENTS.md): world.py
  docstring, maplab validation, npc.py selection, the bake, and the
  companion note for pack repos.
- Authors must keep flags declared and honest; a seed on a stale
  flag silently shows the default (the validator can warn when no
  rule ever writes the flag).
- One more tiny pure function to test: flags in, line out.

It does NOT:

- Call a model, at any point, in any player.
- Add a scripting language, multi-flag conditions, or arithmetic.
- Touch books, whispers, or fragment banks in v1.
- Add a second state store: seeds read the same flags rules set.
- Change any existing pack: a string seed loads exactly as before,
  and every phase is still covered.
