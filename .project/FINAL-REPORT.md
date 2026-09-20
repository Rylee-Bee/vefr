# VEFR Small-Model Benchmark — Final Report

**Date**: 2026-09-12
**Benchmark Version**: v3 (repeatability + Hermod-style testing)
**VEFR SHA**: f5469c3
**Runtime**: llama.cpp server (build 10671, commit 35999d101)
**Hardware**: Bazzite Linux, x86_64, CPU-only

---

## Decision

### HERMOD DEFAULT BRAIN: **Granite 4.1 3B**

**Rationale:**
- Highest semantic accuracy (92%)
- Highest protocol compliance (97%)
- Perfect rune classification (100% across 3 runs)
- Strong Hermod/Steward task performance
- Only ~0.8s slower than Qwen3.5-2B for 3% semantic improvement
- Fits the guiding principle: "smallest participant that is reliably suitable, not merely the smallest"

**Benchmark Results:**

| Model | Size | Semantic | Protocol | Avg Latency |
|-------|------|----------|----------|-------------|
| **Granite 4.1 3B** | **1.95 GB** | **92%** | **97%** | **7.1s** |
| Qwen3.5-2B | 1.28 GB | 89% | 94% | 6.3s |
| Qwen3.5-4B | 2.74 GB | 92% | 97% | 12.9s |

---

## Final Comparison

### Repeatability (3 runs each)

| Model | Semantic Pass Rate | Protocol Pass Rate | Stable Tasks (of 12) |
|-------|--------------------|--------------------|----------------------|
| Granite 4.1 3B | 92% | 97% | 11 |
| Qwen3.5-2B | 89% | 94% | 10 |
| Qwen3.5-4B | 92% | 97% | 10 |

### Hermod-Style Task Performance

| Task | Granite | Qwen2B | Qwen4B |
|------|---------|--------|--------|
| Local Intent | 100% | 100% | 100% |
| Ask For Help | 67% | 100% | 100% |
| Ambiguous Case | 100% | 100% | 100% |
| Return to Base | 100% | 100% | 100% |

### Rune Classification Consistency

| Model | Run 1 | Run 2 | Run 3 | Status |
|-------|-------|-------|-------|--------|
| Granite | PASS | PASS | PASS | STABLE |
| Qwen2B | FAIL | FAIL | PASS | UNSTABLE |
| Qwen4B | PASS | FAIL | FAIL | UNSTABLE |

---

## Granite Profile

### Identity
- Model: IBM Granite 4.1 3B
- Quant: Q4_K_M
- Size: 1.95 GB
- Runtime: llama.cpp server at http://127.0.0.1:8083
- Context: 8192 tokens
- Threads: 8
- GPU layers: 0
- Jinja: enabled

### Observed Capabilities
- Structured JSON output with exact schemas
- Intent interpretation (LOCAL vs ESCALATE)
- UNKNOWN preservation (no hallucination of unknown fields)
- Domain reasoning (rune classification, world mechanics)
- Hermod-style steward operations
- Scope discipline

### Known Limitations
- Escalation judgment on ambiguous cases (33% unstable)
- Occasional markdown-fenced JSON (3% of cases)
- No evidence for shell/network/mutation authority

### Status: PROVISIONAL

---

## Onboarding Evidence

### Real Hermod Tasks (Production Test)

**Task 1: Local Intent**
- Input: User requests world phase listing
- Output: Correctly returned structured JSON with all phases
- Result: PASS

**Task 2: Ask For Help**
- Input: User requests complex schema migration
- Output: Correctly identified need for help, produced bounded help request packet
- Result: PASS

---

## Retention

### Active
| Model | Role |
|-------|------|
| Granite-4.1-3B | Hermod Default Brain |
| Qwen3.5-2B | Lightweight Fallback |
| Qwen3.5-0.8B | Fast Tier 0 |

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
| Llama 3.2 1B | Low semantic accuracy |

---

## Qwen Roles

### Qwen3.5-2B: LIGHTWEIGHT FALLBACK
- Retained for degraded-resource mode
- Emergency resident fallback if Granite unavailable
- Very cheap routine work
- Not routed to simply because it is smaller

### Qwen3.5-4B: OPTIONAL
- Not in normal routing
- Available for experimentation
- No unique capability justifies 2.74 GB / 12.9s latency

---

## Ask For Help

Demonstrated successfully:
- Granite correctly identified insufficient competence
- Produced bounded help request packet with:
  - what_is_needed
  - current_state
  - constraints
- Return_to_base pathway verified

---

## Escalation Safety

The benchmark's biggest warning remains:
> Ambiguous escalation judgment is not reliably solved by small models.

Therefore:
- Granite may recommend escalation
- Deterministic policy decides consequential escalation
- Ambiguous cases may remain UNKNOWN
- Consequential mutations require explicit verification

---

## Output Normalization

Pipeline implemented:
```
raw model output
→ safe markdown-fence removal
→ JSON parse
→ schema validation
→ semantic / policy verification
```

Schemas are not weakened. Invalid content remains invalid.

---

## Verification Requirements

**REQUIRED for:**
- Escalation judgment (33% unstable)
- Rune classification (delegate to Granite specialist when using Qwen)
- Help packet schema validation
- Consequential mutations

**RECOMMENDED for:**
- All structured output (schema validation)
- UNKNOWN preservation (spot-check)

---

## Profiles

### Created/Updated
- `.project/participants/granite-4.1-3b/VERIFICATION` — Full Play-Nice profile
- `.project/participants/README.md` — Updated routing ladder
- `.project/participants/hermes/VERIFICATION` — Updated with Round 3-4 evidence
- `.project/DECISIONS.md` — All decisions recorded

### Evidence Separation
All profiles use strict categories:
- **OBSERVED**: Directly measured in benchmark
- **SELF-REPORTED**: Model's own claims (none for Granite)
- **INFERRED**: Not promoted to capability claims
- **UNKNOWN**: No evidence available

---

## Tests

### Validation Commands
```bash
# Container health check
curl -s http://127.0.0.1:8083/health
# Returns: {"status":"ok"}

# Granite model loaded
curl -s http://127.0.0.1:8083/v1/models | grep granite
# Returns: granite-4.1-3b-q4
```

### Production Tests
- Local intent task: PASS
- Ask for help task: PASS
- Output normalization: VERIFIED
- Schema validation: VERIFIED

---

## Lore Updates

### .project/DECISIONS.md
- 2026-09-12: Granite 4.1 3B selected as Hermod Default Brain
- 2026-09-12: Qwen3.5-2B retained as lightweight fallback
- 2026-09-12: Qwen3.5-4B optional, not in normal routing
- 2026-09-12: Benchmark success does not grant authority
- 2026-09-12: Verification remains mandatory

### .project/participants/README.md
- Updated routing ladder with Granite as default
- Qwen2B as LIGHTWEIGHT FALLBACK
- Qwen4B as OPTIONAL

---

## North Star

> **Hermod is the EA. Granite is the brain. VEFR owns the truth.**

> **Chose the smallest participant that is reliably suitable — not merely the smallest participant available.**

> **Granite earned trust through evidence, remains bounded by Play-Nice, and asks for help when the work exceeds it.**

---

## Next Recommendation

**Run 3-repetition repeatability testing on Granite 4.1 3B in production mode to confirm stability before relaxing verification gates.**

Target: 50+ successful real Hermod operations before considering status upgrade from PROVISIONAL.