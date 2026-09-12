# VEFR Project Participants

This directory contains project-local participant profiles for Play-Nice routing.

## Status

All profiles are currently `PROVISIONAL` - evidence is accumulating.

## Available Workers

| Profile | Model | Size | Status | Semantic | Protocol |
|---------|-------|------|--------|----------|----------|
| qwen3.5-2b | Qwen3.5-2B Q4_K_M | 1.28 GB | **DEFAULT** | 75% | 100% |
| granite-4.1-3b | Granite 4.1 3B Q4_K_M | 1.95 GB | PROVISIONAL | 87.5% | 100% |
| qwen3.5-4b | Qwen3.5-4B Q4_K_M | 2.74 GB | PROVISIONAL | 87.5% | 87.5% |
| qwen3.5-0.8b | Qwen3.5-0.8B Q4_K_M | 533 MB | PROVISIONAL | 87.5% | 75% |
| llama-3.2-3b | Llama 3.2 3B Q4_K_M | 2.02 GB | PROVISIONAL | 75% | 75% |
| phi-4-mini | Phi-4-mini Q4_K_M | 2.49 GB | PROVISIONAL | 75% | 37.5% |

## Routing

```
TIER 0 — Fast Deterministic Worker
  qwen3.5-0.8b (533 MB, ~2.4s/task)
  Use: Exact string handling, simple JSON, bounded extraction
  Verify: Always (markdown fences on complex tasks)

TIER 1 — Default Worker ★ RECOMMENDED
  qwen3.5-2b (1.28 GB, ~6.5s/task)
  Use: General VEFR tasks, state edits, extraction, UNKNOWN preservation
  Verify: Recommended (100% protocol, 75% semantic)
  Note: Escalation judgment and classification may need verification

TIER 1b — Structured-Output Specialist
  granite-4.1-3b (1.95 GB, ~7.7s/task)
  Use: Enterprise-grade instruction following, bounded extraction
  Verify: Recommended (100% protocol, 87.5% semantic)

TIER 2 — Strong Reasoning Worker
  qwen3.5-4b (2.74 GB, ~12.0s/task)
  Use: Complex classification, nuanced reasoning, rune mapping
  Verify: Recommended (87.5% protocol, 87.5% semantic)

TIER 2b — Historical Control
  phi-4-mini (2.49 GB, ~6.8s/task)
  Use: Comparison baseline, creative generation
  Verify: Required (37.5% protocol, 75% semantic)

REFERENCE / ESCALATION
  qwen3.8-27b-iq4xs (15.6 GB)
  Use: Complex reasoning, architecture, debugging

COORDINATOR
  hermes (LongCat via Nous)
  Use: Orchestration, routing, verification
```

## Benchmark Results

- Round 1 (6 models, single-axis): `.project/benchmark-final-report.md`
- Round 2 (8 models, dual-axis): `.project/benchmark-r2-final-report.md`

## Retention

### Keep
- Qwen3.5-2B — Default Tier 1
- Granite-4.1-3B — Structured-output specialist
- Qwen3.5-4B — Reasoning specialist
- Qwen3.5-0.8B — Fast Tier 0
- Llama 3.2 3B — Control comparison
- Phi-4-mini — Historical control

### Not Retained
- SmolLM3-3B — Poor protocol, slow
- Gemma 3 4B — Worst protocol compliance
- Ministral-3-3B (Round 1) — Poor protocol, scope expansion
- Gemma 3 1B (Round 1) — Poor protocol, scope expansion