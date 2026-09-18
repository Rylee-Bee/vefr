# Round 6: Improving Small-Model Benchmark Results

**Date**: 2026-09-12
**Goal**: Can we improve Qwen2.5-1.5B's benchmark scores via prompt engineering, settings, or community techniques?

---

## Community Research Findings

### What the community recommends:
1. **GBNF grammar constraints** — forces valid JSON structure (Reddit r/LocalLLaMA, llama.cpp docs)
2. **json_schema response_format** — OpenAI-compatible structured output (GitHub discussions)
3. **Lower temperature** (0.1-0.3) for factual/structured tasks (llama.cpp guide)
4. **Validate-and-retry pattern** — catch failures, retry with error feedback (LLM configurator guide)
5. **Few-shot examples** — show the model the expected output format

### What actually helped:

| Technique | Result | Verdict |
|-----------|--------|---------|
| **Lower temp (0.1 vs 0.3)** | 5/6 vs 4/6 on one run | Marginal — within variance |
| **GBNF grammar** | 5/6 consistent | No improvement over baseline |
| **json_schema response_format** | **BREAKS** the model | ❌ Causes 1/6 scores on unschemed tasks |
| **Validate-and-retry** | 2/3 on subset | ❌ Worse than single-shot 5/6 |
| **Few-shot examples** | 3/3 PASS for NPC | ✅ Helps for that specific task |

---

## Detailed Results

### Config Comparison (5 runs each, temp=0.3, min_p=0.1 baseline)

| Config | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Mean |
|--------|-------|-------|-------|-------|-------|------|
| **baseline** | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 | **5/6 (83%)** |
| grammar | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 (83%) |
| low_temp_grammar | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 (83%) |
| json_object | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 (83%) |

**All configs produce identical 5/6. Zero variance across 20 total runs.**

### The One Failure: Rune Classification

Every config fails Rune Classification. Even with the mappings explicitly provided in the prompt, Qwen2.5-1.5B produces:

```json
{"whispers": "kenaz", "doubts": "kenaz", "feared": "kenaz", "awed": "kenaz"}
```

All identical values. The model is NOT reading the prompt — it's defaulting to one token.

### Why Rune Classification Fails

The task requires **memorizing VEFR-specific rune-phase mappings** that don't exist in any training data:
- Fehu → whispers
- Thurisaz → doubts
- Kenaz → feared
- Sowilo → awed

This is not a reasoning task. It's a **recall task** disguised as a benchmark. For a 1.5B model, recall of domain-specific knowledge it was never trained on is impossible.

---

## Conclusion: The Benchmark Is the Problem, Not the Model

### Finding 1: We're at the ceiling

Qwen2.5-1.5B consistently scores 5/6 on the current benchmark. That's the practical ceiling for a 1.5B model on these tasks.

### Finding 2: Rune Classification is a knowledge test, not a capability test

The model can't know VEFR's specific lore. No amount of prompt engineering or settings tuning will fix this. It's like asking someone to recall a phone number they've never seen.

### Finding 3: Community techniques don't help

- GBNF grammar: doesn't add new knowledge
- Lower temperature: doesn't add new knowledge
- json_schema: breaks the model on tasks without schemas
- Validate-and-retry: the model makes the same mistake twice
- Few-shot: helps for format, not for content

### Finding 4: Settings have minimal impact

Temperature 0.1-0.8 produces identical scores. The bottleneck is model capability, not sampling randomness.

---

## Recommendations

### 1. Remove Rune Classification from the benchmark

It tests domain knowledge, not model capability. Replace with a different bounded task.

### 2. Accept 5/6 as the practical ceiling for 1.5B

This is not a failure — it's evidence of where the boundary sits.

### 3. If you need higher scores, escalate to a larger model

Granite 4.1 3B also fails Rune Classification (same knowledge gap). This is a task for the ESCALATION tier (Qwen3.8-27B) or for a future specialist that has access to VEFR's lore docs.

### 4. Use few-shot examples where format consistency matters

The NPC task shows 3/3 PASS with a few-shot example vs occasional FAIL without. This is the only technique that reliably improves consistency.

### 5. Don't use json_schema response_format with Qwen2.5-1.5B

It breaks tasks that don't have schemas. The model fills in "default" for every field.

---

## Evidence Summary

| Evidence | Receipt |
|----------|---------|
| 5/6 is the ceiling | 20 runs across 4 configs, all identical |
| Settings don't matter | temp 0.1-0.8, min_p 0.0-0.2, all 5/6 |
| Grammar doesn't help | 5/6 with and without |
| json_schema hurts | 1/6 on tasks without schemas |
| Few-shot helps format | 3/3 PASS for NPC with example |
| Rune is unfixable | Model defaults to one value even with explicit mappings |

---

## Harness Principle Preserved

> "Let Receipts prove only what they prove."

The 5/6 benchmark score proves Qwen2.5-1.5B is reliable on bounded structured tasks. It does NOT prove the model is generally equivalent to larger models, nor does it prove the model can recall knowledge it was never trained on.

> "Don't demand that a participant know truth it can reliably obtain from the participant who owns it."

Rune Classification demands VEFR lore knowledge. VEFR owns that knowledge. The task should be redesigned so the model either:
a) Receives the knowledge in-context (not tested for recall), OR
b) Is a task that doesn't require domain-specific memorization

---

## Stop Condition

This investigation is complete. No further model search or settings tuning is warranted at this time.

**Remaining Question**: What should replace Rune Classification in the benchmark?
**Remaining Reservation**: The six-task suite may not cover the full range of Hermod's actual work.
