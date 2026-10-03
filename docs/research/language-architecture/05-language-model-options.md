# 05 · Language model options

Four shapes were weighed against the Codex proof.

| Option | What it is | Verdict |
|---|---|---|
| **A. Leave as is** | Hand-written JSON packs only | Baseline. Works; repeats creature scalars; no place to hang provenance. |
| **B. Build-time semantic normalizer (recommended)** | Optional authoring source -> validate -> normalize -> today's pack structures -> today's runtime | **ADOPT WITH CONSTRAINTS.** Proven for families and rules; runtime untouched. |
| **C. New runtime language / event-sourced core** | Replace pack structures and runtime with a universal model | **DEFER.** No evidence needs it; adds migration and replay cost. |
| **D. Controlled-English or natural-language source** | Authors write prose that parses to rules | **DEFER.** Highest ambiguity, no probe, large surface. |

## Why B

- Probe B showed the existing `when / if / then / once` is already close to a good intermediate form. The semantic wrapper tried was *more verbose*.
- So the language layer is mostly about **families/defaults, provenance, and generation recipes**, not about re-expressing rules.
- The dependency direction stays: authoring source -> existing structures. Nothing in the runtime knows the source exists.

## Concepts, final disposition

| Concept | Disposition |
|---|---|
| Family/default normalization | ADOPT narrowly (one explicit parent, scalar defaults, explicit overrides) |
| Existing rule IR | KEEP / REUSE |
| Effect capability boundary | ADOPT (current 13 effects are the starting boundary; unknown effects fail at build time) |
| Build-time normalizer | ADOPT WITH CONSTRAINTS |
| Structured provenance / source references | ADAPT |
| Declared contracts / invariants | ADAPT; adopt where checks already exist |
| Property/determinism tests | ADAPT: reuse the repeat-equality and independent-seed checks from probe C |
| Meaning separated from presentation | KEEP (already the shape: pack vs skin) |
| Explainable surface (`explain`/`diff`) | ADAPT later; `probe` and the why log are the seed |
| Event sourcing | DEFER |
| Datalog / logic engine | DEFER |
| Controlled English | DEFER |
| Estate-wide shared kernel | UNKNOWN; wait for a second real domain |
