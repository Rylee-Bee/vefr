# DECISIONS — vefr

## 2026-09-25 — munr is a related repo, not a synced one; D5 unreconciled

**Decision.** `Rylee-Bee/munr` shares this codebase's rewritten-history
origin (identical "v0.1 - rumor engine skeleton" first commits) but
evolves independently. Never merge, rebase, or cherry-pick between the
two without an explicit owner decision.

**Rationale.** AGENTS.md carried this note by name (`78fa0f8`), which
broke `test_no_historical_package_names` and turned `main` red. The
engine tree must not name the sibling; this file is outside the audited
roots, so the name lives here and AGENTS.md points here.

**Open.** D5 (2026-09-21, "Retire munr — archive the repo") does not
match reality: on 2026-09-25 munr is active (`wip/norn-journey`, commits
that day), and VEFR-GAME-PLAN §2 casts munr as a later costume-ruleset
pack on vefr. Owner to reconcile; until then treat D5 as UNKNOWN.

**Status.** ACCEPTED (not-synced rule); D5 OPEN.

---

## 2026-09-13 — Olympus restart: Vulkan campaign, harness evidence fixes, legacy backend labeled UNKNOWN

**Decision.** Complete the Small Model Olympics v0.4.1 qualifier campaign
on the intended Vulkan backend: rerun the 5 partials + hermes-1.5b +
phi-4-mini + the 9 never-started with the fixed harness; keep the 13 legacy
"complete" runs preserved with their backend labeled UNKNOWN; never mix
CPU/GPU numbers for the same participant.

**Rationale.**
- The recovery report's "CPU-bound" claim was unreliable: rootless podman
  shows empty `HostConfig.Devices` despite `--device /dev/dri:/dev/dri`
  working, and this llama.cpp build prints no verifiable backend line at
  boot, so I cannot prove the legacy 13's backend retroactively. UNKNOWN is
  the honest label (evidence = OBSERVED/INFERRED/UNKNOWN split).
- Live reproduction proved three harness bugs, not model faults, caused the
  partials: Gemma3 template 400 on consecutive assistant turns (and any
  mid-session system); Qwen3.5 template 500 on any non-first system
  message; the harness dropped `reasoning_content`, distorting every
  thinking-family participant (qwen3.5-0.8b/-2b/-4b, hermes-1.5b,
  granite-4.2-3b).
- The resident llama-qwen-agent (27B, 41k ctx) holds the GPU (16360/16368
  MiB). **Stop nothing:** keep it running for production stability and for
  methodological parity with the legacy 13; record vram/busy as contention
  context on every new run via `backend_probe`.

**Evidence.**
- `bench/reports/DIAGNOSIS-2026-09-13-stuck-runs.md` (three root causes,
  reproduced against live servers, verified fixed).
- `records.probe_backend` now samples the render node inside the container,
  so the recorded `backend` is OBSERVED, not assumed.

**Status.** ACCEPTED.

---

## 2026-09-12 — promote Qwen2.5-1.5B to DEFAULT; demote Granite 4.1 3B to FALLBACK

**Decision.** Promote **Qwen2.5-1.5B-Instruct** to Hermod DEFAULT Brain. Demote **Granite 4.1 3B** to FALLBACK role (retained, not deleted).

**Rationale.**
- Round 5 bounded benchmark: Qwen2.5-1.5B and Granite 4.1 3B are behaviorally equivalent on the current six-task Hermod benchmark (same pass/fail pattern, zero observed variance across 5 repetitions each).
- Qwen2.5-1.5B is approximately 45% smaller (1.08 GB vs 1.95 GB) and ~46% lower latency under benchmark conditions.
- Both models consistently fail Rune Classification — a domain-knowledge gap, not a capability gap.

**Evidence.**
- Round 5: 5 models similar to Granite tested; Qwen2.5-1.5B, Qwen2.5-3B, and Falcon3-3B tied at 83%.
- Round 5.5: 5x repeatability on Qwen2.5-1.5B and Granite 4.1 3B — all runs identical, zero variance.
- Careful language: "Qwen2.5-1.5B and Granite 4.1 3B are behaviorally equivalent on the current six-task Hermod benchmark" — NOT "the models are interchangeable" or equal general capability.

**Reservation.** Six tasks do not establish general model equivalence. The Receipt proves only the bounded benchmark result.

**Status.** ACCEPTED.

---

## 2026-09-21 — Engine-as-game direction: C+A synthesis, bundled brain, model fleet

**Decision.** The engine's next phase is "game-building engine that is
itself a game." Fourteen owner decisions shape the direction:

1. **DD1: Design direction = C+A synthesis.** The creation experience
   IS the game. Workshop rooms (Foyer, Desk, Vault) become alive and
   responsive to what the builder has done.

2. **DD2: Theme = Workshop.** Already complete. Iterate via OpenDesign.

3. **DD3: Export feel = game-quality.** Woven HTML gets a title card
   (world name, tagline, "play" button) so it feels like a game
   within 3 seconds of opening.

4. **D3′: Brain bundled inside the container.** `podman run vefr` =
   fully playable game, no external LLM setup. CPU-only, least
   hardware possible.

5. **D4′: BJ pack license = CC-BY-4.0.**

6. **D5: Retire munr.** Archive the predecessor engine repo.

7. **D6: Fixture placement = A (BJ-pack-supplied).** Rosa/Mateo
   fixtures move into the BJ pack.

8. **D7: BJ canonical home = `code/Rylee-Bee/burrito-journalism`.**

9. **Model fleet locked:** Qwen3-0.6B, Qwen3-1.7B, SmolVLM2-500M,
   bge-m3. Total: ~2.8GB. All Apache-2.0 or compatible.

**Evidence.** Full inventory, product direction, competitive landscape,
model verification, live demo on :8825.

**Status.** ACCEPTED.

---

## 2026-09-12 — adopt Play-Nice as canonical behavioral authority; preserve engine kernels

**Decision.** Pin `play-nice-contracts @ 0cee0652fb6f13c440b1fd9cc5d78fd87cdca8ad`
as the canonical behavioral constitution for this project. AGENTS.md and
AGENT_POLICY.md remain as the local engine-specific kernels — they
describe VEFR's architecture, world-pack shape, and how to work in this
repo; they do not duplicate Play-Nice's behavioral floors.

**Rationale.** VEFR is its own architecture: bring-your-own-brain, worlds
as data, maplab as the validator. Its behavioral floors (honesty,
truthfulness, inspect-before-claim, deterministic-first) come from
Play-Nice. Its architectural rules (pack loader contract, brain-socket
seam, world-vs-engine split) stay local. The adoption makes the upstream
pointer explicit without rewriting the local kernels.

**Evidence.** Library SHA `0cee065`. `contractctl adopt` reports VALID.
The existing AGENTS.md/AGENT_POLICY.md already reference "canonical
contract/index documentation" without naming one; this adoption names
Play-Nice.

**Conflicts.** None. VEFR's local rules and Play-Nice are layered
(architectural vs behavioral), not opposed.

**Status.** ACCEPTED.

---

## 2026-09-12 — select Granite 4.1 3B as Hermod Default Brain

**Decision.** After 3 rounds of benchmarking (11 models, 8 tested, 3 finalists),
select **Granite 4.1 3B** as the Hermod Default Brain.

**Rationale.**
- Highest combined semantic accuracy (92%) and protocol compliance (97%)
- Perfect rune classification (100% across 3 runs)
- Strong Hermod/Steward task performance (3/4 tasks stable)
- Only ~0.8s slower than Qwen3.5-2B
- Only ~670 MB larger than Qwen3.5-2B
- Better fit for an EA whose job is to reduce correction burden

**Evidence.**
- Round 1: 6 models tested, Qwen3.5-2B led with 8/8
- Round 2: 8 models tested, Granite emerged as challenger with 87.5%/100%
- Round 3: 3 finalists, 3 repetitions each — Granite won on semantic + protocol

**Alternatives considered.**
- Qwen3.5-2B: Lighter (1.28 GB) but lower semantic accuracy (89%)
- Qwen3.5-4B: Same accuracy as Granite but larger (2.74 GB) and slower (12.9s)

**Conflicts.** None. The data supports this choice.

**Status.** ACCEPTED.

---

## 2026-09-12 — retain Qwen3.5-2B as lightweight fallback

**Decision.** Retain Qwen3.5-2B as LIGHTWEIGHT FALLBACK, not as default.

**Rationale.** Smaller footprint (1.28 GB) and faster inference (6.3s) make it
useful for degraded-resource mode or emergency fallback. Its 89% semantic
accuracy is adequate for routine work.

**Evidence.** Round 3 testing showed stable performance across 3 repetitions.

**Status.** ACCEPTED.

---

## 2026-09-12 — Qwen3.5-4B optional, not in normal routing

**Decision.** Qwen3.5-4B is available for experimentation but not in normal routing.

**Rationale.** At 2.74 GB and 12.9s latency, its perfect Hermod task performance
does not justify the resource cost compared to Granite (1.95 GB, 7.1s, 92%).

**Evidence.** Round 3 showed perfect Hermod scores but at 2x the size/latency.

**Status.** ACCEPTED.

---

## 2026-09-12 — do not promote benchmark success to authority

**Decision.** Granite's 92% semantic score does NOT grant it world-state authority,
policy authority, mutation authority, or final acceptance authority.

**Rationale.** Benchmark success is evidence of capability, not a grant of power.
VEFR's architecture requires: model proposes → VEFR validates → policy decides.

**Evidence.** Play-Nice onboarding contract, VEFR architectural principles.

**Status.** ACCEPTED.

---

## 2026-09-12 — verification remains mandatory

**Decision.** All Granite/Hermod outputs remain subject to verification,
especially escalation judgment (33% unstable) and rune classification.

**Rationale.** 92% accuracy means 8% error rate. For consequential decisions,
verification is the safety net.

**Evidence.** Round 3 variance analysis showed instability on ambiguous cases.

**Status.** ACCEPTED.