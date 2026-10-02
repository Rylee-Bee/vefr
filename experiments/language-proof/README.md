# Language proof, 2026-10-02

This is an isolated build-time experiment at PR #219 revision
`6943f13e60bdf8fd2922945e50cb053755c2566f`.
It does not define a supported pack format, change production code, or migrate saves.
No paid model calls, generator replacement, plugin loader, or merge are in scope.

Acceptance: exact family expansion, exact rule lowering and current validator acceptance;
shipped engine and woven-player equivalence;
separate layout/dressing randomness and explicit rejection of unsupported requests.
Private evidence must be written outside this checkout and must never be staged.

```bash
uv sync --group test
npm ci
uv run --group test pytest -q experiments/language-proof/test_prototype.py
uv run --group test python experiments/language-proof/run.py \
  --pack /absolute/private-pack --region REGION --sprite SPRITE \
  --rule RULE_ID --out /absolute/private-evidence
```

The runner reads source but never writes to the pack.
Its output includes PRIVATE story text and woven HTML: do not publish it.
The source comparison is forward lowering, not a supported reverse editor.
Effect signatures are owned by the existing validator; execution stays in the shipped player.

## Results

- A: **FIT WITH CONSTRAINTS**. Three real creatures expand exactly;
  ten repeated scalar occurrences become one shared declaration.
  Actual guardians remain unwired proposals/art, so real guardian runtime fit is UNKNOWN.
  Synthetic drops-on-defeat expands into existing drops; no carrying semantics are inferred.
- B: **identical**. Exact rule JSON, current validator, shipped engine traces,
  action order, state, speech, why, repeats, once, and reload comparison pass.
  A separate adversarial test confirms give does not chain a picks-up event.
  Reload preserves why but resets rule flags/once markers in both representations.
- C: **FIT WITH CONSTRAINTS**. Existing v2 layout unchanged;
  independent shared-PRNG dressing, repeat equality, reachable stairs,
  impossible placement and unsupported-control rejection pass.
  Props remain metadata. Geometry reachability does not prove combat balance or progression.
  Synthetic authored ending data passes through unchanged;
  no real authored ending room exists in the inspected private pack.
  Dressing runtime parity: N/A (build-time only).

## Disposition

**GO WITH CONSTRAINTS** for a reviewed, optional build-time family expander
and rule lowerer into the current pack structures.
HYBRID is a provisional organization of existing semantics, not proof of a universal kernel.
No production code is simplified by this experiment yet.
The rule source wrapper is more verbose than the current rule JSON;
do not require it without a concrete authoring benefit.

Unknown effects fail in the lowerer and validator.
The current runtime defensively skips an invalid rule instead of reporting a hard error;
build-time validation must therefore be mandatory before execution.

Next: agree the single editable source and generated-artifact ownership;
integrate optional normalization with legacy fixtures;
separately decide rule-save semantics and guardian/ending authoring.
Full event sourcing and a logic engine remain deferred.
The private Sonnet packet contains exact inputs, outputs, traces and detailed decisions.
