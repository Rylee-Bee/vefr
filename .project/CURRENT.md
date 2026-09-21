# CURRENT — vefr

> **Live truth lives in `agent-sync status` and `git log`.** This
> file is orientation, not a mirror of HEAD. Refresh the orientation
> when the *phase* changes; let Git tell you the SHA.

## Phase

**Engine-as-game era.** The fleet capability season landed
(2026-09-13/16, `feat/fleet-storyteller` merged). The engine is now
in its next phase: vefr becomes a game-building engine that is itself
a game. The orchestration plan (`VEFR-ORCHESTRATION-PLAN-2026-09-21.md`)
has 15 work packages across 5 weeks. WP1 (defect bundle), WP2
(bundled-brain), WP10 (title card), and WP11 (room acknowledgments)
have landed on feature branches.

**Key owner decisions (2026-09-21):**
- DD1: C+A synthesis (the game IS making something real, plus lean-in
  workshop rooms becoming alive/responsive)
- DD2: Theme = Workshop (iterate via OpenDesign)
- DD3: Export = game-quality (title card + ambient CSS on woven HTML)
- D3′: Brain bundled inside the vefr container (not external)
- D4′: BJ pack license = CC-BY-4.0
- D5: Retire munr (archive repo, keep little-fox pack safe)
- D6: Fixture placement = A (BJ-pack-supplied, content follows ownership)
- D7: BJ canonical home = `code/Rylee-Bee/burrito-journalism`
- Model fleet: Qwen3-0.6B + Qwen3-1.7B + SmolVLM2-500M + bge-m3
  (~2.8GB total, all Apache-2.0 or compatible)

## Known protected work

| Item | Path / scope | Source of truth |
|---|---|---|
| Play-Nice adoption pin | `0cee0652fb6f13c440b1fd9cc5d78fd87cdca8ad` | `.project/contracts/adoption.yaml` |
| Sample world pack (Emberfield) | `worlds/sample-world/` | `worlds/sample-world/` |
| Three lore packs | `worlds/lore/{norse,historical-event,norse-runes}/` | each pack's `LICENSE.md` |

## Active branches

| Branch | WP | Commits | Status |
|---|---|---|---|
| `feat/hygiene-bundle` | WP1: B1+B3+B4+B6 defects | `b77e668` | landed, needs PR |
| `feat/bundled-brain` | WP2: container + quadlet + docs | `178aac4` | landed, needs PR |
| `feat/export-title-card` | WP10: title screen for woven HTML | `12be191` | landed, needs PR |
| `feat/room-acknowledgment` | WP11: workshop room acks | `4f5cec8` | landed, needs PR |

## Next decisions

None currently blocked. The fixture placement question (D6) is resolved:
BJ-pack-supplied. The model fleet is locked.

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
| Working tree | `git status` for live state |
| Origin | `https://github.com/Rylee-Bee/vefr.git` |
| Branch | `git branch --show-current` for live state |
| Last commit | `git rev-parse HEAD` for live state |

> **Agent note:** This section is orientation, not a mirror of HEAD.
> Always verify with git commands, not this table.
