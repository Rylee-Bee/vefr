# Post-Act 2 hardening handoff

Status: **plan only**. This records the smallest follow-up work justified by the post-#236 review. It does not authorize a general refactor.

## Why this exists

The first real multi-act work found an honest seam: VEFR now has more than one code path reading and interpreting the same pack facts.

The next work should reduce duplicated interpretation only where a concrete invariant is already shared.

## Do these next

### 1. Make pack reads stay inside the pack

**Finding.** `world.py` and `maplab.py` both turn act/region names from pack data into filesystem paths. The tile/weave path already uses containment helpers, but the primary runtime/validator readers do not consistently share that guard.

`SECURITY.md` also says untrusted packs are validated on every load, while runtime `load_world()` is not currently routed through `maplab.validate()`.

Treat this as a containment/threat-model hardening issue until a crafted pack proves an exploit.

**Tests first:**
- a region name that tries to leave its act cannot make `world.load_world()` read outside the pack;
- the same is true for `maplab.load_pack()`;
- a valid ordinary pack still loads byte-for-byte/shape-for-shape as before where pinned.

**Implementation rule:** share only the smallest raw pack-reading/path-containment operation both readers actually need. Do not merge the runtime loader and validator loader.

### 2. Fix the unreachable Desk validator

**Finding.** Desk validation currently sits inside a branch that already continued unless `ruleset == "cooking"`, so the `ruleset == "desk"` check cannot run.

**Tests first:**
- a Desk act with fewer than two non-empty headlines fails validation and names the act;
- the existing valid Desk fixture stays green.

Then move the Desk check to reachable control flow. No Desk contract expansion.

### 3. Finish Act 2 validation parity before act switching

#236 is B1, not the end of validation work. Later acts now get law, door, lock and enemy checks, but full region geometry is still intentionally first-region-only.

Before a real Act 2 becomes playable, extend existing region invariants across every declared region in every act where they already make sense.

At minimum, pin representative later-act failures for:
- malformed/non-rectangular geometry;
- unreachable or invalid authored map facts already checked on the first region;
- region asset/path checks that are part of today's validator contract.

Do not invent new geometry rules. This is parity with existing checks, not a new validator design.

### 4. Add one rules conformance corpus

The rules contract is executable in three places today:
- `maplab.py` validates it;
- `cli.py` decides what is safe to bake;
- `web/packaged.html` decides what the runtime accepts.

Keep the implementations separate for now, but make disagreement testable.

Add a compact shared corpus with valid and invalid representatives for the current event, condition and action shapes, and assert that validator, baker and browser runtime agree on accept/reject behavior.

Do this **before** adding more rule vocabulary.

## Order

1. Pack-read containment.
2. Desk validator bug.
3. Act 2 validation parity.
4. Rules conformance corpus.

Items 1 and 2 are small enough to land independently. Item 3 should land before real act advancement. Item 4 should land before the next rules-vocabulary expansion.

## Acceptance

| Work | Done when |
|---|---|
| Pack containment | both primary readers refuse traversal-shaped act/region paths; valid packs are unchanged |
| Desk validation | an invalid Desk headline set fails; the valid fixture passes |
| Act 2 parity | representative later-act region failures are caught by the same existing invariants as the first region |
| Rules conformance | one corpus proves validator, baker and browser accept/reject the same current shapes |

Run the normal gate after each slice:

```bash
uv sync --group test
uv run --group test ruff check src tests scripts
uv run --group test pytest -q
python3 scripts/check_public_surface.py
uv run --group test norns validate --pack worlds/sample-world
```

## Explicit non-goals

- no Blueprint Format 2;
- no estate-wide language/kernel abstraction;
- no large `maplab.py` / `cli.py` / player split just for file size;
- no real Act 2 switching in this handoff;
- no equipment work;
- no new rules vocabulary;
- no broad documentation cleanup campaign.

The extraction rule remains the one already recorded in `.project/DECISIONS.md`: share machinery only when two real consumers need the same operation and invariants. The pack-reading seam now appears to meet that bar; the rest should stay local until evidence says otherwise.
