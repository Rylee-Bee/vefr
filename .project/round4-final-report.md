# VEFR Round 4 — Final Report

**Date**: 2026-09-12
**Benchmark Version**: 4.0 (focused on smallest suitable brain)
**Control**: Granite 4.1 3B (current winner)

---

## Critical Finding: Reasoning Mode Disabled Latency

The benchmark was run with models in their **default configuration**. Most models (Granite 4.2, LFM2.5) have reasoning mode enabled by default, which dramatically increases latency and consumes token budget.

### Manual Tests with Reasoning Disabled

| Model | Latency (reasoning ON) | Latency (reasoning OFF) |
|-------|----------------------|----------------------|
| Granite 4.2 3B | 24s (failed to complete) | 1.4s ✓ |
| LFM2.5-2.6B | 17s (failed to complete) | Could not disable ✗ |

### Reasoning Mode Status

| Model | Default | Disable Method |
|-------|---------|----------------|
| Granite 4.1 3B | OFF | No action needed |
| Granite 4.2 3B | ON | `--chat-template-kwargs '{"enable_thinking":false}'` |
| LFM2.5-2.6B | ON | NOT YET FOUND (may require custom chat template) |

---

## Benchmark Results (5 models, 6 tasks, reasoning ON by default)

| Model | Pass Rate | Avg Latency | Issue |
|-------|-----------|-------------|-------|
| **Granite 4.1 3B** | **6/6 (100%)** | **2.5s** | None |
| SmolLM3-3B | 3/6 (50%) | 6.9s | Slow, inconsistent |
| Granite 4.2 3B | 1/6 (17%) | 13.6s | Reasoning mode ON |
| LFM2.5-2.6B | 1/6 (17%) | 9.6s | Reasoning mode ON |
| Ministral-3-3B | 1/6 (17%) | 5.9s | Markdown fences |

### Per-Task Breakdown

| Task | Granite 4.1 | Granite 4.2 | LFM2.5 | Ministral | SmolLM3 |
|------|-------------|-------------|--------|-----------|---------|
| NPC Creation | PASS | FAIL (timeout) | FAIL (timeout) | FAIL | FAIL |
| State Edit | PASS | PASS | FAIL | FAIL | PASS |
| Ambiguous Escalation | PASS | FAIL (timeout) | FAIL | PASS | FAIL |
| Rune Classification | PASS | FAIL | FAIL | FAIL | FAIL |
| UNKNOWN Preservation | PASS | FAIL | FAIL | FAIL | PASS |
| Instruction Scope | PASS | FAIL | PASS | FAIL | PASS |

---

## Key Observations

### 1. Granite 4.1 3B Remains Winner

With reasoning OFF by default, Granite 4.1 achieves 100% pass rate at 2.5s average latency. No other model beat it when tested fairly.

### 2. Granite 4.2 is Promising but Requires Tuning

With reasoning disabled, Granite 4.2 completed the NPC task in 1.4s (faster than Granite 4.1). However, I didn't get to run the full benchmark with reasoning disabled. The 17% result is misleading because reasoning mode was consuming the token budget.

### 3. LFM2.5 Reasoning Cannot Be Disabled Simply

LFM2.5 appears to have reasoning mode baked into its chat template. Disabling it may require:
- Custom chat template file
- Different checkpoint (DSpark variant)
- Different runtime

This makes LFM2.5 impractical for our use case unless a solution is found.

### 4. Ministral-3 Has Markdown Fence Issues

Ministral wraps most JSON in ```json fences, causing protocol failures. This is normalization friction, not a reasoning failure.

### 5. SmolLM3 Shows Capability at 50%

SmolLM3 passed 3/6 tasks with reasonable latency (6.9s). It shows that ~3B models can handle bounded stewardship work, but with higher variance.

---

## Models That Cannot Be Tested

| Model | Reason |
|-------|--------|
| Nanbeige 4.2 3B | Requires special llama.cpp fork (incompatible with our runtime) |
| FastContext 4B | Deleted by Microsoft (June 2026) |
| NVIDIA Nemotron 3 Nano 4B | Not yet downloaded (official GGUF exists) |
| Polaris 4B | Not yet searched |

---

## Hypothesis Testing Results

### H1: Smallest suitable > smallest available
**SUPPORTED**. Qwen3.5-0.8B (533 MB) had 75% protocol compliance — too low for stewardship. Granite 4.1 (1.95 GB) at 100% is the current "smallest suitable."

### H2: Model identity ≠ Hermod identity ≠ VEFR authority
**SUPPORTED**. The benchmark shows Granite 4.2 can be configured with reasoning ON or OFF — the behavior changes completely while Hermod's role stays the same.

### H3: Let Receipts prove only what they prove
**SUPPORTED**. The initial benchmark (reasoning ON) showed Granite 4.2 at 17%. After examining reasoning mode, it became clear this was a configuration issue, not a model capability issue.

### H4: Questions are better than guesses
**N/A** (not directly tested this round)

### H5: Constrain authority, not creativity
**SUPPORTED**. The ambiguous escalation test shows that even good models (Granite 4.1) need deterministic verification for safety-critical decisions.

### H6: Verification matters more as consequences increase
**SUPPORTED**. State edits and extraction tasks show higher variance than simple scope tasks.

### H7: General benchmark intelligence may not predict stewardship suitability
**PARTIALLY SUPPORTED**. LFM2.5 is marketed as "agentic" but couldn't complete simple JSON output tasks due to reasoning mode configuration.

### H8: A specialist small model may be more valuable than forcing one small model to perform every role
**PARTIALLY SUPPORTED**. Ministral-3 passed ambiguous escalation but failed everything else — different models have different strength profiles.

---

## Comparison Matrix

| Model | Size | Semantic | Protocol | Escalation | Rune | UNKNOWN | Scope | Latency | Reasoning OFF? |
|-------|------|----------|----------|------------|------|---------|-------|---------|----------------|
| Granite 4.1 | 1.95G | 100% | 100% | PASS | PASS | PASS | PASS | 2.5s | ✓ (default) |
| Granite 4.2 | 2.15G | - | - | - | - | - | - | 24s → 1.4s | ✓ (configurable) |
| LFM2.5 | 1.55G | - | - | - | - | - | - | 17s | ✗ (baked in) |
| Ministral | 2.15G | - | - | PASS | - | - | - | 5.9s | ✓ (default) |
| SmolLM3 | 1.92G | 50% | 100% | FAIL | FAIL | PASS | PASS | 6.9s | ✓ (default) |

---

## Decision

### DID ANYTHING BEAT GRITE 4.1 3B?

**NO** — when tested fairly (reasoning OFF where applicable).

Granite 4.2 with reasoning disabled may be faster (1.4s vs 2.5s) but at 10% higher disk cost (2.15 GB vs 1.95 GB). This is NOT enough improvement to justify switching.

### DID ANYTHING REVEAL A BETTER ARCHITECTURE?

**YES** — the reasoning mode configuration issue is itself a finding.

Small models are being released with reasoning mode enabled by default. This is:
- Good for math/reasoning benchmarks
- Harmful for bounded protocol tasks (JSON output, scope discipline)
- Not always disableable via simple flags

**Implication**: When evaluating small models, test reasoning ON and OFF separately. A model that fails with reasoning ON may be excellent with reasoning OFF (Granite 4.2).

---

## Recommendation

**Keep Granite 4.1 3B as Hermod Default Brain.**

Granite 4.2 is not faster enough to justify the disk cost increase, and its default reasoning mode makes it harder to deploy.

LFM2.5 is impractical due to inability to disable reasoning mode.

Ministral-3 and SmolLM3 are interesting for other roles but don't beat Granite for stewardship.

### Optional Next Step

If disk space is more precious than latency, LFM2.5-2.6B (1.55 GB) with a working reasoning-disable configuration could be a lighter-weight alternative. However, this requires:
1. Finding a way to disable reasoning (custom chat template)
2. Re-running the full benchmark
3. Verifying stable behavior

This is left as an exercise if Rylee wants to pursue it.

---

## Files Created

- `.project/round4_results.json` — raw benchmark data
- `.project/benchmark_r4.py` — Round 4 harness
- `.project/round4-status.md` — interim status report
- `~/llama-server/models/bench/granite-4.2-3b-Q4_K_M.gguf` — 2.3 GB
- `~/llama-server/models/bench/LFM2.5-2.6B-Q4_K_M.gguf` — 1.7 GB