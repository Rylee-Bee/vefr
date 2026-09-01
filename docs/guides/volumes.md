# Volumes — the ro/rw split

The engine's runtime has three persistent roots with a clear
capability boundary between them:

| Mount | Read/Write | Holds | Updated by | Backed up by |
|---|---|---|---|---|
| `/app/worlds-template/` | **ro** | `lore/`, `sample-world/`, `poolworld/` — engine-owned templates | `ferry deploy` (image rebuild) | the engine image itself |
| `/app/worlds/` | **rw** | User canon: private packs, anything `ferry fetch` lands, anything the author edits in place | `ferry fetch`, `volumes import`, manual `podman exec` | `ratatoskr volumes export` (host-side git) |
| `/app/data/` | **rw** | `vault.json`, `journal.json`, `weave.jsonl`, `handoffs/`, `dist/` — per-session player data | runtime only | `ferry carry` to NAS + nightly cron |

The rw canon wins on conflict: if a template and a canon share a
pack name, the engine reads the canon. The author can shadow a
template without `ferry deploy` clobbering the edit.

## How the read path works

`load_world(name)` calls `paths.pack_dir(name)`, which:

1. Checks `/app/worlds/<name>/` (the rw canon). If present, uses it.
2. Otherwise falls back to `/app/worlds-template/<name>/` (the ro
   engine template).
3. Otherwise errors with a clear PackError.

The engine has no idea a "merge" happened — `pack_dir()` is the
only seam. `discover_packs()` walks both mounts to populate the
Builder tab's world picker; canon wins on conflict there too.

## How the volume split was made

```sh
# 1. Create the named volumes
podman volume create vefr-template
podman volume create vefr-worlds

# 2. Migrate the legacy ~/vefr-worlds/ bind mount (one-shot)
ratatoskr volumes migrate

# 3. Update the quadlet to mount the new volumes
# (The `volumes migrate` command writes the new quadlet if the
# old one didn't already reference vefr-template.)

# 4. Restart
systemctl --user daemon-reload
systemctl --user restart vefr
```

The migration is **idempotent**: re-running on an already-migrated
host detects the new `Volume=vefr-template:/app/worlds-template:ro`
line in the quadlet and exits 0 without doing anything.

## What lives in ro, what lives in rw

The migration classifies packs by name. The `ENGINE_PACKS` set in
`src/vefr/volumes.py` is the source of truth:

```python
ENGINE_PACKS = {"lore", "sample-world", "poolworld"}
```

Anything else under `~/vefr-worlds/` (private canon) is
treated as user canon and seeded into the rw volume. If you add
a new engine template, edit `ENGINE_PACKS` *and* the `worlds/`
dir in the engine repo, then `ferry deploy` carries the new
template in the image and the loader sees it from the ro mount.

## When a shape change ships in the engine

The canary pack (sample-world) lives in `worlds/sample-world/` in
the engine repo, copied into the image at `worlds-template/` on
build, and re-seeded into the ro volume on `ferry deploy`. When
the canary's on-disk shape changes (flat → acts), the next
`ferry deploy` carries the new shape in the image; the ro
volume picks it up because `ferry deploy` recreates the volume
or Podman overlays the new image content on top.

**User packs** (the rw canon) do not auto-update. If you change a
canary and want a user's canon to track, the user runs
`norns migrate --pack <name>` on their own schedule. The
migrator validates end-to-end before writing.

## Offline boots

The image ships the engine templates at `/app/worlds-template/`.
If the ro volume is empty (first run, after `volume rm`), the
container still has the templates from the image. The rw volume
is empty too; the engine boots with just the canary and no
user canon. A subsequent `ratatoskr volumes migrate` (or a
`ferry fetch` of a canon pack) populates the rw side.

## Why not a single rw volume?

The split exists so a `ferry deploy` updates engine templates
without touching the author's canon. A single rw volume would
mix them; the rsync-dance we used to do is the workaround. The
ro/rw split removes the dance: deploy is `image + named volume`,
canon is `named volume`, no per-template `rsync` calls.

## Future work (not in this PR)

- `volumes export` — pull a canon pack to a host-side git repo
  for editing in `vim`, then `volumes import` to write it back.
- `volumes shell` — `podman exec` with the engine's cwd set.
- A `ferry fetch --target volume` variant that writes straight
  into `vefr-worlds/` instead of `~/vefr-worlds/`.
- An audit command: "which packs are engine-owned, which are
  author-owned, which are shadowing?"
