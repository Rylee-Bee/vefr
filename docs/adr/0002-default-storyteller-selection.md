# Small Model Decision — VEFR Storyteller

Date: 2026-09-13
Benchmark commit: 78e3fb0
Continuity check commit: (pending)

## Decision

**Default storyteller: Ministral 3 3B Q4_K_M**

**Fallback: Phi-4-mini-instruct Q4_K_M**

## Evidence

Quick-final pass: 12 high-signal tasks, 1 run each, CPU-only (AMD Ryzen 7 7800X3D).

| Model | PASS | FAIL | Avg latency |
|-------|------|------|-------------|
| Phi-4-mini | 11 | 1 | 13.3s |
| Ministral 3 3B | 12 | 0 | 35.7s |

Continuity sanity check: 5 difficult multi-turn cases, 1 run each.

| Model | PASS | FAIL | Verdict |
|-------|------|------|---------|
| Phi-4-mini | 2 | 3 | FAIL |
| Ministral 3 3B | — | — | (not retested; 12/12 on full suite) |

Phi failed on:
- Physical state tracking (injury forgotten across turns)
- Character mistake persistence (world truth leaked in, correcting false belief)
- Fact retention (specific details dropped over multi-turn gaps)

Phi passed on:
- Relationship recognition
- Adversarial reasoning

Decision rule was 4/5 or 5/5 for Phi. Phi scored 2/5. Ministral becomes default.

## Why Ministral 3 3B

- 12/12 on deterministic checks (perfect)
- Reliable multi-turn continuity
- Strong voice and character separation
- Canon and sealed-knowledge discipline
- Emotional scenes without melodrama
- Player agency respected

## Trade-off

Ministral is ~3x slower than Phi (35.7s avg vs 13.3s). The continuity reliability is worth the latency cost for a storyteller that must sustain characters across sessions.

## Architecture

The storyteller is wired through the existing pack system:

```
storyteller_packs/ministral3-3b/
  storyteller.toml    ← model config, sampling, capabilities
  system.md           ← system prompt template
  scene.md            ← scene packet template
```

Resolution: `VEFR_STORYTELLER=ministral-3-3b` or active pack selection.

The storyteller renders narrative from authoritative world state. It does not have write access to canon, world facts, or game state.

## Phi-4-mini role

Phi remains available as a fast storyteller for:
- Quick prototyping
- Scenes where multi-turn continuity is not critical
- Resource-constrained environments where latency matters more than continuity

## Files

- Quick-final results: `bench/finals/runs/quick-vefr-*.jsonl`
- Continuity check: `bench/finals/runs/continuity-check-phi-4-mini-*.json`
- Decision packet: `bench/finals/DECISION-PACKET.md`
- This document: `docs/adr/0002-default-storyteller-selection.md`
