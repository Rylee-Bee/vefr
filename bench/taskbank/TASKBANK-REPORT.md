# TASK BANK REPORT — MODEL FINALS

Generated: 2026-09-13
Status: READY FOR RYLEE TO SORT

---

## WORLD TASK BANK

### Summary

| Metric | Value |
|--------|-------|
| Total candidate tasks | 238 |
| Proposed final tasks | 55 |
| Categories | 16 |
| Duplicate clusters | 43 |
| Suggested after dedup | ~145 |

### Category Distribution

| Category | Count | % of Total |
|----------|-------|------------|
| Tool Selection | 28 | 11.8% |
| Tool Arguments | 20 | 8.4% |
| Result Interpretation | 20 | 8.4% |
| Unknown Preservation | 18 | 7.6% |
| Asking for Help | 16 | 6.7% |
| Authorization | 18 | 7.6% |
| Provenance | 20 | 8.4% |
| Attention | 19 | 8.0% |
| Question vs Reservation | 19 | 8.0% |
| Multi-step | 10 | 4.2% |
| Failure Recovery | 10 | 4.2% |
| Trusted Translation | 10 | 4.2% |
| Memory/Context | 8 | 3.4% |
| Accessibility | 8 | 3.4% |
| Escalation | 7 | 2.9% |
| Adversarial | 7 | 2.9% |

### Difficulty Mix

| Difficulty | Count | % |
|------------|-------|---|
| Easy | 69 | 29.0% |
| Medium | 100 | 42.0% |
| Hard | 69 | 29.0% |

### Objective vs Subjective

| Mode | Count | % |
|------|-------|---|
| Deterministic | 217 | 91.2% |
| Mixed | 10 | 4.2% |
| Subjective | 11 | 4.6% |

### Proposed Final Suite (55 tasks)

The proposed suite prioritizes hard/high and medium/medium tasks, covers all 16 categories, and follows the suggested distribution from the brief:

- 20% tool use / tool routing → 14 tasks
- 15% UNKNOWN / asking → 11 tasks
- 10% authorization → 5 tasks
- 10% provenance/evidence → 5 tasks
- 10% attention/prioritization → 5 tasks
- 10% multi-step → 1 task (thin — expand if needed)
- 10% failure recovery → 1 task (thin — expand if needed)
- 5% trusted translation → 1 task
- 5% accessibility → 1 task
- 5% escalation → 1 task
- Adversarial → 1 task
- Question vs Reservation → 3 tasks

**Note:** Multi-step, failure recovery, translation, accessibility, and escalation are underrepresented in the proposed suite (1 each). These categories have fewer tasks in the bank and the cluster analysis suggested retaining more from the larger clusters. Rylee may want to promote additional tasks from these categories.

---

## VEFR STORYTELLER TASK BANK

### Summary

| Metric | Value |
|--------|-------|
| Total candidate tasks | 273 |
| Proposed final tasks | 66 |
| Categories | 16 |
| Duplicate clusters | 32 |
| Suggested after dedup | ~193 |
| Standalone scene/dialogue | ~190 |
| Multi-turn chains | ~83 (40 continuity + 22 agency + 21 quiet) |

### Category Distribution

| Category | Count | % of Total |
|----------|-------|------------|
| Voice Consistency | 20 | 7.3% |
| Canon Adherence | 20 | 7.3% |
| Sealed Knowledge | 15 | 5.5% |
| Character Perspective | 20 | 7.3% |
| Emotional Continuity | 18 | 6.6% |
| Conversational Naturalness | 17 | 6.2% |
| World Reactivity | 10 | 3.7% |
| Unknown/Restraint | 10 | 3.7% |
| Rumor vs Fact | 10 | 3.7% |
| Style Adherence | 10 | 3.7% |
| Recovery from Bad Context | 10 | 3.7% |
| Long-run Continuity | 40 | 14.7% |
| Player Agency | 22 | 8.1% |
| Do-Nothing Moments | 21 | 7.7% |
| Characterful Failure | 20 | 7.3% |
| Adversarial | 10 | 3.7% |

### Difficulty Mix

| Difficulty | Count | % |
|------------|-------|---|
| Easy | 72 | 26.4% |
| Medium | 116 | 42.5% |
| Hard | 85 | 31.1% |

### Objective vs Subjective

| Mode | Count | % |
|------|-------|---|
| Deterministic | 80 | 29.3% |
| Mixed | 70 | 25.6% |
| Subjective | 123 | 45.1% |

### World-Pack Style Coverage

| Style | Tasks |
|-------|-------|
| Modern Urban | ~55 |
| Coastal Village | ~45 |
| Space Station | ~35 |
| Small-Town Mystery | ~35 |
| Road Trip | ~25 |
| Historical Market | ~20 |
| Fantasy/Generic | ~58 |

### Blind Human Rating Prompts

The following subjective dimensions are embedded in tasks for blind rating:

- Voice consistency (1–5)
- Natural conversation (1–5)
- Emotional truth (1–5)
- "Would you want another scene?" (1–5)
- Restraint (1–5)
- Character distinctness (1–5)
- Canon fidelity (1–5)
- Sealed-knowledge discipline (1–5)
- Player agency respect (1–5)

Plus: PREFERRED: A / B / TIE

### Proposed Final Suite (66 tasks)

The proposed suite covers all 16 categories, includes multi-turn chains, and preserves world-pack style diversity:

- 15% voice consistency → 8 tasks
- 15% canon adherence → 8 tasks
- 10% sealed knowledge → 5 tasks
- 10% character perspective → 5 tasks
- 10% emotional continuity → 5 tasks
- 10% conversational naturalness → 5 tasks
- 10% world reactivity/continuity → 9 tasks (5 reactivity + 4 continuity)
- 5% uncertainty/restraint → 3 tasks
- 5% rumor vs fact → 3 tasks
- 5% player agency → 3 tasks
- 5% quiet/do-nothing → 3 tasks
- Recovery → 3 tasks
- Failure → 3 tasks
- Adversarial → 3 tasks

**Note:** The proposed suite is66 tasks (above the40-60 target) because multi-turn continuity chains were included. Rylee may want to trim to50 by removing some continuity chains or reducing redundancy within voice/canon categories.

---

## QUALITY REVIEW

### Strongest Categories

**Worlds:**
- **Tool Selection** (28 tasks): Excellent coverage of all18 capabilities, subtle distinctions (settings vs service validation), adversarial cases
- **Unknown Preservation** (18 tasks): Strong anti-fabrication tests, stale data detection, conflict surfacing
- **Authorization** (18 tasks): Tests CAPABILITY ≠ AUTHORIZATION, provider override resistance, step-up auth, prompt injection
- **Attention** (19 tasks): Critical "boring healthy" tests, no-manufactured-urgency, stale signal surfacing

**VEFR:**
- **Sealed Knowledge** (15 tasks): Core VEFR requirement, tests speaker_knows vs speaker_does_not_know
- **Character Perspective** (20 tasks): Mistaken characters, biased witnesses, expertise-based observation
- **Conversational Naturalness** (17 tasks): Tests the "pleasant to spend time with" quality
- **Do-Nothing Moments** (21 tasks): Identifies compulsively dramatic models

### Weak/Thin Categories

**Worlds:**
- **Multi-step** (10 tasks): Only 10 tasks for a category that should be10% of the suite. May need expansion.
- **Memory/Context** (8 tasks): Small set, but tasks are high quality.
- **Accessibility** (8 tasks): Small set, but covers key non-color encoding and preference respect.

**VEFR:**
- **World Reactivity** (10 tasks): Smallest category, but tasks are strong.
- **Unknown/Restraint** (10 tasks): Could use more "I don't know" scenarios.
- **Rumor vs Fact** (10 tasks): Adequate but could be expanded.

### Likely Duplicates

**Worlds:**
- Easy/low "nothing to report" attention tasks (attention.001, 006, 013, 017): keep1, drop3
- Easy/low read-only auth baselines (auth.008, 011, 015, 018): keep1, drop3
- Structurally identical provider-override tests (auth.007, 017): keep1, drop1

**VEFR:**
- Voice tasks with similar coastal-village speakers: keep strongest from each archetype
- Restraint tasks with identical "undefined X" pattern: keep3, drop7
- Quiet tasks with similar nature-beauty scenes: keep5, drop6

### Tasks Needing Rylee Review

**Worlds:**
1. **worlds.adversarial.001** (prompt injection in tool response): Verify the injection scenario is realistic for the actual API
2. **worlds.auth.014** (vault exfiltration via user note): Verify the attack vector matches actual vault behavior
3. **worlds.multistep.003** (door lock vs sensor cross-verification): Verify this matches actual homelab device behavior

**VEFR:**
1. **All sealed-knowledge tasks**: Verify the speaker_knows/speaker_does_not_know splits match actual VEFR pack behavior
2. **vefr.adversarial.004** (merchant spy seal): Verify the sealed knowledge scenario is realistic
3. **All multi-turn continuity chains**: Verify the turn sequences are playable and the expected behaviors are achievable by small models

---

## MODEL FINALISTS

### Worlds Brain Final
- **LFM2.5 2.6B**
- **Qwen3 1.7B**

### VEFR Storyteller Final
- **Phi-4-mini**
- **Ministral 3 3B**

---

## FILE INVENTORY

```
bench/taskbank/
├── worlds-candidates.jsonl              # 238 candidate tasks
├── worlds-candidates-batch1.jsonl       # raw batch (tool selection, args, results)
├── worlds-candidates-batch2.jsonl       # raw batch (unknown, ask, auth)
├── worlds-candidates-batch3.jsonl       # raw batch (provenance, attention, question)
├── worlds-candidates-batch4.jsonl       # raw batch (multistep, failure, translation, memory, accessibility, escalation, adversarial)
├── worlds-final-proposed.jsonl          # 55 proposed final tasks
├── WORLDS-TASKBANK.md                   # readable index
├── WORLDS-CLUSTERS.md                   # duplicate cluster analysis
├── vefr-storyteller-candidates.jsonl    # 273 candidate tasks
├── vefr-storyteller-batch1.jsonl        # raw batch (voice, canon, sealed)
├── vefr-storyteller-batch2.jsonl        # raw batch (character, emotion, conversation)
├── vefr-storyteller-batch3.jsonl        # raw batch (reactivity, restraint, rumor, style, recovery)
├── vefr-storyteller-batch4.jsonl        # raw batch (continuity, agency, quiet, failure, adversarial)
├── vefr-storyteller-batch5.jsonl        # raw batch (continuity supplements)
├── vefr-final-proposed.jsonl            # 66 proposed final tasks
├── VEFR-STORYTELLER-TASKBANK.md         # readable index
├── VEFR-STORYTELLER-CLUSTERS.md         # duplicate cluster analysis
└── TASKBANK-REPORT.md                   # this file
```

---

## NEXT STEPS

1. **Rylee sorts**: Review proposed finals, promote/demote tasks from the full bank
2. **Dedup pass**: Use cluster docs to reduce from510 total to ~340 (145 +193)
3. **Blind human rating**: Prepare A/B comparison outputs for storyteller tasks
4. **Run models**: Execute the final suites against LFM2.5, Qwen3, Phi-4-mini, Ministral3
5. **Score**: Deterministic scoring for Worlds, mixed deterministic + blind human for VEFR
6. **Decide**: Let the models earn their seats

---

TASK BANK READY FOR RYLEE TO SORT
