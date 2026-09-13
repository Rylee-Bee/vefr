# SMALL MODEL FINALS — RUN PLAN

Generated: 2026-09-13
Status: FINALS READY — AWAITING LAUNCH

---

## Suite Counts

| Suite | Tasks | Participants | Runs Each | Total Trials |
|-------|-------|-------------|-----------|-------------|
| Worlds Brain | 62 | 2 | 3 | 372 |
| VEFR Storyteller | 57 | 2 | 3 | 342 |
| **Total** | **119** | **4** | **3** | **714** |

## Commit SHAs

- Task bank curation: `41e027d`
- Finals infrastructure: `62656cb`

## Models/Artifacts Detected

| Participant | File | Size | Quant |
|------------|------|------|-------|
| LFM2.5 2.6B | `LFM2.5-2.6B-Q4_K_M.gguf` | 1.6 GB | Q4_K_M |
| Qwen3 1.7B | `Qwen3-1.7B-Q4_K_M.gguf` | 1.2 GB | Q4_K_M |
| Phi-4-mini | `Phi-4-mini-Q4_K_M.gguf` | 2.4 GB | Q4_K_M |
| Ministral 3 3B | `Ministral-3-3B-Q4_K_M.gguf` | 2.0 GB | Q4_K_M |

All files present in `/var/home/rylee/llama-server/models/bench/`.

## Backend/Runtime Detected

| Property | Value |
|----------|-------|
| CPU | AMD Ryzen 7 7800X3D (8 cores) |
| RAM | 64 GB (33 GB available) |
| GPU | None (CPU-only inference) |
| Backend | llama.cpp (to be started per participant) |
| Template | Jinja (native chat template) |
| Output format | `response_format.json_schema`, `strict: true` |

**UNKNOWN:** No llama.cpp server currently running. Each participant requires starting a fresh server instance. Contention is zero (no other inference workloads detected).

## Scoring Breakdown

### Deterministic evaluations (automated)

| Suite | Tasks | Scoring Method |
|-------|-------|---------------|
| Worlds Brain | 62 | All deterministic validators (structured, tool, unknown, etc.) |
| VEFR Storyteller (deterministic) | 14 | prose_signals, world_belief, dialogue_distinct validators |
| VEFR Storyteller (mixed) | 20 | Deterministic checks + optional human dimension ratings |
| **Total automated** | **96** | |

### Human comparisons (Rylee)

| Suite | Tasks | Scoring Method |
|-------|-------|---------------|
| VEFR Storyteller (subjective) | 23 | Blind A/B + 1-5 dimension ratings |
| **Total human** | **23** | |

Human review is pre-batched into3 groups of 7-8 tasks. Each comparison shows:
- Scenario context
- Response A (randomized)
- Response B (randomized)
- Relevant dimensions only (not all9)
- PREFERRED: A / B / TIE

## Estimated Run Workload

### Automated inference

| Phase | Tasks | Trials | Est. Time/Trial | Est. Total |
|-------|-------|--------|----------------|-----------|
| Worlds × LFM2.5 | 62 | 186 | ~50s | ~2.6h |
| Worlds × Qwen3 | 62 | 186 | ~40s | ~2.1h |
| VEFR × Phi-4-mini | 57 | 171 | ~70s | ~3.3h |
| VEFR × Ministral3 | 57 | 171 | ~60s | ~2.9h |
| **Total automated** | | **714** | | **~10.9h** |

Time estimates assume CPU-only inference at ~8-15 tok/s for Q4_K_M quants on the 7800X3D. Actual times depend on context length and model-specific throughput.

### Human review

| Batch | Tasks | Est. Time |
|-------|-------|-----------|
| Batch 1 | 8 | ~30 min |
| Batch 2 | 8 | ~30 min |
| Batch 3 | 7 | ~25 min |
| **Total human** | **23** | **~1.5h** |

## Exact Commands to Launch

### Worlds Brain finals

```bash
# LFM2.5 2.6B
uv run python -m bench.finals.run --suite worlds --participant lfm2.5-2.6b --runs 3

# Qwen3 1.7B
uv run python -m bench.finals.run --suite worlds --participant qwen3-1.7b --runs 3
```

### VEFR Storyteller finals

```bash
# Phi-4-mini
uv run python -m bench.finals.run --suite vefr --participant phi-4-mini --runs 3

# Ministral 3 3B
uv run python -m bench.finals.run --suite vefr --participant ministral-3-3b --runs 3
```

### All at once

```bash
uv run python -m bench.finals.run --suite worlds --all-participants --runs 3
uv run python -m bench.finals.run --suite vefr --all-participants --runs 3
```

## What Gets Preserved Per Run

Each trial records:
- `task_id` — which task
- `raw` — exact model output
- `parsed` — structured parse result
- `verdict` — deterministic judge result (semantic, protocol, authority, unknown, etc.)
- `latency_s` — wall-clock time
- `backend` — inference backend (llama.cpp)
- `suite` — which suite
- `run_idx` — repetition number
- `run_id` — unique run identifier

Plus per-run header:
- Model artifact identity (file, SHA, quant)
- Backend probe (GPU/CPU, VRAM)
- Contention conditions
- Task-suite version/SHA

## Human Review Material (Pre-generated)

| File | Contents |
|------|----------|
| `bench/finals/vefr-review-batch-1.json` | 8 subjective tasks |
| `bench/finals/vefr-review-batch-2.json` | 8 subjective tasks |
| `bench/finals/vefr-review-batch-3.json` | 7 subjective tasks |
| `bench/finals/vefr-blind-map.json` | Private A/B ordering map |
| `bench/finals/vefr-human-review-template.json` | Task-to-dimension mapping |

After automated runs complete, the runner will populate Response A/B in each batch file (randomized, model identity hidden). Rylee reviews at her pace.

## UNKNOWN Items

1. **No llama.cpp server currently running.** The runner will start one per participant. No contention expected.
2. **Actual CPU throughput.** Estimates based on prior benchmarks on this hardware; actual may vary ±30%.
3. **Qwen3 thinking mode.** Qwen3 family defaults to thinking mode which may consume output budget. The runner will send `enable_thinking: false` if the model supports it (matching existing Spark/bench convention).
4. **Gemma3/Qwen3.5 template quirks.** The existing harness has `sanitize_messages()` to handle consecutive-assistant-turn and mid-session-system issues. The finals runner inherits this.

---

## FINALS READY — AWAITING LAUNCH
