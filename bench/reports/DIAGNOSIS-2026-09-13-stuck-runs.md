# Diagnosis: stuck/partial qualifier runs (2026-09-13)

Suite 0.4.0 rig. Root causes for every partial run are now reproduced and
confirmed against live llama-server containers. All reproduction used the
same canonical flags as `runtime.py` (`--jinja`, `-ngl 999`, `-c 8192`,
`-t 8`, `--device /dev/dri:/dev/dri`, image `server-vulkan` b10920
`eafe15a5e`), but with `podman run` kept alive (no `--rm`) so error bodies
and logs survive.

## Summary

| Participant | Trial at death | Root cause | Status after fix |
|---|---|---|---|
| gemma3-1b | 37/53, aborts at `assist.longrun1` turn 3 | GGUF template raises HTTP 400 on two consecutive assistant turns (`give` follows a generated reply) and on any mid-session system turn | fixed (sanitizer); longrun1 runs to completion |
| granite-4.2-3b | 6/53, aborts at `hermod.tj4` | thinking-model: emits `reasoning_content`, empty `content`, truncates at 512; ~12 tok/s under resident-27B GPU contention makes tool turns brittle | fixed (reasoning captured; abort recorded, no silent drop) |
| qwen3.5-0.8b / -2b / -4b | 48/53, abort at `flex.switch1` | template raises 500 `"System message must be at the beginning."` on the mid-session tool-instruction system turn | fixed (sanitizer); full 5-turn switch session runs |

## Root cause A: template-strict message shapes (gemma3-1b, qwen3.5 family)

Two GGUF chat templates reject conversation shapes this suite routinely
builds, and the server returns the error at request-parse time (no tokens
consumed; instant response):

- Gemma3-1B template (card1, alive 9142):
  `Unable to generate parser for this template ... Conversation roles must
  alternate user/assistant/...` and `Cannot have 2 or more assistant
  messages at the end of the conversation` (HTTP 400) for any consecutive
  assistant turns. `assist.longrun1` appends a generated reply then a
  `give` (precomputed LOG) assistant turn -> consecutive assistant ->
  HTTP 400 -> whole run aborts. Same shape exists in `story.world1`
  (give after generated story).
- Qwen3.5-0.8B/2B/4B template (alive 9141):
  `raise_exception('System message must be at the beginning.')` (HTTP 500,
  Column 32 CallExpression) on any system message that is not the first
  message. `flex.switch1` carries the tool-instruction system block at
  session position 3 (after two user turns) -> HTTP 500 -> abort at
  turn 4/5, 48/53 recorded.

Both are template acceptance issues, not task failures. All contents in the
transcript were already canonical user/give/system text.

### Fix

`harness.sanitize_messages()` (bench/olympics/harness.py): before every
chat, coalesce consecutive assistant turns into one assistant message
(content joined `"\n\n"`, order preserved) and fold any non-first system
turn into the leading system message (content preserved verbatim). Judge-
visible surfaces (`replies`, `final_raw`) are untouched; the model sees
every instruction, just at a template-safe position. Each transform is
counted and recorded on the trial (`transforms`).

## Root cause B: reasoning stream hidden by the harness (qwen3.5 family, hermes-1.5b, granite-4.2-3b)

`runtime.chat()` read only `message.content`. Qwen3.5 and Granite 4.2 are
thinking-family models: on this server build the answer text goes to
`message.reasoning_content` (prefix `Thinking Process:` etc.) and
`message.content` comes back empty, frequently with `finish_reason=length`
(they burn the whole 512/768 budget reasoning). The harness then recorded
empty content as an ordinary failure (`[TRUNCATED]`) and threw the
reasoning text away. Evidence captured live: qwen3.5-0.8b 5-turn switch
session returned content `""` with full `reasoning_content` on every turn;
granite tj4 returns `reasoning_content` ("The user asks: ...") plus `""`
content when it truncates.

Consequence: `qwen2.5-hermes-1.5b`'s "complete" run (17/53 pass, 11 empty,
21 no-JSON) is materially distorted by this bug and must be rerun.
`qwen3-1.7b` is only lightly touched (2 empty). The qwen3.5 partials'
48/53 each are reasoning-drop-tainted as well.

### Fix

`runtime.chat()` now returns `content` and `reasoning` (the server's
`reasoning_content`) separately, plus `finish_reason` and `truncated`.
The literal `"\n[TRUNCATED]"` splice into content is gone. Trials record
`replies_reasoning`, `finish_reasons`, `truncated` alongside `replies`.
Judging stays on `content` only — a model that reasons but never emits is
judged a failure, with the reasoning preserved as evidence (the report can
show *why*).

## Root cause C: silent partial-run bookkeeping (granite-4.2-3b)

`run_participant` had no abort record: an exception mid-run left a partial
JSONL with only trials and a stray (sometimes leaked) container, no
`index.json` entry, no reason-on-file. That is why the partials looked
like "stopped at last recorded trial".

### Fix

On exception, the store now appends a `{"kind": "abort", ...}` line with
the exception, trial count, epoch, attempt, and the sampled backend probe.
Retry semantics (2 attempts) and index-on-success are unchanged.

## Backend + contention facts (context for the report)

- Intended engine: llama.cpp `server-vulkan` on the Navi21 (RX 6800XT,
  PCI 1002:73BF). `runtime.py` starts servers with `--device /dev/dri:/dev/dri`,
  `-ngl 999`, image `server-vulkan`; the module docstring states the intent.
- Rootless podman does not list `--device` under `HostConfig.Devices`, so
  the recovery report's "empty Devices => CPU" inference was unreliable.
  The drm nodes ARE present inside the containers (`/dev/dri/card1`,
  `renderD128`), and `gpu_busy_percent` spikes 92-97% during generation ->
  Vulkan compute is engaged (with host-pinned memory when VRAM is short).
- The resident `llama-qwen-agent` (27B IQ4_XS, 41k ctx) has been up 6 days
  and now holds the card at 16360/16368 MiB. Every olympics run happened
  (and happens) under this contention. Granite-4.2-3b measured ~12 tok/s
  (vs ~124 tok/s for Qwen3.5-0.8B under the same load).
- `backend` is no longer hard-coded: `records.probe_backend` samples the
  render node inside the container + host amdgpu counters, and the run
  header carries `backend` (OBSERVED) + `backend_probe` (render node,
  vram_used/total MiB, gpu_busy). Legacy 0.4.0 headers state `backend:
  vulkan` with no evidence -> report marks legacy backend UNKNOWN.

## Decision (recorded)

Run the campaign with the intended Vulkan backend, keep the resident agent
running (production stability plus methodological parity with the legacy
13), never mix CPU/GPU numbers for the same participant, and label the
rebuilt evidence OBSERVED vs the legacy UNKNOWN.

## Verification performed

- gemma3-1b `assist.longrun1`: 3/3 turns OK after sanitize (was 400).
- qwen3.5-0.8b `flex.switch1`: 5/5 turns OK after sanitize (was 500),
  reasoning captured.
- granite-4.2-3b tj4: completes, reasoning captured.
- `bench/olympics`: 5 edited modules `py_compile` clean; ruff reports only
  pre-existing findings (validators.py E702/E741, runtime.py F841,
  harness.py F401).