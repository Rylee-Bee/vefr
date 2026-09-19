# Small Model Olympics — Qualifier TL;DR (2026-09-13)

Suite **0.4.1**, 27 models, 53-task qualifier, one canonical run each. Full
report: `bench/reports/QUALIFIER-CAMPAIGN-2026-09-13.md`.

## Bottom line
- Every one of the 27 qualifiers now **completes** (no stuck/aborted runs).
- Three harness bugs caused all the stuck runs; none were model faults.
- Backend is now **OBSERVED**, not assumed; legacy numbers stay labeled
  **UNKNOWN** for backend provenance.
- All latencies are **contended** — a resident 27B agent holds ~16/16.3 GiB
  VRAM. Never compare these to idle-GPU or historical CPU numbers.

## Standings (pass%)
| Tier | Models |
|---|---|
| Top | qwen3-1.7b 76, lfm2.5-2.6b 70, ministral-3-3b 68, falcon3-3b 66 |
| Mid | gemma3-4b / phi-3.5-mini / phi-4-mini 64, granite-4.1-3b / qwen2.5-1.5b-tools / qwen2.5-3b 62, several 50-60 |
| Weak | gemma3-1b 42, qwen3.5-0.8b/-2b 30/28, hermes-1.5b 28 |

## What changed (fixes, suite 0.4.1 — no task/judge edits)
1. Template-safe transcripts — unblocked Gemma3-1b (HTTP 400) and Qwen3.5 (HTTP 500).
2. Reasoning capture — Qwen3.5/Granite4.2/LFM/SmolLM3 empty-content failures now carry evidence.
3. Backend truth probe — `vulkan` is OBSERVED per run, not hardcoded.
4. Abort records — partial runs explain themselves (exception, trials, attempt).

## Key honesty notes
- phi-4-mini **64.2%** here ≠ historical **100/100** (different production-path set, CPU b10818).
- qwen3.5-0.8b **30.2%** here ≠ historical **80.3** (Q8_0 artifact no longer present).
- Legacy 12 models: backend **UNKNOWN** — no CPU-vs-GPU claim is made for them.

## References
| Doc | Path |
|---|---|
| Full campaign report | `bench/reports/QUALIFIER-CAMPAIGN-2026-09-13.md` |
| Root-cause diagnosis + reproductions | `bench/reports/DIAGNOSIS-2026-09-13-stuck-runs.md` |
| Decisions (campaign, backend, hermes) | `.project/DECISIONS.md` (2026-09-13) |
| Raw evidence | `bench/runs/` (canonical per participant in `index.json`) |
| Recovery takeover evidence | `bench/reports/RECOVERY-REPORT-2026-09-13.md` |