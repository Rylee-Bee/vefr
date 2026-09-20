# Final Report: Granite Onboarding + Play-Nice Harness Evidence

**Date**: 2026-09-12
**VEFR SHA**: f5469c3 (main)
**Play-Nice SHA**: 1c05de4 → 60b1bf8 (3 commits ahead)
**Play-Nice VERSION**: 0.6.0 (unchanged)
**Contracts**: 65 (unchanged)

---

## Canonical State

### VEFR
- Starting SHA: f5469c3
- Final SHA: c7a1561 (committed)
- Status: `.project/` untracked, experiments/ untracked

### Play-Nice Contracts
- Starting SHA: 1c05de4
- Final SHA: 60b1bf8
- Commits: 3 ahead of origin
- VERSION: 0.6.0 (unchanged)
- Lockfile: unchanged
- Tests: 106 passed

### rylee_lore
- SHA: b03cc9c (committed)
- Updated Hermod brain documentation

---

## Files Changed

### Play-Nice (committed)

| File | Action | Lines |
|------|--------|-------|
| `profiles/granite-4.1-3b.md` | ADD | +173 |
| `docs/research/hermes-granite-evidence.md` | ADD | +269 |
| `docs/roles/trusted-steward.md` | ADD | +249 |
| `README.md` | MODIFY | +3/-1 |
| `profiles/hermes.md` | MODIFY | +40/-1 (prior session) |

**Total**: 5 files changed, +733 lines

### VEFR (committed)

| File | Action |
|------|--------|
| `.project/CURRENT.md` | MODIFY — added Hermod brain row |

### VEFR (untracked)

| File/Dir | Purpose |
|----------|---------|
| `.project/FINAL-REPORT.md` | Complete benchmark report |
| `.project/benchmark-r3-final-report.md` | Round 3 repeatability results |
| `.project/benchmark-r3-results.json` | Raw Round 3 data |
| `.project/participants/*/VERIFICATION` | 10 model profiles |
| `.project/benchmark_qual.py` | Qualification harness |
| `.project/benchmark_r2.py` | Round 2 benchmark harness |
| `.project/benchmark_r3.py` | Round 3 benchmark harness |
| `experiments/character-packs/` | Experimental corpus (in progress) |

### rylee_lore (committed)

| File | Action |
|------|--------|
| `context/NOW.md` | MODIFY — updated Hermod brain to Granite |

---

## Granite Profile

### Identity
- Model: IBM Granite 4.1 3B
- Quant: Q4_K_M (~1.95 GB)
- Runtime: llama.cpp (Bazzite, CPU-only)
- Endpoint: localhost:8083

### Benchmark Results

| Round | Semantic | Protocol | Reps |
|-------|----------|----------|------|
| 2 | 87.5% | 100% | 1 |
| 3 | 92% | 97% | 3 |

### Role
**Hermod Default Brain (Tier 1)**

---

## Play-Nice Onboarding

### Attestation
- Granite 4.1 3B onboarded as Hermod Default Brain
- Role: Trusted Steward (VEFR implementation)
- Authority: None beyond explicitly granted capabilities
- Status: PROVISIONAL

### Evidence Categories
- **OBSERVED**: 36 task evaluations across 3 rounds
- **SELF-REPORTED**: None
- **INFERRED**: None promoted
- **UNKNOWN**: Long-context behavior, reasoning depth beyond 4 steps

---

## Evidence/Hypotheses Added

### Receipts (8 total)

1. Semantic and protocol are separate axes
2. Small models unreliable at ambiguous escalation
3. One successful run is evidence, not certainty
4. Markdown fences are protocol friction, not intelligence
5. Smallest suitable > smallest available
6. Model ≠ Hermod ≠ VEFR authority
7. Harness bugs masquerade as model failures
8. Verification remains necessary

### Lessons (8 total)

See `docs/research/hermes-granite-evidence.md` for full cross-domain mapping.

### Hypotheses (3 total)

1. **Receipts prove only what they prove** — SUPPORTED (cross-domain)
2. **Reservations are distinct from Questions** — SUPPORTED (within-domain)
3. **Examine before you claim** — SUPPORTED (cross-domain)

### Candidate Compass Language

Research candidates only:
- Observe before you claim
- Know who owns the truth
- Questions are better than guesses
- Let Receipts prove only what they prove
- Voice Reservations when evidence has limits
- Ask for help when you reach yours
- Verify what matters
- Re-examine before consequential action

Existing principle preserved: **Constrain authority, not creativity.**

---

## Cross-Domain Convergence

| Domain | Lesson | Meta-pattern |
|--------|--------|--------------|
| Claude/Fable | Green tests ≠ working product | One evidence type ≠ all evidence |
| Hermes/Granite | Correct output ≠ working protocol | Test what matters, not what's easy |

**Observation**: Independent domains support the same meta-pattern. Status: Research hypothesis, not canonical.

---

## Icebreaker Concept

**Status**: EXPERIMENTAL naming candidate

Concept: Every new participant gets an Icebreaker, not a textbook.
- Relevant Promises
- Compass (orientation kernel)
- Role Guide
- Important Questions/Reservations
- Sources
- Authority boundaries
- Where/how to ask for help

**Reservation**: Not a new canonical architecture layer yet.

---

## Counterexamples Found

### Markdown fences as false positive
Initial assessment suggested Gemma 3 4B had 87% semantic failure rate. Re-examination showed it was protocol failure (markdown fences wrapping correct JSON). The semantic content was accurate.

### Single-run overconfidence
Qwen3.5-2B's 8/8 Round 1 score masked 89% semantic rate across 3 repetitions. The single run was an overestimate.

### Harness vs model failure
Corpus generation exposed double-path bugs and container timing issues. These were misidentified as model failures until traced to harness code.

---

## Research Flow Demonstrated

```
Question: Which brain is best for Hermod?
→ Examine: 3 rounds of benchmarking
→ Receipt: 36 task evaluations
→ Answer: Granite 4.1 3B (92% semantic, 97% protocol)
→ Reservation: Single domain, controlled setting
→ Examine: Cross-domain comparison with Claude/Fable
→ new Receipt: Meta-pattern convergence
→ confirmed Answer: Granite 4.1 3B with verification gates
```

---

## Retention

### Active
| Model | Role | Location |
|-------|------|----------|
| Granite-4.1-3B | Hermod Default Brain | localhost:8083 |
| Qwen3.5-2B | Lightweight Fallback | ~/llama-server/models/bench/ |
| Qwen3.5-0.8B | Fast Tier 0 | ~/llama-server/models/bench/ |

### Optional
| Model | Reason |
|-------|--------|
| Qwen3.5-4B | Experimentation only |
| Llama-3.2-3B | Control comparison |
| Phi-4-mini | Historical control |

### Not Retained
| Model | Reason |
|-------|--------|
| SmolLM3-3B | Poor protocol, slow |
| Gemma 3 4B | Worst protocol compliance |
| Ministral-3-3B | Poor protocol, scope expansion |
| Gemma 3 1B | Poor protocol, scope expansion |
| Llama 3.2-1B | Low semantic accuracy |

---

## Guardrails Observed

- ✅ No canonical contracts changed
- ✅ No lockfiles regenerated
- ✅ No Play-Nice version bumped
- ✅ No Harness PR found/merged
- ✅ No mass-rename of existing repository structure
- ✅ All changes are additive evidence/research artifacts only
- ✅ Tests pass (106/106)

---

## Harness PR Status

**No Harness PR found.** No branch with "harness" in name exists on origin. No PR open on GitHub.

---

## Next Recommendation

**Deploy Granite 4.1 3B as Hermod Default Brain in production.**

Run real Hermod operations to accumulate production evidence:
- Target: 50+ successful operations before status upgrade from PROVISIONAL
- Focus areas: escalation judgment stability, help packet fidelity, specialist-return verification

Also: fix the character pack generation harness (`generate_corpus.py`) and run the full 36-42 pack experimental corpus.

---

## Repos Status

| Repo | SHA | Status |
|------|-----|--------|
| vefr | c7a1561 | .project/ + experiments/ untracked |
| rylee_lore | b03cc9c | clean |
| play-nice-contracts | 60b1bf8 | 3 ahead of origin, unpushed |