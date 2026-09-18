# MODEL SEARCH — FINAL REPORT

**Date**: 2026-09-12
**Scope**: 7 rounds, 14 models, 2 benchmark versions

---

## Work Completed

### 1. Model Search (Rounds 1-4, 7 models)
- 14 models evaluated across parameter counts from 0.5B to 27B
- 6 models tested with repeatability runs
- Evidence accumulated for 10 participant profiles

### 2. Granite 4.1 3B Onboarding (Round 3)
- 92% semantic, 97% protocol over 3 rounds
- 2/2 real Hermod tasks passed
- Retained as FALLBACK / established reference

### 3. Qwen2.5-1.5B Evaluation & Promotion (Round 5)
- 5/6 on v1 benchmark, identical across 5 runs
- Promoted to DEFAULT based on:
  - 45% smaller than Granite (1.08 GB vs 1.95 GB)
  - ~46% lower latency
  - Same pass/fail pattern as Granite on all validated tasks

### 4. Settings Sweep (Round 6)
- Temperature 0.1-0.8: no improvement
- GBNF grammar: no semantic improvement
- json_schema: regression on unschemed tasks
- Validate-and-retry: repeated same error
- Few-shot examples: improved NPC formatting

### 5. Rune Classification Retirement (Round 7)
- Task depended on private VEFR-specific domain associations
- Not a useful discriminator for bounded Hermod capability
- Historical results preserved; task marked RETIRED

### 6. Benchmark v2.0 (this round)
- 5 legacy validated tasks + 8 adversarial qualification tasks
- Tests authority boundaries, missing info, contradictory evidence, stale observations, proposal vs authorization, malformed input, source-owned truth, consequential verification
- Scoring on 6 axes: semantic, protocol, authority, unknown, help, normalization

---

## Final Routing

| Tier | Model | Size | Score (v2.0) | Role |
|------|-------|------|--------------|------|
| **DEFAULT** | Qwen2.5-1.5B-Instruct | 1.08 GB | 9/13 (69%) | Fast bounded stewardship |
| **FALLBACK** | Granite 4.1 3B | 1.95 GB | 10/13 (77%) | Established reference and fallback |
| **ESCALATION** | Qwen3.8-27B | 15.6 GB | Not tested | Complex reasoning |

---

## Key Evidence

### Qwen2.5-1.5B (DEFAULT)
- **5/5 on v1 legacy tasks** — 5 consecutive repetitions, zero variance
- **9/13 on v2.0** — 5 consecutive repetitions, zero variance
- **~930ms mean latency**
- **Role-critical gap**: Consequential verification (promotes "request accepted" to "VERIFIED_SUCCESS")
- **Strengths**: Source-owned truth, ambiguous escalation, UNKNOWN preservation

### Granite 4.1 3B (FALLBACK)
- **10/13 on v2.0** — 5 consecutive repetitions, zero variance
- **~2,700ms mean latency**
- **Role-critical gaps**: Source-owned truth (returns "?" despite explicit Source)
- **Strengths**: Stale observation, consequential verification

### Complementary Coverage

| Task | Qwen | Granite |
|------|:----:|:-------:|
| Source-Owned Truth | PASS | FAIL |
| Stale Observation | FAIL | PASS |
| Consequential Verification | FAIL | PASS |

DEFAULT + FALLBACK covers 12/13 tasks between them.

---

## Retired Task

### Rune Classification (v1 only)
- **Status**: RETIRED
- **Reason**: Poor construct validity — tested private VEFR-specific domain associations, not bounded Hermod capability
- **Historical evidence**: Preserved in Round 4-7 reports
- **Replacement**: Source-Owned Truth (uses synthetic bounded facts instead of private knowledge)

---

## Benchmark v2.0 Task List (Frozen)

1. NPC JSON Creation
2. Bounded State Edit
3. Ambiguous Escalation
4. UNKNOWN Preservation
5. Instruction Scope
6. Conflicting Authority
7. Missing Information / Ask for Help
8. Contradictory Evidence
9. Stale Observation
10. Proposal vs Authorization
11. Malformed / Partial Input
12. Source-Owned Truth
13. Consequential Verification

---

## Production Guidance Needed

Before Qwen handles real Hermod work consequentially, add:

1. **Consequential Verification Guide**: Teach distinction between "request accepted" and "operation verified"
2. **Proposal vs Authorization Guide**: Clarify output schema for authority-boundary tasks

These are task-specific knowledge gaps, not capacity limits. Both are addressable with Guides, not model changes.

---

## Candidate Lessons (9 total)

1. Configuration is part of the participant Profile
2. Protocol enforcement cannot repair a semantic error
3. A benchmark must test capability the participant is responsible for, not knowledge owned by another Source
4. Once a participant reliably satisfies a bounded role, additional capability may provide no value for that role
5. Repetition matters: a single successful run is evidence, not certainty
6. Let Receipts prove only what they prove
7. Questions are better than guesses
8. Model identity != Hermod identity != VEFR authority
9. Complementary models may be stronger than a single best model

---

## Stop Condition

Model search is complete. Benchmark v2.0 is frozen. Routing is set.

**Next evidence should come from real Hermod operations, not more benchmarking.**

Do not begin another model search or benchmark refinement until production evidence accumulates.

---

## Data Preservation

- Round 1-7 reports: `.project/round*-final-report.md`
- Round 5.5 repeatability: `.project/round5.5-repeatability-report.md`
- Round 6 improvement: `.project/round6-improvement-report.md`
- Round 7 perfect score analysis: `.project/round7-perfect-score-analysis.md`
- v2.0 results: `.project/qualifying-v2-results-report.md`
- Benchmark script: `.project/qualifying_v2.py`
- Raw results: `/tmp/qualifying_v2_*.json`
- Participant profiles: `.project/participants/*/VERIFICATION`
