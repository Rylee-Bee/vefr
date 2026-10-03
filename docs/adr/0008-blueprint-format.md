# 0008 - Blueprint format 1

Date: 2026-10-02

## Status

Proposed. Becomes Accepted when the core (plan PR 2) merges. Decisions below were made by Rylee on 2026-10-02 in chat; the plan is `docs/plans/blueprint-family-normalization-plan.md`.

## Context

Repeated creature records are the one place a real pack repeats itself (`docs/research/language-architecture/`). The research found that VEFR already has a language-shaped core, so the answer is an **optional, build-time** layer that expands a small source into today's pack structures. It adds no runtime, no rule language and no event vocabulary.

## Decision

A pack may carry a **Blueprint**: `blueprint.json` at the pack root. It is the edited truth for the regions it owns. `vefr normalize` expands it into the owned regions' `enemies` lists (committed, read-only) and writes `blueprint.lock.json` (source hash, versions, provenance). A pack without a Blueprint is unchanged.

The word is "Blueprint". `grammar.py` means text expansion and is unrelated.

### Format 1

Closed sets, defined once as constants in `src/vefr/blueprint.py`:

| Where | Allowed keys |
|---|---|
| top level | `blueprint`, `families`, `regions` |
| family | `defaults`, `extends` |
| `defaults` / `properties` | `name`, `sprite`, `hp`, `atk`, `xp`, `sight`, `drops` |
| region entry | `enemies` |
| instance | `id`, `family`, `at`, `properties` |

Rules: `"blueprint": 1` is required (the version field, naming reader `read_v1`); expansion order is parent defaults (root first), family, instance `properties`, then `id` and `at`; a later value replaces an earlier one whole and lists are never merged; one explicit parent; unknown key, family, parent, cycle, duplicate id, missing `at`, absent region, region path outside the pack, and unknown `drops` item all fail with a plain sentence and a JSON pointer; emitted key order is `id, name, sprite, at, hp, atk, xp, sight, drops`. Every family is checked for an unknown parent or a cycle, used or not (decided 2026-10-02), and an invalid `drops` error points at the declaration that supplied the value (a family's `defaults` or the instance's `properties`). Format 1 is acts-shape only. There is no event or effect vocabulary: a pack word grants no authority.

### Stale rule

Output is **stale** when the lock's `source_sha256` (SHA-256 of the canonical Blueprint) differs, or any owned value on disk is not structurally equal to what this VEFR expands now. Structural equality is parsed-JSON `==`: key order ignored, list order significant; it is not byte equality. A newer normalizer or format than this VEFR knows fails clearly. `check`, `normalize` and the weave refuse stale output.

### Pipeline

read (versioned reader) -> validate source -> expand -> provenance -> write owned values and lock -> validate the whole normalized pack with today's `maplab.validate`. Only the second validation can see cross-references (items, regions, growth mode).

### Library contract (frozen by the tests)

`vefr.blueprint` exposes: `BlueprintError` (with `.pointer`), `READERS`, `NORMALIZER_VERSION`, the five key sets above, `read(path)`, `expand(source, *, pack_dir)` returning `{region_key: [records]}`, `canonical_hash(source)`, and `check_errors(pack_dir)` returning plain strings (empty when there is no Blueprint and no lock). The CLI is `vefr normalize --pack PACK [--out DIR]`. The tests are the contract; an implementer who needs to change one stops and escalates.

## Versioning and deprecation policy

- The format is an integer in the file. Each format has one reader and its own fixture directory.
- A reader is never removed without a migration tool, a release note, and an end date Rylee approves.
- The normalizer version bumps whenever the same input could produce different output; the lock records it.
- An unknown newer format or normalizer fails with a sentence, never a guess.
- Adding a field, family key or instance key is a format change and needs a written reason in this ADR.
- Hand-written enemy records stay fully supported. Their end of life, if any, is set later by Rylee after the trial.

## Kernel budget

Format 1 stays at the five closed sets above. A second rule language, traits, relations, events or inheritance beyond one parent are out of scope and need a new format and a new ADR.

## Owner and change process

Owner: Rylee. A format change is an ADR amendment, a new reader with fixtures, and a conformance case, merged in that order.

## Exit ramp

Continue only if authored enemy values drop by at least 25% on the first real pack, or one real error is caught. Otherwise delete `blueprint.json` and `blueprint.lock.json`; the generated records are already the old shape, so nothing else changes.

## Consequences

One more file to learn for authors who opt in; two more files in a migrated pack; a bump of the companion repo's pinned VEFR. Nothing changes for packs that do not opt in.
