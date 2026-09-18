# Research log — Small Model Olympics

Data-only literature + community findings. Claims here are **evidence to
verify in our own runs**, never truth claimed for this rig. Each entry:
source, date, claim, evidence-type (community report / vendor benchmark /
personal post / other), relevance, verified-in-our-rig (unfilled until a run
produces the number).

## 2026-02-14 — r/LocalLLaMA "Agent Score" small-model tool report
- source: r/LocalLLaMA Round 3 (the [2026-02-14 report](https://www.reddit.com/r/LocalLLaMA/comments/1ip5hom/8_small_coderiented_language_models_local_agent/)), 10 models <=3B+LlamaScope 3B, standard JSON function-calling, 1-3 posts sampled/model.
- claims:
  - qwen3:1.7b Agent Score **0.960** — only model to call a second function with no tool output contamination; reached the "do nothing but reply" task without hallucinated work. Slowest: ~10,665 ms/prompt.
  - lfm2.5:1.2b Agent Score **0.920** at ~1,567 ms/prompt — "by far the best speed/quality ratio" of the group.
  - qwen2.5:1.5b: simple tool routing solved at 1.5B on CPU; scored **above its own 3B sibling**.
  - LlamaScope: "better at product rules than all others, with a simple request+tool format" (agent-specific).
- evidence-type: community report (one author, small N, self-reported timings = iMac 24" metrics).
- relevance: ranking prior, speed model, "smart is not enough" (3B sibling underperform).
- verified-in-our-rig: TODO.

## 2026-02 — the famous benchmark-parser failure (Round 2 lesson)
- source: r/LocalLLaMA Round 2 + follow-up thread; the same author earlier scored
  LFM2.5-1.2B **0.640** because its EmFunc/simple `name(arg=val)` bracket syntax
  was mis-scored, then **0.860-0.880** after a fallback parser accepted bracket
  notation — jumping it from rank 13 to tied #1.
- claims: a mis-parser produces model-false negatives; dialect leniency must be a
  first-class part of the benchmark, not a fix-up.
- evidence-type: community report, self-corrected.
- relevance: the single strongest argument for our raw/parsed/normalized rule and
  for a bracket/XML/bare-JSON fallback parser. Our parser fixture set includes
  `famous-bracket` (deliberate).
- verified-in-our-rig: `bench/tests/test_parse.py` famous-lfm-case; **PASS** (2026-09-12).

## 2025-12 — distill-labs $10K small-model "bake-off" run
- source: distill-labs blog
  [we benchmarked 1,500+ fine-tunes of a 4B model](https://www.reddit.com/r/LocalLLaMA/comments/1pi8z74/distilllabs_we_benchmarked_1500_finetunes_of_a_4b/) + R2R.
- claims: Qwen3-4B-Instruct-2507 best fine-tuned 4B, avg rank 2.25 across runs,
  beats its GPT-OSS-120B teacher on 7/8 scores incl. +19 SQuAD points; ordinary
  "just train a bit" fine-tunes can outperform the teacher family in ~$100.
- evidence-type: commercial-ish blog, their own eval harness (R2RBench); treat
  as directional.
- relevance: 4B is a genuinely competent tier; middleweight floor for our suite.

## 2026-02 — BFCL v1 small-model numbers
- source: BFCL leaderboard (Berkeley Function-Calling Leaderboard), checked while
  reviewing theta-labs' small-tool-capabilities fork.
- claims: xLAM-2-1b-fc-r **78.94%** overall BFCL v1 — the only <2B model on the
  board, beating GPT-3.5-Turbo (76.2%); Gemma-3-1b-it only **7.17%** on BFCL v4
  (~rank 106).
- evidence-type: vendor + third-party leaderboards (DSP, API-native eval).
- relevance: specialist FC derivatives actually exist at 1B; a general 1B model
  can be near-broken at FC. Distinguishes a capability from a base-model grade.
- verified-in-our-rig: xLAM-2-1b-fc-r + Gemma-3-1b both registered as participants; TODO numbers.

## 2026 — BFCL eval-method criticism (why we prompt-render tools)
- source: [github.com/brilee/python_go_parser/issues/50#issuecomment-...](https://github.com/brilee/python_go_parser/issues/50#issuecomment-2552912860) / the same author's posts on benchmark harnesses passing tools as a concatenated prompt blob; also issue
  [#861](https://github.com/ShishirPatil/gorilla/issues/861) in the BFCL repo
  where tools are concatenated into the user prompt rather than sent as native
  `tool` message fields.
- claims: native-API tool fields are a HARNESS feature, not a model feature; a
  model that answers well to prompt-rendered tools is being judged on real
  capability, while one that only works with native fields is being judged on
  API sugar.
- evidence-type: maintainer issue discussion + author posts.
- relevance: our rig prompt-renders tools into the system prompt (spreader
  `<|tool_call|>` syntax), deliberately skipping OpenAI-style native tool fields.

## 2026-09 — model family lineups on disk (GGUF snapshots)
- source: local `~/llama-server/models/bench/` + official HF hub repos
  (lm-kit, ibm-granite, LiquidAI, HuggingFaceTB, Salesforce, ministral/LMstudio).
- claims/notes:
  - Qwen3.5 (0.8B/2B/4B) exists; several Distil-0.6B variants on v3.5ng lineage.
  - Granite-4.2-3B: official GGUF `ibm-granite/granite-4.2-3b-GGUF` (Q4_K_M on disk).
  - Ministral-3-3B: official GGUF incl. `[TOOL_CALLS]` template.
  - Qwen3 (0.6B/1.7B) + Qwen2.5 (0.5B/1.5B/3B) official GGUFs on disk.
  - SmolLM2 (360M/1.7B), SmolLM3-3B GGUFs on disk.
  - LFM2.5-1.2B official GGUF `LiquidAI/LFM2.5-1.2B-Instruct-GGUF`.
  - xLAM-2-1b-fc-r official GGUF `Salesforce/xLAM-2-1b-fc-r-gguf`.
- evidence-type: vendor artifacts.
- relevance: our 27-participant roster was drawn from what actually fits on disk
  (Q4/Q8, <=4B) and what is plausibly general-purpose.

## Our rig decisions traced to above
- prompt-render tools (BFCL #861).
- parser fixtures per BFCL criticism + the Round-2 LFM lesson.
- xLAM/Gemma registered as separate participants so base vs derivative confusion
  is recorded, not pre-judged.
- no private-domain lore tests; only the pack-neutral VEFR shape (bridge/tank).

## Reminder
- All claims above are TODO until verified by a run in this repo. Nothing here
  is assumed when writing conclusions.