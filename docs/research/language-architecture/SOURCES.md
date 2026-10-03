# Sources

Every claim in this packet traces to one of these. Re-run to reproduce.

| Source | Used for |
|---|---|
| `docs/plans/language-architecture-campaign.md` (PR #219) | scope, gate, Phase A spec |
| `docs/plans/language-architecture-proof-pass.md` | probe design |
| `docs/plans/language-architecture-sonnet-phase-a-handoff.md` | Codex dispositions |
| `experiment/language-proof-20261002` @ `649034f` | probe code and README results |
| `docs/research/2026-10-02-language-prior-art.md` + Codex addendum | prior art (addendum authoritative) |
| `src/vefr/maplab.py:313,339` | event and effect vocabulary |
| `web/packaged.html:2191` | rule-state persistence |
| `docs/guides/rulesets.md`, `docs/adr/0004-scoped-rules.md` | rule semantics |
| `src/vefr/features.py`, `grammar.py`, `schema_grammar.py` | existing modules, name collision |

## Commands I ran (2026-10-02)

- `gh pr view 219`, `gh pr checks 219`
- `git worktree add --detach .../lang-proof-verify 649034f`
- `uv run --group test pytest -q experiments/language-proof/test_prototype.py` -> 9 passed
- `uv run --group test python experiments/language-proof/run.py --pack <cottage pack> --region floor-2 --sprite shade --rule the-keeper-knows --out <scratch>` -> three PASS lines
- `vefr --help`, `vefr check --help`, `vefr probe --help`, grep of route and version keys

| Codex private packet (`vefr-language-proof-sonnet.zip`, received 2026-10-02) | paper non-game probe, effect table, gate results; kept outside every repo |

`UNVERIFIED`: Codex's full-gate numbers (1335 passed) were read from its receipt, not rerun; the second Cottage rule through the engine; the 7 prior-art URLs that blocked bots.
