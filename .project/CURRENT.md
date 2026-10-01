# CURRENT — vefr

> **Live truth lives in `git log`, `gh pr list`, and the gate.** This
> file is orientation, not a mirror of HEAD. Refresh it when the
> *phase* changes; let Git tell you the SHA.
>
> Last refreshed: 2026-10-01.

## 2026-10-01 (one long day)

**Landed and merged:** the studio loop's first slice (put a character in the game, play it in the studio, the edit log with one-level undo, the first-playable walk; `design/close-the-loop.md`,
`docs/guides/studio-edits.md`); grid tiles (one picture drawn as cells); the `vefr` front door with `vefr find`; Lab 1; first-run fixes; hero motion; the glossary with plain names first.
**Landed, recovered from a crashed offload Foreman fleet (2026-10-01):** the **rules engine**
(optional `flags`/`claims`/`people`/`rules` pack keys, the `maplab` validator, the pure engine wired into six player events with a `window.VEFR_WHY` log, and the Desk **Undo last edit** button;
`design/rules-when-then.md`) and **one-button Interact** (one verb on `E`/`Space`/`Enter`/`F` with the label, ring and gentle nudge; combat folded in; and **Start over** in the pause menu;
`design/one-button-interact.md`). Both were built by throwaway `offload` Foreman clones whose sessions crashed; the commits were rescued, merged, gated and landed by this session.
**Designed, approved to plan (no code yet):** named edits (`design/named-edits.md`), equipment with five slots (`design/equipment.md`), and a swappable UI skin (`design/ui-skin.md`).
**Deployed:** the studio at the home host from the merged commit; checked at runtime (health, the new routes, a weave and an inline play, a preview that wrote nothing).
**Known gaps:** the rules **Why did that happen?** button / `vefr why`, the Cottage rules demo and `add_rule` edits are not built (rules Tasks 5-7); the first-playable sticker is parked until a picture is chosen; the placement preview copies the whole pack to check it.
**Next, in order:** equipment; the rules why-log button and `vefr why`; the Cottage rules demo; `add_rule`/`add_reaction` edits; the UI skin tools and loader.

## Phase

**The studio grows by building its first game (owner, 2026-09-25).**
The engine is the bones; games are the flesh, in private pack repos.
The engine now grows one ruleset at a time, each one pulled in by the
first studio project: a classic town-and-dungeon roguelike remake in a
private pack. The owner learns game-making by building it; the engine
gets fun and accessible by carrying it. The BJ pack is paused and
becomes the **launch title** later.

Landed so far (all in `ROADMAP.md`): boundary, cooking, desk, rulesets guide,
Library L1 and L2, delve, fog of war, combat, loot + bag, the reward end
(gold, shop, using a thing), regions + doors, and - this stretch - the
commission board, the woven camera and sprites, the studio handbook, books
found in play, **autoexplore**, the **fog toggle**, **author grammars**, and
the **torch/reveal light**.

**The one next step:** the open `Next` entries in `ROADMAP.md` (enhancement
waves 1-2 and the studio items). Each pack-contract change is its own
ask-first. The old "play Act 2 before Act 3+" gate is retired by owner
decision (estate vision Q9).

**The north star (owner, 2026-09-30):** anyone can make their own game, their
own way - documented and taught. It decides what gets built next.

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

- `docs/guides/accessibility-contract.md` and `docs/guides/brain-socket.md`
  kept the demo game's name in a few places until the 2026-09-29/30 sweeps;
  both are now game-neutral, and the name sweep is recorded in `DECISIONS.md`.

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
