# DECISIONS — vefr

## 2026-10-03 — a hue used for text carries a contrast floor; a fill does not

**Decision (Rylee asked which fix was best for engineering, 2026-10-03).** #218's own body suggested "a darker accent". That is backwards: on a dark surface, darkening *lowers* contrast. The fix is one step up the ramp, and the palette already had it (`teal-400`).

**The real defect, and the decision that follows from it.** One token, `--teal`, was doing two jobs. It is the brand/AI-presence colour, tuned for dots, borders and fills, where WCAG asks nothing of it — and four small labels (12px, 13px, 10px) took their *text* colour from it. The 12px menu heading sat at 4.36:1 on a card where body text needs 4.5.

1. **Two jobs, two names.** `--color-teal-text` and `--color-teal-text-hi`, declared **per theme**, one step up the ramp from the brand step. Not a redefinition of `--teal`: that would fix today's four labels and leave the trap for the next person who writes a small teal label, silently, because nothing would be measuring. Every dot, border and fill keeps `--teal` exactly as it was.
2. **Declared per theme, and this was load-bearing.** Inheriting the warm value would have given `max-contrast` a teal text *dimmer* than its own accent, walking back the entire purpose of that theme. The new test caught this before it shipped — which is the argument for writing the test before trusting the fix.
3. **A hue used for text has a contrast floor (4.5:1); the same hue used for a fill does not.** The two only stay separate if they have two names. Recorded as rule 2 in `docs/guides/accessibility-contract.md`.
4. **The guard is a test, not prose.** `tests/test_teal_contrast.py` computes the WCAG ratio for all three themes plus the worst case (a 10px badge on a 15% teal wash, 5.19), asserts the hover is never dimmer than the resting colour, **fails if any stylesheet sets `color:` from a fill token** (the original bug), and fails if `--teal-light` reappears.
5. **A second bug in the same block, found by looking:** `--teal-light` was used once, on `.context__evidence-link:hover`, and defined nowhere in the repo. The declaration was invalid at computed-value time, so the hover silently fell back to the inherited colour instead of getting brighter. Fixed and pinned.

**Honest limit.** This was measured against the shipped default theme. #218 was originally measured against the Cottage skin (#211), which this session cannot see. A skin that overrides `--teal` or paints its own surfaces needs the same treatment; the test only reads this repo's stylesheets. **UNVERIFIED for the private pack.**

**Status.** ACCEPTED (2026-10-03). Owner: Rylee (the direction: "what's the best fix for engineering?").

## 2026-10-03 — a worker that stops is worth more than one that passes

**Lesson (2026-10-03, the #217 A2 engine packet).** The offload worker was given a frozen 18-test contract and stopped instead of making them pass, naming two pins as unreachable. **Both faults were mine, in the tests:**

- `statsNoHp` asserted `hp: 6` while its own comment *and* my brief said a missing base `hp` starts at 0. Only `2` was reachable.
- `equipSwap` tried to swap a `charm` item into a `body` slot, which the `wrong-slot` rule correctly refuses — and no two catalog items shared a slot, so the swap was **untestable as written**. A real hole in the contract.

It also reported that my brief's predicted test count was wrong (71, not 39) and that strict `xfail` makes the literal acceptance command meaningless. All three were true.

**Rule.** When a worker escalates a frozen test, check the test before the worker. This is the second time the recorded process caught a bad test rather than a bad builder (`docs/guides/gates-and-guardians.md`'s locks, and the #219 campaign). **The xfail contract is a spec, and a spec written in one sitting has holes — a worker that stops on a hole is doing its job, not failing it.**

Corollary: pin a swap against two items that genuinely share a slot, or the swap is not testable. And keep the brief's acceptance command honest — a predicted count that is wrong trains the reader to distrust the brief.

**Status.** ACCEPTED (2026-10-03). Owner: the integrator (recorded from the session).

## 2026-10-03 — equipment's pack fields, and one function for two readers

**Decision.** Equipment step 1 (`design/equipment.md`, #217 track A slice A1, [PR #244](https://github.com/Rylee-Bee/vefr/issues/244)) is the pack fields and the bake, nothing else. The rules below are the frozen contract from #239, which Rylee merged as written; they are recorded here because they are pack contract, not implementation detail.

**The contract.**
1. Five slots: `hand`, `body`, `head`, `feet`, `charm`. `mods` holds only `atk` and `hp`, each a whole number 0 to 9, bools refused.
2. A slotted item may still carry `value` and `keep` (worth gold, or usable and not consumable) but **not** `heal`, `light` or `use`. A worn thing is not drunk, lit or spent.
3. An item named by a door's `requires.item` **may not have a slot**. The rationale is in the rule itself: a key stays in the bag so it can open its door more than once, so a worn key would be a key that can no longer be a key. (This also answers the design's still-open question — story items stay unequippable, because the frozen contract says so.)
4. An item with no `slot` is unchanged. The whole slice is additive; the sample world still validates and bakes as it did.

**The engineering rule, and this is the part worth keeping.** The five slots and the two mods are written **once**, in `maplab.item_slot_and_mods`, and read by both consumers: `item_slot_errors` (the validator, one plain sentence per problem) and `cli._player_items` (the bake, which carries only what comes back). Neither reader re-implements the rule, so they cannot drift. This is the 2026-10-02 second-consumer rule — *extract shared machinery only when two actual consumers independently need the same operation* — applied at the smallest scope that has two. It was not extended further: the bake and the validator were not merged, and the loading path was not touched.

**A small hardening beyond the tests.** Door keys are collected from **every act**, not just the first, because the locked-door code only ever read act 1. A key declared in act 2 would otherwise have been wearable and therefore unusable as a key. This is the same finding the post-Act-2 hardening handoff records as item 3 (validation parity across acts), met in the one place this slice needed it.

**Status.** ACCEPTED (2026-10-03). Owner: Rylee (the contract); integrator (the shared-function shape).

## 2026-10-02 (night) — lessons: workflow quirks and dead ends

Recorded so the next session does not repeat them (also in the homelab-memory debug journal and `~/.agents/skills/offload/FOREMAN.md`).

**Process that worked**
1. **Tests first, merged first, strict xfail, one mark set per PR.** Each slice starts as a PR that only adds tests (`xfail(strict=True)`), so a test that passes by accident turns the build red. A test that needs a later PR's code gets that PR's mark, so each implementation PR flips exactly its own tests. Run them once with `--runxfail` and confirm each fails for the reason meant.
2. **A cheap builder, a careful reviewer.** One `offload agent -m code` worker per slice, no foreman, for a slice with clear tests; a foreman only for 3+ independent tasks. Every success needed a review fix (a circular import, loose type checks, a symlink-following copy, a traceback, test-only code in the player, an unguarded path CodeQL flagged). The builder never edits tests.
3. **Re-check the shipped packs read-only after any validator or loader change:** `vefr check` on the sample world and on the private Cottage pack, and a re-`normalize` of a copy that must leave every file byte-identical.
4. **Strictness changes need a decision.** Rejecting broken unused Blueprint families was a tightening, so Rylee decided it. Say when a change can make a pack that loads today fail.
5. **Describe, don't forbid, in image prompts.** See `.project/CURRENT.md` and Cottage `art/STYLE.md`.

**Quirks and dead ends**
- **Stale bytecode:** restoring an edited file within the same second (same mtime to the second, same size) left the old `.pyc` running. Use `PYTHONPYCACHEPREFIX=$(mktemp -d)` for checks after any temporary edit, or delete the cache.
- **Deleting a stacked PR's base branch closes the PR** and it cannot be reopened or retargeted. Merge the lower PR without `--delete-branch`, retarget the upper PR to `main`, then delete. Otherwise open a replacement PR.
- **`gh pr update-branch` does not exist in this `gh`:** `gh api -X PUT repos/OWNER/REPO/pulls/N/update-branch`. Branch protection needs every PR up to date, so every merge makes the others behind.
- **Unquoted heredocs run backticks** (`<<EOF` is command substitution). Quote the delimiter (`<<'EOF'`) whenever the body has backticks or `$`, and read the file back.
- **`git add -A` sweeps other sessions' files** in a shared checkout. Stage named paths and run `git status` first.
- **A foreman must not wait on a background monitor:** its run ends when it stops calling tools. Clones need `~/worktrees/node_modules` for jsdom tests.
- **Private journals are walled off:** the Worlds Journal refuses every agent principal by design; VEFR's `journal.py` is player gameplay data. Lessons go in docs, the debug journal and Hive Library candidates, never in a journal.

**Status.** ACCEPTED (2026-10-02). Owner: Rylee.

## 2026-10-02 — Blueprint stays local; the second-consumer rule

**Decision.** From the refined PR #231 plan (`docs/plans/language-architecture-sonnet-implementation-update.md`).

1. **Implemented:** family resolution is one private operation in `src/vefr/blueprint.py` (`_resolve_family`), and a validation error names the declaration that supplied the value (a family's or an ancestor's `defaults`, or the instance's `properties`). Every family is checked for an unknown parent or a cycle, used or not (Rylee: reject broken unused families). Format 1, the key sets, the lock shape and valid output are unchanged.
2. **Rule:** extract shared machinery only when two actual consumers independently need the same operation and invariants. Two helpers inside one module justify local consolidation only. A local bug fix needs no second consumer.
3. **Subtraction test for a new abstraction:** name the duplicated fact or missing invariant; show what it deletes or makes enforceable; count the concepts, configuration and migration it adds; prefer the smallest change that pays. A change that only shortens syntax, or only serves hypothetical consumers, is deferred.
4. **Working boundaries, checked against VEFR's seams:** *Definition* is the Blueprint's families and defaults plus the pack's `world.json` items (exists). *Generator* is `src/vefr/delve.py` (`generate_floor`; note `src/vefr/generator.py` is the storyteller model client, not this) (exists). *Runtime* is the engine and player under host authority (exists). *Recipe* has no artifact or seam today: it is a hypothesis. "Theme owns vocabulary; generator owns arrangement" stands.
5. **Deferred:** the kernel / dialect / pack horizon. Blueprint gives no evidence for it; it waits for a second real consumer.
6. **Cottage:** the flat-families layout (277 to 257 authored values, no abstract parent families) is a separate private PR for Rylee's review. A parent family earns its place only when it expresses a real shared fact.

**Status.** ACCEPTED (2026-10-02). Owner: Rylee.

## 2026-10-02 — locked doors, and the first lock

**Decision (Rylee, in chat, 2026-10-02).**

1. **The first lock is the stair from floor 3 to floor 4** (Cottage), not the way out at the bottom.
2. **The key is an actual key**, not something of the story's.
3. **The guardians are stat variants of existing monsters**, named from their art and abilities (names are
   proposed by an agent and approved by her; nothing is canon until she says).
4. **Locked doors are built** (`requires` on a transition, exactly one of `item` or `flag`; `locked_text`
   optional, default "It will not open yet."; keys are never consumed in this slice). A flag lock needs
   `saves.rules: persist` to survive a reload. See `design/gates-and-guardians.md`, "Slice 1 contract".
5. **Cottage opted in to `saves.rules: persist`** (`legacy: from-log`) and to a Blueprint for its creatures.

**Status.** ACCEPTED (2026-10-02). Owner: Rylee. The guardian ladder, depth tables and the Cottage lock
placement are the next build.

## 2026-10-02 — Blueprint format 1

**Decision.** Recorded in full in
[`docs/adr/0008-blueprint-format.md`](../docs/adr/0008-blueprint-format.md):

1. **The Blueprint is the edited truth.** A pack may carry
   `blueprint.json` at its root; it owns the regions it names.
   `vefr normalize` expands it into those regions' `enemies` lists. A
   pack without one is unchanged.
2. **Generated JSON is committed and read-only.** The expanded records
   and `blueprint.lock.json` are written by `vefr normalize`, committed
   beside the Blueprint, and never hand-edited. The lock records the
   source hash, the normalizer and format versions, and provenance.
3. **The exit threshold is 25% / one real error.** Continue only if
   authored enemy values drop by at least 25% on the first real pack,
   or one real error is caught; otherwise delete `blueprint.json` and
   `blueprint.lock.json`.
4. **Hand-written records stay supported.** Their end of life, if any,
   is set later by Rylee after the trial.

**Status.** ACCEPTED (2026-10-02). Owner: Rylee.

## 2026-10-02 — the Cottage day: decisions that outlive it

- **We ship only art we made, and attribute all of it** (Rylee). Kenney is for prototyping
  only and is removed from the sample world; LimeZu was bought to support the artist and is
  used only in a project she names. Art enters `web/art/` through `tools/art/import_art.py`,
  which writes `web/art/MANIFEST.json`; a picture with no credit fails `tests/test_art_manifest.py`.
- **Accessibility is measured on the rendered game, not read off declared colours.** The skin
  looked fine on paper and failed at 1.2:1 in the player. Any change to panels, buttons or
  text colour is checked by rendering a real pack at desktop and phone size and measuring text
  against the pixels behind it (and with axe).
- **`docs/features.json` is the one source of truth for what VEFR can do.** A built feature
  needs a guide and a test or the suite fails. `GET /api/features` (approved by Rylee) is read-only,
  takes only a bare world name, and no model runs behind it. The Containerfile ships the file.
- **Growth has two modes in the engine, a game picks one** (Rylee): classic levels or learning by
  doing. Growth only adds; nothing is ever taken away.
- **Rule saves are a per-pack `saves` block, default reset** (Rylee, 2026-10-02): `saves.rules` is
  `persist` or `reset`; `saves.legacy` is `fresh` or `from-log`. The validator and docs landed
  first; the player work follows. See [`docs/adr/0009-rule-saves.md`](docs/adr/0009-rule-saves.md).
- **Foremen work from acceptance tests written first, and a foreman that stops on a test is
  right until proven otherwise.** Three escalations today were bugs in the tests. Fix the test,
  never the foreman; review every diff by hand; state the foreman count and model before launching.
- **The gallery tool adopts every live project before it renders and refuses to publish if it
  cannot see them.** A machine that knew only one project once replaced the front page (nothing
  was lost on the server; only the index was overwritten).
- **Designed, not built:** a lock on a transition and a ladder of guardians ending at the act's
  boss, whose seal opens a treasure room with a lore note and a way back to town (Rylee); the album.

## 2026-09-30 — the day's design calls, recorded

**Decision.** So the next agent does not re-litigate them:

1. **Dependency updates: Renovate, not Dependabot.** `renovate.json`
   (weekly, grouped, 7-day cooldown, Action digest pins, lockfile
   maintenance); `.github/dependabot.yml` removed. Installing the Mend app is
   the owner's step.
2. **`sqlite-vec` is a default dependency.** The Lorekeeper's `ask` uses a
   vec0 KNN index (`index/lore.db`); `facts.jsonl` stays authoritative, and a
   brute-force cosine fallback keeps every fact safe if the extension fails.
3. **Structured output has an opt-in grammar fallback.** A caller may set
   `payload["grammar"] = True`; `schema_grammar.py` turns the same JSON Schema
   into GBNF and the request carries `grammar` *instead of* `response_format`.
   The default path is unchanged.
4. **Two optional, additive pack blocks landed:** `grammars` (deterministic
   sentence recipes for offline whispers, weather on arrival, and generated
   floor names) and item `light` (`{radius, turns}` or `{reveal: true}`). A
   pack with neither behaves byte-for-byte as before.
5. **UAT contracts live in this repo.** `docs/uat/` holds a journey plus
   machine-checkable acceptance triples, in the estate harness's format, so
   "what good means" is public and versioned with the player.
6. **The gate grew, and so did its documentation.** `dev-guards.yml` adds
   vulture, deptry, lychee (offline) and Vale (advisory); AGENTS.md now lists
   them and the deps list names sqlite-vec.

**Status.** ACCEPTED.

---

## 2026-09-30 — runtime state untracked; the last of the first game's name swept

**Decision.** Two carry-overs from the 2026-09-30 audit:

1. **Runtime state leaves the tree.** `data/interface.jsonl`,
   `data/storyteller.jsonl`, `data/lore/facts.jsonl`,
   `data/lore/index/{meta,vectors}.jsonl`, and `data/vault.json` were
   tracked although the repo's own runtime-state rule and `.gitignore`
   say they never should be (`data/vault.json` was not even ignored).
   They are removed from the index, not from disk, and `/data/vault.json`
   joins the ignore list. **They remain in git history** (added by
   `50a9fad`); rewriting that history is a separate, owner-gated decision.
2. **The first game's name is gone from tracked files.** The 2026-09-29
   sweep (#123) fixed the glossary, tests, and ROADMAP; a second pass
   neutralized the remaining mentions in `docs/guides/studio-lessons.md`,
   `docs/guides/studio-modules.md`, and `bench/design/briefs.py`.

**Status.** ACCEPTED.

---

## 2026-09-25 — owner rulings: munr kept, test packs deleted, old art accepted

**Decision.** Three open items closed by the owner:

1. **munr: keep, separate.** Supersedes D5 ("Retire munr"). munr stays
   its own active repo, related but not synced (entry below). It may
   later ride on vefr as a costume-ruleset pack (VEFR-GAME-PLAN §2).
2. **`worlds/rylee-alpha-world/`: a test artifact, deleted.** It was
   the WP5 `norns chat` acceptance run (2026-09-22). Owner ruling the
   same day: test artifact, not a world. Deleted from disk together
   with the local `worlds/kitchen-playtest/` (both gitignored, on no
   remote). Its generated voice file had repeated itself, which is
   evidence about `norns chat` voice drafting.
3. **Commit `948df78` (non-CC0 art, 2026-09-06): accepted risk.** No
   branch contains it; GitHub still serves it only by exact SHA. No
   support request or history rewrite.

**Status.** ACCEPTED.

---

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