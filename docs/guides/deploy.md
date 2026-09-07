# Deploying vefr — the wrapper

> Replaces the legacy bind-mount dance described in
> [deploy-rsync-dance.md](deploy-rsync-dance.md). The current deploy
> path uses named Docker volumes (`vefr-template` ro + `vefr-worlds`
> rw + `vefr-data` rw) declared in `deploy/vefr.container`. The
> wrapper hides the rsync + build + restart + healthcheck behind one
> command that any fresh checkout can run.

## One command, from a fresh clone

```sh
# 1. Tell the wrapper about your deploy host.
export VEFR_DEPLOY_HOST=<your-host-or-ssh-alias>

# 2. Stack your local changes on top of the image and ship them.
uv run ratatoskr ferry deploy
```

That's it. The wrapper:

| Step | Command | Skippable? |
|---|---|---|
| Pre-flight | `uv run --group test pytest -q` + `uv run --group test norns validate --pack sample-world` | `--skip-tests` |
| Sync | `rsync -a --delete <excludes> ./ $VEFR_DEPLOY_HOST:~/vefr/` | always runs |
| Image | `podman build --build-arg ENGINE_SHA=$(git rev-parse HEAD) -t localhost/vefr:latest .` on the host | skipped when image SHA already matches HEAD; `--rebuild` forces |
| Restart | `systemctl --user restart vefr` on the host | always runs |
| Volume check | `podman volume exists vefr-{template,worlds}` (create if missing) | always runs |
| Verify | `/api/health` + `maplab verify` | `--no-health` |

The pre-flight gate is the load-bearing part: a broken `main` never
reaches the deploy host. The image-SHA skip is the convenience part:
when you've already deployed this exact commit, the wrapper is one
restart, not a full rebuild.

## First-time setup on a new host

The wrapper refuses to run with the silent `bazzite` default — that
was a leak that bit every fresh checkout. To get started:

```sh
# 1. Generate the example config + this guide (idempotent — refuses
#    to overwrite an existing deploy.toml.example).
uv run ratatoskr ferry deploy --init

# 2. Copy + edit to match your topology.
cp deploy.toml.example deploy.toml
$EDITOR deploy.toml

# 3. Export the host. The wrapper reads env, not deploy.toml, so you
#    can keep deploy.toml out of git (it is, by default).
export VEFR_DEPLOY_HOST=$(grep '^host' deploy.toml | cut -d'"' -f2)

# 4. Smoke-test without touching the engine.
uv run ratatoskr ferry deploy --skip-tests --no-health

# 5. Full deploy.
uv run ratatoskr ferry deploy
```

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `VEFR_DEPLOY_HOST` | SSH target — alias or `user@host` | (none — required) |
| `VEFR_DEPLOY_IMAGE` | podman image name/tag the quadlet runs | `localhost/vefr:latest` |
| `VEFR_LIVE_URL` | engine URL for post-deploy health check | `http://127.0.0.1:8820` |
| `VEFR_GITEA_URL` | Gitea base for `ferry fetch` shorthand | `http://localhost:3000` |
| `VEFR_DEFAULT_BACKUP_LOCATION` | `host:/path` for `ferry carry` | `homelab-vm:/mnt/nas/shared/backups` |

All five are runtime data, not repo data. They live in your shell,
your direnv, or your secret store — never in a commit.

## What the wrapper does NOT do

- **Push to Gitea.** That's `git push` or `tea`. The wrapper
  ships *this checkout* to the deploy host via rsync; it does not
  touch the remote ref.
- **Back up play history.** That's `ratatoskr ferry carry` (per-date
  bundle + vault/journal snapshot to the NAS).
- **Fetch a story pack.** That's `ratatoskr ferry fetch owner/name`.
  Fetched packs land in the `vefr-worlds` rw volume; restart the
  container (the wrapper does this for you) for the loader to see
  them.
- **Update the ro template volume.** Engine-owned packs (`worlds/lore/`,
  `worlds/sample-world/`) ship baked into the image at
  `/app/worlds-template/`. A new image rebuild republishes them; the
  ro named volume is the live overlay.

## When the pre-flight gate is wrong for you

The gate is opinionated. To bypass it once:

```sh
uv run ratatoskr ferry deploy --skip-tests
```

To run a subset of tests instead of the full suite:

```sh
uv run --group test pytest -q -k chat       # fast feedback loop
uv run ratatoskr ferry deploy --skip-tests  # ship what you just verified
```

If you're shipping a docs-only change, `--skip-tests` is fine: the
suite doesn't change, the gate still proves the source tree imports
clean on the next un-skipped deploy.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `refusing to deploy: VEFR_DEPLOY_HOST is not set` | Env var missing. Run `export VEFR_DEPLOY_HOST=...` or `ferry deploy --init`. |
| `ssh: Could not resolve hostname bazzite` | The leaked default bit you. Set `VEFR_DEPLOY_HOST` explicitly. |
| `pre-flight: pytest failed` | `uv run --group test pytest -q` to see why; fix; retry. |
| `pre-flight: sample-world validate failed` | `uv run --group test norns validate --pack sample-world` for details. |
| `health check failed: ...` | Container started but `/api/health` did not return 200 within 2s. `ssh $VEFR_DEPLOY_HOST podman logs vefr` for the cause. |
| `image localhost/vefr:latest already at HEAD` printed but the change isn't live | The image SHA matched HEAD but the source wasn't rsynced (or vice-versa). Pass `--rebuild` to force. |

## See also

- [volumes.md](volumes.md) — the ro/rw volume split on the deploy host.
- [deploy-rsync-dance.md](deploy-rsync-dance.md) — legacy bind-mount path, kept for old hosts.
- [volumes-export.md](volumes-export.md) — exporting a pack to a host-side git repo for editing.
- [handoff.md](handoff.md) — the bundle a session-end handoff should include (dated session snapshots live under `archive/`).
