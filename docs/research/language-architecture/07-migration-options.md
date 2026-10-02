# 07 · Migration and compatibility

Rule: **old packs keep working unchanged, forever or until an explicit, announced end of life.**

## Strategy (recommended)

1. The source is **optional**. A pack with no source is exactly today's pack.
2. Normalization output must validate with today's `maplab.validate`. If it cannot, the source is wrong, not the validator.
3. **Legacy equivalence fixtures:** for each migrated structure, a test asserts `normalize(source) == existing JSON` byte-for-byte. Probes A and B already did this for enemy records and one rule.
4. Add a pack/source **version field** only when the first source format ships (no pack version field exists today). It names a reader; each reader has fixtures.
5. One editable source of truth per migrated structure. Generated JSON is marked generated; hand edits to it fail a check. `UNKNOWN` until the owner decides which side is editable (see 11).
6. Cottage migrates one structure at a time, creature families first, behind equivalence fixtures. Each step is its own PR.

## What does not migrate

Rules (already fine), growth tables (small), story text (canon is Rylee's).

## Retirement

Prove replacement -> keep evidence -> remove in a bounded cleanup PR. No removal before migration proof.
