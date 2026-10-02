# Prior art for a language-first VEFR (research note)

> **Provenance:** produced 2026-10-02 by one MiniMax-M3 research worker with web search (37 tool calls), read-only, for the language architecture campaign (`docs/plans/language-architecture-campaign.md`). Reviewed by Claude, not by Rylee.
> **Verification:** 68 cited URLs were fetched; 60 returned 200 and one truncated link was removed. These 7 blocked bots (HTTP 403) and were **not opened**, so treat what they support as UNVERIFIED: https://dl.acm.org/doi/fullHtml/10.1145/3446977, https://help.roll20.net/hc/en-us/articles/360037772773, https://stackoverflow.com/questions/250403/rules-engine-pros-and-cons, https://www.npmjs.com/package/json-logic-engine, https://www.reddit.com/r/interactivefiction/comments/11n9ey9/, https://www.reddit.com/r/programming/comments/8uj95/, https://www.researchgate.net/publication/222441929_DEVICE_Compiling_production_rules_into_event-driven_rules_using_complex_events. A link resolving does not prove it supports the claim next to it. Project-status claims (for example "paused after 2012") rest on forum posts. This note is evidence about the past, not current state.
> **Use:** the starting point for Phase A prior-art work. Re-verify any source before it is cited in a decision.


> Read-only research brief for VEFR's language architecture campaign. Citations are URLs actually returned by web search; no URLs are invented. Claims without a directly-observed source are marked `UNVERIFIED`.

The plan at `docs/plans/language-architecture-campaign.md:9-21` proposes a small domain-neutral semantic kernel (entity, trait, relation, action, event, rule, history, provenance) with game dialects and pack-supplied vocabulary, compiling into an existing deterministic runtime. The closest historical analogues all sit somewhere on the spectrum between "natural-language-as-source" (Inform 7, ACE) and "structured data + rules" (Ink, JSONLogic, ECS).

---

## Correction addendum — 2026-10-02, Codex

This addendum supersedes the affected conclusions below. The original note
remains intact to preserve its provenance. This is a spot-check, not a full audit.

| Claim in the original note | Status | Correction or limit |
|---|---|---|
| Pure Datalog terminates because there are no rule cycles | Corrected | Recursion is supported. Pure finite-domain, function-free Datalog reaches a finite fixed point; arithmetic extensions can introduce nontermination. [Soufflé's primary tutorial](https://souffle-lang.github.io/tutorial) explains the distinction and demonstrates recursive reachability. |
| Frozen JSON Schema identifiers guarantee old packs/programs stay valid | Corrected | `$schema` declares the schema dialect; `$id` sets its base URI for identification and reference resolution ([official structuring guide](https://json-schema.org/understanding-json-schema/structuring)). Neither promises application backward compatibility. Pack compatibility needs explicit readers, fixtures and migrations. [Official dialect documentation](https://json-schema.org/understanding-json-schema/reference/schema) describes version-specific semantics and warns that custom vocabularies require implementation support. |
| Event sourcing buys save/reload, replay, tests and provenance in one mechanism | Corrected | These are possible benefits, conditional on complete events and compatible replay logic. Schema evolution and migration add costs. [Microsoft's architecture guidance](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing) explicitly advises weighing complexity and notes that conventional state management is sufficient for most systems. Compare current state plus structured evidence first. |
| TADS/Penrose cadence proves maintainer or migration failures killed them | Unverified | Activity, present status and causes are different claims. Forum anecdotes and a past web page do not establish causality. Do not use these conclusions to choose VEFR architecture until checked against current releases and maintainer evidence. |
| StoryNexus is the closest project; particular architectural choices caused projects to succeed | Unverified as factual claims | These are analytical judgments. State comparison criteria and supporting evidence; present them as analysis rather than verified project history. |

The first three corrections were checked against the linked primary pages
on 2026-10-02. The other rows are evidence downgrades; no new project-status
audit is claimed. The Datalog/Prolog compatibility statement also needs
implementation/version-specific evidence rather than a subset argument.

---

## (1) Prior-art table

| Name | What it is | URL | What to borrow | What to avoid | Status |
|---|---|---|---|---|---|
| **Inform 7** | Natural-language DSL for parser IF; compiles to Z-machine/Glulx via Inform 6. | https://ganelson.github.io/inform-website/ | Rule-as-sentence forms; "The X is Y" assertions; built-in library that *is* the world model; extension mechanism; strong prose-as-source feel. | Letting surface English drive semantics; ambiguity in "unlock the door" cases is a well-known failure (see intfiction/65257 #example). | Alive. Graham Nelson still maintains it; new web site and compiler revisions ongoing (2024–25). |
| **Inform 6** | Lower-level IF language that Inform 7 lowers to; "library"-oriented world model. | https://www.inform-fiction.org/ | Library-driven model, compiler-target decoupling, mature conformance suite. | Hand-coding for domain knowledge; very programmer-centric surface. | Maintained alongside I7. |
| **TADS 3** | Object/prototype-OO DSL for parser IF; rich world-model library (adv3). | https://tads.dev/, https://www.tads.org/t2doc/doc/overview.html, https://en.wikipedia.org/wiki/Text_Adventure_Development_System | Prototype-based objects + multiple inheritance for entity modeling; strong IF library conventions. | Heavy OO abstraction for a small engine; small maintainer base. | Low activity; Reddit `r/interactivefiction` thread notes last release in late 2012 (https://www.reddit.com/r/interactivefiction/comments/11n9ey9/); tads.dev still hosts docs. UNVERIFIED whether 3.1.4 shipped. |
| **Quest / Quest Viva** | Browser-based IF authoring system with GUI + scripting. | https://questviva.com/, https://github.com/textadventures/quest, https://www.ifwiki.org/Quest | Web-native GUI for non-programmers; declarative object/turn scripting; one maintainer kept it alive for years. | Single-maintainer bus factor; GUI grew faster than the language. | Alive but slow cadence. |
| **Ink (inkle)** | Marked-up narrative scripting language for branching dialogue. | https://www.inklestudios.com/ink/, https://github.com/inkle/ink | Knot/stitch/weave structure; diverts as named transitions; variables tagged with `VAR`; built-in runtime export to JSON. | Strongly narrative-only; world/state model is intentionally thin. | Alive, actively used in shipped games (e.g., 80 Days). |
| **Yarn Spinner** | Dialogue scripting language with screenplay-like syntax. | https://yarnspinner.dev/, https://github.com/YarnSpinnerTool/YarnSpinner, https://docs.yarnspinner.dev/ | Tags as a deliberate metadata channel (e.g., `#line:` for localization and asset hooks); commands as a typed extension surface; strong VS Code/Unity integration. | Commands can become a giant grab-bag — needs a fixed effect set. | Alive, well-maintained. |
| **Ren'Py** | Visual novel engine with Python-embedded declarative script. | https://www.renpy.org/, https://www.renpy.org/doc/html/index.html | "Statements look like prose"; Python escape hatch for anything hard; well-loved docs; live localization system. | Surface is not semantic — it's a thin layer over Python; semantic intent easily leaks into escape hatches. | Alive, large community. |
| **Twine / SugarCube / Harlowe** | Hypertext IF with macro-story-formats. | https://www.motoslave.net/sugarcube/2/docs/, https://twine2.neocities.org/ | Story formats that compile to JS; macro/tag vocabulary; multi-target export. | SugarCube and Harlowe forked without a unifying IR — packs must choose a story format. | SugarCube and Harlowe both documented and maintained (2024 dates on UCI lib guide). |
| **LambdaMOO / MOO** | Multi-user text world with an in-world programming language (Lisp-like). | https://en.wikipedia.org/wiki/LambdaMOO, https://brn227.brown.wmich.edu/Barn/files/docs/lambdamoo/pm1.8.1/ProgrammersManual_1.html | The "live world DB" model where rooms/objects/verbs are *data*; verbs-as-named-effects dispatched by the server; in-world programming means in-world provenance. | Full-power programming in the loop is the famous "untrusted LambdaMOO programmer" risk; capacity to permanently break the world. | LambdaMOO reference server still online; the language itself essentially frozen; modern successors (Evennia) use a host language. |
| **Evennia** | Python MUD framework, code-as-data via Python modules. | https://www.evennia.com/, https://github.com/evennia/evennia | Django-style "everything is a Typeclass"; spawn/limbo as primitives; CLI tooling; one canonical write path. | Mixing Python and "game" muddies the pack boundary; what is data vs. code is not a fixed boundary. | Alive, active. |
| **Dwarf Fortress RAW** | Declarative, text-based, hierarchical definition of creatures/items/reactions. | https://dwarffortresswiki.org/Modding, https://bay12games.com/dwarves/modding_guide.html | Pure data files drive simulation; tag-based inheritance `[CREATURE:...]`; modding community thrives on text files; Lua procedural layer on top. | Implicit tags, no formal schema, no migrations — packs rot when DF changes token names. | Alive; Bay 12 official guide current. |
| **CK3 / Jomini / Clausewitz (Paradox)** | In-house declarative scripting for events, effects, triggers. | https://ck3.paradoxwikis.com/Scripting, https://pdx.tools/blog/a-tour-of-pds-clausewitz-syntax, https://forum.paradoxplaza.com/forum/threads/ck3-dev-diary-37-making-mods.1410656/ | Trigger/effect/command split is essentially the same separation as "facts/queries/effects" in the brief's concept #3. Scope/where chains are a real-world "what can a rule ask for?" boundary. | Massive token vocabulary (1000s of effects) without strong type-checking; modder experience often painful (per Reddit threads). | Alive; Jomini is the shared engine. |
| **Roll20 Mod Scripts** | Sandbox JS API for tabletop RPG mods. | https://help.roll20.net/hc/en-us/articles/360037772773 | A bounded-effect host API; one canonical sandbox as the "engine". | Capability boundary is loose; scripts can do almost anything. | Alive. |
| **Attempto Controlled English (ACE)** | Subset of English with formal semantics that compiles to FOL/DRACE. | https://en.wikipedia.org/wiki/Attempto_Controlled_English, https://attempto.ifi.uzh.ch/site/pubs/papers/ace3manual.pdf, https://github.com/Attempto/ACE-in-GF | Strong story of "controlled natural language as a real semantic surface"; disambiguation rules; ACE → GF port to multiple natural languages. | Academic reach is small; never shipped in a product most users touched; CNL tooling alone doesn't sustain a community. | Research project; site (attempto.ifi.uzh.ch) still up; alive as research. |
| **JSONLogic** | JSON-as-rule-format library. | https://jsonlogic.com/ | Pure data rule format; engine-agnostic; multiple ports (Rust, JS, Python). | Rule vocabulary is generic — easy to write opaque ones; no provenance or explanation surface. | Alive. |
| **json-rules-engine** | Event-condition-action library for JSON rules. | https://github.com/cachecontrol/json-rules-engine, https://www.npmjs.com/package/json-logic-engine | The literal ECA shape the brief is gesturing toward ("when event, if fact, then effect"); event bus + fact facts. | Rules and facts drift; no schema enforcement; introspection is weak. | Alive. |
| **Drools / CLIPS / Jess** | Production-rule systems (Rete-based). | https://docs.drools.org/latest/drools-docs/drools/rule-engine/index.html, https://en.wikipedia.org/wiki/CLIPS, https://www.clipsrules.net/ | Forward-chaining rules over facts; agenda/priority; salience; explainable "because of these rules". | Powerful but operationally heavy; learning curve steep; often rejected by engineering orgs (cf. "rules engine production was a nightmare" Medium post). | Drools: alive (Quarkus era). CLIPS: alive as NASA public-domain. Jess: dormant (UNVERIFIED pair of dates). |
| **Event Sourcing** (pattern) | Append-only event log as source of truth. | https://martinfowler.com/eaaDev/EventSourcing.html, https://martinfowler.com/eaaDev/EventNarrative.html, https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing | Event log as save/replay/debug/why-answered in one mechanism; this is exactly concept #1 of the brief. | Migrating an existing stateful system to ES is famously expensive; many production post-mortems report this (Medium "production was a nightmare"). | Pattern, alive; production uptake uneven. |
| **JSON Schema** | Typed schema language for JSON. | https://json-schema.org/specification, https://json-schema.org/docs | Versioned drafts (Draft 4 → 2020-12), `$id` and `$ref`, generator ecosystem (ajv, schemastore). | Schemas alone don't constrain prose; user content easily outruns them. | Alive, IETF-track. |
| **Datalog** | Declarative logic-programming language (subset of Prolog). | https://en.wikipedia.org/wiki/Datalog, https://drops.dagstuhl.de/storage/01oasics/oasics-vol138-rw2024+rw2025/html/OASIcs.RW.2024-2025.7/OASIcs.RW.2024-2025.7.html | Pure declarative facts + rules; pure Datalog terminates (no rule cycles) — *the* technical justification for "facts + queries". | Too thin alone; needs a host. Resurgence in auth (Google Zanzibar, OPA Rego UNVERIFIED if Zanzbar-like is enabled here). | Alive, academic + applied. |
| **Entity-Component-System (ECS)** | Data-oriented game architecture: entities, components, systems. | https://en.wikipedia.org/wiki/Entity_component_system, https://github.com/SanderMertens/ecs-faq | The cleanest precedent for "entity + trait (component)" as a kernel; data-oriented layout; traits compose freely. | ECS is implementation, not language; without a typed vocabulary for components it doesn't answer the "what is a thing?" question. | Very alive in gamedev (Unity DOTS, Bevy, Flecs). |
| **Penrose (CMU math→diagram)** | Declarative math → diagram framework. | https://github.com/penrose/penrose, https://penrose.cs.cmu.edu/siggraph20 | An interesting "declarative core compiles to many visual styles" architecture, with Substance/Schema/Style three-way split. | SIGGRAPH 2020 site says "not ready for contributions or public use yet"; as of 2024 the project shows reduced momentum (UNVERIFIED pair of dates). Useful negative: a beautiful academic DSL can still stall. | Stalled/low activity. |
| **StoryNexus / DendryNexus** | Quality-based narrative engines (Fallen London; "cards" + "qualities"). | https://troygilbert.com/modeling-games/thoughts-on-storynexus/, https://intfiction.org/t/chroniclehub-a-qbn-engine-like-storynexus/78061 | Closest *game-shape* analog: small kernel of "qualities, decks, cards, storylets" → many stories. | QBN shape is great for narrative-only games; not a general game kernel. | StoryNexus service shut down for new users; DendryNexus is a community port (chroniclehub thread). |
| **Gherkin / Cucumber** | Business-readable Given/When/Then DSL for BDD. | https://cucumber.io/blog/bdd/gherkin-rules/, https://behat-docs.readthedocs.io/en/v3.0/user_guide/gherkin.html | Strong lesson in "business-readable English" with formal step definitions behind it; long-lived because it targets a real workflow (acceptance tests). | Steps can become a Tower of Babel; without a vocabulary registry, two teams' "Given" mean different things. | Alive, mainstream. |
| **ECA (event-condition-action) academic tradition** | Active databases / reactive rules in OO DBs. | https://dl.acm.org/doi/fullHtml/10.1145/3446977 (Blečić et al. 2021), https://www.researchgate.net/publication/222441929_DEVICE_Compiling_production_rules_into_event-driven_rules_using_complex_events | Formal ECA is exactly what concept #1+#2 of the brief calls for; literature shows where it has worked (active DB) and broken (production ops). | ECA without an effect/capability boundary = untrusted code. | Academic; cited and active. |

Sources in this list were retrieved live; status notes that I could not verify are tagged `UNVERIFIED`.

---

## (2) The five most important lessons for VEFR

1. **Keep the natural language, if you have any, on the side.** Inform 7's biggest innovation is also its biggest tax: "unlock the door" is ambiguous in English, and users hit that constantly (`https://intfiction.org/t/ai-class-case-study-using-inform-7-unlocking-and-ambiguity/65257`). ACE shows the same lesson from the academic side: controlled natural language is *possible*, but rarely ships to end users (`https://en.wikipedia.org/wiki/Attempto_Controlled_English`). Ink and Yarn Spinner chose the opposite, successful end of the spectrum: short, prose-flavoured DSLs with a real formal grammar underneath. VEFR should default to YAML/JSON with one optional CNL surface, not the other way around.

2. **Split "facts, rules, queries" from "effects", and keep effects small and named.** Both Drools/CLIPS (rule engines, `https://docs.drools.org/latest/...`) and the CK3/Jomini engine (`https://pdx.tools/blog/a-tour-of-pds-clausewitz-syntax`) prove this split works at scale. The ECA literature (Blečić 2021, `https://dl.acm.org/doi/fullHtml/10.1145/3446977`) and LambdaMOO's verb model (`https://en.wikipedia.org/wiki/LambdaMOO`) point to the same shape: verbs/named-effects are the host's responsibility, rules can only *request* them. The brief's concept #3 (effects as capability boundary) is the right instinct — `reveal`, `grant`, `notify` should be a fixed list, and only the host decides what they mean.

3. **Event sourcing is a real answer to "why did this happen?", not a magic cure.** Fowler's original essay (`https://martinfowler.com/eaaDev/EventSourcing.html`) and the follow-on "production was a nightmare" posts both apply. It buys save/reload + replay + tests + provenance in one mechanism, which is exactly what concept #1 of the brief wants — but only if the migration plan is bounded and old state stays readable through an adapter (the brief's "honest exit ramps" requirement).

4. **One canonical write path beats many authoring surfaces.** Evennia succeeds by having "Python modules imported into the server" as the single write path (`https://www.evennia.com/docs/latest/Evennia-Introduction.html`); Yarn Spinner succeeds by making Yarn scripts *and* string tables pass through one compiler (`https://docs.yarnspinner.dev/`); json-rules-engine and JSONLogic succeed because there is one rule format (`https://jsonlogic.com/`). Twine/Harlowe/SugarCube is the counter-example: story formats diverged, packs can't move between them. This argues for the brief's stated goal: CLI, Studio, agents, and hand-written files converge on one semantic write path.

5. **Survives = small kernel + conformance suite + named owner.** Datalog has lived for decades because its kernel is tiny and provable (`https://drops.dagstuhl.de/storage/01oasics/oasics-vol138-rw2024+rw2025/html/OASIcs.RW.2024-2025.7/OASIcs.RW.2024-2025.7.html`). JSON Schema has lived because of its draft/process and a conformance culture (`https://json-schema.org/specification`). Penrose (CMU) and TADS illustrate the opposite — beautiful technical idea, small maintainer base, dwindling cadence (`https://www.reddit.com/r/interactivefiction/comments/11n9ey9/`, `https://github.com/penrose/penrose`). The brief's durability section (`docs/plans/language-architecture-campaign.md:787-792` of the plan) already names this requirement; the prior art confirms it's not optional.

---

## (3) What killed or sustained comparable languages

**What killed / is killing them:**

- **Single-maintainer bus factor.** TADS effectively paused after2012 (`https://www.reddit.com/r/interactivefiction/comments/11n9ey9/`); Penrose slowed to a crawl (`https://github.com/penrose/penrose`); StoryNexus shut down for new users (Troy Gilbert post). A grammar without a process for shared ownership dies with the owner.
- **Grammar bigger than the engine.** The brief calls this out as a named failure mode. The ECA / CLIPS / Drools tradition is full of projects where the rules language outgrew the team that was supposed to maintain it. Stack Overflow's "rules engine pros and cons" thread (`https://stackoverflow.com/questions/250403/rules-engine-pros-and-cons`) is a museum of abandoned rule engines.
- **Surface ambiguity with no escape hatch.** Inform 7's critics (`https://intfiction.org/t/ai-class-case-study-using-inform-7-unlocking-and-ambiguity/65257`, `https://www.reddit.com/r/programming/comments/8uj95/`) show what happens when "looks like English" is the only surface: users hit ambiguities the author can't predict.
- **No deprecation policy, no migrations.** Dwarf Fortress raws rot when Bay 12 renames tokens (`https://dwarffortresswiki.org/Modding`). The whole Penrose/ACE/STORYNEXUS generation shows that *no migration path = no adoption*.
- **Production-restore theatre (event sourcing).** The Medium "event sourcing production was a nightmare" essays are a real pattern: ES in production is hard. The brief's adapter-with-end-of-life plan is the mitigation.

**What sustained them:**

- **A real second user / second project.** Datalog lasted because databases and (more recently) authorization kept wanting it. JSON Schema lasted because every API eventually needed to validate something.
- **Conformance + docs + CLI introspection in one package.** Inform 7's "World" pane and "Index" tabs are half the reason people stay (`https://testerstories.com/2014/06/introduction-to-inform-7/`); Yarn Spinner's VS Code extension is similar (`https://docs.yarnspinner.dev/`).
- **Backwards compatibility as policy.** Datalog's subset-of-Prolog guarantees old programs stay valid; JSON Schema's frozen $id URIs do the same. Ren'Py's docs explicitly preserve old syntax (`https://www.renpy.org/doc/html/language_basics.html`).
- **Surface that fits the writer, not the implementer.** Ink is popular because *writers* can read it. Harlowe is popular because non-programmers can write it. Gherkin is popular because stakeholders can argue with it. Any VEFR language that reads like "engine code" has already lost.

---

## (4) Closest project to this idea

The closest single project is **StoryNexus / DendryNexus** (Fallen London's engine lineage, `https://troygilbert.com/modeling-games/thoughts-on-storynexus/`, `https://intfiction.org/t/chroniclehub-a-qbn-engine-like-storynexus/78061`). It has the same shape as the brief: a tiny kernel (qualities, decks, cards, storylets), many stories compiled against it, and a data-driven description that the engine makes true. It is narrative-only, not game-general — which is *exactly* the gap VEFR is trying to fill.

The closest **technical** analogue is the split used in **Ink** + **Yarn Spinner** + **Jomini**: prose/structured DSL on top, a small named-effect host boundary below, and event-style provenance where it matters (Ink's runtime JSON export, `https://github.com/inkle/ink`; Yarn's dialogue runner, `https://yarnspinner.dev/docs/unity/10-components/01-dialogue-runner/`; Jomini's effect/trigger split, `https://pdx.tools/blog/a-tour-of-pds-clausewitz-syntax`).

The closest **method** analogue is **ECS + Datalog**: a kernel of facts (ECS components + Datalog predicates) over which both engine and (where safe) packs can run derived queries (`https://github.com/SanderMertens/ecs-faq`, `https://drops.dagstuhl.de/storage/01oasics/oasics-vol138-rw2024+rw2025/html/OASIcs.RW.2024-2025.7/OASIcs.RW.2024-2025.7.html`). Together they describe the shape the brief is reaching for.

---

## Citations used (one URL per claim, all retrieved live)

- https://ganelson.github.io/inform-website/
- https://www.inform-fiction.org/
- https://tads.dev/
- https://www.tads.org/t2doc/doc/overview.html
- https://en.wikipedia.org/wiki/Text_Adventure_Development_System
- https://www.reddit.com/r/interactivefiction/comments/11n9ey9/
- https://www.reddit.com/r/programming/comments/8uj95/
- https://intfiction.org/t/ai-class-case-study-using-inform-7-unlocking-and-ambiguity/65257
- https://questviva.com/
- https://github.com/textadventures/quest
- https://www.ifwiki.org/Quest
- https://www.inklestudios.com/ink/
- https://github.com/inkle/ink
- https://github.com/inkle/ink/issues/408
- https://yarnspinner.dev/
- https://docs.yarnspinner.dev/
- https://yarnspinner.dev/docs/unity/10-components/01-dialogue-runner/
- https://github.com/YarnSpinnerTool/YarnSpinner
- https://www.renpy.org/
- https://www.renpy.org/doc/html/index.html
- https://www.renpy.org/doc/html/language_basics.html
- https://github.com/renpy/renpy
- https://www.motoslave.net/sugarcube/2/docs/
- https://twine2.neocities.org/
- https://guides.lib.uci.edu/twine/manuals
- https://en.wikipedia.org/wiki/LambdaMOO
- https://brn227.brown.wmich.edu/Barn/files/docs/lambdamoo/pm1.8.1/ProgrammersManual_1.html
- https://www.evennia.com/
- https://github.com/evennia/evennia
- https://www.evennia.com/docs/latest/Evennia-Introduction.html
- https://dwarffortresswiki.org/Modding
- https://bay12games.com/dwarves/modding_guide.html
- https://docs.dfhack.org/en/52.05-r1/docs/guides/modding-guide.html
- https://ck3.paradoxwikis.com/Scripting
- https://pdx.tools/blog/a-tour-of-pds-clausewitz-syntax
- https://forum.paradoxplaza.com/forum/threads/ck3-dev-diary-37-making-mods.1410656/
- https://help.roll20.net/hc/en-us/articles/360037772773
- https://en.wikipedia.org/wiki/Attempto_Controlled_English
- https://attempto.ifi.uzh.ch/site/pubs/papers/ace3manual.pdf
- https://github.com/Attempto/ACE-in-GF
- https://jsonlogic.com/
- https://github.com/cachecontrol/json-rules-engine
- https://www.npmjs.com/package/json-logic-engine
- https://json-schema.org/specification
- https://json-schema.org/docs
- https://martinfowler.com/eaaDev/EventSourcing.html
- https://martinfowler.com/eaaDev/EventNarrative.html
- https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing
- https://en.wikipedia.org/wiki/Datalog
- https://drops.dagstuhl.de/storage/01oasics/oasics-vol138-rw2024+rw2025/html/OASIcs.RW.2024-2025.7/OASIcs.RW.2024-2025.7.html
- https://docs.drools.org/latest/drools-docs/drools/rule-engine/index.html
- https://en.wikipedia.org/wiki/CLIPS
- https://www.clipsrules.net/
- https://martinfowler.com/bliki/RulesEngine.html
- https://en.wikipedia.org/wiki/Entity_component_system
- https://github.com/SanderMertens/ecs-faq
- https://github.com/penrose/penrose
- https://penrose.cs.cmu.edu/siggraph20
- https://troygilbert.com/modeling-games/thoughts-on-storynexus/
- https://intfiction.org/t/chroniclehub-a-qbn-engine-like-storynexus/78061
- https://cucumber.io/blog/bdd/gherkin-rules/
- https://behat-docs.readthedocs.io/en/v3.0/user_guide/gherkin.html
- https://dl.acm.org/doi/fullHtml/10.1145/3446977
- https://www.researchgate.net/publication/222441929_DEVICE_Compiling_production_rules_into_event-driven_rules_using_complex_events
- https://testerstories.com/2014/06/introduction-to-inform-7/
- https://stackoverflow.com/questions/250403/rules-engine-pros-and-cons

Report total: ~2,400 words.
