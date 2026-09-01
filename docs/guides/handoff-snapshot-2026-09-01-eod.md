# Session handoff — vefr (2026-09-01 end of day)

> Where the repo + live bazzite stack stand as of 2026-09-01
> ~15:40Z. All evidence re-checked within minutes of writing;
> commands sit next to the claims. This supersedes the
> mid-morning snapshot at
> `docs/guides/handoff-snapshot-2026-09-01.md` (HEAD `2a7d4c0`),
> which stays pinned for its deploy-fix history.

## Verified right now (re-run any time)

| Check | Command | Result |
|---|---|---|
| Repo + working tree | `git status && git log --oneline -3` | clean, HEAD `5d57083` |
| All pushed | `git log --oneline origin/main -3` | matches local |
| Lint | `uv run --group test ruff check src tests` | All checks passed |
| Full test suite | `uv run --group test pytest -q` | **215 passed, 2 skipped** |
| Bazzite engine | `curl -sS -m 5 http://192.168.2.76:8820/api/health` | `{"ok":true,...}` |
| Bazzite world | `curl -sS -m 5 http://192.168.2.76:8820/api/world` | Emberfield, `surface: combat`, per-phase hp `{dusk:3, dawn:4}` |
| Play loop live | see the 2026-09-01 verification report (PR #34 report in session) | forge → keep → combat → star → rewind/undo → fork → rumor tour → stefna → export, all green end-to-end |
| Deployed engine SHA | `ssh bazzite "podman image inspect localhost/vefr:latest --format '{{.Config.Labels}}'"` | labels carry the deployed engine sha |

### URL notes (supersedes the morning note)

- The SSH alias `bazzite` on this dev box is **fixed and
  correct**: `HostName 192.168.2.76`, `User rylee`. Use
  `VEFR_DEPLOY_HOST=bazzite` — a bare IP literal drops the user
  and rsync fails as `ryleeb@`. (The morning snapshot's warning
  is inverted now; its file has the correction.)
- `rtk` lives at `~/.cargo/bin/rtk` (0.42.4); this session's
  shell does not source `.bashrc`, so
  `export PATH="$HOME/.cargo/bin:$PATH"` per command when needed.

## What landed today (6 PRs + ledger commits, all merged)

| Block | PR | Commit | What |
|---|---|---|---|
| 2 — Play zone | #31 | `fa9992e` | Ledger catch-up: surface UI was already landed+live; ROADMAP Next item corrected |
| 3 — Dev zone | #32 | `526e06c` | Board reorder announcements, draft-thread paragraphs + clear button + 6-turn note, inspector section filter |
| 4 — Reading row | #33 | `a579d90` | Urd saved-state readout + Skuld live `reading now:` readback; dead em-dash meta gone; sound controls deliberately absent |
| play-loop fixes | #34 | `2bfa064` | Vault takes typed `ItemCard` (422 names missing fields); npc 404s in plain English (unknown speaker / voice-less pack); route guide regenerated from `app.routes` (41 routes; the `POST /api/starred` myth dead) |
| 5 — sample-world | #35 | `041b77d` | board.js stops hardcoding a pack's bond keys + neutrality guard; `voices: 0` caveat corrected (1 speaker exists) |
| packaged surface | #36 | `bb4a665` | The weave artifact carries the combat costume: data-surface from the pack, HP bar, engine-neutral encounter prompt, verbs → local localStorage journal |
| 6 — chat v2 | #37 | `59b3a25` | The interview grows the map (model proposes run-length rows, `maplab.validate()` gates on a deep copy, scaffold layout wins on failure) and takes 1–3 town voices (deterministic tile placement, drafted words) |

Plus ledger docs commits (`fa9992e`→`5d57083`) pinning every
landed change.

## Things you must not do (unchanged + one)

- Don't repoint `git origin` — default
  `http://192.168.2.216:3000/rylee/vefr.git`.
- Don't rename the engine. `vefr` public, `Old Name` private.
- Don't bake `192.168.2.76` into engine source.
- Don't claim "codebase is solid" without the gate output.
- Don't let the packaged template name a pack's phase vocabulary
  or bond keys — both now have test guards; keep them.

## "Continue on" checklist

1. `VEFR_LIVE_URL=http://192.168.2.76:8820 uv run --group test norns doctor`
2. `preferences_get_profile` — mem0 healthy as of session close.
3. Read `docs/guides/one-source-of-routes.md` before touching the
   web layer — the table now derives from `app.routes` (41 routes).
4. ROADMAP → Next is the queue: interactive chat helper, formatted
   ebook export, full git scaffold, Tiled importer (parked), more
   lore packs (data-only).

## Single ship button (unchanged)

```sh
export VEFR_DEPLOY_HOST=bazzite
uv run --group test ratatoskr ferry deploy
```

Warm path ~29s; builds only when the engine sha differs from
deployed. Session evidence: deployed three times today, health
green each time.
