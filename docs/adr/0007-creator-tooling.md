# 0007 - Creator tooling

Date: 2026-10-02

## Status

Proposed

## Context

The first independent pack reinvented three practices that any
serious pack author hits (finding 19):

- A **content/ vs generated** split - authored source on one side,
  rebuilt pack output on the other, with a deterministic rebuild.
- **Acceptance checks** - the author's own `check_*` scripts run
  before sharing.
- **Art contact sheets** - a labelled grid of the pack's pictures
  so the author can verify the art by looking at it.

All three lived in pack-local tooling (`tools/`, `art/tools/`).
None is a game-specific need; each is a general authoring habit.
The engine's law stands in the way of copying them wholesale: a
pack-declared command is code, and code from a pack must never run
implicitly; and the engine must not force structure on
hand-authored packs.

## Decision

**Small, optional primitives go in the engine. Structure and
self-promises stay in the pack.**

**(a) `vefr pack new` - in the engine.** A scaffold command that
writes a starting pack: `content/` for authored source, a rebuild
step that deterministically regenerates the pack output from it,
and acceptance checks wired to `norns validate`. The scaffold is a
starting point, not a law:

- Hand-authored packs with no `content/` are fully supported and
  never rewritten; `norns validate` sees no difference.
- The rebuild is deterministic: same source in, same pack out, so
  a diff means the author changed something.
- Acceptance checks the scaffold writes are ordinary pack files the
  author owns and may edit or delete.

**(b) `norns validate --play` - in the engine, with a trust
boundary.** A pack may *declare* a playtest command in its
metadata; `--play` runs that pack's own playtest.

- **Opt-in and explicit:** plain `norns validate` never runs it.
  The declaration alone never runs it. Only the explicit `--play`
  flag runs it, and only for the pack named on the command line.
- **Never implicit:** no other verb, hook, CI step, or studio
  action triggers it. The engine prints the exact command it is
  about to run before running it.
- **The pack owns the playtest.** The engine provides the flag and
  the boundary, not the test. A pack that declares nothing gains
  nothing and loses nothing.

**(c) Art contact sheet - stays in pack/studio tooling.** A small
importer that lays a pack's pictures out in a labelled grid for
eyeball verification. Label and look; that is the whole job.

- It is a viewing aid, not an asset manager: no catalog, no
  database, no format pipeline, no rename-on-import.
- It lives where pack art already lives (studio tooling), so the
  engine gains no art-directory convention.

**The line:** the engine ships verbs and boundaries (`pack new`,
`--play`); packs ship their own structure and their own promises
(`content/` layout, checks, playtest, sheets). A pack may use any
of it, all of it, or none.

## Consequences

It costs:

- Two new public verbs to document, test and keep stable
  (`docs/guides/vefr-command.md`, ROADMAP entry when landed).
- A trust boundary to actively maintain: the `--play` rule (flag
  only, pack only, printed first) needs a test that fails if
  anyone wires it to an implicit path.
- Scaffold drift: `pack new` must track the pack contract as it
  evolves, or its output goes stale.

It does NOT:

- Force `content/`, generated output, checks, or a playtest on any
  existing or hand-authored pack - `norns validate` remains the
  one shared gate.
- Execute any pack-declared command without the explicit flag, and
  never implicitly from validation alone.
- Build an asset manager, an art pipeline, or a pack marketplace.
- Move pack-owned acceptance checks into the engine; a pack's
  promises are the pack's.
- Touch play itself: no model calls, no change to the woven player.
