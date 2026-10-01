# The vefr command

One front door.
Every verb that used to live in `ratatoskr` (running things) or
`norns` (making things) is a `vefr` verb now, and the old names keep
working as aliases. Nothing you have written down goes stale.

```sh
uv run vefr --help    # every verb, in the order you use them
```

## The verbs

In journey order: the order an author walks the path, from a session
that starts sound to a file you can send to a friend. This is the
order `vefr --help` prints them in, too.

| Verb | What it is | Old spelling |
|---|---|---|
| `vefr doctor` | session-start health: git, tree, tests, pack, live, backups, vault; one answer | `norns doctor` + `ratatoskr skipa` |
| `vefr chat` | interview a new world into existence | `norns chat` |
| `vefr map` | rebuild the map from run-length rows | `norns build-map` |
| `vefr delve` | generate dungeon floors from a seed, wire the stairs | `norns delve` |
| `vefr check` | validate the pack geometry; `--live URL` validates a running deployment | `norns validate` / `norns verify` |
| `vefr weave` | package a world into one self-contained HTML file | `ratatoskr weave` |
| `vefr handbok` | write the mechanics manual from real play | `norns handbok` |
| `vefr spark` | the resident small brain: `install`, `status`, `smoke`, `task` | `ratatoskr spark` |
| `vefr test` | the pytest suite; extra args pass through, e.g. `-k chat` | `ratatoskr test` |
| `vefr ferry` | deploy, carry, fetch, scaffold | `ratatoskr ferry` |
| `vefr skipa` | kept for now; prints one line saying it is part of `vefr doctor` | `ratatoskr skipa` |
| `vefr find` | local read-only search of the pack's markdown and the journal | new |

Two habits carry over unchanged: validate after every pack write
(`uv run vefr check --pack worlds/<name>`), and read `--help` for the
live list straight from the code.

## Escape hatches

Old muscle memory still runs. Both of these run the old CLIs exactly
as they were, unchanged:

```sh
uv run vefr norns validate --pack worlds/sample-world
uv run vefr ratatoskr test
```

The bare old names (`norns ...`, `ratatoskr ...`) also still work as
aliases. Every verb that had `--json` still has it.

## Exit codes

The same across every command, so a script can branch without a table
of exceptions:

| Code | Meaning |
|---|---|
| `0` | did what it says |
| `1` | refused, invalid, or failed |
| `2` | bad arguments |
| `3` | a backend (Spark, the live stack) could not be reached |
| `4` | gated: nothing changed, a person must approve |

## `--json` for agents

The envelope is the same every time, whichever verb you call:

```json
{"ok": true, "status": "ok", "changed": false, "warnings": [], "actions": [], "data": {}}
```

- `ok` - did it work
- `status` - a short machine-readable state
- `changed` - did anything change on disk or on the host
- `warnings` - what it noticed but did not stop for
- `actions` - what it did
- `data` - the verb's own payload

```sh
uv run vefr check --pack worlds/sample-world --json
```

## Where to go next

- [The Journey](journey.md) - the whole path, stop by stop.
- [World creation](world-creation.md) - the interview, the map, the file.
- [Spark](spark.md) - the resident small brain.
- [The Lorekeeper](lore.md) - facts and the derived index.
- [Volumes](volumes.md) - export and carry a session's state.
- [Bundled brain](bundled-brain.md) - the models that ship with the image.
