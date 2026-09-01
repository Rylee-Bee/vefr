# Session handoff — vefr (2026-09-01 mid-morning)

> Where the repo + live bazzite stack stand as of 2026-09-01
> ~13:45Z. This is the document you paste at the top of the next
> agent session. All evidence below was re-checked within the
> past 5 minutes — commands are right next to the claim so any
> downstream agent can re-verify or roll back to truth.
>
> The previous handoff at `docs/guides/session-handoff.md` is
> stale (it references HEAD `8a88221` and the PR #29 ledger);
> this snapshot supersedes it.

## Verified right now (re-run any time)

| Check | Command | Result |
|---|---|---|
| Repo + working tree | `git status && git log --oneline -5` | clean, HEAD `a11e532` |
| All pushed | `git log --oneline origin/main -5` | matches local (`a11e532` is on `origin/main`) |
| Lint | `uv run --group test ruff check src tests` | All checks passed |
| Full test suite | `uv run --group test pytest -q` | **203 passed, 2 skipped, 1 warning in ~16s** |
| Bazzite engine health | `curl -sS -m 5 http://192.168.2.76:8820/api/health` | `{"ok":true,"service":"vefr","purpose":"it gives the hellos that never happened"}` |
| Bazzite world payload | `curl -sS -m 5 http://192.168.2.76:8820/api/world` (then inspect) | `title=Emberfield`, `phases=[dusk,dawn]`, `surface=combat`, `hero_start=[3,4]`, `voices=0` (sample-world is voice-less by design) |
| Bazzite journal | `curl -sS -m 5 http://192.168.2.76:8820/api/journal` | 1 entry (kind `stefna_letter`), 0 starred |
| llama.cpp reachable | `curl -sS -m 5 -o /dev/null -w "%{http_code}" http://192.168.2.76:8081/v1/models` | 200 |
| Live deployed pack validates | `uv run --group test norns verify` (with `VEFR_LIVE_URL=http://192.168.2.76:8820` if querying a running stack) | passes |
| Deploy artefact exists | `git log --oneline -1 origin/main` | `a11e532` (the wrapper harden + tunnel health probe + bare-name path fix landed together) |

### **Important URL note (caught 2026-09-01)**

**UPDATE 2026-09-01 ~15:00Z: the alias is fixed.** `~/.ssh/config`
now has `Host bazzite` → `HostName 192.168.2.76`, `User rylee`,
`IdentityFile ~/.ssh/id_ed25519` — verified with
`ssh bazzite 'echo ok: $(whoami)@$(hostname)'` → `ok: rylee@rylee-bazzite`.
Use the alias `bazzite` for SSH/rsync/deploy (`VEFR_DEPLOY_HOST=bazzite`),
which carries the correct user; a bare IP literal drops the user and
fails as `ryleeb@192.168.2.76: Permission denied`. The deploy wrapper
still tunnels its health probe, so it never depended on this either way.

Original note (2026-09-01 morning, now historical): the alias then
resolved to 192.168.2.145 (homelab-vm), and the wrapper's SSH-tunnelled
probe existed because of it.

## What landed last session

**PR #30 (merged `076ef57`, "feat(deploy): harden ferry deploy as
the single ship button"):**

| Change | File | What |
|---|---|---|
| Hardened deploy | `src/vefr/cli.py` | `ratatoskr ferry deploy` owns the end-to-end path: pre-flight (`pytest -q` + `norns validate --pack sample-world`), rsync, image-SHA-skip-build (`vefr.engine_sha` label), `systemctl --user restart vefr`, named-volume ensure, post-deploy health + `maplab verify`. New flags: `--init`, `--skip-tests`, `--rebuild`, `--no-health`. Refuses to run with the silent `bazzite` default — forces operators to set `VEFR_DEPLOY_HOST`. |
| Image SHA stamp | `Containerfile` | `ARG ENGINE_SHA=unknown` + `LABEL vefr.engine_sha=${ENGINE_SHA}`. The wrapper reads it from the remote image and skips `podman build` when it matches local HEAD; `--rebuild` forces. |
| Fresh-clone guide | `docs/guides/deploy.md` | New — the wrapper's user manual. |
| Wrapper tests | `tests/test_deploy.py` | 4 tests: silent-default refusal, host-declared pass-through, `--init` writes `deploy.toml.example`, `--init` refuses to overwrite. |
| Cross-link | `GETTING_STARTED.md` | New section "5b. Shipping to a deploy host". |

**Direct commit `a11e532` to main** (the deploy that exposed the
two bugs below; atomic with the PR it implements):

| Change | File | What |
|---|---|---|
| Path resolution | `src/vefr/maplab.py` | `cmd_validate` accepts a bare name (`sample-world`), a relative (`worlds/<name>`), or an absolute path — matches what `handbok`/`doctor`/`export` already do. The pre-flight's `norns validate --pack sample-world` was previously raising `FileNotFoundError`. |
| Tunnel + retry probe | `src/vefr/cli.py` | Replaces the fixed 2-second sleep with a 20-attempt × 1.5s retry loop, and probes via SSH port-forward (`ssh -L 8820:127.0.0.1:8820 $VEFR_DEPLOY_HOST`) instead of `127.0.0.1` — the dev box's local DNS was resolving `bazzite` to the wrong host. |
| Regression tests | `tests/test_validate_pack_path.py` | 3 tests: bare name resolves, absolute path resolves, missing name gives a clean error. |

## What's still open (honest gaps)

None known as of this revision. The previous handoff's three gaps
were closed 2026-08-31. The only known unresolved work is the
queue in **ROADMAP.md → Next**.

**Caveat: `voices: 0` on the deployed sample-world.** That's a
deliberate state (sample-world is the mechanical scaffold — it has
no NPC speakers, by design). If a Play/World/Dev flow expects
voices and reads `[]`, the bug is in the consumer, not the pack.

## What to do next (the locked-in morning order)

Today's matrix was agreed at session start. Wrapper and bazzite
ship; the next blocks go in this order, **each in sequence, run
in batches of updates that affect similar systems, plan for
multiple sessions** (Rylee's words):

| # | Block | System / file | Wall | Why |
| - | --- | --- | --- | --- |
| 0 | **Wrapper** | `src/vefr/cli.py` + `Containerfile` + `docs/guides/deploy.md` + `tests/test_deploy.py` | ✅ done | Reusable deploy button, pre-flight gate, no-op skip. |
| 1 | **Bazzite deploy via wrapper** | bazzite `vefr` quadlet at `192.168.2.76:8820` | ✅ done | The truth runtime. Live now; sample-world end-to-end. |
| 2 | **Play zone batch** | `web/state.js`, `web/town.js`, `web/index.html`, `web/play.css` | ~90 min | HUD, rumors rail, kept-item gold ring, phase→water-level/radius propagation. State.js is the spine (landed 2026-08-31). |
| 3 | **Dev zone batch** | `web/board.js`, `web/dev.js` | ~60 min | Board drag polish, draft-thread UX (the 6-turn replay), aspect-inspector filters. **Note**: `vefr` is on the ro template volume; live edits need rebuild + restart OR `ratatoskr volumes export` for host-side edit. |
| 4 | **Reading row batch** | `web/prefs.js`, `web/reading.css` | ~45 min | Urd / Verdandi / Skuld live tuning; Skuld empty-state honesty check (em-dashes, not the sample-world voice). |
| 5 | **Sample-world polish** | `worlds/sample-world/` | ~30 min | The only canonical pack on bazzite. Boring-but-correct surfaces UI gaps faster than a good pack hides them. |
| 6 | **`norns chat` v2 — grow the map** | `src/vefr/chat.py`, `src/vefr/maplab.py` | ~60 min (spillover) | Riskier (model call inside the map pipeline); best as a "we have headroom" task. |

**Today's end-of-day target** (per session-start decision): a
fully playable game dev environment — Play loop end-to-end on
bazzite, ready for UI work against the live stack, not mocks.

If you're the next session and you arrive mid-day, run `norns doctor`
first to re-pin the matrix; the deploy command itself is the
single ship button:

```sh
export VEFR_DEPLOY_HOST=192.168.2.76  # use IP literal — see the URL note above
uv run --group test ratatoskr ferry deploy
```

That command does the gate, the rsync, the SHA-skip build, the
restart, the volume ensure, and the tunnel-probed health check
in one pass. Total wall on the warm path: **~29s**.

## Seams the next agent will touch

Same layout the prior handoff documented, but with three additions
for this session's wrapper work:

| Path | What's there now |
|---|---|
| `src/vefr/cli.py` | `cmd_deploy(args)` is the single ship button. `_deploy_init` + `_DEPLOY_TOML_EXAMPLE` for `--init`. `_wait_for_health` is the retry loop. The deploy's `--deploy-host` argparse stays top-level on `ratatoskr` (not on `ferry`) for backward compat — see the existing `--deploy-host` arg. |
| `src/vefr/maplab.py` | `cmd_validate` now resolves bare pack names via `pack_root()` before walking into `load_pack()`. Re-exported through `norns validate` + `norns map validate`. |
| `Containerfile` | `ARG ENGINE_SHA=unknown` + `LABEL vefr.engine_sha`. Wrapper builds with `--build-arg ENGINE_SHA=$(git rev-parse HEAD)`. |
| `tests/test_deploy.py` | 4 tests for the wrapper (silent-default refusal, host-declared, --init happy path, --init overwrite refusal). |
| `tests/test_validate_pack_path.py` | 3 tests for the path-resolution fix (bare name, absolute path, missing pack). |
| `docs/guides/deploy.md` | The deploy guide. Start here before touching the wrapper. The legacy `docs/guides/deploy-rsync-dance.md` is for the bind-mount hosts and is kept intact for them. |
| `docs/guides/handoff-snapshot-2026-09-01.md` | This file — pinned snapshot of the working state. |
| `docs/guides/session-handoff.md` | **Stale (predates today's wrapper work).** Update it as part of every landed PR (see the "WARN" in the always-layer) or replace it with a fresh snapshot. |

## Things the next agent must not do

Same rules as before, plus one new:

- **Don't repoint `git origin`** at the DuckDNS hostname. Default
  is `http://192.168.2.216:3000/rylee/vefr.git` (LAN-direct Gitea).
- **Don't rename the engine again.** `vefr` is the public name;
  The private game runs on the engine. Both repos
  exist; if a real trademark issue surfaces, file an issue and
  pause — don't pick a new name.
- **Don't bake `192.168.2.76` into the engine source.** The wrapper
  reads `VEFR_DEPLOY_HOST` from env; the deploy.toml.example is a
  template, not a config file (renamed + gitignored by the operator).
- **Don't run `ssh bazzite` from this dev box without checking the
  alias resolves correctly.** Today it resolves to 192.168.2.145
  (homelab-vm); use the IP literal `ssh 192.168.2.76` or update
  `~/.ssh/config` first.
- **Don't claim "the codebase is solid" without the gate output.**
  `uv run --group test ruff check src tests && uv run --group
  test pytest -q` — paste it next to the claim.

## Quick checklist for "continue on"

1. `uv run --group test norns doctor` — git sync, working tree,
   test gate, current pack, and (set `VEFR_LIVE_URL=http://192.168.2.76:8820`
   first) the deployed stack in one pass.
2. `preferences_get_profile` — confirm mem0 reachable; if not,
   say so once and continue from `rylee.md`.
3. Read `docs/guides/one-source-of-routes.md` if touching the web
   layer or adding a route — same rule as before.
4. Pick from the "What to do next" table above. Block 2 is next.
