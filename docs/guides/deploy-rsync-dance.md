# Deploying vefr — the rsync dance (LEGACY, replaced by volumes)

> **This guide is for legacy installs on the bind-mount path.**
> New installs use named Docker volumes; see
> [docs/guides/volumes.md](volumes.md) for the current flow.
> The dance below is preserved because old deploy hosts still
> run it, and the migration script can take a legacy host to
> the new shape in one command.

The `ferry deploy` command is the happy-path, but it has a hidden
requirement: the worlds live on a **separate bind mount** on the
deploy host, so star/import edits persist across container
rebuilds. That bind mount is NOT rsynced by `ferry deploy`. When
the engine repo's `worlds/<name>/` changes shape (e.g. flat →
acts), the bind mount keeps the old shape until you sync it
manually.

## The two volumes on the deploy host

| Mount | What it holds | Backed up by |
|---|---|---|
| `~/vefr/` | the engine checkout — `src/`, `web/`, `Containerfile`, the *template* `worlds/sample-world/` | `ferry deploy` rsyncs the engine checkout into here |
| `~/vefr-worlds/` | the worlds *volume* — every pack currently loaded, plus the user's private canon | manual rsync (this guide) |
| `~/vefr-data/` | runtime state — `vault.json`, `journal.json`, `weave.jsonl`, `handoffs/` | `ferry carry` bundles to NAS |

The container's `/app/worlds` is **bound to `~/vefr-worlds/`**, NOT
to `~/vefr/worlds/`. The engine checkout's `worlds/` is the
*template*; the bind mount is the *live* copy.

## When the template changes shape

If `worlds/sample-world/` (or any engine-owned pack like
`worlds/lore/`) gains, loses, or restructures files, the live
bind mount is now out of sync. Symptom: the engine loads but the
old shape is served. The "first" pack alphabetically still wins
when `VEFR_WORLD` is unset, so it can be confusing which copy is
in use.

## The dance

```sh
# 1. rsync the engine-owned packs from the checkout to the bind mount.
#    SKIP user-owned packs (any private canon).
rsync -a --delete \
  ~/projects/vefr/worlds/sample-world/ \
  ${VEFR_DEPLOY_HOST}:~/vefr-worlds/sample-world/
rsync -a --delete \
  ~/projects/vefr/worlds/lore/ \
  ${VEFR_DEPLOY_HOST}:~/vefr-worlds/lore/

# 2. restart the container so the loader re-reads the bind mount.
ssh ${VEFR_DEPLOY_HOST} "systemctl --user restart vefr"

# 3. verify
curl -s ${VEFR_LIVE_URL:-http://127.0.0.1:8820}/api/world | jq '.title, .act'
curl -s ${VEFR_LIVE_URL:-http://127.0.0.1:8820}/api/weave | jq '.events[] | {event, shape, act}'
```

## Why `--delete`

The bind mount may have leftover files from the old shape (e.g.
the README-style `map.md` in the legacy flat shape). Without
`--delete`, those linger and the loader is ambiguous about which
is the source of truth. With `--delete`, the bind mount is a
clean mirror of the engine template.

## What this guide does NOT cover

- **User-owned packs** (private canon). These are *not* in
  the engine checkout; they live in the user's private repo and
  land on the bind mount via `ratatoskr ferry fetch` or by hand.
  Do not `--delete` them off the bind mount.
- **Migrating a flat-shape user pack to the acts tree.** Use
  `norns migrate --pack <name>` once on the dev box, then
  rsync the result. The migrator validates end-to-end before
  writing.
- **The `data/` volume.** Backed up by `ferry carry` and the
  nightly cron on the deploy host. Do not rsync `~/vefr-data/`
  from the dev box; it's machine-local runtime state.

## Future work (not PR 1)

This dance should be one command. Candidates:

- `ratatoskr ferry sync-worlds` — does the rsync + restart in
  one shot, asks before touching user-owned packs.
- The `ferry deploy` command could detect template drift and
  prompt for the rsync.
- The bind mount could be replaced with a copy-on-write overlay
  so engine-owned packs auto-update and user-owned packs stay
  isolated. Larger infra change; defer.

For now: bookmark this file. Run it after any engine-pack shape
change.
