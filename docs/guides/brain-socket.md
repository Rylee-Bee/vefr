# Bring your own brain - VEFR architecture notes

This is the architectural rule this repo should preserve as model
benchmarking and builder work continue:

> **Bring your own brain. VEFR provides the world.**

Short form:

- **VEFR owns reality.**
- **Brains interpret reality; they do not define it.**
- **AI proposes. VEFR governs.**
- **The world remembers what actually happened.**

This note is design intent, not a demand for a large refactor.
The current code already has useful seams; the goal is to keep them
open and avoid closing them by accident.

## The governing rule

Authoritative state belongs to VEFR and its world-pack contract.
That includes things like:

- locations and geometry
- collision and reachability
- entities and NPC placement
- inventory and kept items
- time / phases / active act
- journaled events
- persistent flags and consequences
- world history and memories derived from real events

Models may:

- read relevant context
- propose dialogue
- propose actions
- propose edits

Models may not directly establish truth.

The runtime shape we want to preserve is:

```text
WORLD
  ↓
relevant context
  ↓
BRAIN
  ↓
proposed action
  ↓
VEFR validation
  ↓
commit/reject
  ↓
WORLD
```

The builder shape should mirror it:

```text
CREATOR
  ↓
BUILDER AGENT
  ↓
proposed change set
  ↓
VEFR validation / preview
  ↓
creator approval when appropriate
  ↓
PROJECT / WORLD
```

In both cases:

> **AI proposes. VEFR governs.**

## Provider and brain are different concepts

VEFR should keep these separate.

A **provider** answers:

> Where/how does inference come from?

Examples:

- local inference
- llama.cpp
- Ollama
- OpenRouter
- a hosted partner service
- a custom OpenAI-compatible endpoint
- some deeply questionable machine in somebody's garage

A **brain** answers:

> What kind of cognition should operate here?

A future brain configuration may describe:

- model choice
- role
- prompting / personality
- temperature
- context policy
- memory policy
- tool capability policy
- routing / fallback behavior

Credentials belong to provider or user configuration.
Brain packs must not contain secrets.

VEFR should normalize the transport contract, not flatten cognition.
A strange model is allowed to be strange as long as it obeys the
world contract.

## Hot-swappable cognition

No single provider or model should become the engine's permanent
truth source.

A player should be able to run:

- locally on a strong PC
- through a hosted service on weaker hardware
- through self-hosted LAN infrastructure
- through a future provider that does not exist yet

All of them should operate against the same VEFR world contract.
More intelligence does not grant more authority.

## Capability negotiation, eventually

Do not assume every provider can do everything.
Document the seam now so we do not paint ourselves into a corner.
Useful future capability labels may include:

- structured output
- tool calls
- streaming
- vision
- context window size

Adapters may bridge missing capabilities when practical.
For example:

```text
native tool calls
```

versus:

```text
constrained JSON action proposal
```

Both can still feed VEFR's validation layer.

## Brain packs and the Brain Garage

The codebase should preserve room for distributable cognition
configurations without forcing a marketplace or plugin framework now.

Examples a future VEFR could support as data/config:

- Cozy Brain
- Dramatic Brain
- Tiny Local Brain
- Chaotic Brain
- Storyteller Brain

A pack may eventually route roles differently:

```text
ambient NPCs → small/fast model
characters   → storytelling model
planner      → reasoning model
```

That desired behavior should remain portable across local, hosted,
and custom infrastructure.

The future "Brain Garage" UX idea fits this architecture:

- help the user connect a provider
- inspect capability support
- explain tradeoffs conversationally
- audition brains inside VEFR scenarios

But that remains a future UX layer, not a requirement for this pass.

## Current local-model direction

The current project direction is not "VEFR requires one specific host"
or "VEFR requires a GPU host."

The important shift is toward a small local model that can run on the
player's own machine, including CPU-only setups, so more people can
actually play.

The earlier benchmarking work stays useful as research:

- it taught us about latency and structured-output reliability
- it exercised the provider seam under a stronger local backend
- it helped prove that model horsepower does not change authority

But that path is now a lab path, not the default promise.

The question is increasingly:

> What kinds of brains fit through the VEFR socket while keeping the
> world authoritative?

not:

> Which GPU host is the one true way to run VEFR?

## Persistent memory is a first-class VEFR job

A defining VEFR promise is that the world remembers facts that really
happened.

Example factual memory:

```text
Tuesday, 11:43 PM
Lane behind the market hall

Player helped Ana after her car broke down.
Present:
- Player
- Ana
- Ivo
```

Later, whichever brain is active may receive a compact factual memory
like:

```text
Ana recognizes player.
Relationship: mildly positive.
Reason: player helped during car trouble.
They have not met since.
```

The brain decides how Ana expresses that memory.
VEFR keeps the fact stable.

> **VEFR stores what happened. Brains decide what characters make of it.**

## Genre and mechanics must stay swappable

Different kinds of games should be normal uses of the engine, not edge
cases.

Examples we want to stay architecturally ordinary:

- burrito journalism
- a food-truck action game
- an identity-focused personal story
- a modern story refracted through mythic language

That does not mean every mechanic exists today.
It means new seams should not quietly hardwire one genre's assumptions
into the engine unless the project explicitly chooses to.

## Current seams in this repo

The existing code already contains several of the right joints.

### 1. VEFR-owned world contract

`src/vefr/world.py`
: The pack loader is the seam between engine and story. It loads the
  pack, canonicalizes acts, applies the surface grammar, and resolves
  voices by convention.

`src/vefr/maplab.py`
: Validates geometry and reachability offline and live. This is a real
  example of VEFR validation sitting between authored data and accepted
  truth.

`src/vefr/main.py` + `/api/world`
: The renderer reads a world payload built by VEFR, not raw model text.

### 2. Provider/model abstraction seam

`src/vefr/generator.py::_completion()`
: The current single transport seam. Callers build inference payloads;
  `_completion()` decides how to talk to the active provider.

Current provider-level env/config:

- `VEFR_LLAMACPP_URL`
- `OLLAMA_URL`
- `VEFR_MODEL`
- `VEFR_KEEP_ALIVE`

This is a useful start because most generation modules already depend
on the payload contract, not the HTTP wire shape.

### 3. Builder-side proposal surfaces

`src/vefr/chat.py`
: `norns chat` interviews the author, drafts content, and only writes a
  pack through deterministic flow plus `maplab.validate()`.

`src/vefr/enhance.py`
: The enhance endpoints are scoped proposal generators returning strict
  JSON structures for the authoring UI.

`src/vefr/main.py` `/api/builder/chat`
: Builder chat is now intentionally **stateless and proposal-only**.
  It returns prose suggestions but does not silently write pack files.

### 4. Persistent world memory surfaces

`src/vefr/journal.py`
: The record of what actually happened in play.

`src/vefr/forge.py`
: Persistent kept items, per session.

`src/vefr/sessions.py`
: Session ids, per-session file derivation, and undo scaffolding.

`src/vefr/export.py`
: Deterministic retelling of canon plus factual play history.

`src/vefr/trace.py` and `src/vefr/weave.py`
: Engine-observation memory for debugging and loader truth.

## Current limitations to preserve consciously

These are not emergencies, but they are the main places where future
work should stay deliberate.

### Provider and brain are not separate objects yet

Today, provider choice and model choice are process-global values in
`generator.py`. That is enough for current work, but it means:

- one process mostly uses one model at a time
- role-based routing is not first-class yet
- provider capabilities are implicit, not negotiated

That is acceptable for now.
It should not become an excuse to hardwire one provider as VEFR's
identity.

### Most cognition entry points reach the same module directly

`chat.py`, `forge.py`, `enhance.py`, and `lore.py` all call
`generator._completion()` and usually read `generator.MODEL` directly.
That is good in one way - the transport seam is centralized.
It also means a future provider/brain split will probably want a thin
higher-level layer above `_completion()`, not a rewrite of every caller.

### Builder change validation is strong for packs, lighter for prose help

`maplab.validate()` is already the clearest example of a validation
layer between proposal and acceptance.

Future builder-agent work will likely want the same shape for:

- pack edits beyond geometry
- structured change previews
- role/provider configuration changes
- memory/prompt policy changes

The important rule is that a builder agent should propose a change set,
not become an unreviewed file-writer.

## Non-goals for this architecture pass

This document does not require the repo to immediately implement:

- Denizen-specific wiring
- OpenRouter integration
- Kilo integration
- every local backend
- a capability framework
- a plugin marketplace
- a full Brain Garage
- a brain-pack installer
- a rewrite of persistence
- direct AI authority over world state

The goal is simply to keep the seams open and the authority model
clear.

## Guiding test

When choosing a new abstraction, ask:

> **Does this let creators change more while keeping VEFR authoritative over reality?**

If yes, it probably fits.

And keep the central promise visible:

> **Bring your own brain. VEFR provides the world.**

