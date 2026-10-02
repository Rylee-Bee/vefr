# 12 · Kernel and second domain

Codex returned a provisional **HYBRID**: three layers (kernel, dialect, pack) as an organizing idea over what VEFR already has. It is **not** proven as a shared kernel.

## Tagging of what exists

| Item | Layer |
|---|---|
| entities with ids, relations by id, history (WHY log) | kernel-shaped, but only exercised inside VEFR |
| the 11 events and 13 effects | dialect (game) |
| creature records, items, levels | pack and dialect |
| validator signatures | dialect |

## Second-domain paper probe

Codex wrote one on paper (from its private packet): a monitoring rule, "a check fails twice in a row opens one incident and notifies the owner". Event `check.completed(check_id, run_id, status)`, deduplicated by `run_id`; condition: failure count goes 1 to 2 with no open incident; effects: record incident, enqueue one notification. Result: **PLAUSIBLE, not implemented**. It needs host contracts the games do not (persistent counters, deduplication, idempotent delivery), and notification authority must come from explicit configuration, never from a pack word. Plausibility only: do not extract a shared library until a second real domain exists.

## Guardrail

The semantic layer must stay domain-neutral in *shape* (ids, relations, rules, provenance) and put game words in the dialect. Check this in review; do not build machinery for it yet.

## Effect classification (Codex, checked against `RULE_ACTION_KEYS`)

| Effects | Class |
|---|---|
| `set`, `unset` | kernel-level candidates |
| `believes`, `stops-believing`, `tells`, `give`, `takes`, `point-to`, `weather` | game dialect |
| `say`, `show`, `hide`, `reveal` | presentation only |

The runtime skips an invalid rule silently, so the closed catalog must be enforced at build time.
