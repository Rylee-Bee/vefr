# 07 · Migration and compatibility

Rule: **old packs keep working unchanged, forever or until an explicit, announced end of life.**

## Strategy (recommended)

1. The source is **optional**. A pack with no source is exactly today's pack.
2. **Validate twice.** The source is validated before normalization (closed fields, known families, no cycles, unknown event/effect names rejected). The normalized result is then put back into the whole pack and run through today's `maplab.validate` and `maplab.rules_errors`, because cross-references (items, regions, rule ids) only resolve in the full world. This is what the probes did: they substituted the normalized records into the loaded world and validated that. If the normalized world fails, the source is wrong, not the validator.
3. **Legacy equivalence fixtures:** for each migrated structure, a test asserts `normalize(source)` is *structurally equal* to the existing JSON (defined below). Probes A and B already did this for enemy records and one rule.
4. Add a pack/source **version field** only when the first source format ships (no pack version field exists today). It names a reader; each reader has fixtures.
5. One editable source of truth per migrated structure. Generated JSON is marked generated; hand edits to it fail a check. `UNKNOWN` until the owner decides which side is editable (see 11).
6. Cottage migrates one structure at a time, creature families first, behind equivalence fixtures. Each step is its own PR.

## What does not migrate

Rules (already fine), growth tables (small), story text (canon is Rylee's).

## Retirement

Prove replacement -> keep evidence -> remove in a bounded cleanup PR. No removal before migration proof.

## Structural equality, defined

The probes asserted Python `==` on the parsed JSON values. That means:

- same keys and values at every depth;
- object **key order is ignored**;
- **list order matters** (the order of enemies in a region is part of the result);
- number types compare by value, so `3` equals `3.0` (avoid relying on that).

It does **not** mean the files are byte-identical. Byte equality also needs one canonical serializer (key order, indentation, trailing newline). Do not claim it until a serializer is chosen and tested. The fixtures should assert structural equality now, plus a separate canonical-bytes check only if the generated JSON is committed.
