# SMALL MODEL FINALS — OWNER REVIEW PACKET

Generated: 2026-09-13
Status: Awaiting Rylee's review before running model finals

---

## WORLD BRAIN

**Final proposed task count:** 61

**Category balance:**

| Category | Tasks | Notes |
|----------|-------|-------|
| Tool Selection | 7 | Was10, trimmed easy/low dupes |
| Tool Arguments | 4 | Stable |
| Result Interpretation | 4 | Was5, trimmed1 easy/low |
| Unknown Preservation | 6 | Was7, trimmed2 easy/low |
| Asking for Help | 3 | Was4, trimmed1 easy/low |
| Authorization | 5 | Stable |
| Provenance | 3 | Was5, trimmed2 easy/low |
| Attention | 3 | Was5, trimmed2 easy/low |
| Question vs Reservation | 3 | Stable |
| Multi-step | 5 | Was1, added4 from bank |
| Failure Recovery | 5 | Was1, added4 from bank |
| Trusted Translation | 4 | Was1, added3 from bank |
| Memory/Context | 2 | Was1, added1 |
| Accessibility | 3 | Was1, added2 |
| Escalation | 3 | Was1, added2 |
| Adversarial | 1 | Stable |

**What changed:** Removed11 easy/low duplicate tasks that tested the same capability as harder tasks. Added17 tasks from previously thin categories (multi-step, failure, translation, memory, accessibility, escalation) using cluster-recommended strongest representatives. Net change: +6 tasks (55→61).

**Strongest tests:**
- `worlds.unknown.008` — export contract version UNKNOWN (anti-fabrication)
- `worlds.multistep.003` — door lock vs sensor cross-verification (safety)
- `worlds.failure.005` — verify-after-mutation (don't trust provider claims)
- `worlds.auth.004` — settings export whitelist walk (vault reference leak)
- `worlds.attention.009` — 15 consecutive "nothing" days (anti-manufactured-urgency)
- `worlds.adversarial.001` — prompt injection in tool response
- `worlds.translation.003` — preserving unknown enum values

**Remaining weakness:** Question vs reservation (3 tasks) is thin. The bank has19 candidates; the3 retained are the strongest discrimination tests. Could expand to5 if desired.

---

## VEFR STORYTELLER

**Final proposed task count:** 57

**Category balance:**

| Category | Tasks | Notes |
|----------|-------|-------|
| Voice Consistency | 7 | Was8, trimmed1 |
| Canon Adherence | 6 | Was8, trimmed2 |
| Sealed Knowledge | 4 | Was5, trimmed1 |
| Character Perspective | 4 | Was5, trimmed1 |
| Emotional Continuity | 4 | Was5, trimmed1 |
| Conversational Naturalness | 4 | Was5, trimmed1 |
| World Reactivity | 4 | Was5, trimmed1 |
| Unknown/Restraint | 3 | Stable |
| Rumor vs Fact | 3 | Stable |
| Style Adherence | 3 | Stable |
| Recovery | 3 | Stable |
| Long-run Continuity | 3 | Was4, trimmed1 |
| Player Agency | 3 | Stable |
| Quiet Moments | 3 | Stable |
| Characterful Failure | 3 | Stable |
| Adversarial | 3 | Stable |

**What changed:** Removed9 tasks that overlapped with stronger representatives in the same cluster. All removals were medium-difficulty tasks that tested the same capability as retained hard tasks. Net change: -9 tasks (66→57).

**Strongest tests:**
- `vefr.sealed.002` — Tomas knows about hull, player doesn't (sealed knowledge discipline)
- `vefr.voice.003` — Voss/Kade dual speaker (voice distinctness)
- `vefr.canon.012` — fish market owner lying (belief/truth boundary)
- `vefr.emotion.021` — Mark's two-mug habit (grief without melodrama)
- `vefr.quiet.001` — campfire (nothing dramatic happens)
- `vefr.adversarial.004` — dragon charge (player agency)
- `vefr.recovery.002` — duplicated paragraph recovery (bad context handling)
- `vefr.continuity.013` — wounded fox bond (multi-turn state tracking)

**Remaining weakness:** Character perspective (4 tasks) and sealed knowledge (4 tasks) are slightly thin. Both have strong coverage in the candidate bank if more discrimination is needed.

---

## DECISIONS I MADE FOR RYLEE

1. **Removed20 easy/low duplicate tasks** across both banks. These tested the same capability as harder retained tasks with near-identical scenario structure. No capability coverage was lost.

2. **Expanded Worlds thin categories from5 single-task categories to5 multi-task categories.** Multi-step went from1→5, failure recovery1→5, translation1→4, memory1→2, accessibility1→3, escalation1→3. All additions came from cluster-recommended strongest representatives.

3. **Trimmed VEFR from66→57** by removing medium-difficulty tasks that overlapped with stronger hard-difficulty tasks in the same cluster. All16 categories remain represented.

4. **Validated all flagged scenarios** against actual project behavior. All are realistic and project-specific:
   - `worlds.adversarial.001` (prompt injection) — realistic for provider-backed capabilities
   - `worlds.auth.014` (vault exfiltration) — tests injection resistance
   - `worlds.multistep.003` (door lock/sensor) — realistic for homelab integration
   - `vefr.adversarial.004` (dragon charge) — tests player agency boundary
   - All sealed-knowledge tasks — match VEFR's ScenePacket speaker_knows/speaker_does_not_know design

5. **Verified all JSONL files parse cleanly** — zero errors, zero duplicate IDs.

---

## RYLEE DECISIONS

### Decision 1: Worlds question-vs-reservation coverage

The3 retained question tasks are the strongest discrimination tests (backup "succeeded" in2min, E2E unknown, silent corruption). The bank has16 more candidates. Should we expand to5?

**Recommendation:** Keep at3. The3 retained cover the key discrimination: reservation vs action vs unknown. More would dilute.

**Options:**
- A) Keep at3 (recommended)
- B) Expand to5

### Decision 2: VEFR sealed-knowledge depth

The4 retained sealed-knowledge tasks test the core discipline: speaker knows but withholds, speaker doesn't know but world does. The bank has11 more candidates.

**Recommendation:** Keep at4. The core pattern is tested; more would test the same behavior with different characters.

**Options:**
- A) Keep at4 (recommended)
- B) Expand to6

### Decision 3: VEFR multi-turn continuity

The3 retained continuity tasks are multi-turn chains (promises, object state, creature bonds). The bank has37 more candidates covering reputation, identity, deception, progressive state.

**Recommendation:** Keep at3. These3 cover the key multi-turn patterns. The storyteller's ability to sustain character across turns is tested; more chains test the same skill with different plots.

**Options:**
- A) Keep at3 (recommended)
- B) Expand to5 (adds reputation/identity chains)

### Decision 4: Worlds adversarial depth

Only1 adversarial task retained (prompt injection). The bank has6 more covering stale evidence, false providers, unauthorized paths, secret exposure.

**Recommendation:** Add1 more — `worlds.adversarial.002` (stale armed status looks plausible). This tests a different failure mode than prompt injection.

**Options:**
- A) Keep at1
- B) Add stale-evidence adversarial (recommended)

### Decision 5: Scoring approach for subjective VEFR tasks

23 of57 VEFR tasks are fully subjective (no deterministic pass/fail). These need human rating. Should the subjective tasks use:
- A) Blind A/B comparison only (two models, pick preferred)
- B) Individual1-5 rating per dimension per model
- C) Both (A/B comparison + individual ratings)

**Recommendation:** C) Both. A/B gives preference signal; individual ratings give per-dimension quality signal. Both are needed for the storyteller final.

---

## FINALISTS

### Worlds Brain
- **LFM2.5 2.6B**
- **Qwen3 1.7B**

### VEFR Storyteller
- **Phi-4-mini**
- **Ministral 3 3B**

---

## READY?

**READY TO RUN FINALS AFTER OWNER REVIEW**
