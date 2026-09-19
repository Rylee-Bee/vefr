# CURRENT — vefr

> **Live truth lives in `agent-sync status` and `git log`.** This
> file is orientation, not a mirror of HEAD. Refresh the orientation
> when the *phase* changes; let Git tell you the SHA.

## Phase

Fleet-capability season. The Storyteller capability WIP **landed**
on `feat/fleet-storyteller` (lore `e74626c`, interface translator
`bdfb421`+`045f289`, fleet storyteller `e434249`, Foyer UI `fae6ca3`
— see ROADMAP.md 2026-09-13/15 entries). Branch is committed to
origin as of 2026-09-16. The working tree is dirty with an
in-flight fleet benchmark experiment; see AGENTS.md
"Working-tree state".

## Known protected work

| Item | Path / scope | Source of truth |
|---|---|---|
| Fleet benchmark experiment (dirty tree) | `.project/` reports, `bench/` reports/runs, `experiments/`, `web/shell*`, `design/owner/`, `src/vefr/chat.py`, `.project/DECISIONS.md` | AGENTS.md "Working-tree state" |
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
| Working tree | dirty (fleet benchmark experiment, see above) |
| Origin | `https://github.com/Rylee-Bee/vefr.git` |
| Branch | `main` (fleet-storyteller merged 2026-09-19) |
| Last commit at write time | see `git log -1` for the current SHA |