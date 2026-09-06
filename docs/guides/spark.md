# Spark - VEFR's resident small brain

Spark is VEFR's resident intelligence: a small local model that is
always awake, handles the cheap and common work quickly, and hands
anything bigger to K2. This guide is the complete operating record -
what was selected and why, how the service runs, how to switch
profiles, and how to re-prove all of it.

## The decision (benchmark, 2026-09-06)

A 16-model-quant benchmark on the Bazzite box (Ryzen 7 7800X3D,
CPU-only, llama.cpp b10818, 10-test VEFR functional suite with strict
JSON-schema) settled the model selection. Raw numbers live on the
benchmark host at `~/llama-server/vefr-spark/` (REPORT.md + raw.jsonl
per model); the conclusions live here.

| Profile | Model | File (GB) | Resident RAM | Gen tok/s | TTFT | VEFR score |
|---|---|---|---|---|---|---|
| `spark-quality` (default) | Phi-4-mini-instruct Q4_K_M | 2.49 | ~1.9 GiB | ~21 | ~635 ms | 100/100 |
| `spark-tiny` | Qwen3.5-0.8B Q8_0 | 0.81 | ~1.05 GiB | ~58-62 | ~231 ms | 80.3/100 |

Keep the two size comparisons distinct: Phi's **resident memory** is
about 1.8x Qwen's (1.9 GiB vs 1.05 GiB); the **model file** itself is
about 3x larger (2.49 GB vs 0.81 GB).

Two memory numbers, two environments - both correct, do not overwrite:

- **benchmark resident measurement**: ~1.9 GiB (podman stats at ctx
  4096, benchmark harness, 2026-09-06)
- **production observed steady state**: ~2.46 GB (quadlet service at
  ctx 8192 under systemd, after the reboot test, 2026-09-06)

The production figure runs slightly higher (8K context KV + grammar/
state buffers); neither number is wrong - they are different stages.

Why Phi won the default slot: the only 100/100 (perfect JSON, state
edits, continuity, creativity, hallucination resistance, escalation
judgment), in-voice dialogue, MIT license, and reading-speed
generation on CPU. Why Qwen 0.8B stays: every reliability-critical
test still passes at ~1 GiB resident - it loses only dialogue
creativity - and it is the fastest model measured (58+ tok/s, 231 ms
TTFT). Why nothing larger is resident: 3.4-3.8B reaches the reliability
ceiling (Granite-4.0-Micro Q8 96.4, Phi 100) at 2-4x the RAM while
staying slower than the player's patience for heavy work, and heavy
work is exactly what K2 (36B-A4B, ~15 tok/s) is already resident for.

The capability cliff, measured: 0.3B = toy (47.4, invents facts);
sub-1B at Q8 = viable-thin; ~2B = comfortable; 3.8B = ceiling. Below
Q8 on sub-1B models, state-edit reliability collapses (Qwen3.5-0.8B
Q4: 65.8 with corrupted edits) - **never quant sub-1B below Q8_0**.

## Model artifacts (pinned)

| Profile | Source repo | File | sha256 (first 12) | License |
|---|---|---|---|---|
| quality | `unsloth/Phi-4-mini-instruct-GGUF` | `Phi-4-mini-instruct-Q4_K_M.gguf` | `88c002299140` | MIT |
| tiny | `unsloth/Qwen3.5-0.8B-GGUF` | `Qwen3.5-0.8B-Q8_0.gguf` | `0ad885ffd4bb` | Apache-2.0 |

Full hashes and sizes live in `src/vefr/spark.py` (`PROFILES`) and are
verified on every install. GGUFs are never committed to the repo; they
live on the deploy host at `~/spark/models/`.

## The service (transcode appliance)

Spark runs as a **compose service on the transcode host** (192.168.2.141)
as of 2026-09-06 — deliberately host-segregated from Bazzite so the
game's core AI survives Bazzite being off. The full appliance doc lives
in the homelab repo: `docs/spark-appliance.md` (compose service,
rebuild steps, benchmarks, isolation proofs).

- Compose: `homelab-transcode` project, service `spark`
  (compose/transcode.yml in rylee/homelab; deploy via
  `scripts/deploy-transcode.sh`)
- Model: `/opt/spark/models/Phi-4-mini-instruct-Q4_K_M.gguf`
  (sha256 verified on copy; bazzite keeps a fallback copy at
  `~/spark/models/`)
- Image: `ghcr.io/ggml-org/llama.cpp:server`, pinned by digest
- Flags: `-ngl 0 -c 8192 -t 4 --jinja` - CPU-only, 4 threads (the
  transcode box runs a 4C/8T i7-6770HQ), 8K context, native chat
  template, `reasoning_effort: low` via env var
- Bound to `0.0.0.0:8082` on the transcode LAN (no Traefik route on
  purpose - the engine reaches it over the LAN; gatus probes it direct)
- Measured there: 9.6 tok/s, TTFT 0.1-0.25 s short prompts, ~32 tok/s
  prefill (Skylake CPU - long-prompt prefill is the host's weak spot;
  heavier work escalates to K2)
- Logs: `ssh rylee@192.168.2.141 'docker logs spark'`
- Restart: `ssh rylee@192.168.2.141 'docker restart spark'`

VEFR talks to Spark through one seam: `VEFR_SPARK_URL`
(= `http://192.168.2.141:8082`, set in the engine's quadlet
environment on bazzite). The escalation target is `VEFR_LLAMACPP_URL`
(K2, same host as the engine), never modified by Spark work.

## The context contract

The GGUF knows nothing about VEFR. Context is generated, not curated:

| Layer | Source | Where |
|---|---|---|
| 1 core contract | `src/vefr/spark-contract.md` (versioned, shipped) | `spark.core_contract()` |
| 2 task contract | per-task instructions + output schema + token budget | `spark.TASK_CONTRACTS` |
| 3 world | the loaded pack (world.json + capped logbok) | `spark.world_context()` |
| 4 character | the speaker's voice file in the pack | `spark.character_context()` |
| 5 runtime | the minimum state, supplied per request | `spark.runtime_context()` |
| 6 output | strict json_schema through llama.cpp grammar | `response_format` |

The model proposes; VEFR validates (`state_edit_check` for state
mutations: exactly the requested change or fail closed); VEFR applies.
Invalid proposals are discarded, never guessed around. Debug the
generated context with `GET /api/spark/inspect?task=...&user=...`
(read-only) - it shows profile, sections, token estimate, and the
exact messages, so a Spark failure can be attributed to the model or
to the context.

## Escalation architecture

Two gates, cheap one first: a deterministic keyword pre-filter
(`spark.needs_escalation`) and the model's own judgment
(`POST /api/spark/escalate` - the benchmark's fixed probes, scored
against ground truth). LOCAL work runs on Spark; ESCALATE work routes
to the K2 seam. When uncertain, escalate - the benchmark proved even
the tiny model can be trusted to know what is not its job, and a
100/100 escalation score is the load-bearing number, not the prose.

## Thinking-mode invariant

Thinking-capable models may ship with thinking enabled by default,
which silently consumes VEFR's output budget and changes functional
results (2026-09-06: Qwen3.5-4B scored 0.0 until disabled). The
profile table carries each model's `chat_template_kwargs` and the
client always sends them; Phi needs nothing, Qwen3.5 needs
`{"enable_thinking": false}`. **When adding or swapping a profile,
set the thinking behavior explicitly and re-run the smoke test** -
never trust the model's default.

## Revalidation

**Real path required.** The deployment pass caught two integration
bugs (an unimported module in the health probe, a wrong HTTP verb)
that the fully-passing mocked/unit suite never touched - the live-path
probes found them within one run. **Any future model swap, runtime
bump, or context change must pass the real Spark smoke/integration
path below, not merely unit tests.**

```sh
uv run ratatoskr spark status    # model verified? service active? health?
uv run ratatoskr spark smoke     # 4 functional probes through the live engine
uv run --group test pytest tests/test_spark.py -q   # the subsystem contract
```

The smoke probes are health, NPC JSON (schema + key set), state-edit
preservation (target changed, rest byte-equal), and escalation
judgment (benchmark probes vs ground truth). A full re-benchmark uses
the harness in `~/llama-server/vefr-spark/scripts/` on the deploy host.

## Rollback

Stop the `spark` compose service on the transcode host
(`ssh rylee@192.168.2.141 'docker compose -p homelab-transcode
-f /opt/compose/transcode.yml stop spark'`): the engine keeps
working exactly as before Spark - every generator path is unchanged
and every Spark route degrades to a graded payload. VEFR_LLAMACPP_URL
(K2) was never modified. The model files in `~/spark/models/` are
plain files; delete at will.
