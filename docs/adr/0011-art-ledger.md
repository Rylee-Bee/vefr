# 0011 - Art ledger

Date: 2026-10-04

## Status

Proposed. Becomes Accepted when `vefr art check` merges. Plan: `docs/plans/tighten-shapes/PLAN.md` section 5.

## Context

A pack's pictures have three credit formats today and 41 credit files that embed scratch paths. The record of how a picture was made (subject, style, which variant was picked, where it went) lives in prose.

## Decision

A pack may keep `art/ledger/round-NN.json`, one file per round:

```json
{"ledger": 1, "round": 19, "made_with": "codex", "style": "storybook-item", "date": "2026-10-05",
 "pictures": [{"id": "copper-ladle", "role": "item-icon", "subject": "a battered copper soup ladle",
   "variants": 2, "ref": "art/source/round13/keys_a/keys_a_v1.png", "pick": 2,
   "to": "sprites/copper-ladle.png", "sha256": "<hex>", "status": "draft"}]}
```

- Key sets are closed. Top level: `ledger`, `round`, `made_with`, `style`, `date`, `pictures`. Picture: `id`, `role`, `subject`, `variants`, `ref`, `pick`, `to`, `size`, `grid`, `sha256`, `status`, `note`. Required top level: `ledger`, `round`, `made_with`, `style`, `pictures`. Required per picture: `id`, `role`, `subject`, `to`, `sha256`.
- `role` is one of `item-icon`, `creature`, `tile`, `sheet`, `ui-part` (`ROLES` in `src/vefr/art_ledger.py`).
- `vefr art check --ledger DIR [--root DIR]` reads every `round-*.json` in DIR, validates keys, ids unique across the DIR, recomputes the sha256 of each `to` file under `--root` (default: the parent of DIR's parent), and enforces the clean-credits rule: no absolute path, `~`, `/tmp`, `/home`, or `..` in any string of any ledger. Every problem is one plain sentence with a pointer; exit 1 if any.
- `vefr art credits --ledger DIR` prints generated credits as markdown, one line per picture: `- <to>: <made_with>, <style> (round <n>)`.
- `tools/art/cut.py` (run with `uv run --with pillow`) is the cutter, ported from Cottage's `process_sprites.py`, `process_tiles.py` and `process_ui.py` with their tests. Pictures are encoded once, at cut time; the weave never re-encodes.
- Generation (`codex_batch.sh`, prompts, styles) stays in the pack's repo. VEFR holds the schema, the role table and the checks, nothing private.

## Consequences

Old `*.credits.txt` stay as history. New rounds write only a ledger. Hash drift between ledger and file is caught by `check`.
