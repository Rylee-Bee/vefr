# VEFR language framework — Sonnet implementation update

Please take this through a bounded implementation pass in `Rylee-Bee/vefr`. Read the repository instructions, current implementation, tests, and architecture records first. Challenge the proposed changes where the code disagrees, then implement the smallest justified changes and verify them.

The goal is **more useful flexibility with fewer shared concepts and less duplicated meaning**.

> Universalize mechanisms and guarantees. Keep domain vocabulary local.
>
> Shared machinery does not require shared authoring syntax.

This authorizes the implementation scope below. It does not authorize a new universal language, a Format 2 design, or an estate-wide framework.

## 1. Establish the current baseline

VEFR references:

- `src/vefr/blueprint.py`
- `docs/adr/0008-blueprint-format.md`
- `docs/plans/blueprint-family-normalization-plan.md`
- `docs/plans/language-architecture-campaign.md`
- `docs/plans/language-architecture-proof-pass.md`
- `docs/plans/language-architecture-sonnet-phase-a-handoff.md`
- `.project/DECISIONS.md`
- `ROADMAP.md`

Cottage evidence source: `Rylee-Bee/cottage-of-the-breeze`, reported PR #68 / branch `feat/blueprint-creatures`.

- `worlds/cottage-of-the-breeze/blueprint.json`
- `worlds/cottage-of-the-breeze/blueprint.lock.json`
- `worlds/cottage-of-the-breeze/acts/act-1/floor-*/contract.json`

These references and results come from the supplied handoff; they have not been independently reverified for this update. Resolve the actual current branches and record the commit SHAs before making comparisons. If the trial has merged or changed, use the relevant actual revision and explain the difference. Do not overwrite unrelated work.

Reported corpus: 69 creature instances, 10 current creature families, and 6 floors containing creatures.

| Representation            | Family values | Instance values | Total authored game values | Reduction from 508 |
| ------------------------- | ------------- | --------------- | -------------------------- | ------------------ |
| Legacy records            | —             | —               | 508                        | —                  |
| Current Blueprint trial   | 45            | 232             | 277                        | 45.47%             |
| Proposed semantic cleanup | 49            | 209             | 258                        | 49.21%             |

The source excludes the format version marker from these counts. Reconstruct the counting method, state exactly what it counts, and apply it consistently. Do not silently substitute file size, JSON key count, or line count. Independently verify the numbers and compare all expanded enemy lists with the committed canonical lists.

The source reports 69 expanded records across 6 regions with zero structural differences for the proposed cleanup. Treat that as a claim to reproduce.

207 current instance values are explicit decisions: 69 IDs, 69 family selections, and 69 positions. This suggests limited remaining compression for this hand-authored corpus; it does not prove a universal compression floor.

## 2. Implement one family-resolution operation

The reported implementation uses `_family_record()` for inheritance validation/default merging and `_family_chain()` for ancestry provenance. Inspect whether that duplication still exists.

If it does, consolidate the semantic traversal into one local resolution operation that provides:

- resolved defaults;
- the ancestry chain in the existing order;
- enough source information to identify the declaration supplying a validated value.

Record expansion and provenance should consume the same resolved result. Preserve existing merge precedence, error behavior except for intentional diagnostic corrections, and deterministic ordering. Preserve missing-parent and cycle rejection, including unused families if the current contract validates them.

Keep this implementation in Blueprint. Use the simplest internal representation that fits the current code. Do not create a resolver framework, dialect registry, public API, or persistent cache. If resolution is memoized, keep it scoped to one compilation and prevent instance overrides from mutating shared resolved defaults.

This change should remove duplicated semantic logic. Performance is a secondary benefit, not its justification.

## 3. Make validation errors identify the actual source

The reported `drops` validation checks the merged record but points to an instance `properties/drops` path even when the value came from family defaults.

Track the winning source through the existing merge rules. For an invalid drop, report the actual declaration:

- a family default when inherited from that family;
- an ancestor default when inherited through a descendant;
- the instance property when explicitly overridden there.

For example, an inherited invalid drop should identify `/families/<family>/defaults/drops`, rather than an instance property that does not exist. Include the offending list element where the existing diagnostic convention supports it. Use correctly escaped JSON Pointer segments.

Do not search afterward for an equal value to guess its origin: multiple declarations can contain identical values. Origin follows precedence. Reuse source tracking for other existing checks where it simplifies the same path; do not build a general provenance subsystem.

Keep richer source tracking internal unless the existing public contract requires otherwise. Do not add serialized provenance fields or change lock format as an incidental part of this refactor. Preserve existing canonical output and provenance semantics, apart from explicitly tested diagnostic corrections.

## 4. Verify the Cottage taxonomy cleanup

Evaluate this candidate graph against actual defaults and instances:

| Family              | Parent          | Proposed shared facts or change                               |
| ------------------- | --------------- | ------------------------------------------------------------- |
| `nest-of-moths-3hp` | `nest-of-moths` | Preserve the explicit HP variant for now                      |
| `rat-kind`          | none            | Only genuinely shared facts; reported `sprite: rat`, `atk: 1` |
| `cellar-rat`        | `rat-kind`      | Keep its one-off potion drop at instance level                |
| `fat-cellar-rat`    | `rat-kind`      | Put the repeated `cloudy-potion` drop in its defaults         |
| `rustle`            | none            | Base of the rustle hierarchy                                  |
| `loud-rustle`       | `rustle`        | Preserve the existing expanded values                         |
| `howling-rustle`    | `loud-rustle`   | Preserve the existing expanded values                         |
| `shade-kind`        | none            | Only genuinely shared facts; reported `sprite: shade`         |
| `damp-shade`        | `shade-kind`    | Preserve the one-off `brass-ring` exception                   |
| `deep-shade`        | `shade-kind`    | Put the repeated `cloudy-potion` drop in its defaults         |
| `hollow-shade`      | `deep-shade`    | Inherit the shared drop                                       |

Reported evidence: potion drops occur in 9/9 fat cellar rats, 12/12 deep shades, and 2/2 hollow shades, but only 1/7 cellar rats. Damp shades do not normally have that drop.

The principle is **move repeated facts to their real source of truth**. A parent must express meaningful shared facts, not merely save characters. Verify every property affected by reparenting; the table is not a complete replacement definition.

Use Cottage as read-only integration evidence for the VEFR implementation. Prove the candidate cleanup in an isolated working copy and report the exact patch or follow-up needed. Do not bundle a Cottage migration into the VEFR change.

Keep `nest-of-moths-3hp` for now. The source reports HP 3 variants on floors 1–3 and HP 4 variants on floors 4–6, with the same name, sprite, attack, and XP. That suggests a progression boundary worth investigating later; it does not justify introducing tuning or generation machinery now.

## 5. Update the architecture records narrowly

Update the existing relevant records rather than creating another overlapping manifesto. Distinguish implemented decisions from hypotheses and deferred work.

Record these working boundaries:

- **Definition:** what exists and its authored defaults.
- **Recipe:** what is wanted; an ownership hypothesis for future work.
- **Generator:** how it is arranged within constraints.
- **Runtime:** what executes, under host authority.

Check those labels against VEFR's actual seams. Keep the existing conclusion “Theme owns vocabulary; Generator owns arrangement.” Do not rename established concepts just to fit this model.

The earlier campaign considered `kernel / dialect / pack` and a larger semantic ontology. The current evidence supports keeping Blueprint local and looking for repeated transformation machinery. It does not prove an estate-wide kernel.

Make the second-consumer rule operational: extract shared machinery only when two actual consumers independently need the same operation and invariants. Two helper functions inside Blueprint justify local consolidation, not cross-domain extraction.

Use a practical subtraction test for future abstractions:

1. Name the duplicated fact, implementation, misplaced decision, or missing invariant.
2. Show what the change deletes or makes enforceable, including provenance accuracy.
3. Account for the concepts, configuration, maintenance, and migration it adds.
4. Prefer the smallest change whose concrete benefit outweighs that cost.

Flexibility alone is insufficient. If a proposal only shortens syntax or serves hypothetical consumers, defer it. A local bug fix does not need a second consumer.

Potential shared transformation/provenance machinery remains a research direction. Do not implement generic `read / validate / resolve / transform / verify / explain` interfaces in this pass, or treat the rule language as equivalent to Blueprint inheritance.

## 6. Preserve these invariants

- Blueprint Format 1 and closed schemas.
- Existing normalized runtime structures and deterministic output.
- Stale-output refusal and the current lock/freshness contract.
- Compatibility with packs that do not use Blueprint.
- Explicit IDs, family choices, hand-authored positions, instance order, and overrides.
- One-off exceptions, including drops.
- Pack-owned vocabulary and host-owned effect authority.
- The existing `when / if / then / once` rule language.

No traits, mixins, multiple inheritance, arbitrary templates, plugin framework, universal entity model, relation graph, Datalog, event sourcing, natural-language parsing, new runtime, or broad migration. No `vefr explain` command yet. No Format 2 proposal without a reproduced Format 1 limitation in real content.

If a requested change needs one of those excluded features, document the concrete blocker and continue the independent in-scope work. Do not expand the project to accommodate it.

## 7. Verify behavior with targeted checks

Run the repository-required checks and meaningful tests for the changed contracts:

- Existing inheritance/default precedence and ancestry order remain stable.
- Missing parents and cycles still fail correctly.
- Instance overrides do not leak into siblings or later compilation runs.
- Invalid direct family drops point to their declaration.
- Invalid ancestor drops point to the ancestor declaration.
- Invalid instance overrides point to the instance declaration.
- A valid override follows existing semantics when it replaces an invalid inherited value; do not invent new eager-reference validation rules.
- Family names requiring JSON Pointer escaping produce correct pointers, if allowed by the schema.
- Canonical records, ordering, and existing serialized provenance remain equivalent on valid fixtures.
- Existing determinism, lock verification, stale-output refusal, and no-Blueprint compatibility checks pass.
- The isolated Cottage cleanup reproduces all 69 canonical records across the six relevant regions/floors with no structural differences.

Use the existing test conventions and commands. Report the commands actually run. If a repository or revision is unavailable, state the limitation; do not replace real integration evidence with invented data or label it verified. VEFR's independently justified refactor and diagnostic fixes can proceed without the Cottage checkout, but Cottage equivalence and counts remain unverified.

Lock bytes may legitimately change when authored source changes. Refresh through the existing workflow and verify freshness; do not edit hashes by hand or confuse a source-dependent lock change with a runtime behavior change.

## 8. Finish with a reviewable implementation report

Keep changes cohesive and separately reviewable where practical: local resolver/diagnostic changes with tests, then the narrow architecture update. Keep the Cottage cleanup as a distinct follow-up. Do not merge or deploy as part of this handoff.

Return:

1. The revisions inspected and what changed in VEFR.
2. Any premise corrected or rejected, with code/data evidence.
3. The independently verified count table and structural comparison, or explicit verification gaps.
4. Tests and commands run, outcomes, and material limitations.
5. Public behavior or compatibility changes, including corrected error pointers.
6. What stayed local, what was deferred, and what remains UNKNOWN.
7. The smallest next step, only if the evidence justifies one.

Completion means the justified local implementation is done, tested, and documented. It does not mean producing another architecture questionnaire.

**Make the existing language easier to trust and maintain. Let broader reuse earn its place through a second real consumer.**
