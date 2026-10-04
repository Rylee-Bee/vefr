# A1 brief: the art ledger and the cutter (foreman plan)

Objective: make `tests/test_art_ledger.py` pass and make `tests/art_cut/` pass with Pillow (read them and `docs/adr/0011-art-ledger.md` first; frozen, never edit them; if a test contradicts this brief STOP and report).

Two workers (tier `code`), in order:
1. `src/vefr/art_ledger.py` (stdlib only: `ROLES`, `check`, `credits`) and a `vefr art` verb in `src/vefr/cli.py` with `check` and `credits` subcommands, wired in `vefr_main` the way its sibling verbs are. Follow the ADR exactly: closed key sets, sha256 recompute, the clean-credits rule over every string in every ledger, one plain sentence per problem naming the file and picture id, no traceback on bad JSON.
2. Port the cutter: copy Cottage's `art/tools/process_sprites.py`, `process_tiles.py`, `process_ui.py` into `tools/art/` UNCHANGED from `~/code/Rylee-Bee/cottage-of-the-breeze/art/tools/` (read-only; copy with `cp`, then only edit imports/paths if a test needs it). Add `tools/art/cut.py ROLE ARGS...` that forwards `item-icon` and `creature` to process_sprites, `tile` to process_tiles, `ui-part` to process_ui (a short dispatcher, no new logic). Pillow is not a VEFR dependency: do not add it to `pyproject.toml`; the tests skip without it.

Constraints: nothing else under `src/vefr/` changes; no change to weave output.
Acceptance: `bash tests/run.sh tests/test_art_ledger.py --runxfail`, then `uv run --with pillow python -m pytest tests/art_cut -q`, then the full suite.
