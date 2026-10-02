# 04 · Prior art, synthesized

Source: [`../2026-10-02-language-prior-art.md`](../2026-10-02-language-prior-art.md). Its **Correction addendum (Codex, 2026-10-02) is authoritative** where it disagrees with the body.

## What survives the corrections

| Lesson | Standing |
|---|---|
| Keep authored data separate from the code that runs it (Inform 7, Ink, Yarn Spinner, Clausewitz raws) | Supported by many independent designs. Fits VEFR's existing pack/engine split. |
| A small closed vocabulary beats open extension (ECS, JSONLogic, json-rules-engine) | Supported; matches the effect capability boundary. |
| Declared schemas help, but identifiers do not promise compatibility | **Corrected.** `$schema`/`$id` identify; they do not guarantee old packs stay valid. Compatibility needs readers, fixtures and migrations. |
| Event sourcing gives replay, tests and provenance in one mechanism | **Corrected.** Conditional on complete events and replay logic; real cost in schema evolution. Compare "current state plus structured evidence" first. |
| Datalog terminates because there are no cycles | **Corrected.** Recursion is allowed; finite function-free Datalog reaches a fixed point, arithmetic can break that. |
| Which maintenance choices killed TADS, Penrose, others | **Unverified.** Do not decide VEFR architecture on these. |
| StoryNexus is the closest project | **Unverified analysis**, not fact. |

## Net

The research does not argue for a new engine model. It argues for: closed vocabulary, one source of truth, explicit versioned readers, and caution about big mechanisms (event sourcing, logic engines) that VEFR's evidence does not yet need.
