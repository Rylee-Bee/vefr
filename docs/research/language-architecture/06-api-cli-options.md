# 06 · API and CLI options

Principle: **extend what exists**. No new server, no new framework.

## CLI

| Option | Shape | Note |
|---|---|---|
| **1. `vefr check` learns the source (recommended first)** | `vefr check PACK` also validates an optional `source/` dir | Reuses the front door and the validator. |
| 2. New `vefr normalize PACK [--out DIR]` verb | Prints or writes the expanded pack and a provenance map | Needed once there is a source; read-only by default. |
| 3. `vefr explain ID` / `vefr diff A B` | Why a record has its values; what changed between packs | Later. Seed is `vefr probe` and the why log. |

Avoid the word *grammar* in names: `grammar.py` already means text expansion.

## HTTP (read-only first)

- Reuse `POST /api/builder/validate`, which already validates a pack.
- Add at most one read route for provenance only after the normalizer exists. No write routes in this campaign.

## Not in scope

Studio UI, natural-language authoring, any model call in the deterministic path.
