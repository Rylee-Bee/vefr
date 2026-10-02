# Plan: the skin loader — VEFR

Goal: make tests/test_skin_validator.py, tests/test_skin_apply.py and tests/test_skin_docs.py pass (design/ui-skin.md steps 4 and 5). You do NOT write code yourself: workers do, via `offload`. Your job is to dispatch, verify, and report honestly. Rylee approved this work on 2026-10-02.

## Tasks
| ID | What | Brief | Acceptance (repo root, after the patch is applied and committed) | Tier |
|---|---|---|---|---|
| K1 | validator, `load_pack`, bake of `window.VEFR_SKIN` | `docs/plans/skin/briefs/K1.md` | `bash tests/run.sh tests/test_skin_validator.py` | `-m code` |
| K2 | the player paints the skin | `docs/plans/skin/briefs/K2.md` | `bash tests/run.sh tests/test_skin_apply.py tests/test_quiet_ui.py tests/test_interact_play.py` | `-m code` |
| K3 | docs | `docs/plans/skin/briefs/K3.md` | `bash tests/run.sh tests/test_skin_docs.py` | `-m code` |

Dependencies: K2 needs K1 committed; K3 needs K2.

## How to delegate
Workers run in throwaway clones of this repo. Dispatch one at a time:
`offload agent -m code --repo . --brief docs/plans/skin/briefs/<ID>.md --name skin-<id> "Implement task <ID> per the brief"`
It prints a `--- apply:` command: run it, then run the task's acceptance command yourself. A worker's claim is worth nothing; the acceptance run is the truth. Commit accepted work locally with `git add <the files the brief allows> && git commit`; never push.

## Budget and rules
- At most 4 worker runs in total (retries count; a retry needs a new brief quoting the failing output). At most 40 minutes.
- Never edit, delete or weaken any test or fixture named in the acceptance column, or anything under `tests/fixtures/*skin*|*floor_v2*|*features*`. If a test looks wrong or contradicts a brief, do NOT work around it: stop that task and report the conflict (the most important rule). Do not special-case a test (no spelling a word around a grep, no checking for the test harness).
- No deploys, no push, no network, no sudo. You have no Edit/Write tools; if a worker fails twice on a task, mark it blocked and move on. Never commit `PLAN.md` copies or `node_modules` (add only the files the brief allows: `git add <paths>`, not `git add -A`).
- Another foreman or two are running on this machine: keep test runs sequential and small; run the FULL suite once at the end with `bash tests/run.sh -x`.
- Out of scope, escalate if proposed: changing `design/ui-skin.md` beyond its Status line, any change to `web/packaged.html` outside the allowed places, real artwork (Cottage owns it), contrast measurement (a later task), anything under `worlds/` except via the fixture builder.

## Final report (your last message must END with this JSON on one line, nothing after it)
{"tasks": {<one entry per task id>: "done|blocked|escalated"}, "worker_runs": <int>, "acceptance_pass": {<id>: true|false}, "full_suite_pass": true|false, "escalations": ["short reason", ...]}
Before it, write 3-6 plain sentences: what is verified, what is not, and anything the owner must decide.
