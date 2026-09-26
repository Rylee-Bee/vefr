# CURRENT — vefr

> **Live truth lives in `git log`, `gh pr list`, and the gate.** This
> file is orientation, not a mirror of HEAD. Refresh it when the
> *phase* changes; let Git tell you the SHA.
>
> Last refreshed: 2026-09-25.

## Phase

**The studio grows by building its first game (owner, 2026-09-25).**
The engine is the bones; games are the flesh, in private pack repos.
The engine now grows one ruleset at a time, each one pulled in by the
first studio project: a classic town-and-dungeon roguelike remake in a
private pack. The owner learns game-making by building it; the engine
gets fun and accessible by carrying it. The BJ pack is paused and
becomes the **launch title** later.

| Slice | Engine (this repo) | Pack |
|---|---|---|
| Phase 0 — boundary | Done, PR #23 | — |
| Act 1 — cooking | Ruleset + act-runner, PR #24 | BJ: paused (launch title later) |
| Act 2 — desk | Ruleset + world-knowledge loop, PR #27 | BJ: paused |
| Rulesets guide | `docs/guides/rulesets.md`, PR #28 | — |
| **Library** | L1 landed: the book format, validator, API, Urðr's Library room, the export chapter. Next: L2, finding books in play | First studio project |
| Delve (proposed) | Ruleset: floors, items, weight, spells, turns | First studio project |

**The one next step:** Library slice L2, finding books in play (map
pickup, a resident gives one, earned), through the checklist in
`docs/guides/rulesets.md`. The owner approved this pack-contract
change on 2026-09-25; each later ruleset is its own ask-first.
The old "play Act 2 before Act 3+ engine work" gate is retired by owner
decision (estate vision doc Q9).

## Where things live

The vision and plan are **outside this repo on purpose** — they carry
private canon, and this repo is public.

| What | Where |
|---|---|
| Vision (owner's words govern) | estate `docs/vefr/VEFR-VISION-INTERVIEW-2026-09-22.md` |
| Plan: phases, acts, gates | estate `docs/vefr/VEFR-GAME-PLAN-2026-09-22.md` |
| Act 1 spec | estate `docs/vefr/VEFR-ACT1-SPEC-2026-09-22.md` |
| Older direction docs (09-21) | estate `docs/vefr/` (product direction, orchestration plan, inventory) |
| Demo game pack + its characters | `code/Rylee-Bee/burrito-journalism` (private; D7) |
| Engine UI | `web/` (workshop + `packaged.html` player); mockups in `design/` |
| Landed-change ledger | `ROADMAP.md` |
| Durable decisions | `.project/DECISIONS.md` |

The estate `media_files/designs/` holds copies of some plan docs.
Treat `docs/vefr/` as the canonical copy.

## Open owner decisions

None. "Should rumors read pack canon?" (raised 2026-09-25) was already
true: `saga.system_prompt` has carried the pack's `logbok.md` since
2026-08-31. The orchestration plan's "pack-blind" note was wrong; a
test now pins it (`test_rumor_prompt_carries_pack_canon`).

Closed 2026-09-25 (see `DECISIONS.md`): munr kept separate (D5
superseded); the local test packs deleted; commit `948df78` accepted as risk.

## Known debt (small, safe to pick up)

- **Kitchen screen shows town leftovers.** The woven Act 1 player renders
  the Whisper button, an `HP 0/0` bar, and an empty town canvas above
  the kitchen (seen in headless Chromium, 2026-09-25). Cosmetic; the
  kitchen loop itself plays clean.

- `docs/guides/accessibility-contract.md` and
  `docs/guides/brain-socket.md` name the demo game as a product (not
  its canon). Leave them unless the owner wants the docs fully
  game-agnostic.

Closed 2026-09-26: `norns chat` voice drafting looping (the WP5 voice
file repeated itself). The draft seam now dedupes repeated sentences —
see `ROADMAP.md`. Left open, found while fixing it: the interview writes
the first speaker's draft to the pack root's `voices/<name>.md` while an
acts-shape pack's live voice file is the region one.

## Branches

| Branch | Status |
|---|---|
| `main` | trunk; land by PR (convention — protection does not require reviews) |
| `oa/old-main-20260920` | local-only snapshot of main (last commit 2026-09-19); do not push |

## Known protected work

| Item | Path / scope | Source of truth |
|---|---|---|
| Play-Nice adoption pin | `0cee0652fb6f13c440b1fd9cc5d78fd87cdca8ad` | `.project/contracts/adoption.yaml` |
| Sample world pack (Emberfield) | `worlds/sample-world/` | `worlds/sample-world/` |
| Three lore packs | `worlds/lore/{norse,historical-event,norse-runes}/` | each pack's `LICENSE.md` |

## Verification entry points

```bash
# Gate - must match CI (.github/workflows/ci.yml)
uv sync --group test
uv run --group test ruff check src tests scripts
uv run --group test pytest -q
python3 scripts/check_public_surface.py

# Pack integrity
uv run --group test norns validate --pack worlds/sample-world

# Session-start health
uv run --group test norns doctor   # set VEFR_LIVE_URL to check a stack
```

Run the full gate even for docs-only commits: `tests/test_pack_neutrality.py`
audits `README.md`, `AGENTS.md`, `ROADMAP.md`, and `docs/`.
