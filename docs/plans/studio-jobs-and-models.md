# Studio jobs and models: a universal intelligence plan

Status: **plan only**  
Date: 2026-10-04

## Purpose

Make VEFR feel simple to a person who wants to tell stories while letting the
Studio use whichever deterministic code, local model, or online model can do a
job well.

The durable product boundary is:

> **The Studio may use intelligence to help make a game. The bundled game is
> complete without that intelligence.**

This plan turns that boundary into one small architecture. It does not add a
new game runtime, plugin system, authoring language, agent framework, or pack
format.

## Existing truth this plan preserves

This plan is an extension of current VEFR, not a restart.

- ADR 0003 already says models work in the Studio and woven games are finished
  artifacts.
- `weave_html` already produces one shareable HTML document without model
  calls.
- The player already carries deterministic gameplay, rules, saves, UI, art,
  audio and other features inside that document.
- Studio residents already present development roles in friendly form.
- The repository already prefers rules before models and the smallest capable
  mechanism for a job.
- The current bundled deployment and model-role documents already prove that
  VEFR can run local models, download pinned artifacts, verify them, and connect
  to external endpoints.
- The gameplay-feature work keeps reusable gameplay over one small core rather
  than inventing a plugin runtime.

The plan should remove parallel concepts from those pieces, not create another
system beside them.

## Product invariants

These are the boundaries future implementation must keep.

### 1. The bundle is the game

A released game is one bundled HTML file.

It must be able to start, progress, save, load and reach its authored ending
without:

- VEFR running;
- a model;
- a GPU;
- an account;
- an API key;
- a network connection.

A game may offer optional enrichment, but enrichment may never be required for
the authored play path.

### 2. Models belong to the Studio, not the game

Game content must not depend on a named model, provider, quantization, context
size, GPU setting or inference runtime.

A game describes game truth. The Studio decides how to help create that truth.

Existing compatibility surfaces such as `player.model = "optional"` are not
expanded by this plan. Any later change to that public contract needs its own
evidence and decision.

### 3. Deterministic truth wins

Use, in order:

1. deterministic code or existing game data;
2. retrieval of known information;
3. a small/cheap model that has proved capable;
4. a stronger local model;
5. an online model, when the maker permits it;
6. the person, when judgment or approval is required.

A model proposes. VEFR validates and applies.

Models must not silently become the authority for saves, rules, inventory,
combat, quests, maps, authored facts or other canonical state.

### 4. Local and online are one choice surface

A Job asks for the kind of help it needs.

It does not know whether the answer comes from:

- deterministic code;
- a locally loaded model;
- an existing local model server;
- an online provider;
- another compatible gateway.

The maker chooses privacy/cost policy. The Job stays the same.

### 5. Easy is the default; detail is opt-in

The normal Studio should not require a maker to understand:

- prompts;
- model families;
- quantization;
- context windows;
- GPU layers;
- provider APIs;
- tool schemas;
- routing;
- MCP;
- agent terminology.

The existing **Show me how things work** path may expose the real machinery for
people who want to learn or tune it.

## Small public vocabulary

Keep the normal maker-facing vocabulary small.

### Game side

- **Game** — the thing being made.
- **Act** — a chapter of the game.
- **Gameplay feature** — a reusable way to play.

### Studio side

- **Room** — a place in the Studio.
- **Resident** — a Studio character who helps.
- **Job** — one repeatable thing the Studio knows how to help do.

Technical views may additionally show:

- **Tool** — an operation VEFR can perform.
- **Model** — a program used when a Job needs generated or interpreted output.
- **Connection** — where a model is reached, local or online.

Do not make `agent`, `worker`, `router`, `provider`, `skill`,
`capability`, `role` or protocol names required learner vocabulary.

Those may remain useful implementation words.

## Core architecture

```text
PERSON
  |
  v
RESIDENT
  |
  v
JOB
  |
  +-----------> VEFR TOOLS
  |
  +-----------> THINKING, when needed
                    |
                    v
               MODEL BROKER
                /       \
             LOCAL      ONLINE
```

The game path stays separate:

```text
GAME
  |
  +-- acts
  +-- gameplay features
  +-- rules/content/assets
  |
  v
BUNDLE
  |
  v
one complete game.html
```

The Studio may be complicated internally. The bundle must not inherit that
complexity.

## Job: the one new abstraction

A Job is the smallest reusable description of Studio work.

A Job answers four questions:

1. What result are we trying to produce?
2. Which VEFR tools may be used?
3. What kind of model help, if any, is useful?
4. What makes the result valid?

A Job is not an agent, process, service, resident or model.

Example, conceptually:

```yaml
job: make-map
result: valid map proposal
tools:
  - read-game
  - read-map
  - check-map
  - playtest
needs:
  - text
  - structured-output
```

The representation is deliberately **not decided here**. Existing Python/data
structures should be preferred until two independent consumers prove a new
format is useful.

### Residents do not own Jobs

Residents are the Studio presentation for Jobs.

The same `make-map` Job may be invoked by:

- the Cartographer;
- another resident;
- a Studio button;
- the CLI;
- an external automation;
- a future interoperability adapter;
- tests.

This keeps the friendly UI separate from the callable architecture.

### Jobs compose only when evidence earns it

Do not create a generic workflow graph or orchestration language now.

If a larger task requires several Jobs, ordinary application code may call them
in sequence. Extract reusable orchestration only after multiple real Studio
flows repeat the same sequence and invariants.

## VEFR tools stay authoritative

Tools are VEFR operations with narrow inputs and checked effects.

Prefer existing operations and seams before inventing new ones:

- read/check game data;
- create or edit a draft;
- validate a map or record;
- preview;
- playtest;
- keep an approved edit;
- bundle a game.

The model is allowed to call or request tools only through the Job's allowed
surface.

A tool that changes durable truth must preserve the repository's existing
preview/check/approval/undo rules.

## The model broker

The model broker should be deliberately boring.

A Job declares needs. The broker chooses among available candidates that have
evidence for those needs.

It should not use another model merely to decide which model to call when a
deterministic decision is available.

Conceptual selection:

```text
eligible for the Job?
        |
        v
allowed by maker policy?
        |
        v
meets quality floor?
        |
        v
prefer lower cost / lower latency / local
        |
        v
chosen candidate
```

The exact scoring policy is implementation detail. It should stay inspectable
and deterministic.

## Evidence, not model names

An API shape is not proof of behavior.

Two endpoints that both resemble an OpenAI chat API may differ in:

- tool calling;
- structured output;
- multimodal input;
- reasoning controls;
- context behavior;
- streaming;
- state carried between turns.

Therefore the unit VEFR trusts is not only a model name.

It is the tested combination of:

```text
model + runtime/connection + settings
```

The Studio should consume a small set of evidence-backed model records.

A record may include:

- source/revision/file/hash/license for local artifacts;
- connection type for online endpoints;
- measured memory and disk needs;
- measured latency/throughput;
- supported input/output kinds;
- structured-output reliability;
- tool-use reliability;
- VEFR Job scores;
- required model-specific settings;
- date/version of the evidence.

Do not expose this whole record in the simple UI.

## A small model catalog

VEFR should not become a directory of every model that exists.

Maintain a small tested catalog with enough choices to cover useful hardware
tiers and needs.

For example, internally:

- lightweight text;
- stronger text/reasoning;
- vision;
- embeddings;
- image generation;
- speech, if/when the Studio has proven Jobs for it.

The names above are implementation categories, not new maker vocabulary.

A model only enters the recommended catalog when:

1. its license/provenance is acceptable;
2. the exact artifact/endpoint and settings are known;
3. the relevant VEFR checks pass;
4. resource use is measured;
5. a fallback exists when it is unavailable.

Old entries may remain usable without remaining recommended.

## Local model management

The VEFR container should contain the ability to manage local models, not the
large model files themselves.

Conceptual layout:

```text
VEFR container
  Studio
  Jobs
  model broker
  model catalog
  download/verify logic
  local inference runtime

persistent storage
  model cache
  user configuration
```

Requirements:

- model files survive VEFR upgrades;
- exact recommended artifacts can be revision/hash pinned;
- unchanged files are reused rather than downloaded again;
- downloads require explicit user approval;
- failed or missing models degrade to another allowed path rather than crash
  the Studio;
- a real functional smoke test proves a newly selected model works through the
  VEFR path.

### Prefer one local runtime surface

The current bundled script starts several fixed model servers and ports. Do not
grow that pattern.

Prefer a local runtime that can discover/load multiple models and apply
per-model presets so VEFR owns one connection rather than a fleet of ports.

The exact runtime is replaceable. Current `llama.cpp` features make it a
strong candidate, but this plan does not make its private endpoints part of the
VEFR contract.

VEFR tools must remain VEFR tools.

## Online connections

Online models use the same Job and broker path as local models.

The basic maker policy should be understandable without provider vocabulary:

```text
How should VEFR get model help?

- This computer first
- Online first
- This computer only
```

Default direction: local first, and ask before sending game material to a new
online connection.

Advanced settings may expose named connections and per-Job overrides.

### Keep the provider layer replaceable

Do not build a large gateway product inside VEFR.

Start with the smallest adapter surface that covers real connected providers.
If a compatibility SDK removes more VEFR code than it adds operational
complexity, it may be used. If an operator already runs a compatible gateway,
VEFR should be able to connect to it rather than duplicate it.

Connection-specific quirks belong in adapters/catalog evidence, not in Jobs.

## First-run experience

The desired experience is recommendation, not configuration.

Example:

```text
VEFR checked this computer.

Recommended local setup
  Everyday help     ready after download
  Harder work       ready after download
  Picture reading   ready after download

Download: about 6 GB
Models load only when needed.

[ Set it up ]
[ Use online models instead ]
[ Stay without models ]
```

A weaker machine may instead be offered one lightweight local model plus an
optional online connection.

A strong machine may be offered a larger local setup.

No hardware class should be described as a failure. Making and playing games
must still work when no model is installed.

## Day-to-day Studio experience

The person should be able to say what they want rather than select machinery.

Example:

> Add a shy lighthouse keeper who knows why the birds stopped coming.

The Studio may internally:

1. inspect the current game;
2. use the appropriate resident/Job;
3. select deterministic tools and an eligible model;
4. create a checked proposal;
5. preview it;
6. ask the person to keep or revise it;
7. write only approved truth.

The maker does not need to learn which model, template or provider produced the
proposal.

The advanced view may show all of it.

## External interoperability

Do not use an interoperability protocol as VEFR's internal architecture.

VEFR's native Job/Tool interfaces should stay ordinary application interfaces.

At the boundary, adapters may expose VEFR Tools/Jobs or consume external
capabilities through standards such as MCP when a real integration needs it.

Rules:

- external descriptions are untrusted input;
- external tools never bypass VEFR validation/approval;
- protocol-specific concepts do not leak into game content;
- no external protocol is required to use VEFR.

If future standard workflow/skill formats map cleanly to Jobs, build an adapter
after a real second consumer proves the need.

## Migration from current VEFR

This plan should land incrementally.

### Phase 0 — record the boundary

Docs only.

- record this plan;
- keep ADR 0003 authoritative;
- do not alter pack/player/runtime behavior;
- do not interrupt active gameplay, interface, art or shape campaigns.

### Phase 1 — inventory existing model seams

Before building anything, map and deduplicate:

- `generator._completion` and other completion callers;
- Spark profiles/install/status/smoke logic;
- storyteller configuration/packs;
- current Model settings UI;
- `brain-roles.md`;
- bundled-brain deployment scripts;
- model environment variables;
- existing benchmarks and task banks.

Deliverable: one table of what is canonical, reusable, legacy or removable.

No new abstraction until that inventory names duplicated facts.

### Phase 2 — prove one Job

Choose one existing Studio operation that already has:

- a deterministic/validated result shape;
- an existing model-assisted path;
- a real UI or CLI consumer.

Express it through the smallest Job interface possible without changing its
public behavior.

Exit proof:

- current behavior remains;
- local and external model paths can satisfy the same Job;
- invalid model output still fails closed;
- no game/player contract changes.

### Phase 3 — extract the broker only after two Jobs need it

When two independent Jobs repeat model selection/fallback logic, extract the
small deterministic broker.

It should initially know only:

- available connections;
- evidence-backed needs;
- maker local/online policy;
- fallback order.

No generic agent scheduler.

### Phase 4 — unify local model management

Replace expansion of the fixed multi-server deployment with one managed local
model surface.

Reuse current pinned-artifact, hash verification, profile and smoke-test work.

Models live in persistent storage rather than the image.

### Phase 5 — first-run recommendation

Add hardware inspection and a recommended setup only after measured catalog
entries exist for the hardware classes VEFR actually supports.

Recommendation must state:

- download size;
- expected memory use;
- whether work stays local;
- what will be unavailable if skipped.

One button should perform download, verification, configuration and smoke test.

### Phase 6 — optional interoperability

Only after native Jobs/Tools are stable, expose or consume them through an
external protocol where a real consumer benefits.

## What this plan explicitly does not authorize

- a VEFR agent framework;
- an internal MCP bus;
- a plugin loader;
- a package manager;
- a new pack DSL;
- a workflow-graph language;
- a model per resident;
- a model per game;
- a model chosen by another model when deterministic selection works;
- a required cloud account;
- a required local model;
- shipping multi-gigabyte model files inside the VEFR image;
- a large public model marketplace/catalog;
- inference becoming authoritative game logic;
- provider/runtime names in authored game truth;
- changes to the one-file bundle contract.

## Acceptance criteria for the architecture

The plan has succeeded when all of these are true.

### For a new maker

- They can start making a game without understanding models.
- VEFR can recommend a local setup in plain language.
- They can connect an online model without changing their game.
- They can switch between local and online help without rewriting Jobs.
- They can opt out of models and still make/play games.

### For a finished game

- The bundled HTML is still one file.
- It runs without VEFR, a model, GPU, account or network.
- Model absence never blocks the authored completion path.
- Deterministic game state remains authoritative.

### For an advanced maker/operator

- They can see which Job, tools, model and connection were used.
- They can replace model choices without changing game content.
- They can supply compatible local or online connections.
- Model-specific quirks live in evidence/settings rather than Job logic.

### For maintainers

- One model-selection path serves Studio Jobs.
- One local model-management surface replaces expansion of fixed server ports.
- New model support usually means evidence + settings, not feature code.
- New provider support usually means an adapter, not changes throughout VEFR.
- A model/runtime swap has a real functional smoke test.
- The public game format remains independent of inference architecture.

## Research direction

The plan deliberately follows established external patterns without making any
of them architectural dependencies:

- MCP demonstrates small discovery/call contracts for tools, resources and
  prompts. Its 2026-07-28 protocol also moved to a stateless core, reinforcing
  that VEFR should use MCP at interoperability boundaries rather than copy a
  session framework internally.
- Current `llama.cpp` server supports router mode, dynamic model
  load/unload, a maximum resident-model count and per-model presets. That is
  enough evidence to stop expanding VEFR's one-process/port-per-model pattern.
  Its own server documentation says the built-in `/tools` endpoint is for
  the Web UI and must not be treated as a downstream contract, which supports
  keeping VEFR Tools independent of the inference runtime.
- Hugging Face Hub supports revision-pinned downloads, including full commit
  hashes, and a shared local cache. VEFR can therefore pin recommended
  artifacts without baking large model files into the container image or
  redownloading unchanged files on each upgrade.
- Multi-provider compatibility layers demonstrate that one call surface can
  span many providers, but also expose real feature differences. For example,
  current LiteLLM provider documentation shows endpoints that omit tool calling
  entirely and models that require provider-specific reasoning state across
  turns. API compatibility is therefore not capability evidence.

References checked 2026-10-04:

- MCP 2026-07-28 release:
  https://blog.modelcontextprotocol.io/posts/2026-07-28/
- MCP primitives overview:
  https://modelcontextprotocol.io/specification/draft/server/index
- llama.cpp server/router/presets:
  https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- Hugging Face Hub downloads/revisions/cache:
  https://huggingface.co/docs/huggingface_hub/en/guides/download
- LiteLLM provider feature variation examples:
  https://docs.litellm.ai/docs/providers/nadir
  https://docs.litellm.ai/blog/mimo_v2_6

Adopt the pattern, not the dependency.

## Short form

For product language:

> **Residents know Jobs. Jobs use Tools. Models help when needed.**

For engineering:

> **A Job declares a checked result, allowed tools and model needs; a
> deterministic broker chooses an evidence-backed local or online candidate.**

For the game boundary:

> **The Studio can be intelligent. The game it publishes must stand on its
> own.**
