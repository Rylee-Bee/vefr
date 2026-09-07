# Agent Policy — VEFR Decision Kernel

This is the mandatory entry point for AI agents working on VEFR.

## Mandatory preflight

Before planning, researching, modifying, reviewing, merging, or releasing:

1. Read the repository's canonical contract/index documentation.
2. Load every applicable contract.
3. Inspect the current engine, world format, runtime, tests, and existing seams before proposing new architecture.
4. Determine whether an existing world/NPC/journal/pack mechanism already owns the capability.
5. Decide how the result will be proven.

**Repository truth outranks inference. Unknown is a valid state. Make honesty cheaper than fabrication.**

## VEFR design rule

Prefer the dumbest useful implementation with the fewest moving parts.

Before introducing:

- an agent framework
- database
- service
- daemon
- state engine
- orchestration system
- new file format

prove that VEFR's existing small-file/world-pack architecture cannot express the capability cleanly.

Prefer:

- tiny reference files
- ordinary directories
- explicit schemas
- deterministic loading
- existing engine seams
- ordinary Git
- inspectable state
- simple APIs
- content that remains understandable outside the AI system

## Decision rule

Prefer systems where:

- truth is easier to retrieve than fabricate
- content is data rather than hidden behavior
- state is inspectable
- worlds are portable
- behavior degrades gracefully
- recovery is straightforward
- humans can edit important content
- AI enhances the world rather than becoming an undocumented dependency

## Contracts

Use the repository's canonical contract/index system.

Always consider applicability of:

- Accessibility
- Human Reliability
- security
- world/content architecture
- runtime/recovery
- asset provenance/licensing
- public repository boundaries

Do not duplicate canonical contracts here.

## Preserve existing seams

Search before inventing.

Prefer extending existing concepts such as:

- worlds
- acts
- maps
- contracts
- NPCs
- voices
- sprites/assets
- journals
- storyteller/reference material
- pack loading

over introducing parallel systems.

## AI behavior

Do not use an LLM where deterministic logic is sufficient.

Do not make an agent framework necessary merely because a feature involves characters, storytelling, or AI.

AI-generated behavior must not silently overwrite canonical world truth.

Persistent state should be inspectable.

If generated content becomes durable world state, its ownership and provenance should be understandable.

## Accessibility and human reliability

User-facing work must obey the Accessibility and Human Reliability contracts.

A game/world interface can be playful without becoming unreadable, inaccessible, unpredictable, or impossible to recover.

Unknown and degraded states must remain representable.

## Evidence

Do not call something working because:

- the server started
- an endpoint returned 200
- a model produced output
- an asset exists
- a handoff claims completion

Exercise the actual relevant behavior.

## Definition of done

When applicable:

`implement → validate world/content → test → accessibility check → docs → review → CI → merge → runtime verification`

Evaluate relevant contracts as:

- `PASS`
- `FAIL`
- `N/A`
- `UNKNOWN`

Never silently convert `UNKNOWN` into `PASS`.

## Final truth report

Substantial work ends with:

**CHANGED:** actual changes  
**VERIFIED:** evidence  
**CONTRACTS:** applicable contract status  
**UNKNOWN:** unresolved truth  
**DEFERRED:** intentional future work  
**NEXT:** legitimate next action or `nothing required`

## Core principle

> **Make honesty cheaper than fabrication.**

VEFR should make the simple, inspectable, truthful implementation easier to build than the clever opaque one.
