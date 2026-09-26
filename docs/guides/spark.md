# Spark - VEFR's resident small brain

Spark is VEFR's resident intelligence: a small local model that is
always awake, handles the cheap and common work quickly, and hands
anything bigger to K2. This guide is the complete operating record -
what was selected and why, how the service runs, how to switch
profiles, and how to re-prove all of it.

## The decision (benchmark)

A 16-model-quant benchmark settled the model selection. Raw numbers
live on the benchmark host (under the deploy operator's chosen
location; see the deploy host's `~/llama-server/vefr-spark/` README
for the path the operator chose at install time); the conclusions
live here.

| Profile | Model | File (GB) | Resident RAM | Gen tok/s | TTFT | VEFR score |
|---|---|---|---|---|---|---|
| `spark-quality` (default) | Phi-4-mini-instruct Q4_K_M | 2.49 | ~1.9 GiB | ~21 | ~635 ms | 100/100 |
| `spark-tiny` | Qwen3.5-0.8B Q8_0 | 0.81 | ~1.05 GiB | ~58-62 | ~231 ms | 80.3/100 |

Keep the two size comparisons distinct: Phi's **resident memory** is
about 1.8x Qwen's (1.9 GiB vs 1.05 GiB); the **model file** itself is
about 3x larger (2.49 GB vs 0.81 GB).

Two memory numbers, two environments - both correct, do not overwrite:

- **benchmark resident measurement**: ~1.9 GiB (podman stats at ctx
  4096, benchmark harness)
- **production observed steady state**: ~2.46 GB (quadlet service at
  ctx 8192 under systemd, after a reboot)

The production figure runs slightly higher (8K context KV + grammar/
state buffers); neither number is wrong - they are different stages.

Why Phi won the default slot: the only 100/100 (perfect JSON, state
edits, continuity, creativity, hallucination resistance, escalation
judgment), in-voice dialogue, MIT license, and reading-speed
generation on CPU. Why Qwen 0.8B stays: every reliability-critical
test still passes at ~1 GiB resident - it loses only dialogue
creativity - and it is the fastest model measured (58+ tok/s, 231 ms
TTFT). Why nothing larger is resident: 3.4-3.8B reaches the reliability
ceiling at 2-4x the RAM while staying slower than the player's
patience for heavy work, and heavy work is exactly what K2 (36B-A4B,
~15 tok/s) is already resident for.

The capability cliff, measured: 0.3B = toy (invents facts);
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
live on the deploy host at the path the operator chose at install time
(default under `~/spark/models/`).

## The service

Spark runs as a **compose service on the deploy host**, deliberately
host-segregated from the engine host so the game's core AI survives
the engine host being off. The full appliance doc is owned by the
deploy operator and lives outside this repository (the engine reaches
Spark over HTTP via `VEFR_SPARK_URL`, not by SSH).

- Project: `homelab-spark` (or whatever the operator named it at
  install time); service `spark`
- Model: `${SPARK_MODELS_DIR}/Phi-4-mini-instruct-Q4_K_M.gguf`
  (sha256 verified on copy; the file lives on the Spark host only)
- Image: `ghcr.io/ggml-org/llama.cpp:server`, pinned by digest
- Flags: `-ngl 0 -c 8192 -t 4 --jinja` - CPU-only, 4 threads, 8K
  context, native chat template, `reasoning_effort: low` via env var
- Bound to `${SPARK_BIND}:${SPARK_PORT}` (no reverse-proxy route on
  purpose - the engine reaches it directly over the LAN)
- Logs: `docker logs spark` (or `journalctl` if running under systemd)
- Restart: `docker restart spark` (or `systemctl --user restart spark`)

VEFR talks to Spark through one seam: `VEFR_SPARK_URL` (set in the
engine's quadlet environment). The escalation target is
`VEFR_LLAMACPP_URL` (K2, same host as the engine), never modified by
Spark work.

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
results. The profile table carries each model's `chat_template_kwargs`
and the client always sends them; Phi needs nothing, Qwen3.5 needs
`{"enable_thinking": false}`. **When adding or swapping a profile,
set the thinking behavior explicitly and re-run the smoke test** -
never trust the model's default.

## Revalidation

**Real path required.** A prior deployment pass caught two integration
bugs (an unimported module in the health probe, a wrong HTTP verb)
that the fully-passing mocked/unit suite never touched - the live-path
probes found them within one run. **Any future model swap, runtime
bump, or context change must pass the real Spark smoke/integration
path below, not merely unit tests.**

`ratatoskr spark status` checks where Spark actually is. When
`VEFR_SPARK_URL` points at another machine (the appliance setup above),
it asks the server which GGUF it serves (llama.cpp `/props`, `model_path`)
and compares it to the profile's pinned file, and the health probe is
the service's proof of life. On a local Spark it verifies the model file
(size + sha256) and the `spark` user service directly.

```sh
VEFR_SPARK_URL=<spark url> uv run ratatoskr spark status    # model served? health?
uv run ratatoskr spark smoke     # 4 functional probes through the live engine
uv run --group test pytest tests/test_spark.py -q   # the subsystem contract
```

The smoke probes are health, NPC JSON (schema + key set), state-edit
preservation (target changed, rest byte-equal), and escalation
judgment (benchmark probes vs ground truth).

## From the command line (scripts, agents, residents)

`ratatoskr spark task` runs one Spark task through the same checked
doorway the studio uses: the context layers, the task's JSON schema
(grammar-locked by llama.cpp), validation and one retry, fail-closed.

```sh
uv run ratatoskr spark task dialogue "Two lines at dusk." --speaker keeper
uv run ratatoskr spark task npc -f request.txt --json      # the envelope
echo "A shy apprentice" | uv run ratatoskr spark task npc  # stdin works
uv run ratatoskr spark task lore "..." --inspect           # what WOULD be sent; no model call
```

Plain mode prints the result on stdout and one meta line on stderr, so
it pipes. With `--json`, `ratatoskr skipa`, `ratatoskr spark status`,
`ratatoskr spark task` and `norns doctor` print the estate's stable
envelope, `{ok, status, changed, warnings, actions, data}`, with the
same exit codes as the Worlds CLI: 0 ok, 1 error (for a task: the
output failed its schema, nothing to apply), 2 bad arguments,
3 unavailable (Spark or the live stack can't be reached), 4 needs a
person's approval. The `profile_model` field names the profile's
model; a `--spark-url` pointing elsewhere may serve a different one.

## Rollback

Stop the `spark` compose service (`docker compose stop spark`, or
`systemctl --user stop spark`): the engine keeps working exactly as
before Spark - every generator path is unchanged and every Spark route
degrades to a graded payload. `VEFR_LLAMACPP_URL` (K2) is never
modified. The model files in `~/spark/models/` are plain files;
delete at will.