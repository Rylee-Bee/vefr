# Plan: the features catalog — VEFR

Goal: make tests/test_features.py and tests/test_features_shelf.py pass, and keep tests/test_cli_help.py green: a read-only catalog of what VEFR can do (docs/features.json, already written), a pack scan, the `vefr features` verb, `GET /api/features`, and two shelves in the studio. You do NOT write code yourself: workers do, via `offload`. Your job is to dispatch, verify, and report honestly. Rylee approved this work on 2026-10-02.

## Tasks
| ID | What | Brief | Acceptance (repo root, after the patch is applied and committed) | Tier |
|---|---|---|---|---|
| F1 | `src/vefr/features.py`: load, drift check, pack scan, report | `docs/plans/features/briefs/F1.md` | `bash tests/run.sh tests/test_features.py -k "catalog or drift or scan or report"` | `-m code` |
| F2 | the `vefr features` verb (thin `cmd_features`) | `docs/plans/features/briefs/F2.md` | `bash tests/run.sh tests/test_features.py -k cli && bash tests/run.sh tests/test_cli_help.py` | `-m code` |
| F3 | `GET /api/features` | `docs/plans/features/briefs/F3.md` | `bash tests/run.sh tests/test_features.py -k api` | `-m code` |
| F4 | the studio shelves: `web/js/features.js`, `api.js`, the mount | `docs/plans/features/briefs/F4.md` | `bash tests/run.sh tests/test_features_shelf.py` | `-m code` |

Dependencies: F2 and F3 need F1 committed; F4 needs F3. All four stay in their own files.

## How to delegate
Workers run in throwaway clones of this repo. Dispatch one at a time:
`offload agent -m code --repo . --brief docs/plans/features/briefs/<ID>.md --name features-<id> "Implement task <ID> per the brief"`
It prints a `--- apply:` command: run it, then run the task's acceptance command yourself. A worker's claim is worth nothing; the acceptance run is the truth. Commit accepted work locally with `git add <the files the brief allows> && git commit`; never push.

## Budget and rules
- At most 5 worker runs in total (retries count; a retry needs a new brief quoting the failing output). At most 40 minutes.
- Never edit, delete or weaken any test or fixture named in the acceptance column, or anything under `tests/fixtures/*skin*|*floor_v2*|*features*`. If a test looks wrong or contradicts a brief, do NOT work around it: stop that task and report the conflict (the most important rule). Do not special-case a test (no spelling a word around a grep, no checking for the test harness).
- No deploys, no push, no network, no sudo. You have no Edit/Write tools; if a worker fails twice on a task, mark it blocked and move on. Never commit `PLAN.md` copies or `node_modules` (add only the files the brief allows: `git add <paths>`, not `git add -A`).
- Another foreman or two are running on this machine: keep test runs sequential and small; run the FULL suite once at the end with `bash tests/run.sh -x`.
- Out of scope, escalate if proposed: editing `docs/features.json` (the catalog is the owner's data), more than one new route, any POST/PUT/DELETE route, anything under `scripts/` or `.github/`, new dependencies.

## Final report (your last message must END with this JSON on one line, nothing after it)
{"tasks": {<one entry per task id>: "done|blocked|escalated"}, "worker_runs": <int>, "acceptance_pass": {<id>: true|false}, "full_suite_pass": true|false, "escalations": ["short reason", ...]}
Before it, write 3-6 plain sentences: what is verified, what is not, and anything the owner must decide.
