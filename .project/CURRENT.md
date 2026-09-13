# CURRENT — vefr

> **Live truth lives in `agent-sync status` and `git log`.** This
> file is orientation, not a mirror of HEAD. Refresh the orientation
> when the *phase* changes; let Git tell you the SHA.

## Phase

Refinement pass after Play-Nice adoption. Engine rules and Play-Nice
cooperation boundaries are settled; the Storyteller capability work is
in flight and preserved as WIP. Engine is *not* in active feature
development.

## Active WIP (intentionally preserved)

Storyteller capability: benchmark harness, NPC action schemas, fixture
scenarios, and a second storyteller pack set covering small language
models. See AGENTS.md "Active checkout and Storyteller WIP" for the
exact protected-file list and the rule against staging them.

## Known protected work

| Item | Path / scope | Source of truth |
|---|---|---|
| Storyteller capability WIP | 5 modified + 20 untracked files | AGENTS.md "Active checkout" |
| Play-Nice adoption pin | `21b6841a50a1b0d459a760861385e99679852430` | `.project/contracts/adoption.yaml` |
| Sample world pack (Emberfield) | `worlds/sample-world/` | `worlds/sample-world/` |
| Three lore packs | `worlds/lore/{norse,historical-event,norse-runes}/` | each pack's `LICENSE.md` |

## Next decision

Storyteller architecture (how Rosa/taqueria fixtures move between
engine / pack / harness — see "Deferred" below). Do not begin without
Rylee's design call.

## Deferred architecture

- **Storyteller fixture placement.** The current Storyteller benchmark
  includes a single anchor scenario (`rosa-after-close`) that carries
  private-pack flavor (`Rosa`, `Mateo`, the taqueria, the
  transmitter). The engine's `AGENTS.md` "Never" rule says the engine
  must not name any specific game. Possible structural directions:
  A. fixture stays in engine but becomes engine-neutral; B. fixture
  becomes pack-supplied; C. scenario/tests move into the specific world
  pack; D. evidence insufficient. **Classification: D** — the
  Storyteller WIP itself acknowledges the question
  (`tests/test_npc_action.py:243-250`) but has not settled it. Do not
  restructure as part of a refinement pass.

## Verification entry points

```bash
# Gate - run before any "done" claim
uv run --group test ruff check src tests
uv run --group test pytest -q

# Pack integrity
uv run --group test norns validate --pack worlds/sample-world

# Session-start health
uv run --group test norns doctor   # set VEFR_LIVE_URL to check a stack

# Authority check
cat .project/contracts/adoption.yaml | head -10
```

## Ad-hoc state (refresh when phase changes)

| Item | Value |
|---|---|
| Working tree | dirty (Storyteller WIP, see above) |
| Origin | `https://github.com/Rylee-Bee/vefr.git` |
| Last commit at write time | see `git log -1` for the current SHA |