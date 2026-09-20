# VEFR Small-Model Benchmark — Recovery Report (2026-09-13)

Host: bazzite (`rylee-bazzite`, 192.168.2.76). Scope: verify the benchmark
environment, prior results, model artifacts, runtime configuration, and
production wiring survived the reboot, without starting a full new suite.

**Summary:** environment is verified live and intact. No full new suite was
started. A benchmark session was already mid-flight on takeover; it finished
with 2 of 5 targets clean and 3 partial. 14 of 27 participant qualifiers
remain. One leaked container cleaned.

---

## 1. Repositories

| Repo | Branch | HEAD | Upstream (origin/main) | State |
|---|---|---|---|---|
| `/var/home/rylee/vefr` | main | `c7a1561` | `294ebce…` | ahead 1 (unpushed), dirty: 5 modified `.project/*` + untracked `bench/`, `experiments/`, `.project/*` |
| `/var/home/rylee/projects/homelab` | main | `53169d2` | `53169d2` | clean, in sync |
| `/var/home/rylee/munr` | main | `f8bf58e…` | — | dirty; unrelated personal project |

- The active harness `vefr/bench/` (Small Model Olympics) is **untracked WIP**.
- `~/llama-server/` is a loose runtime dir (not a git repo) holding the
  historical spark benchmark.
- Nothing was staged, committed, reset, or deleted during recovery.

## 2. Historical benchmark truth (evidence-backed, 2026-09-06)

Authoritative record: `~/llama-server/vefr-spark/REPORT.md` plus
`results/<tag>/score.json + raw.jsonl`, `results/bench-*.md`, `logs/`.

| Model | Score | Gen tok/s | TTFT | RAM | Evidence |
|---|---|---|---|---|---|
| Phi-4-mini-instruct 3.84B Q4_K_M | **100.0/100** | 21–22 (tg 22.21 @ t8) | 635 ms | ~1.9 GiB (VmHWM 4.7G @16K) | `results/phi4mini-q4/{score.json,raw.jsonl}`, `bench-phi4mini-q4.md` (build `4d9176092 (10818)`), `REPORT.md` |
| Phi-4-mini **production path** | **96.1/100** | — | — | — | `results/phi4mini-prod/{score.json,raw.jsonl}` (ctx 4096) |
| Qwen3.5-0.8B Q8_0 | **80.3/100** (T4 hard fail) | 58–62 | ~231 ms | 1.05 GiB idle / 1.06 GiB @8K | `results/qwen35-08b-q8/{score.json,raw.jsonl}`, `REPORT.md` |

Conditions: CPU-only, llama.cpp **b10818** (`4d9176092`), Ryzen 7800X3D
8C/8T/61 GiB, `-t 8`, `--jinja`; 10-test VEFR functional suite, strict
JSON-schema. Numbers above are supported by files (not chat memory).

**UNVERIFIED / corrected handoff items:**
- Handoff "production loopback 127.0.0.1:8082 Spark" — **outdated**. Live truth:
  bazzite `:8082` is the bge-m3 embedder (`llama-embed`); production Spark is
  remote `192.168.2.141:8082` (vefr quadlet `VEFR_SPARK_URL`).
- Handoff "~21 tok/s" — evidence says 21–22 (22.2 table / 22.21 bench).
- Handoff K2 "early-boot segfault/backoff" — **not reproduced** on this boot;
  K2 simply is not running (intentional rollback state).

## 3. Production wiring

| Endpoint | What | State | Confirmed |
|---|---|---|---|
| `192.168.2.141:8082` | Spark prod, `phi-4-mini-instruct-q4` | healthy | `/v1/models` returns alias; canonical: homelab `compose/transcode.yml`, `docs/spark-appliance.md`; pinned digest run b10818; model SHA `88c00229…` |
| `127.0.0.1:8081` | `llama-qwen-agent` (Qwen3.8-27B IQ4_XS, ROCm) | up 5d, healthy | `/v1/models`; quadlet `qwen-agent.container`; ROCm image `localhost/llama.cpp:server-rocm-k2` |
| `127.0.0.1:8082` | `llama-embed` (bge-m3, CPU) | up 5d, healthy | `/v1/models`; quadlet `llama-embed.container` |
| `127.0.0.1:8083/8087/8091` | hermod stack (qwen2.5-1.5b, granite fallback, granite-ref) | up ~5h | podman ps |
| `127.0.0.1:8820` | `vefr.service` (VEFR engine quadlet) | **inactive/dead** | `systemctl --user status vefr` — gap |
| K2 `k2horizon.service` | K2-Horizon-36B-A4B (ROCm, 8081 backstop) | inactive (intentional) | quadlet has no `[Install]`; last stop 2026-09-07T01:16Z bakeoff; `~/llama-server/bakeoff-k2-pause.log`; `RACE-PREVENTION.md` contract; `/dev/kfd`+`renderD128` present |

## 4. Runtime / harness

- Suite: Small Model Olympics **v0.4.0** (`bench/olympics/`), stdlib-only
  harness driving llama.cpp llama-server in podman.
- Image: `ghcr.io/ggml-org/llama.cpp:server-vulkan` = revision
  `eafe15a5e3d8…`, build **b10920** (2026-09-12). **Different build** from the
  historical b10818 — cross-report comparisons must account for this.
- Canonical cmdline (`bench/olympics/runtime.py`):
  `podman run -d --rm -p PORT:8080 -v <MODELS_DIR>:/models:Z [--device /dev/dri:/dev/dri] <IMAGE> --model /models/<file> --alias <key> --host 0.0.0.0 --port 8080 -c 8192 -t 8 -ngl 999 --jinja`.
  Env overrides: `OLY_IMAGE`, `OLY_MODELS_DIR`, `OLY_CTX`, `OLY_THREADS`,
  `OLY_NGPU`, `OLY_SERVE_PORT_BASE`.
- **Backend caveat:** run metadata hardcodes `backend=vulkan`, but live
  containers have empty `HostConfig.Devices` (no `/dev/dri`) and no GPU-pool
  load lines → runs are effectively **CPU-bound while labeled vulkan**.

## 5. Model availability

- All 27 registered participants have artifacts present in
  `~/llama-server/models/bench/`.
- `Phi-4-mini-Q4_K_M.gguf` (2,491,874,272 B) SHA-256 `88c00229914083cd…`
  **exactly matches** the production pin for `Phi-4-mini-instruct-Q4_K_M.gguf`
  (filename renamed; artifact identical).
- **`Qwen3.5-0.8B-Q8_0.gguf`** (spark-tiny, per `src/vefr/spark.py`
  MODEL_PROFILES and REPORT) is **NOT present on this box**. Not redownloaded
  (needs authorization). The olympics `qwen3.5-0.8b` participant runs the
  Q4_K_M file instead.

## 6. Evidence store & safety

- Historical evidence: `~/llama-server/vefr-spark/results/<tag>/{score.json,raw.jsonl}`,
  `bench-*.md`, `logs/`; vefr `.project/*` results. All intact.
- Active harness store: `vefr/bench/runs/<TS>__<stage>__<key>__<6hex>.jsonl`
  (append-only per `records.py`; uuid suffix → no overwrite) + `index.json`.
- Smoke tests (all exit 0, wrote nothing): `cli.py --help`,
  `cli.py list` (27/27 ok), `cli.py campaign` (offline scoring),
  `cli.py parsertest`, `curl :9003/health`.

## 7. Current run inventory (qualifier stage)

| key | status | runs |
|---|---|---|
| granite-4.1-3b | complete (53/53) | 1 |
| lfm2.5-1.2b | complete | 1 |
| llama3.2-1b | complete | 1 |
| qwen2.5-0.5b | complete | 1 |
| qwen2.5-1.5b | complete | 1 |
| qwen2.5-1.5b-tools | complete | 1 |
| qwen2.5-3b | complete | 1 |
| qwen2.5-hermes-1.5b | complete | 2 |
| qwen3-0.6b | complete | 1 |
| qwen3-1.7b | complete | 1 |
| smollm2-1.7b | complete | 1 |
| smollm2-360m | complete | 1 |
| xlam-2-1b-fc-r | complete | 1 |
| gemma3-1b | **part (37/53)** | 3 |
| granite-4.2-3b | **part (6/53)** | 1 |
| qwen3.5-0.8b | **part (48/53)** | 2 |
| qwen3.5-2b | **part (48/53)** | 3 |
| qwen3.5-4b | **part (48/53)** | 1 |
| falcon3-3b | none | 0 |
| gemma3-4b | none | 0 |
| lfm2.5-2.6b | none | 0 |
| llama3.2-3b | none | 0 |
| ministral-3-3b | none | 0 |
| phi-3.5-mini | none | 0 |
| phi-4-mini | none | 0 |
| smollm3-3b | none | 0 |
| stablelm-zephyr-3b | none | 0 |

**13 complete · 5 partial · 9 none.** Remaining to finish all 27: **14
qualifier runs** (~740 trials; est. 2.5–5 h serialized on CPU).

## 8. Blocked-run diagnosis (partial qualifiers)

Partial runs abort at a **deterministic per-model task** across every attempt
(no error trials recorded; suite expects 53):

- qwen3.5 family (0.8b/2b/4b): stop after `story.style0` (48/53) — every attempt
- gemma3-1b: stop after `assist.reconcile1` (37/53) — every attempt (3×)
- granite-4.2-3b: stop after `hermod.tj3` (6/53) — process likely killed;
  leaked container `olympics-granite-4.2-3b` (port 9018) was cleaned post-recovery.

Hypothesis: llama-server b10920 dies/times-out (client 300 s) on one specific
prompt; retries reproduce it. Root cause **not yet confirmed** (server logs are
lost on container remove). Recommendation: reproduce one blocked task against a
kept-alive server before rerunning, or the reruns abort again.

## 9. Missing pieces / decisions

1. `Qwen3.5-0.8B-Q8_0.gguf` absent → redownload requires authorization.
2. `vefr.service` (engine, 8820) not running.
3. Harness `bench/` untracked → any final retention/commit is a repo-policy decision.
4. Backend intent: harness records vulkan but runs are CPU → decide GPU wiring
   (`--device /dev/dri`) before claiming GPU numbers.

## 10. Safe next commands

```
# 1. Resolve blocked runs: keep server alive and reproduce the failing task
cd ~/vefr && IDS=story.style0 && python3 bench/cli.py run qwen3.5-0.8b qualifier --ids $IDS

# 2. After unblocking, run the never-started models
cd ~/vefr && python3 bench/cli.py many falcon3-3b gemma3-4b lfm2.5-2.6b llama3.2-3b \
  ministral-3-3b phi-3.5-mini phi-4-mini smollm3-3b stablelm-zephyr-3b --stage qualifier

# 3. Then rerun the 5 partial keys (qwen3.5-0.8b gemma3-1b qwen3.5-2b qwen3.5-4b granite-4.2-3b)
cd ~/vefr && python3 bench/cli.py many qwen3.5-0.8b gemma3-1b qwen3.5-2b qwen3.5-4b granite-4.2-3b --stage qualifier

# 4. Report
cd ~/vefr && python3 bench/cli.py report
```

Backend-disclosure rule for any future claim: state image+build (`server-vulkan`
b10920 vs historical `server` b10818), backend actually engaged (CPU here), ctx
8192, t 8, and compare only against same-config runs.