# UAT contracts

Each file here is a small contract for something a person does in a woven
player: a **journey** (the job in their own words) and **acceptance criteria**
as machine-checkable triples.

## Format

```md
# Journey: <name>

**Persona:** <who>
**Job:** As a <who>, I want to <job> so that <outcome>.

1. <starting state - where the run begins>
2. <a step a person would take, in their words>
3. <the outcome they need to reach>

# Acceptance: <what and where>

| triple |
| --- |
| <description> / <action> / <expected> |
```

The `expected` value must be one a machine can decide, and only from this
vocabulary:

```
visible | contains text | value equals | URL is | focus is on | axe has 0 critical | request returned N
```

No free-text verdicts - "works correctly", "looks right", "seems usable" are
opinions, not acceptance criteria. If a machine cannot decide it from the page,
split it until it can.

## Why these live in the repo

They are public, versioned with the player they describe, and readable by
anyone who clones the engine - so an outside user can see what "good" means
before changing anything. The estate's UAT harness (which drives a URL
read-only and emits findings, never a verdict) can run the same contracts.

## Current contracts

- `autoexplore.md` - walking to the unexplored ground, and the fog toggle.
- `light.md` - the torch and the one-shot reveal.
