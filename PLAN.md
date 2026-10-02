# Plan: devtools — `vefr publish`, `vefr look`, `vefr probe`, doctor tooling rows

Goal: make `tests/test_devtools.py` and `tests/test_cli_help.py` pass. You do NOT write code yourself: workers do, via `offload`. Your job is to dispatch, verify, and report honestly.

## Tasks
| ID | What | Brief | Acceptance (repo root, after the patch is applied and committed) | Tier |
|---|---|---|---|---|
| D1 | `src/vefr/devtools.py`: publish + `tooling_checks`; `cmd_publish` in cli.py | `docs/plans/devtools/briefs/D1.md` | `bash tests/run.sh tests/test_devtools.py -k "publish or tooling_checks"` | `-m code` |
| D2 | look + probe (Playwright); `cmd_look`, `cmd_probe`; all three parsers registered in `vefr_main` | `docs/plans/devtools/briefs/D2.md` | `bash tests/run.sh tests/test_devtools.py tests/test_cli_help.py` | `-m code` |
| D3 | doctor tooling rows; `docs/guides/vefr-command.md` | `docs/plans/devtools/briefs/D3.md` | `bash tests/run.sh tests/test_devtools.py tests/test_doctor.py tests/test_cli_help.py` | `-m code` |

Dependencies: D2 needs D1 committed (same file); D3 needs D2 committed.

## How to delegate
Workers run in throwaway clones. Dispatch one at a time:
`offload agent -m code --repo . --brief docs/plans/devtools/briefs/D1.md --name devtools-d1 "Implement task D1 per the brief"`
It prints a `--- apply:` command: run it, then run the task's acceptance command yourself. A worker's claim is worth nothing; the acceptance run is the truth. Commit accepted work locally (`git add -A && git commit -m "devtools D1: ..."`); never push.

## Budget and rules
- At most 5 worker runs in total (retries count; a retry needs a new brief quoting the failing output). At most 40 minutes. Another foreman is running on this machine: keep test runs sequential.
- Never edit, delete or weaken `tests/test_devtools.py` or `tests/test_cli_help.py`. If a test looks wrong or contradicts a brief, do NOT work around it: stop that task and report the conflict (this is the most important rule).
- After D3 run the FULL suite once: `bash tests/run.sh -x`. Everything that passed before must still pass (tests needing Chromium may skip).
- No deploys, no push, no network, no sudo. You have no Edit/Write tools; if a worker fails twice on a task, mark it blocked and move on.
- Out of scope, escalate if proposed: anything in `web/packaged.html`, new dependencies in `pyproject.toml` (Playwright is already in the `test` group; import it lazily with a plain error message if missing), any change to `scripts/` or `.github/`.

## Final report (your last message must END with this JSON on one line, nothing after it)
{"tasks": {"D1": "done|blocked|escalated", "D2": "...", "D3": "..."}, "worker_runs": <int>, "acceptance_pass": {"D1": true|false, "D2": true|false, "D3": true|false}, "full_suite_pass": true|false, "escalations": ["short reason", ...]}
Before it, write 3-6 plain sentences: what is verified, what is not, and anything the owner must decide.
