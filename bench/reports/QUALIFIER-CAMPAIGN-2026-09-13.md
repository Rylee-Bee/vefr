# Small Model Olympics — Qualifier Campaign 2026-09-13

Suite **0.4.1** (restart evidence build) · 27 participants · 53-task qualifier · generated 2026-09-13 11:18Z

## Evidence status

| Label | Meaning |
|---|---|
| OBSERVED | backend confirmed at runtime (drm render node present in the model container, header `backend_probe`) |
| UNKNOWN | backend trusted from header or prior report only; no runtime evidence survives (containers removed, pre-0.4.1 headers) |

**Environment:** bazzite box (`bazzite`), rootless podman, llama.cpp `server-vulkan` image build b10920 commit `eafe15a5e`, context 8192, threads 8, `-ngl 999`, GEN temperature 0.3 / max_tokens 768 (tool 512, story 1024). GPU: AMD Navi21 (`card1`/`renderD128`, PCI 1002:73BF).
**Contention (must-read):** a resident 27B llama-qwen-agent holds the GPU at 15.9–16.3 GiB of 16.3 GiB VRAM throughout. Every number below is a _contended_ latency and a contended throughput. Do not compare these to an idle-GPU run or to historic CPU-box numbers.

## Campaign table (canonical runs, 53 trials each)

| participant | class | pass | pass% | hermod/a/story/flex | tool | struct | unknown | lat mean | art MB | backend evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3-1.7b | WELTER | 40/53 | 76% | 0.821 / 0.6 / 1.0 / 0.6 | 1.0 | 0.75 | 1.0 | 14.0s | 1223.0 | UNKNOWN (legacy header, no probe) |
| lfm2.5-2.6b | MIDDLE | 37/53 | 70% | 0.857 / 0.6 / 0.4 / 0.4 | 0.909 | 1.0 | 1.0 | 26.5s | 1596.9 | OBSERVED (render node in ctr) |
| ministral-3-3b | MIDDLE | 36/53 | 68% | 0.821 / 0.533 / 0.8 / 0.2 | 0.909 | 1.0 | 0.963 | 7.5s | 2047.1 | OBSERVED (render node in ctr) |
| falcon3-3b | MIDDLE | 35/53 | 66% | 0.714 / 0.6 / 0.6 / 0.6 | 0.818 | 1.0 | 0.926 | 6.2s | 1912.8 | OBSERVED (render node in ctr) |
| gemma3-4b | MIDDLE | 34/53 | 64% | 0.643 / 0.667 / 0.8 / 0.4 | 0.818 | 1.0 | 0.92 | 6.2s | 2374.5 | OBSERVED (render node in ctr) |
| phi-3.5-mini | MIDDLE | 34/53 | 64% | 0.714 / 0.533 / 0.6 / 0.6 | 0.818 | 1.0 | 0.923 | 14.1s | 2282.4 | OBSERVED (render node in ctr) |
| phi-4-mini | MIDDLE | 34/53 | 64% | 0.679 / 0.6 / 0.8 / 0.4 | 0.818 | 0.75 | 0.96 | 6.1s | 2376.4 | OBSERVED (render node in ctr) |
| granite-4.1-3b | MIDDLE | 33/53 | 62% | 0.607 / 0.6 / 0.8 / 0.6 | 0.727 | 0.75 | 0.958 | 4.3s | 2002.2 | UNKNOWN (legacy header, no probe) |
| qwen2.5-1.5b-tools | WELTER | 33/53 | 62% | 0.643 / 0.6 / 0.6 / 0.6 | 0.818 | 0.75 | 0.917 | 2.0s | 940.4 | UNKNOWN (legacy header, no probe) |
| qwen2.5-3b | MIDDLE | 33/53 | 62% | 0.679 / 0.467 / 0.8 / 0.6 | 0.909 | 0.75 | 0.958 | 4.0s | 1840.5 | UNKNOWN (legacy header, no probe) |
| lfm2.5-1.2b | LIGHT | 32/53 | 60% | 0.679 / 0.467 / 0.8 / 0.4 | 0.818 | 0.5 | 0.957 | 1.6s | 697.0 | UNKNOWN (legacy header, no probe) |
| llama3.2-3b | MIDDLE | 32/53 | 60% | 0.643 / 0.533 / 0.6 / 0.6 | 0.818 | 1.0 | 0.92 | 4.5s | 1925.8 | OBSERVED (render node in ctr) |
| qwen3-0.6b | BANTAM | 32/53 | 60% | 0.643 / 0.467 / 0.8 / 0.6 | 0.818 | 0.5 | 0.955 | 1.3s | 461.8 | UNKNOWN (legacy header, no probe) |
| smollm3-3b | MIDDLE | 32/53 | 60% | 0.679 / 0.533 / 0.4 / 0.6 | 1.0 | 0.75 | 1.0 | 13.7s | 1826.6 | OBSERVED (render node in ctr) |
| qwen2.5-1.5b | WELTER | 31/53 | 58% | 0.607 / 0.467 / 1.0 / 0.4 | 0.727 | 0.5 | 0.905 | 2.1s | 1065.6 | UNKNOWN (legacy header, no probe) |
| xlam-2-1b-fc-r | LIGHT | 30/53 | 57% | 0.536 / 0.467 / 1.0 / 0.6 | 0.909 | 0.75 | 1.0 | 2.5s | 940.4 | UNKNOWN (legacy header, no probe) |
| granite-4.2-3b | MIDDLE | 29/53 | 55% | 0.607 / 0.6 / 0.2 / 0.4 | 0.909 | 0.75 | 1.0 | 42.2s | 2209.8 | OBSERVED (render node in ctr) |
| stablelm-zephyr-3b | MIDDLE | 27/53 | 51% | 0.536 / 0.467 / 0.6 / 0.4 | 0.727 | 0.75 | 0.864 | 6.1s | 1629.4 | OBSERVED (render node in ctr) |
| qwen2.5-0.5b | BANTAM | 25/53 | 47% | 0.5 / 0.467 / 0.4 / 0.4 | 0.727 | 0.25 | 0.9 | 1.0s | 468.6 | UNKNOWN (legacy header, no probe) |
| smollm2-1.7b | WELTER | 25/53 | 47% | 0.429 / 0.533 / 0.6 / 0.4 | 0.364 | 0.5 | 0.9 | 2.5s | 1006.7 | UNKNOWN (legacy header, no probe) |
| gemma3-1b | LIGHT | 22/53 | 42% | 0.429 / 0.267 / 0.8 / 0.4 | 0.364 | 1.0 | 0.789 | 2.5s | 768.7 | OBSERVED (render node in ctr) |
| llama3.2-1b | LIGHT | 20/53 | 38% | 0.357 / 0.333 / 0.6 / 0.4 | 0.636 | 0.25 | 0.786 | 2.3s | 770.3 | UNKNOWN (legacy header, no probe) |
| qwen3.5-4b | MIDDLE | 19/53 | 36% | 0.393 / 0.333 / 0.0 / 0.6 | 0.909 | 0.25 | 0.933 | 76.7s | 2614.0 | OBSERVED (render node in ctr) |
| smollm2-360m | FEATHER | 19/53 | 36% | 0.321 / 0.4 / 0.4 / 0.4 | 0.364 | 0.25 | 0.857 | 1.3s | 368.5 | UNKNOWN (legacy header, no probe) |
| qwen3.5-0.8b | BANTAM | 16/53 | 30% | 0.357 / 0.267 / 0.0 / 0.4 | 0.727 | 0.25 | 0.857 | 6.1s | 507.8 | OBSERVED (render node in ctr) |
| qwen2.5-hermes-1.5b | WELTER | 15/53 | 28% | 0.25 / 0.333 / 0.6 / 0.0 | 0.455 | - | 0.875 | 2.9s | 940.4 | OBSERVED (render node in ctr) |
| qwen3.5-2b | WELTER | 15/53 | 28% | 0.393 / 0.2 / 0.0 / 0.2 | 0.818 | 0.25 | 0.833 | 29.2s | 1221.5 | OBSERVED (render node in ctr) |

## Evidence cohorts

- **0.4.1 restart cohort (15):** every trial carries captured `reasoning_content`, finish reasons, per-trial template transforms, and an OBSERVED backend probe. No aborted runs; all 53 trials each. Runs: falcon3-3b, gemma3-1b, gemma3-4b, granite-4.2-3b, lfm2.5-2.6b, llama3.2-3b, ministral-3-3b, phi-3.5-mini, phi-4-mini, qwen2.5-hermes-1.5b, qwen3.5-0.8b, qwen3.5-2b, qwen3.5-4b, smollm3-3b, stablelm-zephyr-3b.
- **0.4.0 legacy cohort (12):** preserved but backend UNKNOWN; headers hard-coded `backend: vulkan` with no evidence. Kept append-only per policy; not invalidated, not re-proven. Runs: granite-4.1-3b, lfm2.5-1.2b, llama3.2-1b, qwen2.5-0.5b, qwen2.5-1.5b, qwen2.5-1.5b-tools, qwen2.5-3b, qwen3-0.6b, qwen3-1.7b, smollm2-1.7b, smollm2-360m, xlam-2-1b-fc-r.

## Thinking-family handling (suite 0.4.1)

Qwen3.5 (0.8b/2b/4b), Granite4.2-3b, SmolLM3-3b and LFM2.5-2.6b emit their answer text into `reasoning_content` and frequently return empty `content` while burning the whole token budget (`finish_reason=length`). The 0.4.0 rig dropped that text. In 0.4.1 it is captured as `replies_reasoning` per trial; judging still honors `content` only, so a model that reasons but never emits is recorded as a failure **with** evidence.

| participant | trials with reasoning | empty-content trials | truncated |
|---|---|---|---|
| lfm2.5-2.6b | 53/53 | 7/53 | 11/53 |
| smollm3-3b | 24/53 | 0/53 | 2/53 |
| granite-4.2-3b | 53/53 | 13/53 | 14/53 |
| qwen3.5-4b | 53/53 | 32/53 | 35/53 |
| qwen3.5-0.8b | 53/53 | 34/53 | 34/53 |
| qwen3.5-2b | 53/53 | 37/53 | 38/53 |

## Not claimed

- **phi-4-mini 64.2% (34/53) is the olympics-qualifier 0.4.1 result.** The historical 100.0/100, 21–22 tok/s, 635 ms TTFT figure was a different, production-path scratch set on llama.cpp b10818 (CPU). Non-comparable; both facts are reported separately, neither folded.
- **qwen3.5-0.8b historical 80.3** refers to a Q8_0 artifact that is no longer present (per prior handoff) and a different set; its olympics 0.4.1 result is 30.2%.
- Legacy 13 participants' backend is **UNKNOWN**, so no CPU-vs-GPU claim is made for them.
- Latencies are contended; no idle or package-size-adjusted comparisons are implied.

## Fixes landed this cycle (suite 0.4.1, harness/records/runtime only — no task prompt or judge changed)

1. **Template-safe transcripts** (`harness.sanitize_messages`): merge consecutive assistant turns, hoist mid-session system turns. Unblocks Gemma3-1b (HTTP 400 on consecutive assistant + mid-system) and the Qwen3.5 family (HTTP 500 on any non-first system message). Content preserved verbatim; transforms recorded per trial.
2. **Reasoning capture** (`runtime.chat`): returns `content`/`reasoning`/`finish_reason`/`truncated`; `[TRUNCATED]` no longer spliced into content. Trials record `replies_reasoning`.
3. **Backend truth** (`records.probe_backend`): header `backend` is OBSERVED, with `backend_probe` (render node, vram_used/total, gpu_busy).
4. **Abort records** (`run.py`): exceptions write a `kind=abort` line with exception, trial count, attempt, probe; retry/index semantics unchanged.

Diagnosis reproductions and verification in `bench/reports/DIAGNOSIS-2026-09-13-stuck-runs.md`; decisions in `.project/DECISIONS.md` (2026-09-13 entry).

## Reproduce

```bash
cd /var/home/rylee/vefr
python3 bench/cli.py many <keys> --stage qualifier   # suites 0.4.1
python3 bench/cli.py report                          # per-participant summaries
```
Canonical run ids live in `bench/runs/index.json` (one per participant; hermes keeps a legacy twin).
