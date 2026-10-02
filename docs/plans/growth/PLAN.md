# Plan: growth (levels or learning by doing) — VEFR

Goal: build `design/growth.md` so the five red test files below go green. You do NOT write code yourself: workers do, via `offload`. Your job is to dispatch, verify, and report honestly.

## Tasks
| ID | What | Brief | Acceptance (repo root, after the worker's patch is applied and committed) | Tier |
|---|---|---|---|---|
| T1 | validator, `load_pack`, bake of `VEFR_GROWTH` + enemy `xp` | `docs/plans/growth/briefs/T1.md` | `uv run pytest tests/test_growth_validator.py -q` | `-m code` |
| T2 | the pure `window.VEFR_GROWTH_ENGINE` block in the player | `docs/plans/growth/briefs/T2.md` | `uv run pytest tests/test_growth_engine.py -q` | `-m code` |
| T3 | wire it into the player (award, lines, hp/atk, save) | `docs/plans/growth/briefs/T3.md` | `uv run pytest tests/test_growth_play.py -q` | `-m code` |
| T4 | docs: glossary, rulesets guide, mark the design note built | `docs/plans/growth/briefs/T4.md` | `uv run pytest tests/test_growth_docs.py -q` | `-m code` |

Dependencies: T1 and T2 are independent (T1 edits Python and ONE placeholder line in `web/packaged.html`; T2 adds one block to `web/packaged.html`: apply T1 first, then T2, to avoid a conflict). T3 needs T1 and T2 committed. T4 needs T3 committed.

## How to delegate
Workers run in throwaway clones of this repo. Dispatch one at a time:
`offload agent -m code --repo . --brief docs/plans/growth/briefs/T1.md --name growth-t1 "Implement task T1 per the brief"`
When it finishes it prints a `--- apply:` command: run it, then run the task's acceptance command yourself. A worker's claim is worth nothing; the acceptance run is the truth. Commit accepted work locally (`git add -A && git commit -m "growth T1: ..."`); never push.

## Budget and rules
- At most 6 worker runs in total (retries count; a retry needs a new brief quoting the failing output). At most 45 minutes.
- Never edit, delete or weaken any `tests/test_growth_*.py` or `tests/fixtures/*growth*`. If a test looks wrong or contradicts a brief, do NOT work around it: stop that task and report the conflict (this is the most important rule).
- After T3 also run the FULL suite once: `uv run pytest -q -x`. Everything that passed before must still pass.
- Never run deploys, push, or touch the network. You have no Edit/Write tools; if a worker fails twice on a task, mark it blocked and move on.
- Out of scope, escalate if a worker proposes it: any change to `design/growth.md` beyond T4, a `grows` rule event, equipment, anything under `worlds/` other than via the fixture builder.

## Final report (your last message must END with this JSON on one line, nothing after it)
{"tasks": {"T1": "done|blocked|escalated", "T2": "...", "T3": "...", "T4": "..."}, "worker_runs": <int>, "acceptance_pass": {"T1": true|false, "T2": true|false, "T3": true|false, "T4": true|false}, "full_suite_pass": true|false, "escalations": ["short reason", ...]}
Before it, write 3-6 plain sentences: what is verified, what is not, and anything the owner must decide.
