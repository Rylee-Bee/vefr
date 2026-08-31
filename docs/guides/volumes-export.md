# Volumes: export / import / shell

The engine lives in named Docker volumes. When the author wants
to edit a pack — tweak a voice, change a phase tone, fix a
typo in the logbok — `vim` inside the container is awkward. The
export/import workflow gives the author a host-side git repo
they can edit in their normal tooling.

## The flow

```sh
# 1. Export a pack to a host-side git repo
ratatoskr volumes export \
  --pack sample-world \
  --dest ~/my-forks/sample-world

# 2. Edit the pack in your normal editor
cd ~/my-forks/sample-world
$EDITOR voices/keeper.md    # the keeper's voice
$EDITOR acts/act-1/town/contract.json   # town metadata
git add -A
git commit -m "keeper's voice, more tired on feared phase"

# 3. Import the change back into the rw volume
ratatoskr volumes import \
  --pack sample-world \
  --from ~/my-forks/sample-world

# 4. The engine picks it up on the next request
curl http://localhost:8820/api/world | jq .title
# "Emberfield"
```

The engine's loader cache is busted on every import. The next
`/api/rumor` or `/api/world` call sees the new file. No
container restart needed.

## What "engine-native layout" means

The export creates a directory whose *root is the pack*:

```sh
~/my-forks/sample-world/
  .git/                       # initial commit
  README.md                   # explains what's here
  world.json                  # the pack-level contract (phases, voices, ...)
  logbok.md
  ledger.md
  map.md                      # the legacy flat-shape walkable grid
  acts/
    act-1/
      world.json              # the act contract
      town/
        contract.json         # town metadata
        map.md                # the walkable grid (acts shape)
        voices/
          keeper.md           # speaker voice files
```

For a flat-shape pack the tree is flatter (no `acts/`). The
export *preserves the shape* — the engine doesn't reshape on
the way out. The import validates the source via maplab before
writing, so a broken pack can't clobber a good one.

## Editing voices in vim

The most common case. The export's `voices/*.md` are plain
markdown; the engine concatenates them with the world logbok to
form the system prompt the LLM sees. Tweaking a voice is one
`$EDITOR` away:

```sh
ratatoskr volumes export --pack sample-world --dest ~/my-forks/sample-world
$EDITOR ~/my-forks/sample-world/voices/keeper.md   # write
git -C ~/my-forks/sample-world add -A && git -c commit.gpgsign=false commit -m "keeper's dusk line, warmer"
ratatoskr volumes import --pack sample-world --from ~/my-forks/sample-world
# the next /api/npc call sees the new voice
```

## The `shell` subcommand

For one-off poking without exporting:

```sh
ratatoskr volumes shell --pack sample-world
# drops into bash inside the container, cwd = /app/worlds/sample-world
# you can `ls voices/`, `cat contract.json`, edit with `vi` if you must
```

The shell uses `podman exec -it`. On a remote deploy host, the
same command drops you into the running container.

## When to export instead of editing in place

| Edit in place (podman exec + vim) | Export to git repo |
|---|---|
| one-off, throwaway fix | part of a real change with intent |
| debugging the engine | shipping to other people |
| no need for history | want a commit log |
| | the file might be edited by multiple people |

Both end up at the same place: the rw volume at
`/app/worlds/<name>/`. Export is just a different on-ramp.

## The "export refuses to clobber" rule

If the destination is already a non-empty git repo — the
author probably has in-progress work — `volumes export` is a
no-op. Use a fresh path or `rm -rf` first. The point: don't
trash a working copy by accident.

## Round-trip is lossless

`export -> import -> export` produces the same file tree
(modulo timestamps + the README which carries a timestamp +
`.git/` internals which have different commit hashes). The
engine doesn't reshape on the way out; the import doesn't
re-derive anything. Whatever the author committed is what
the volume sees.

## Limitations

- **One pack at a time.** `volumes export --pack X` exports X.
  If you want to edit lore/ and sample-world/ together, do
  two exports.
- **No auto-watch.** The import is a one-shot. The author
  runs it after committing; the engine picks it up on the
  next request. There's no file-watcher that re-imports on
  every save — the loop is "save in vim, run ratatoskr".
- **Read-only engine templates.** `lore/` and `sample-world/`
  are engine-owned (ro volume). You can export them for
  reading, but the import writes to the rw volume and
  shadows the engine copy. To change an engine template, edit
  the engine repo and `ferry deploy`.
