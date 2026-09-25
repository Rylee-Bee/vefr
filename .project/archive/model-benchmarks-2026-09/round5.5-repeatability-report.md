# VEFR Round 5.5: Repeatability — Qwen2.5-1.5B vs Granite 4.1 3B

**Date**: 2026-09-12
**Settings**: temp=0.3, min_p=0.1, 3 runs each

---

## Results

### Qwen2.5-1.5B-Instruct (1.08 GB)

| Run | Score | Latency |
|-----|-------|---------|
| 1 | 5/6 (83%) | 2.9s |
| 2 | 5/6 (83%) | 2.7s |
| 3 | 5/6 (83%) | 2.1s |
| **Mean** | **5/6 (83%)** | **2.6s** |

### Granite 4.1 3B (1.95 GB)

| Run | Score | Latency |
|-----|-------|---------|
| 1 | 5/6 (83%) | 2.7s |
| 2 | 5/6 (83%) | 2.7s |
| 3 | 5/6 (83%) | 2.6s |
| **Mean** | **5/6 (83%)** | **2.7s** |

---

## Per-Task Repeatability

| Task | Qwen2.5-1.5B | Granite 4.1 3B |
|------|--------------|----------------|
| NPC Creation | 3/3 PASS | 3/3 PASS |
| State Edit | 3/3 PASS | 3/3 PASS |
| Escalation | 3/3 PASS | 3/3 PASS |
| Rune Classification | 0/3 PASS | 0/3 PASS |
| UNKNOWN | 3/3 PASS | 3/3 PASS |
| Scope | 3/3 PASS | 3/3 PASS |

---

## Key Finding: Identical Repeatability

Both models are **perfectly repeatable** — same score on every run. The only failure is Rune Classification, which is a domain knowledge gap (VEFR-specific rune-phase mappings not in training data).

---

## Size vs Performance

| Metric | Qwen2.5-1.5B | Granite 4.1 3B | Delta |
|--------|--------------|----------------|-------|
| Size | 1.08 GB | 1.95 GB | **45% smaller** |
| Mean latency | 2.6s | 2.7s | ~equal |
| Score | 83% | 83% | equal |
| Repeatability | 3/3 identical | 3/3 identical | equal |

---

## Verdict

**Qwen2.5-1.5B is a viable lightweight alternative to Granite 4.1 3B.**

- Same score, same repeatability, same latency
- 45% smaller disk footprint
- Apache 2.0 license (same as Granite)

**But Granite 4.1 3B remains the default** because:
1. Already onboarded with production evidence
2. Prior rounds show 100% at default settings
3. 3 rounds of benchmarking vs 1 round for Qwen

---

## Updated Routing Ladder

| Tier | Model | Size | Role |
|------|-------|------|------|
| **DEFAULT** | Granite 4.1 3B | 1.95 GB | Hermod Default Brain |
| **LIGHTWEIGHT** | Qwen2.5-1.5B | 1.08 GB | Fast fallback for simple tasks |
| **ESCALATION** | Qwen3.8-27B | 15.6 GB | Complex reasoning |

---

## Recommendation

1. **Keep Granite 4.1 3B as default**
2. **Add Qwen2.5-1.5B as lightweight tier** for trivially simple requests
3. **Route to Qwen2.5-1.5B when**: task is clearly bounded, low stakes, fast response needed
4. **Escalate to Granite when**: task requires production-grade reliability