# VEFR language architecture campaign

> **Status:** proposed campaign handoff · **Owner:** Rylee · **Date:** 2026-10-02  
> **Scope:** VEFR + Cottage of the Breeze  
> **Purpose:** research, plan, then implement a language-first architecture while the engine is still small.

## Owner intent

Rylee wants to test, and if it survives contact with reality, implement this hypothesis:

> **VEFR is a language for describing games. The engine makes those descriptions true.**

More specifically:

> **VEFR owns the grammar and a small shared vocabulary. Each game pack owns its own vocabulary / dialect and content.**

This is not a request to parse arbitrary English.

The likely architecture is a deterministic structured semantic model with optional controlled-natural-language authoring surfaces.

The working analogy is:

| Human language | VEFR meaning |
|---|---|
| noun | entity / thing |
| adjective | trait / property / state |
| verb | action |
| adverb | action modifier |
| preposition | relation |
| event | something that happened |
| tense | history / prior state |
| sentence | rule |
| paragraph | encounter / scene |
| chapter | act / progression |
| voice | narrative / presentation style |
| lexicon | reusable game vocabulary |
| grammar | what combinations are valid |

The important distinction is:

> **Meaning is declarative. Machinery is replaceable implementation.**

Rendering, geometry, pathfinding, input, saves, RNG, browser plumbing, asset loading, accessibility, audio, and similar runtime concerns remain ordinary engine machinery.

The experiment is about **game meaning**.

## Campaign workflow

The requested workflow is:

1. **Sonnet 5.5:** full research and current-state packet.
2. **Opus 5.5:** orchestration and implementation plan from that packet.
3. **Sonnet 5.5:** campaign integrator, orchestrating implementation through the existing offload Foremen.
4. **Offload Foremen:** bounded builders that may themselves route to configured offload workers.
5. Finish with a **complete usable implementation**, not only a foundation or architecture document.

Do not begin implementation during the first Sonnet research pass.

**Phase A budget:** state the number of agents and their model before launching; default to Sonnet, no Opus fan-out. The packet may be smaller than the file list below if the evidence is already clear.

**Early probe (do this first, before the full census):** write one Cottage monster family plus one guardian in the proposed grammar and show it normalizing to today's `world.json` shape. If that fit is awkward, say so at once; it is the cheapest test of the core claim.

## Current repository truth when this handoff was written

Reverify before doing any work.

### VEFR

Repository: `Rylee-Bee/vefr`

Current `main` when this handoff was written:

`45f57672b343d67ad8f686be672186f59fecc0bc`

No open PRs were present.

Recent landed work includes:

- the Cottage-tested skin loader and accessibility repair;
- one-button Interact and the later declutter pass;
- quiet UI / WASD work;
- growth: classic levels and practice / learn-by-doing;
- combat;
- library/books;
- items/bag/shop;
- fog;
- build-time delve;
- developer verbs such as `publish`, `look`, and `probe`;
- the features catalog;
- theme/art kits;
- random-floor phase 1:
  - shared deterministic PRNG;
  - `generate_floor_v2`;
  - exact Python/JavaScript parity.

Recent skin verification on Cottage's real artwork measured no checked desktop or phone text below 4.5:1, with the lowest measured contrast at 5.3:1, and axe clean.

Random-floor phase 2, gates/guardians, album, equipment, and fuller act progression remain the important nearby seams.

Open backlog this campaign may reshape: VEFR #215 (random floors phase 2), #216 (album), #217 (equipment and real act 2). Treat them as **informed by Phase A**: do not build them in the old style while the campaign is pending, and do not freeze the phase 2 floor contract before the disposition.

### Cottage of the Breeze

Repository: `Rylee-Bee/cottage-of-the-breeze`

Current `main` when this handoff was written:

`c86c18a` (reverified 2026-10-02; the CI-pin commit `c0a2616` is two docs PRs behind it)

No open PRs were present.

Cottage now has:

- CI validation against pinned VEFR;
- the parchment-and-wood skin inside the real pack;
- real rendering/accessibility verification;
- town, tavern, cottage and six cellar floors;
- authored floors 1–3 and generated/dressed floors 4–6;
- 69 monsters;
- residents;
- notes/books;
- items/chests;
- fog;
- classic growth with 8 levels;
- rules/reactions;
- approved guardian art;
- an owner-decided last-room structure involving the Cellar King's seal;
- future guardian/gate, album, equipment, and per-run floor work.

Cottage is VEFR's first-game proving ground and should remain the live acceptance test for this campaign.

**Canon boundary:** Cottage story/canon remains Rylee's. Do not invent or promote story material during this architecture work.

## Architecture hypothesis

The target shape is approximately:

```text
                  VEFR
          owns GRAMMAR + CORE WORDS
                    │
        ┌───────────┴────────────┐
        │                        │
    grammar                core vocabulary
        │                        │
  entity / trait             thing / place
  relation / action          item / creature
  event / rule               move / take
  state / history            open / read
        │
        └───────────┬────────────┘
                    │
              GAME PACK
            owns its DIALECT
                    │
        ┌───────────┴────────────┐
        │                        │
   vocabulary                 content
        │                        │
   spider-family            cellar-spider
   guardian                 brass-key
   webbed                   floor themes
   mossy                    game rules
   cozy-spooky              actual prose/canon
```

Candidate semantic primitives:

- ENTITY
- TRAIT
- PROPERTY
- RELATION
- ACTION
- EVENT
- STATE
- RULE
- HISTORY / EVIDENCE
- PRESENTATION

Do not assume this exact list is correct. The research and semantic census must prove or revise it.

Core design rule:

> **Prefer vocabulary and composition over bespoke subsystems.**

Before adding a new bespoke subsystem for bosses, shops, equipment, keys, themed floors, quests, doors, books, NPCs, or encounters, first ask whether the concept can be expressed by existing grammar and vocabulary.

Do not force awkward fits. If a concept genuinely needs runtime machinery, say so.

## API hypothesis

Do **not** create one HTTP route per literal game word.

Bad:

```text
POST /add-spider
POST /make-spider-webbed
POST /unlock-door
POST /make-door-creaky
```

Investigate a small semantic API around concepts such as:

- entities;
- traits / properties;
- relations;
- actions;
- rules;
- events;
- transformations;
- validation;
- explanation / introspection.

Possible conceptual operations:

```text
entity.create
trait.add
relation.add
rule.create
action.invoke
event.record
transform.apply
validate
explain
```

Actual REST/CLI shape should follow research.

Game-specific nouns, adjectives, and verbs should normally be **data registered in a vocabulary**, not new hard-coded routes.

Multiple authoring surfaces should converge on one semantic model:

- hand-written YAML/JSON;
- CLI;
- Studio GUI;
- agent API;
- controlled-natural-language front-end;
- future conversational authoring.

## CLI / authoring hypothesis

Investigate whether VEFR can become discoverable through commands roughly like:

```sh
vefr words
vefr words --pack cottage-of-the-breeze

vefr nouns
vefr verbs
vefr traits
vefr relations

vefr explain creature
vefr explain locked
vefr explain carries

vefr describe old-webmother

vefr add creature cellar-spider
vefr describe cellar-spider as small webbed

vefr add item brass-key
vefr relate old-webmother carries brass-key

vefr when old-webmother defeated reveal brass-key

vefr generate map
vefr generate floor
vefr add level
vefr make icon cellar-spider

vefr validate
vefr play
```

These spellings are examples, not requirements.

The important idea is:

> **The CLI is an editor for the language, not a pile of unrelated engine commands.**

Generation commands are transformations:

```text
existing game description
        ↓
transformation
        ↓
new game description
```

## Themed procedural floors are part of the proof

Current random-floor phase 1 already provides:

- a shared deterministic PRNG;
- `generate_floor_v2`;
- exact Python/JavaScript parity.

Preserve that work.

Use the language architecture to improve phase 2 before its contract freezes.

Desired distinction:

> **Theme owns the vocabulary. Generator owns the arrangement.**

A floor theme may declare:

- place traits;
- creature families;
- guardian family;
- props;
- loot biases;
- structural biases;
- guarantees / signatures.

The generator should not understand “spider floor.”

It should understand something closer to:

```text
generate PLACE
using VOCABULARY
under CONSTRAINTS
from SEED
```

Preserve determinism, reachability, required parity, save compatibility, accessibility, and authored ending-room guarantees.

## Sonnet phase A: full research + current-state packet

**Do not implement yet.**

### Establish repository truth

For both VEFR and Cottage, establish live state:

- git status;
- branch/worktree truth;
- recent log;
- remote state;
- open PRs;
- CI state;
- current docs;
- current pack shape;
- runtime seams;
- existing tests.

Read the relevant VEFR policy/current-state docs, feature catalog, rulesets/CLI/journey/world-creation guides, pack loader, validator, delve implementation, feature catalog implementation, rules engine, CLI, weave/bake path, player, and relevant tests.

Read Cottage's policy/current-state docs, NOTES, DESIGN, BRIEF, STORY read-only, the real pack, rules, items, enemies, books/library, maps/regions, skin, and CI workflow.

### Semantic census of VEFR

Classify every current meaningful game concept as one of:

- entity / noun;
- trait / adjective;
- property;
- relation;
- action / verb;
- modifier / adverb;
- event;
- state;
- history;
- rule / sentence;
- encounter / scene;
- act / chapter;
- presentation / voice;
- runtime machinery;
- UNKNOWN / DOES NOT FIT.

Include at least:

- people/NPCs;
- enemies;
- items;
- books;
- map regions;
- doors/transitions;
- fog;
- combat;
- Interact;
- growth;
- shop/trading;
- rules;
- flags;
- claims;
- beliefs;
- weather;
- phases;
- acts;
- equipment proposal;
- gates proposal;
- guardians proposal;
- album proposal;
- random floors;
- skins;
- themes/art kits;
- hints/where-next;
- journal/why log;
- save state.

For each, record:

- current representation;
- proposed grammatical representation;
- whether it simplifies;
- what remains runtime machinery;
- migration risk.

### Semantic census of Cottage

Try to express the actual game, not a toy example.

Prove at least:

- a monster;
- a monster family;
- one floor theme;
- a guardian;
- a key/seal;
- locked progression;
- a book/note;
- a rule/reaction;
- growth;
- loot;
- shop;
- fog;
- skin/presentation;
- generated floor;
- authored room;
- last-room connection.

Surface ugly fits rather than hiding them.

### External research

Do current web research across:

- Inform 7;
- Quest / Quest Viva;
- TADS or equivalent IF world models;
- other controlled-natural-language game DSLs;
- Ink;
- Yarn Spinner;
- Twine/SugarCube as relevant;
- Ren'Py where useful;
- ECS/component composition;
- data-oriented game definitions;
- modding-oriented declarative engines;
- production-rule systems;
- Datalog-style approaches where useful;
- JSONLogic or similar declarative rules;
- event-condition-action systems;
- JSON Schema;
- typed AST / IR design;
- compiler normalization passes;
- language versioning/migration;
- source maps/provenance;
- knowledge-graph/ontology lessons only where useful;
- introspectable CLIs and semantic APIs.

Use roughly 15–30 useful sources. Prefer primary docs, code, papers, or maintainer explanations.

Research questions must include:

1. What did Inform 7 get brilliantly right?
2. What became difficult because it tried to look too much like English?
3. Where should VEFR use controlled language versus explicit YAML/JSON?
4. What is the smallest useful semantic IR?
5. How do we avoid ontology astronautics?
6. How do packs extend vocabulary safely?
7. How are extension collisions handled?
8. How are verbs typed?
9. How are traits defined versus merely tagged?
10. How are rules kept deterministic?
11. How are validation errors made understandable?
12. How is provenance preserved through transformations?
13. How is the grammar versioned?
14. How do old packs remain valid?
15. How do tools introspect legal nouns/verbs/traits?
16. Can graphical and CLI authoring share one write path?
17. What must remain engine machinery?
18. How do generated and authored content coexist?
19. How do we avoid turning every word into executable code?
20. How do we keep the public engine game-neutral?

### Failure modes

Explicitly test for:

- arbitrary-English ambiguity;
- grammar becoming larger than the engine;
- generic abstraction hiding simple code;
- uncontrolled pack extensions;
- runtime type confusion;
- duplicated definitions;
- semantic version drift;
- rule cycles;
- event/action recursion;
- nondeterminism;
- model-generated invalid semantics;
- weak provenance;
- giant generic API;
- “everything is an entity” abstraction failure;
- YAML archaeology;
- hard-to-debug compiler lowering;
- opaque generated state;
- accessibility lost behind presentation abstraction.

### Research packet deliverable

Produce a durable packet suitable for Opus, preferably with:

```text
00-executive-summary.md
01-current-vefr.md
02-current-cottage.md
03-semantic-census.md
04-prior-art.md
05-language-model-options.md
06-api-cli-options.md
07-migration-options.md
08-risks-and-counterexamples.md
09-recommended-core-grammar.md
10-cottage-proof.md
11-open-decisions.md
SOURCES.md
```

End with one evidence-based disposition:

- GO
- GO WITH CONSTRAINTS
- PARK

Do not implement during this phase.

## Opus 5.5 phase: orchestration / implementation plan

Give Opus the complete Sonnet packet plus live repository state.

Opus's job is synthesis and orchestration, not rediscovery.

The plan must:

- cover both VEFR and Cottage;
- be incremental;
- preserve existing behavior;
- keep old packs working;
- avoid a big-bang rewrite;
- preserve deterministic gameplay;
- use Cottage as the live acceptance test;
- use the existing Foreman workflow;
- identify safe parallelism;
- name integration points;
- separate owner decisions from engineering work.

Opus should define:

### Canonical architecture

- grammar;
- semantic IR;
- core vocabulary;
- pack vocabulary/extensions;
- canonical storage shape;
- normalization/compiler path;
- runtime lowering;
- validation;
- introspection;
- transformation API;
- CLI;
- Studio integration;
- provenance;
- versioning/migration.

### Compatibility strategy

Prefer, at least initially:

```text
new semantic source
        ↓
    normalize
        ↓
current proven VEFR model/runtime
        ↓
   existing player
```

Do not replace proven runtime machinery for conceptual purity.

### Implementation slices

Favor vertical slices such as:

1. architecture docs + frozen acceptance contracts;
2. grammar/core schema + introspection, no runtime behavior change;
3. Cottage dialect/vocabulary with one real monster/floor/key/rule;
4. normalization into existing VEFR representation with behavioral equivalence proof;
5. semantic CLI editing + explain/words surfaces;
6. Studio consuming the same semantic path;
7. themed procedural floors using vocabulary;
8. broader Cottage migration;
9. docs, cleanup, compatibility, release proof.

These are examples, not mandatory sequencing.

### Foreman topology

For every slice specify:

- repo;
- branch;
- files allowed;
- files prohibited;
- prerequisites;
- acceptance tests;
- model/tier;
- number of workers;
- parallelizability;
- integration order.

Sonnet remains the integration owner.

### Escalation conditions

Escalate only for:

- product meaning;
- canon;
- destructive compatibility break;
- public-contract decision materially different from the approved concept;
- authority/security boundary;
- accessibility tradeoff;
- unexpected third-party runtime dependency;
- inability to preserve old-pack compatibility.

Do not interrupt Rylee for routine implementation choices.

### End-state acceptance contract

The plan should end in a real journey such as:

- inspect vocabulary;
- add a Cottage entity;
- add a trait;
- add a relation;
- create a rule;
- validate;
- play;
- generate a themed floor;
- inspect/explain resulting semantics;
- weave one offline game;
- reload/save correctly;
- pass accessibility gates.

The plan must end in a complete usable system, not “phase 1 foundation complete.”

## Sonnet phase B: orchestrate implementation

After Opus returns the plan, Sonnet becomes campaign integrator.

Before launching Foremen:

- reverify both repos;
- reconcile the plan with live HEAD;
- write acceptance tests/contracts first where appropriate;
- create bounded briefs;
- commit those plans;
- make clean worktrees;
- state Foreman/worker/model count before launch;
- respect machine capacity.

Before launch, state the number of Foremen, workers and the model for each, within machine capacity.

Foremen must:

1. receive an exact brief;
2. receive an exact file scope;
3. receive an explicit acceptance command;
4. not expand scope;
5. not hide fallback behavior;
6. treat UNKNOWN as valid;
7. commit their work;
8. return a report.

Foremen should stop/escalate rather than bend frozen tests.

Sonnet independently reviews:

- diff;
- tests;
- contract;
- docs;
- migration;
- actual runtime behavior.

Land through PRs and run full gates after integration.

## Owner authorization for this campaign

**Gate:** everything below applies only after Phase A returns **GO** or **GO WITH CONSTRAINTS** and Rylee has read the disposition. On **PARK**, nothing below is authorized and the campaign stops. Scope is whatever the disposition allows; a smaller GO is a success.

Within this campaign, once that gate is passed, Rylee authorizes:

- research and architecture work;
- additive VEFR pack-contract changes needed for the language layer;
- additive public read/introspection API routes when justified;
- semantic CLI verbs;
- schema/version fields;
- compatibility adapters/normalizers;
- Cottage migration to the new representation;
- themed-floor integration;
- supporting docs/tests.

This does **not** authorize:

- weakening validation/security/accessibility gates;
- destructive removal of old-pack support before migration proof;
- arbitrary story/canon changes;
- making Cottage public;
- unrelated deployment/infrastructure work;
- force pushes/history rewrites;
- mass deletion outside proven superseded implementation;
- introducing cloud/model requirements into deterministic gameplay.

When old implementation becomes obsolete:

> prove replacement → preserve evidence/history → retire it in a bounded cleanup PR.

## Non-negotiable properties

1. Game meaning stays game-owned.
2. VEFR remains game-neutral.
3. Old packs keep working during migration.
4. Models may suggest language; they do not define runtime truth.
5. Deterministic substrate, generative edges.
6. UNKNOWN is valid.
7. Every transformation is inspectable.
8. Human-readable must not mean ambiguous.
9. Canonical state must not depend on one authoring interface.
10. CLI, Studio, agents, and hand-written files should converge on one semantic write/validation path where practical.
11. The language layer must make VEFR easier to understand, not merely more abstract.
12. A beginner should be able to ask:
    - What words does this game know?
    - What can this thing do?
    - Why did this happen?
    and get checkable answers.
13. Accessibility remains structural.
14. Delivery includes discoverability: new grammar/features appear in handbook/catalog/introspection.

## Definition of done

This campaign is not done when documents exist. The checklist below is the ceiling; the Phase A disposition may cut it (for example, Studio, the HTTP API, or a controlled-natural-language front-end may be deferred), and a smaller GO that ships alive is a success.

### VEFR

- [ ] core grammar implemented;
- [ ] core vocabulary implemented;
- [ ] schema/version defined;
- [ ] validation implemented;
- [ ] introspection implemented;
- [ ] semantic representation canonical or clearly normalized;
- [ ] CLI can inspect and make meaningful semantic edits;
- [ ] transformations use the semantic model;
- [ ] old-pack compatibility proven;
- [ ] existing runtime remains deterministic;
- [ ] catalog/docs describe the system honestly;
- [ ] full VEFR gate green.

### Cottage

- [ ] pack declares its own vocabulary/dialect where needed;
- [ ] real existing content uses the grammar;
- [ ] monsters/families/traits/relations/rules are demonstrated;
- [ ] guardians/gates fit the model cleanly;
- [ ] themed procedural floors use vocabulary rather than bespoke Cottage code;
- [ ] Cottage validates in CI;
- [ ] real gameplay works;
- [ ] save/reload works;
- [ ] woven offline file works;
- [ ] skin/accessibility stay green;
- [ ] no Cottage canon leaks into VEFR.

### Proof

- [ ] show semantic source;
- [ ] show normalized/compiled representation;
- [ ] show CLI explanation;
- [ ] show validation failure for an invalid sentence;
- [ ] show a valid Cottage edit;
- [ ] show the result in the actual game;
- [ ] show deterministic regeneration where expected;
- [ ] show a themed floor generated from vocabulary;
- [ ] show same seed → same result;
- [ ] show an old pack unchanged;
- [ ] show accessibility/browser gates.

Final documentation should let a stranger understand:

> **VEFR is a language for describing games. A pack supplies the words. The engine makes the sentences true.**

## Final deliverable to Rylee

When complete, return a low-cognitive-load report covering:

1. what changed conceptually;
2. what VEFR calls its grammar;
3. the final primitive vocabulary;
4. what Cottage adds;
5. real Cottage sentences;
6. CLI examples;
7. API/introspection examples;
8. what remained normal engine machinery;
9. compatibility proof;
10. test/accessibility proof;
11. exact VEFR and Cottage main SHAs;
12. remaining UNKNOWNs / intentionally deferred ideas.

Also show the game.

The finish line is something alive.
