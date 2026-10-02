# 00 · Executive summary

**Disposition: GO WITH CONSTRAINTS.**

VEFR already has a language-shaped core: `when / if / then / once` rules, a closed set of 11 events and 13 effects, a validator that owns their signatures, and a deterministic runtime. Codex ran three bounded probes against the real Cottage pack, and I reran them on 2026-10-02 (9 public tests pass; the runner passed all three probes).

## What the evidence earns

An **optional, build-time** layer: authoring source -> validate -> normalize -> today's pack structures -> today's runtime. First slice: family/default expansion with provenance and legacy-equivalence fixtures, proven live on Cottage.

## What it does not earn

A new runtime, event sourcing, a logic engine, natural-language authoring, a plugin system, an estate-wide kernel, or broad pack migration.

## Key facts

- Rules lowered with identical behavior; the semantic wrapper was more verbose, so the existing rule shape stays.
- Real creatures expanded to structurally equal records from one family (parsed-JSON equality, not byte equality); guardians are unwired, so their semantics are `UNKNOWN`.
- Theme owns vocabulary, generator owns arrangement, only for controls the generator has.
- Pre-existing issue: rule flags and `once` markers reset on reload.
- Prior art is a thin base: its Datalog, JSON Schema and event-sourcing claims were corrected, and its project-history claims are unverified.

## Decisions needed from Rylee

See `11-open-decisions.md`. Nothing is authorized until she has read this disposition.

## Packet map

Public (this folder): 00, 01, 03, 04, 05, 06, 07, 08, 09, 11, 12, SOURCES. Private (Cottage repo, `docs/language-architecture/`): 02, 10.
