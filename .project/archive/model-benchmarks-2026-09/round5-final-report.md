# VEFR Round 5: Models Similar to Granite 4.1 3B — FINAL

**Date**: 2026-09-12
**Control**: Granite 4.1 3B
**Quant**: Q4_K_M for all
**Runtime**: llama.cpp (build 10671) via Podman on Bazzite
**Settings**: temp=0.3, min_p=0.1

---

## Models Tested

| Model | Size | Params | Source | License |
|-------|------|--------|--------|---------|
| **Granite 4.1 3B** | 1.95 GB | 3.0B | IBM (control) | Apache 2.0 |
| Qwen2.5-3B-Instruct | 1.86 GB | 3.0B | Alibaba | Apache 2.0 |
| Phi-3.5-mini-3.8B | 2.39 GB | 3.8B | Microsoft | MIT |
| Qwen2.5-1.5B-Instruct | 1.08 GB | 1.5B | Alibaba | Apache 2.0 |
| Falcon3-3B-Instruct | 1.96 GB | 3.0B | TIIUAE | Apache 2.0 |
| StableLM-Zephyr-3B | 1.71 GB | 3.0B | Stability AI | CC BY-SA 4.0 |

---

## Results (temp=0.3)

| Model | Size | Run 1 | Run 2 | Run 3 | Mean |
|-------|------|-------|-------|-------|------|
| **Granite 4.1 3B** | 1.95 GB | 5/6 | 5/6 | 5/6 | **5/6 (83%)** |
| Qwen2.5-3B | 1.86 GB | 5/6 | — | — | 5/6 (83%) |
| Qwen2.5-1.5B | 1.08 GB | 5/6 | 5/6 | 5/6 | **5/6 (83%)** |
| Falcon3-3B | 1.96 GB | 5/6 | 4/6 | — | 4.5/6 (75%) |
| StableLM-Zephyr-3B | 1.71 GB | 4/6 | — | — | 4/6 (67%) |
| Phi-3.5-mini-3.8B | 2.39 GB | 3/6 | — | — | 3/6 (50%) |

*Granite 4.1 3B at default settings (Round 4): 6/6 (100%)*

---

## Per-Task Breakdown

| Task | Granite | Qwen3B | Qwen1.5B | Falcon | StableLM | Phi3.5 |
|------|---------|--------|----------|--------|----------|--------|
| NPC Creation | PASS | PASS | PASS | PASS | PASS | PASS |
| State Edit | PASS | PASS | PASS | PASS | **FAIL** | PASS |
| Escalation | PASS | PASS | PASS | PASS | PASS | **FAIL** |
| Rune Classification | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| UNKNOWN | PASS | PASS | PASS | PASS | PASS | **FAIL** |
| Scope | PASS | PASS | PASS | PASS | PASS | PASS |

---

## Key Findings

### 1. Rune Classification Is Universal Failure
Every model failed. This is a **knowledge gap** — the task required memorizing VEFR-specific rune-phase mappings that aren't in any training data. Not a fair capability test.

### 2. Granite 4.1 3B Still Leads
- 83% at temp=0.3 (this round, 3 runs)
- 100% at default settings (Round 4)
- 92% semantic / 97% protocol (Round 3, averaged over 3 runs)
- **Most importantly**: already onboarded and tested in production

### 3. Two Models Tie at 83% with Perfect Repeatability
- **Qwen2.5-3B**: 5/6 (single run, needs more reps)
- **Qwen2.5-1.5B**: 5/6 (3 runs, **perfect repeatability**)

### 4. Falcon3-3B Shows Instability
Scored 5/6 on run 1, 4/6 on run 2. This confirms single-run results are unreliable — a core lesson from earlier rounds.

### 5. Phi-3.5-mini Is the Worst Performer
Despite being largest (3.8B), it scored 50%. It failed 3 tasks including UNKNOWN preservation — a critical failure for a steward that should know when it doesn't know.

### 6. Qwen2.5-1.5B Is the Surprise
At half the size of Granite (1.08 GB vs 1.95 GB), it tied on score with **perfect repeatability**. This makes it a compelling lightweight fallback.

---

## Size vs Performance

| Model | Size | Params | Score | Repeatability |
|-------|------|--------|-------|---------------|
| Granite 4.1 3B | 1.95 GB | 3.0B | 83% | 3/3 identical |
| **Qwen2.5-1.5B** | **1.08 GB** | **1.5B** | **83%** | **3/3 identical** |
| Qwen2.5-3B | 1.86 GB | 3.0B | 83% | needs more reps |
| Falcon3-3B | 1.96 GB | 3.0B | 75% | unstable |

---

## Verdict

**Granite 4.1 3B remains Hermod Default Brain.**

Why it wins despite the tie:
1. **Highest observed score**: 100% at default settings
2. **Production evidence**: Already onboarded, 2/2 real Hermod tasks passed
3. **Prior evidence**: 3 rounds of benchmarking, consistently strong
4. **Not just the score**: Granite's failures are semantic (rune knowledge), not protocol (formatting, scope, UNKNOWN)

**But Qwen2.5-1.5B is now a confirmed lightweight tier** with perfect repeatability at half the size.

---

## Updated Routing Ladder

| Tier | Model | Size | Use When |
|------|-------|------|----------|
| **DEFAULT** | Granite 4.1 3B | 1.95 GB | Production tasks, high reliability |
| **LIGHTWEIGHT** | Qwen2.5-1.5B | 1.08 GB | Simple bounded tasks, fast response |
| **ESCALATION** | Qwen3.8-27B | 15.6 GB | Complex reasoning, ambiguity |

---

## Recommendation

| Action | Model |
|--------|-------|
| **Keep as Default** | Granite 4.1 3B |
| **Add as Lightweight Tier** | Qwen2.5-1.5B |
| **Viable Alternative** | Qwen2.5-3B (needs 3 reps) |
| **Drop** | Phi-3.5-mini (50%), StableLM-Zephyr-3B (67%), Falcon3-3B (unstable) |

---

## Data Quality

- **3 repetitions** for Qwen2.5-1.5B and Granite 4.1 3B
- **Single run** for Qwen2.5-3B, Phi-3.5-mini, StableLM-Zephyr-3B (screening only)
- **Falcon3-3B** showed run-to-run variance — needs 3 reps for confidence
- **Rune Classification** is confounded by domain knowledge; should be redesigned
- **Production evidence** for Granite outweighs benchmark ties

---

## Postscript — 2026-09-12

After this report was finalized, a 5x repeatability study was performed on both Qwen2.5-1.5B and Granite 4.1 3B. Both models showed identical scores across all 5 runs (5/6, zero variance).

Based on this evidence, **Qwen2.5-1.5B was promoted to Hermod DEFAULT Brain** and **Granite 4.1 3B was demoted to FALLBACK**. See `.project/DECISIONS.md` for the formal decision record.

This change is not reflected in the body of this report, which was written before the promotion.