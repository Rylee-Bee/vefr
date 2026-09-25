# CURRENT — vefr

> **Live truth lives in `git log`, `gh pr list`, and the gate.** This
> file is orientation, not a mirror of HEAD. Refresh it when the
> *phase* changes; let Git tell you the SHA.
>
> Last refreshed: 2026-09-25.

## Phase

**Game plan Phase 1 → 2, engine running ahead of the game.**
The engine is the bones; the demo game is the flesh, built in a
separate private pack repo. The plan is one playable act per slice,
and each act's fun gate must pass before the next begins.

| Slice | Engine (this repo) | Game pack (BJ repo) |
|---|---|---|
| Phase 0 — boundary | Done, PR #23 | — |
| Act 1 — cooking | Ruleset + act-runner, PR #24 | Content proposed; **owner taste-pass pending** |
| Act 2 — desk | Ruleset + world-knowledge loop, PR #27 | Not started |
| Rulesets guide | `docs/guides/rulesets.md`, PR #28 | — |

**The one next step:** the owner plays Act 1 as the woven file (the
"smile test"). Only after it passes: bump the BJ pack's vefr pin
(it is on `fc0e798`, before the desk ruleset) and write Act 2 content.
Do not start engine work for Act 3+ until Act 2 has been played.

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

1. **munr's fate (D5).** Recorded as "retire"; in reality it is
   active and the game plan casts it as a later pack. See the
   2026-09-25 entry in `DECISIONS.md`.
2. **Local private pack `worlds/rylee-alpha-world/`** (gitignored):
   active, or retire? Status UNKNOWN.
3. **Non-CC0 art still fetchable on GitHub** (commit `948df78`,
   2026-09-06): no branch contains it any more, but GitHub still
   serves the commit by SHA. Purging it means a GitHub support
   request, not a force-push. Owner-gated.

## Known debt (small, safe to pick up)

- **D6 half-done:** `tests/test_cooking_contract.py` and
  `tests/test_kitchen_loop.py` still carry game-pack names in their
  fixture strings. D6 says pack-owned fixtures live in the pack;
  neutralize them the way `tests/fixtures/make_kitchen_pack.py` did.
- **PR #29** (`fix/openai-compatible-max-tokens`): all checks green
  since 2026-09-24, awaiting review.
- **CI-ignored Storyteller tests** (`test_npc_action.py`,
  `test_storyteller_benchmark.py`) point at tracker item "#50"; it is
  not a GitHub issue on this repo. Tracker location UNKNOWN.
- `.project/` still holds the 2026-09 benchmark-era reports and
  scripts (`round*`, `qualifying_v2*`, `benchmark_r4.py`). History, not
  current work.

## Branches

| Branch | Status |
|---|---|
| `main` | trunk; land by PR (convention — protection does not require reviews) |
| `fix/openai-compatible-max-tokens` | PR #29, green |
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
uv run --group test pytest -q \
  --ignore=tests/test_npc_action.py \
  --ignore=tests/test_storyteller_benchmark.py
python3 scripts/check_public_surface.py

# Pack integrity
uv run --group test norns validate --pack worlds/sample-world

# Session-start health
uv run --group test norns doctor   # set VEFR_LIVE_URL to check a stack
```

Run the full gate even for docs-only commits: `tests/test_pack_neutrality.py`
audits `README.md`, `AGENTS.md`, `ROADMAP.md`, and `docs/`.
