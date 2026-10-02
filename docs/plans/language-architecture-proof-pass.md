# Language architecture: concept refinement and Codex proof brief

> Status: proposed, docs only · Owner: Rylee · Date: 2026-10-02
> Companion to [the campaign charter](language-architecture-campaign.md), PR #219.
> Adapted from the owner's supplied Codex handoff. No probes have been run
> by the act of adding this document; no runtime contract is approved here.

## The concept to prove

**VEFR is a language for describing games. A pack supplies the words.
The engine makes the sentences true.**

The useful ambition is to make existing game meaning visible, composable,
checkable and teachable. A language succeeds when an author can describe a
game with fewer special cases and understand what will happen when it runs.
The language analogy guides authoring; it does not dictate the internal model.

Investigate three ownership layers:

| Layer | Owns | Must not own |
|---|---|---|
| Semantic kernel | A small grammar for typed facts, relations, events, conditions, effects, rules and provenance, if the probes justify these | Combat, floors, story canon, or permission to perform effects |
| Game dialect | Game types, legal combinations, state queries and named effect signatures | One game's characters, prose, or arbitrary executable pack extensions |
| Pack | Its definitions, content, compositions and references to presentation | New executable semantics or replacement runtime handlers |

The host implements and authorizes each supported effect. A dialect describes
what an effect means and what arguments it accepts. A pack may request or
compose it, but declaring a word does not install a handler or grant authority.
This distinction matters especially in the paper-only non-game probe.

These are logical boundaries first. Do not extract a shared library, invent a
plugin loader, rename VEFR, or modify other estate products to demonstrate them.
Game-dialect vocabulary can stay inside VEFR until another implementation
actually needs it. A paper example tests plausibility, not cross-domain reuse.

## One source, explicit normalization

Start with the smallest demonstrable path:

```text
structured semantic source
  -> resolve vocabulary and types
  -> validate supported meaning
  -> normalize into today's VEFR structures
  -> existing deterministic player
```

JSON is enough for the first proof. YAML or controlled language is optional
and needs a concrete authoring benefit. No arbitrary-English parser, runtime
model calls, RDF/OWL stack, general-purpose Datalog engine or new runtime
dependency is required by this brief.

Keep exactly one authoritative editable representation for each migrated
object. The normalized artifact is derived and rebuildable. It must not become
a second editable truth. Legacy packs remain authoritative in their existing
shape. Mixed source for the same object is an error unless a deliberate,
documented precedence rule is proven necessary.

Distinguish four things in the census: authored definitions, runtime instances,
mutable play state, and presentation references. A family is not an enemy
instance; a descriptive tag is not behavior; a displayed verb is not an effect;
an event records an occurrence rather than requesting an action.

## Vocabulary has meaning only where it is declared

Test these small rules before selecting a permanent registry:

- IDs identify definitions; labels may change without changing identity.
  Scope IDs deliberately across pack, act and region. Preserve existing IDs
  and POI-label behavior until migration is proven.
- References resolve locally and deterministically. No network lookup while
  loading, normalizing, generating or playing a pack.
- A term declares its category, argument types where relevant, ownership,
  and whether it is descriptive metadata or changes runtime behavior.
- Reject collisions, undeclared references, wrong argument types, unsupported
  effects and unsupported required capabilities. Do not silently reinterpret
  an unknown term as a harmless tag.
- Prefer explicit family defaults plus instance overrides to inheritance
  machinery. If composition is needed, define conflict precedence and reject
  cycles; do not introduce multiple inheritance merely to shorten examples.
- Preserve rule/effect order. Sorting dictionaries for stable serialization
  must never sort a sequence whose order has meaning.

A future introspection surface should answer what words exist, what they
accept, what they can do, and where they came from. Reuse `vefr features`,
`vefr probe`, the validator and existing editing seams where possible.
Do not create one API route per word. New public routes remain a later decision.

## Starting evidence, with limits

Inspected VEFR PR head: `3d7e9ed288acb5ad2d14006f1ae7f2f1007fe888`.
These observations locate proof seams; they do not establish equivalence.

- `src/vefr/maplab.py`: `RULE_EVENTS`, `RULE_EVENT_KEYS`,
  `RULE_CONDITION_KEYS`, `RULE_ACTION_KEYS`, `RULE_LIMIT`, `rules_errors`
  and `_rule_known_ids` already expose much of a typed rule vocabulary.
- [The rules contract](../guides/rules.md) describes eleven events, ordered
  rules, default `once: true`, a 40-rule limit, and non-chaining behavior:
  a `give` action does not cause a `picks-up` event.
- `src/vefr/world.py`: `load_world` normalizes flat and acts-shaped packs.
  Check this seam before adding another loader or parallel world model.
- `src/vefr/delve.py`: `prng` and
  `generate_floor_v2(seed, width=30, height=20, rooms=8)` provide a concrete
  floor seam. This signature does not expose loop-frequency or corridor-width
  controls. Do not claim these theme requests already lower to it.
- Existing tests include `test_rules_engine.py`, `test_rules_validator.py`,
  `test_rules_play.py`, `test_rules_bake.py`, `test_delve_prng.py`,
  `test_delve_properties.py` and `test_pack_neutrality.py`.

Reverify live state before executing the brief. Source inspection and a green
existing test suite cannot prove a proposed semantic representation works.

## Codex's bounded task

**Validate the hypothesis with three isolated probes and return engineering
evidence to Sonnet. This brief does not launch the implementation campaign.**

Read `AGENTS.md`, `AGENT_POLICY.md`, `README.md`, `.project/CURRENT.md`,
`.project/DECISIONS.md`, `ROADMAP.md`, the adopted contracts, the campaign
charter and its prior-art note. Inspect `world.py`, `maplab.py`, `delve.py`,
`features.py`, `cli.py`, `devtools.py`, `web/packaged.html`, relevant tests,
and the rules, floors, gates/guardians, equipment and album design notes.

Read Cottage policy and its actual pack at the inspected revision, including
the world, acts, regions, rules, items, enemies and books. Repository truth
outranks every example in the supplied handoff. If a named rule or guardian
is absent or only proposed, report that rather than inventing it.

Record worktree status, main and PR SHAs, Cottage SHA, open PRs/issues and CI.
Name budget and scope before starting. Prefer fixtures, tests or `experiments/`
over production edits. Do not merge, deploy, broadly refactor, migrate the
pack, change canon, add a public route or freeze a pack contract.

Keep real Cottage text, identities and source/normalized fixtures in its
private repository or a private return packet. Public VEFR evidence uses
synthetic fixtures with the same structure; never copy private canon into
the engine's docs or tests. Report which evidence is synthetic and which
was actually exercised against the private pack.

### Probe A: one family and one guardian

Use a real inspected monster family and an existing guardian definition.
If the guardian is proposal-only, separate the observed family from the
proposed guardian; that portion remains an unimplemented fit test.

Show semantic source, expanded values, target current-pack structure,
and the exact loader/validator seam accepting it. Test identity and reference
resolution, conflicting defaults, invalid traits and relation targets.
Explain whether family composition eliminates repeated definitions or
merely creates an extra file to consult. Do not encode a guardian/key drop
through a relation unless the lowering preserves when and where the drop occurs.

### Probe B: one real rule, end to end

Find the existing rule named in the private handoff. Preserve its exact
trigger payload, condition, action order, text, identity and once semantics.
No canon edits and no new effect are needed.

Prove the forward path:

```text
semantic source -> current rule JSON -> validator -> current rule engine
```

Compare original and normalized rules against identical initial states and
event sequences: condition false, condition true, unrelated event, repeated
event, and save/reload if supported by the current harness. Compare state,
effects, speech, once markers and why records. Test that effects do not
cause rule chaining. A serialization snapshot alone is insufficient.

Call this lowering and behavioral equivalence. A true round trip would also
reconstruct editable source from normalized output; that is not required here.
If information is lost, name it. Optional source maps must not change the
existing player why-log format just to make this probe prettier.

### Probe C: one themed floor, using the existing generator

Show a theme that resolves declared families, props and constraints into
current generator inputs and a separate deterministic dressing step.
Use an independently derived dressing seed so decorations cannot consume
the layout PRNG stream and change already-proven geometry.

Split every request into supported now, dressing-only, and missing machinery.
Loops, wider/narrower corridors, signature rooms and guardian progression are
not fulfilled merely because a theme names them. Reject unsupported required
requests in the prototype, or report them as deferred. Do not silently fall
back to an ordinary floor and claim success.

Prove equal complete inputs produce equal outputs. Record seed, generator
version, normalization version, theme/content revision and parameters; seed
alone is not a promise across changing algorithms or content. Preserve exact
Python/JavaScript parity where both implementations execute the operation.
If dressing runs only at build time, explicitly label runtime parity N/A.

Check reachable stairs before and after dressing, valid placement, no blocked
progression, and bounded behavior for impossible constraints. An authored
ending-room connection must remain authored. No generator replacement.

## Decide the smallest kernel honestly

Compare the supplied candidates:

- A: entity, trait, property, relation, action, event, state, rule, history,
  presentation.
- B: fact, relation, event, condition, effect, rule, provenance.

Return A, B, hybrid or UNKNOWN against Cottage, existing rules, random floors,
growth and the equipment/gates/album proposals. An IR can reuse existing
`when`/`if`/`then` directly if a new vocabulary adds no value.

For each primitive, show the concrete job it does, the current owner of that
job, and the code/concepts it removes or adds. Do not preselect B because it
sounds more general. Present the simplest current-pack representation beside
the proposed one so the abstraction has a fair comparison.

Do one paper-only non-game probe such as a repeated failed check requesting
incident recording and notification. State whether "twice" means consecutive
failures or a time window, who holds the counter, and who authorizes notification.
Use a real inspected rule if available; otherwise label the example synthetic
and generality UNKNOWN. Do not implement a service dialect or send anything.

## Effects, evidence and contracts

Treat today's named effect list as the starting capability boundary.
Keep pure queries separate from state mutation. Distinguish authored truth,
observed events, character belief and derived answers: a belief is not a fact
about the world, and provenance is not permission or proof of correctness.

Initially preserve current state plus structured evidence. Evaluate full event
sourcing only if there is a demonstrated requirement that this cannot meet.
Likewise, try pure derived queries before any logic engine. Retain ordered,
finite, deterministic, non-chaining rules and existing limits.

Prefer declared invariants where they reuse actual checks. Separate schema
validity, reference validity, static contracts, generator guarantees and runtime
assertions. A declaration cannot prove an implementation satisfies it. A
failed guarantee must produce a clear failure, not an unreported retry loop.

Source mapping should resolve an emitted rule or field back to an origin
path and JSON pointer, with the normalizer version and defaults applied.
Keep paths pack-relative and avoid leaking private text into public evidence.
Define useful validation errors before adding a prose front end.

## Research spot-check and compatibility

Audit architecture-changing claims in the existing prior-art note; do not
restart its whole research campaign. Use primary docs, code or papers and
record confirmed, corrected or unverified per claim. The correction addendum
in that note is a starting point, not a full audit.

In particular: Datalog permits recursion; schema identifiers do not guarantee
pack compatibility; an event log is not automatically a complete save/replay
system; project cadence does not establish why a project slowed; and
"closest project" is an analytical judgment with criteria, not an observed fact.

Propose an explicit compatibility matrix for legacy packs, semantic source,
normalized artifacts and saves. Grammar/dialect version, JSON Schema dialect,
runtime version and save version are different contracts. Unknown required
versions fail clearly. No guessed deprecation date or automatic adapter removal.

## Return packet to Sonnet

Keep the report concise but include reproducible artifacts and exact commands:

1. Live state: repos, main/PR/pack SHAs, clean or preserved dirty state, CI.
2. Semantic census: existing owners, duplicated shapes, missing capabilities,
   and kernel/game/runtime classification with paths and symbols.
3. Probes A/B/C: source, normalized form, exercised behavior, negative cases,
   provenance, determinism and parity results; synthetic/private distinction.
4. Kernel decision and conceptual cost; actual simplifications and ugly fits.
5. Effect boundary: existing effect classification and ownership;
   proposed renames remain aliases or deferred until compatibility is proven.
6. Adopt/adapt/defer/reject for event sourcing, queries and declared contracts.
7. Research corrections with primary sources and remaining unverified claims.
8. Smallest migration path, compatibility matrix, rollback and real risks.
9. GO, GO WITH CONSTRAINTS or PARK, with the exact scope earned by evidence.
10. Next safe implementation slices, dependencies and remaining owner decisions.

State branch, commit SHA, changed files, exact test commands/results and
applicable contract statuses. Follow the repo's final truth-report format.
Put unknowns beside the relevant probe rather than burying them in a footer.

## Acceptance and stop conditions

The proof pass is complete when all three probes have evidence-backed
outcomes, the kernel comparison is explicit, and Sonnet can plan the next
slice without reconstructing assumptions. A falsified probe is useful output.

Stop or narrow if the adapter changes gameplay, needs unapproved executable
extensions, cannot preserve private canon or compatibility, or adds more
conceptual weight than it removes. Missing guardian/theme machinery may
reduce the GO scope; it must not turn into an unrequested subsystem build.

Sonnet incorporates the proof packet into Phase A. Opus plans from verified
evidence, and Sonnet remains campaign integrator using the existing Foremen
workflow after the charter's owner/disposition gate. This addition changes
neither merge authority nor that gate.

**Success is a game description that is easier to understand and change,
with an engine that remains small enough to understand.**
