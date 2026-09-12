# CURRENT — vefr

## State

| Area | Status | Evidence |
|---|---|---|
| Repository | healthy, working-tree dirty | `git status` shows M on `deploy/vefr.container`, `docs/guides/storyteller-packs.md`, `src/vefr/cli.py`, `src/vefr/generator.py`, `src/vefr/storyteller_test.py` |
| Last commit | `d929b0a` 2026-09-07 merge PR 51 ("docs: canonical checkout, archive stale handoffs, add CI") | `git log -1` |
| Active rule surface | AGENTS.md, AGENT_POLICY.md | project-specific engine/world-pack truth |
| Play-Nice adoption | adopted | `.project/contracts/adoption.yaml` pinned to `21b6841` |

## VEFR-specific truth (preserved)

- **Engine only.** VEFR owns the pack loader, journal, forge, vault,
  session/fork mechanics, inference-backend plumbing, and the maplab
  validator. World packs (Emberfield ships here; burrito-journalism and
  munr-story live in their own repos) are data-only.
- **Two CLIs:** `ratatoskr` (ops: skipa, test, weave, ferry) and `norns`
  (craft: chat, validate, build-map, verify). Both share one
  geometry/contract validator (`src/vefr/maplab.py`).
- **Bring-your-own-brain.** Any OpenAI-compatible LLM backend. Brain seam
  lives at `docs/guides/brain-socket.md`.
- **World packs are data.** `mkdir worlds/<name>` + four markdown files
  (or the acts shape). A pack author writes data, not code.
- **Deterministic surfaces stay deterministic.** World validation, map
  transforms, exports. Models operate at explicit generative edges.

## What changed in the adoption pass

| Path | Change |
|---|---|
| `.project/project.yaml` | new — manifest |
| `.project/contracts/adoption.yaml` | new — Play-Nice bundle pin |
| `.project/CURRENT.md` | new — this file |
| `.project/DECISIONS.md` | new — adoption decision |
| `AGENTS.md`, `AGENT_POLICY.md` | unchanged (engine-specific kernels preserved) |
| `src/**`, `docs/**`, `deploy/**` | unchanged (uncommitted WIP untouched) |

## Unknown / Deferred

- The uncommitted WIP in this kilo2 checkout belongs to the Storyteller
  lane and is intentionally preserved per AGENTS.md "Canonical checkout"
  note. Deferred to the next storyteller design session.

## NEXT

Nothing required (rule-wise). Storyteller WIP remains for Rylee's session.