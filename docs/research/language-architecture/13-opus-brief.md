# 13 · Brief for Opus 5.5

Input: this whole packet (public 00–12 here, private 02 and 10 in the Cottage repo) plus live repo state. Reverify every fact before relying on it.

Disposition carried in: **GO WITH CONSTRAINTS**. Rylee must have read it before anything below is authorized.

## Ask

Produce **two separate plans**, in two documents, for two independent tracks. Neither blocks the other. Each ships as its own PR sequence. Do not merge them into one campaign.

### Plan 1 · Family normalization (plan this first)

Goal: an optional, build-time source that expands families into today's enemy records, with provenance, then proven live on Cottage.

Must include:

- Acceptance tests first: legacy-equivalence fixtures asserting **structural equality** with today's records (definition in `07`); a pack with no source is unchanged.
- The pipeline `validate source -> expand -> provenance -> validate the whole normalized pack` (`07`, `09`). Closed fields; unknown family, cycle or event/effect name fails.
- CLI on the real syntax: `vefr check --pack PACK` extended, then `vefr normalize --pack PACK [--out DIR]` (`06`). No new server, no Studio, no write routes.
- The source version field, introduced with the first format, with a named reader and fixtures.
- Stale-output rule: generated files carry source hash and normalizer version; a stale one is rejected.
- Cottage step: creature families only, behind fixtures, one PR in the Cottage repo.
- Decided inputs (`11`): the Blueprint is a JSON file inside the pack and is the edited truth; generated JSON is read-only and stale output is rejected; Cottage's CI pin is bumped with the first normalizer. Use the name "Blueprint" in code and docs.
- Exit ramp: if the slice does not shrink Cottage's creature data or catch a real error, stop and revert.

Out of scope: rules lowering, floors/themes, guardians, events, kernel extraction, event sourcing, logic engines, natural language.

### Plan 2 · Durable rule saves (separate)

Goal: decide and, if chosen, build persistence of rule flags and `once` markers across reloads. This is an existing engine gap (`08`), unrelated to the source language.

Must include:

- First, the decision (`11` item 4): persist, or declare reset-on-reload intended and document it. Plan both; recommend one.
- Persist mode: where state is stored (a versioned per-world key beside the WHY log at `vefr-rules-<world>`), what is saved (flags, fired markers), and recovery when a pack changes (drop unknown ids rather than crash, as growth does), plus Start over clearing it.
- Acceptance tests first: persist mode: reload keeps a fired `once` rule fired and a set flag set; reset mode and no setting: behavior identical to today; a changed pack recovers; storage unavailable degrades quietly.
- It must not depend on Plan 1 and must keep today's behavior for packs and saves already in the wild, or state the migration.
- Any docs that now say rule state resets (`rulesets.md`) change in the same PR.

## Shared rules

- Sonnet 5.5 integrates; bounded offload Foremen only. State the Foreman count and model before launch. No Opus fan-out.
- Old packs and the existing runtime stay intact. No speculative kernel extraction.
- No gate, accessibility or validation weakening. Cottage canon stays Rylee's. No deploys.
- Both plans mark each task offloadable (well specified, with a test that proves it) or keep (judgment, security, owner-gated).
