# 01 · Current VEFR (reverified 2026-10-02)

Every line below was checked against the live repo on 2026-10-02 unless marked `UNVERIFIED`.

| Fact | Evidence |
|---|---|
| `main` is `45f5767`; branch `docs/language-architecture-campaign` (PR #219) is based on it | `git rev-parse origin/main`; `git merge-base --is-ancestor` |
| CLI verbs: find, publish, look, probe, features, doctor, check, chat, map, delve, weave, spark, test, ferry, handbok, skipa, norns, ratatoskr | `vefr --help` |
| 11 rule events, 13 rule effects, validated at build time | `maplab.RULE_EVENTS`, `maplab.RULE_ACTION_KEYS` (`src/vefr/maplab.py:313,339`) |
| Rule shape is `when / if / then / once`; no priorities, no chains, written order | `docs/adr/0004-scoped-rules.md`, `docs/guides/rulesets.md` |
| The runtime defensively **skips** an invalid rule instead of failing | Codex proof README; build-time validation is therefore the only hard gate |
| A pack has **no schema/version field** | grep of `maplab.py`, `world.py`, `weave.py`, `cli.py` for version keys: none; Cottage `world.json` keys carry none |
| `features` catalog is already a single-source-of-truth pattern | `src/vefr/features.py` reads `docs/features.json`, checks drift, powers `vefr features` and `GET /api/features` |
| Read-only and builder HTTP routes exist (`/api/features`, `/api/builder/validate`, `/api/builder/map/check`, ...) | route scan of `src/vefr/*.py` |
| Delve: `generate_floor_v2` with a shared deterministic PRNG and exact Python/JS parity | `src/vefr/delve.py`; random-floor phase 1 |
| Test suite: 198 tracked files under `tests/`, with rules, growth, events and play tests | `git ls-files tests` |
| **Name collision:** `src/vefr/grammar.py` is a Tracery-style text expander and `schema_grammar.py` is a JSON-Schema-to-GBNF converter | file headers |

## Seams the language layer would touch

1. `maplab.validate` and `maplab.rules_errors`: the existing validator. It already owns event and effect signatures.
2. `cli.weave_html` and the bake path: where normalized data becomes `window.VEFR_*` globals.
3. `window.VEFR_RULES_ENGINE` in the woven player: executes rules. Not changed by anything proposed here.
4. `delve.generate_floor_v2`: arrangement. Not changed.

## Open backlog this reshapes

VEFR #215 (random floors phase 2), #216 (album), #217 (equipment and real act 2), #218. Treat them as informed by this disposition; none starts without Rylee.
