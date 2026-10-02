# 03 · Semantic census (engine side)

The words VEFR already understands. This is the vocabulary a language layer must carry, not invent.

## Events a rule can wait for (11)

`starts`, `enters`, `comes-near`, `opens`, `picks-up`, `uses-with`, `defeats`, `buys`, `sells`, `reads`, `phase-changes`.
Each carries a fixed payload (`maplab.RULE_EVENT_KEYS`). `give` does not raise `picks-up` (proved by an adversarial test in the Codex probe).

## Effects a rule can perform (13)

`say`, `show`, `hide`, `reveal`, `give`, `takes`, `set`, `unset`, `believes`, `stops-believing`, `tells`, `weather`, `point-to`.
This list is the **capability boundary**. A pack may only name what is in it.

## Other declared structure in a pack

Growth (`levels` or `practice`), items, enemies with `hp/atk/xp/at/drops`, regions with `contract.json`, flags, claims, people, voices, phases, surface and skin, a library of books, and `grammars` (text expansion, unrelated to this campaign).

## Repetition measured (Cottage, structure only)

- 69 enemy records across the region contracts; within a region, several share every scalar except `id` and `at`.
- 2 rules. One was lowered and run through the shipped engine in the Codex probe (identical). The other has not been run through it: `UNVERIFIED`.
- 8 growth levels in one table.
- Details and names: see the private companion `02-current-cottage.md` in the Cottage repo.

## What this census says

Duplication is concentrated in **creature records**, not in rules or growth. Rules are already compact and declarative (one of two proven).
