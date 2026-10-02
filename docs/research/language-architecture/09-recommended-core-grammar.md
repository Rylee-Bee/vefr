# 09 · Recommended smallest model

"Grammar" here means the shape of the optional authoring source, not `grammar.py`.

```
AUTHORING DEFINITIONS   families / instances / vocabulary
EXISTING VEFR RULES     when / if / then / once   (unchanged)
GENERATION RECIPES      parameters / vocabulary / guarantees
        |
   NORMALIZATION  (validate -> expand -> provenance)
        |
EXISTING VEFR STRUCTURES  ->  EXISTING DETERMINISTIC RUNTIME
```

## First slice: families

- A **family** has scalar `defaults` and at most one explicit `extends`. No implicit traits, no mixins, no behavior.
- An **instance** names a family and gives `properties` that override defaults.
- Expansion order: parent defaults, then family, then instance. Cycles, unknown parents and unknown fields **fail**.
- Output is exactly today's enemy record shape. Proven for real creatures (Codex probe A).

## Effects

- Packs define words and content. The engine's dialect defines legal signatures. The host runs effects.
- Unknown event or effect names fail at build time. Declaring a new word grants no authority.

## Provenance (adapt)

Each generated record carries a source reference (file, family, instance, override keys). Stored beside the pack, never in the runtime globals unless a feature needs it.

## Themed floors (adapt, capability-limited)

**Theme owns vocabulary; the generator owns arrangement.** Theme may set width, height, rooms, props, creature vocabulary and named guarantees (`reachable-stairs`, `nonblocking-dressing`). Layout and dressing use separate deterministic seeds. Props are metadata. Do not promise corridor width, loop frequency, signature rooms or guardian progression until the generator has them. Phase 2 (#215) is built after this lands.

## Durability requirements (from the plan)

- Conformance suite: legacy-equivalence fixtures plus a versioned reader per source format.
- Versioning and deprecation policy before the first release of the format.
- One source of truth; generated docs and CLI help come from it (the `features` catalog is the model).
- Kernel size budget: the semantic layer may not grow a second rule language.
- Named owner (Rylee) and a teachable one-page guide.
- Dogfood on Cottage. Honest exit ramp: if the slice does not shrink the Cottage pack or catch a real error, stop and revert.

## First implementation slice (if the gate passes)

Optional source + family expansion + normalization + provenance + validation + legacy-equivalence fixtures. No Studio, no API write routes, no natural language.
