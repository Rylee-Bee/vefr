# Sonnet handoff: Phase A synthesis after Codex proof

> Status: handoff for Phase A synthesis · Owner: Rylee · Date: 2026-10-02  
> Parent campaign: PR #219  
> Codex proof branch: `experiment/language-proof-20261002`  
> Codex proof commit: `649034fe0c41d26f617c9020e2824207ea5d68a1`

## Task

Incorporate the completed Codex proof into Phase A, finish the research/current-state synthesis, and prepare the decision-grade packet for Opus 5.5.

**Do not begin implementation yet.**

## Codex disposition

**GO WITH CONSTRAINTS.**

The earned scope is narrow and useful:

```text
optional build-time semantic authoring
    ↓
mandatory validation
    ↓
normalization
    ↓
existing VEFR pack structures
    ↓
existing deterministic runtime
```

Do not reinterpret this as approval for:

- a new runtime language;
- full event sourcing;
- Datalog / logic engine;
- arbitrary-English parsing;
- estate-wide shared-kernel extraction;
- plugin-style pack execution;
- broad pack migration.

## What Codex proved

### Probe A: families

**PASS WITH CONSTRAINTS.**

- Three real Cottage creatures were represented through one family/default declaration.
- Expansion recreated the existing enemy records exactly.
- Current VEFR validation accepted the normalized result.
- Ten repeated scalar occurrences were removed.
- Actual guardian runtime semantics remain UNKNOWN because guardians are not wired yet.
- Synthetic `drops-on-defeat` proved timing can be modeled without pretending a guardian simply carries a key.

Important conclusion:

> family + instance + explicit overrides is promising.

Do not add inheritance/composition machinery beyond what evidence requires.

### Probe B: rules

**STRONG PASS.**

Codex used Cottage's real `the-keeper-knows` rule and proved:

```text
semantic wrapper
→ current rule JSON
→ current validator
→ shipped VEFR_RULES_ENGINE
→ actual woven-player DOM
```

Behavior matched for:

- false condition;
- true condition;
- unrelated event;
- repeated event;
- once semantics;
- action ordering;
- state;
- speech;
- why/provenance;
- no `give` → `picks-up` chaining.

Important conclusion:

> VEFR's existing `when / if / then / once` format is already very close to a good semantic IR.

The experimental semantic wrapper is **more verbose** than current rule JSON.

Do not replace the existing rule shape unless a concrete authoring benefit is proven.

### Probe C: themed floors

**PASS WITH CONSTRAINTS.**

- Existing `generate_floor_v2` remained unchanged.
- Layout and dressing use separate deterministic seeds.
- Changing dressing does not change geometry.
- Repeat inputs produce repeat output.
- Stair reachability survives.
- Impossible placement fails.
- Unsupported generator controls fail explicitly rather than silently degrading.
- Props are metadata only.
- No real authored ending room currently exists; ending pass-through was synthetic.
- Dressing runtime parity is N/A because the experiment is build-time only.

Important conclusion:

> **Theme owns vocabulary. Generator owns arrangement.**

But only for capabilities the current generator actually supports.

Do not claim support for corridor width, loop frequency, signature rooms, or guardian progression until machinery exists.

## Existing save-state issue discovered

Reload currently preserves WHY history but resets:

```text
rule flags
fired / once markers
```

This is existing VEFR behavior, not caused by the language experiment.

Treat rule/save durability as a real architecture decision before new progression systems depend heavily on `once` or flags.

## Effect boundary

The proof supports:

```text
packs define words/content
game dialect defines legal meaning/signatures
host owns actual effect execution
```

Unknown effects must fail during build-time validation.

Do not let a pack gain executable authority merely by declaring a new word.

Current effect vocabulary should be treated as the starting capability boundary.

## Current architectural read

The evidence currently supports something closer to:

```text
AUTHORING DEFINITIONS
  families / instances / vocabulary

EXISTING VEFR RULES
  when / if / then / once

GENERATION RECIPES
  parameters / content vocabulary / guarantees

        ↓

  NORMALIZATION

        ↓

EXISTING VEFR STRUCTURES

        ↓

EXISTING DETERMINISTIC RUNTIME
```

This is simpler and safer than introducing a new universal runtime model.

## Kernel status

Codex returned a provisional **HYBRID**.

Do not call the estate-wide kernel proven.

Still UNKNOWN / unproven:

- behavioral traits;
- generalized relations;
- guardian semantics;
- universal estate kernel;
- dialect extension system;
- full source-map/provenance architecture;
- runtime themed generation;
- signature-room/topology semantics.

A paper non-game probe may support plausibility only.

Do not extract a shared library yet.

## Evidence-based defaults for Phase A

Carry these forward unless the synthesis finds contrary evidence:

| Concept | Current disposition |
|---|---|
| family/default normalization | ADOPT narrowly |
| existing rule IR | KEEP / REUSE |
| effect capability boundary | ADOPT |
| build-time semantic normalizer | ADOPT WITH CONSTRAINTS |
| structured provenance/source references | ADAPT |
| declared contracts/invariants | ADAPT; likely adopt where existing checks already exist |
| event sourcing | DEFER |
| Datalog / logic engine | DEFER |
| arbitrary controlled-English source | DEFER |
| estate-wide shared kernel | UNKNOWN / defer until a second real domain exists |

## Phase A deliverable

Complete the synthesis and produce/update the decision packet with:

1. current VEFR state;
2. current Cottage state;
3. semantic census;
4. prior-art synthesis, with the Codex correction addendum authoritative;
5. Codex proof results;
6. exact simplifications proven;
7. concepts that did **not** earn implementation;
8. recommended smallest grammar / normalization model;
9. API/CLI implications;
10. migration/compatibility strategy;
11. save-state issue and recommendation;
12. themed-floor implications;
13. durability/versioning/conformance requirements;
14. remaining owner decisions;
15. final disposition: `GO`, `GO WITH CONSTRAINTS`, or `PARK`.

Then package it for Opus 5.5.

## What Opus should be asked to produce

If Phase A still earns GO or GO WITH CONSTRAINTS, the Opus packet should ask for:

- an incremental implementation campaign;
- VEFR + Cottage together;
- Sonnet as integrator;
- bounded offload Foremen;
- acceptance tests first;
- old packs preserved;
- existing runtime preserved;
- no speculative kernel extraction;
- no implementation beyond what Phase A actually earned.

## Strong implementation bias from the proof

If Phase A still lands on **GO WITH CONSTRAINTS**, the likely first implementation slice should be small:

```text
optional semantic source
+ family/default expansion
+ normalization
+ provenance
+ validation
+ legacy equivalence fixtures
```

Then use Cottage to prove it live.

Do not start with Studio/API/natural-language authoring.

Get the boring semantic spine correct first.

## Final reminder

The strongest outcome from Codex is not:

> we invented a language.

It is:

> **VEFR already has a language-shaped core, and we may be able to expose it with less code and less duplication without replacing the runtime.**

Optimize for that.
