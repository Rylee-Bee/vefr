# 08 · Risks and counterexamples

| Risk or counter-evidence | Evidence | Response |
|---|---|---|
| The semantic rule wrapper is longer than today's rule JSON | Codex probe B | Do not require it. Keep today's rule shape. |
| Invalid rules are silently skipped at runtime | Codex README | Make build-time validation mandatory before any execution path. |
| **Rule state resets on reload** | `web/packaged.html:2191` persists only the WHY log (`vefr-rules-<world>`: `{id, why}`); `RULES_STATE` (flags, once markers) is rebuilt in memory by `engine.newState` | Real, pre-existing. See "Save-state" below. |
| Guardians are not wired | Codex probe A; `design/gates-and-guardians.md` is a proposal | Do not claim guardian semantics. Probe used a synthetic `drops-on-defeat`. |
| No real authored ending room exists | Codex probe C | Ending pass-through is synthetic only. |
| Generator supports few controls | Codex probe C: only width, height, rooms | Reject unsupported controls explicitly; never degrade silently. |
| Reachable stairs do not prove balance | Codex probe C | Reachability is one guarantee, not a quality bar. |
| Over-reach: a new runtime, plugins, estate kernel | Plan non-negotiables | Out of scope. |
| Verbose abstraction nobody uses | Prior art (Inform 7, Quest), analysis only | Dogfood on Cottage; exit ramp if it saves nothing. |
| Name collision with `grammar.py` | file header | Pick another word for the source layer. |

## Save-state (pre-existing, not caused by this campaign)

After a reload the player remembers *why* rules fired but not their flags or `once` markers, so a `once` rule can fire again and a flag gate can reset. Recommendation: decide this **before** new progression (guardians, gates, album) leans on `once` or flags. Options: (a) persist `RULES_STATE` per world beside the WHY log, versioned and recoverable from a changed pack the way growth is; (b) declare reset-on-reload as intended and document it in `rulesets.md`. Either is a small, separate PR. Not part of the language layer.
