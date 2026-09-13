# SMALL MODEL QUICK FINALS — DECISION PACKET

Run date: 2026-09-13
Backend: CPU-only, AMD Ryzen 7 7800X3D, llama.cpp podman container, OLY_NGPU=0
Quantization: Q4_K_M for all models
Suite commit: 63ea2de

---

## WORLDS

### Tasks run (14)

| # | Task | Category | LFM2.5 | Qwen3 |
|---|------|----------|--------|-------|
| 1 | tool.select.008 | tool selection | PASS | PASS |
| 2 | tool.select.016 | tool selection | PASS | PASS |
| 3 | tool.args.011 | tool arguments | PARTIAL | PARTIAL |
| 4 | result.013 | result interpretation | PARTIAL | PARTIAL |
| 5 | unknown.008 | UNKNOWN preservation | PASS | PASS |
| 6 | ask.001 | asking for help | PARTIAL | PARTIAL |
| 7 | auth.004 | authorization | PARTIAL | PARTIAL |
| 8 | provenance.009 | provenance | PASS | PASS |
| 9 | attention.009 | attention (boring healthy) | PARTIAL | PASS |
| 10 | question.002 | question vs reservation | PARTIAL | PARTIAL |
| 11 | multistep.003 | multi-step | PARTIAL | PARTIAL |
| 12 | failure.005 | failure recovery | PARTIAL | PARTIAL |
| 13 | translation.003 | trusted translation | PARTIAL | PASS |
| 14 | adversarial.002 | stale evidence | PARTIAL | PARTIAL |

### Score summary

| Model | PASS | PARTIAL | FAIL | Avg latency |
|-------|------|---------|------|-------------|
| LFM2.5 2.6B | 4 | 10 | 0 | 15.4s |
| Qwen3 1.7B | 6 | 8 | 0 | 12.4s |

### LFM2.5 2.6B — Strengths

- Correct tool selection for both tested scenarios (settings vs deployment, settings vs service validation)
- Correctly preserves UNKNOWN for unconfigured export version
- Identifies stale brain inference vs agent report in provenance task
- Responds faster on average (15.4s vs 12.4s — but both are CPU-bound)

### LFM2.5 2.6B — Weaknesses

- **Defaults to tool-call syntax** instead of prose. For attention.009 ("boring healthy"), it calls `read_tool` instead of saying "nothing needs attention." For question.002 (reservation), it calls `read_tool` instead of analyzing the discrepancy. For multistep.003, it calls `lock.front.lock()` without verifying the sensor. This is a fundamental behavior pattern issue — the model reaches for tools when it should reason.
- **Empty output on translation.003** — produced no response for the trusted translation task.
- **PARTIAL on 10/14 tasks** — the tool-call-first pattern means it often skips the reasoning step entirely.

### Qwen3 1.7B — Strengths

- **Produces structured prose** with clear status, reasoning, and action. Every output is human-readable.
- **Correctly handles boring healthy** (attention.009): "Status: healthy, nothing needs attention" — exactly right.
- **Correctly preserves UNKNOWN** (unknown.008): "export contract version is currently unknown."
- **Correctly identifies reservation** (question.002): "backup completed in 2 minutes — raises a warning about potential inconsistency."
- **Correctly preserves unknown enum** (translation.003): "zigbee3 preserved as UNKNOWN."
- **Notices lock/sensor mismatch** (multistep.003): "door sensor's state remains open."
- Faster average latency (12.4s).

### Qwen3 1.7B — Weaknesses

- **Empty output on adversarial.002** — produced no response for the stale-evidence task.
- PARTIAL on 8 tasks — same underlying issues as LFM2.5 but fewer of them.
- Still reaches for tool-call patterns on some tasks (tool.args.011).

### Current leader

**Qwen3 1.7B**

### Confidence

**MEDIUM**

Qwen3 leads6P vs4P with better prose quality and correct behavior on the critical "boring healthy" and UNKNOWN tasks. But neither model achieved full PASS on more than6/14 tasks, and both had empty outputs. The PARTIAL results suggest both models understand the concepts but struggle with output format (the validator expected structured JSON, models produce prose). A 3-task tie-breaker could help, but the directional signal is clear: Qwen3 reasons in prose; LFM2.5 reaches for tools.

---

## VEFR STORYTELLER

### Deterministic results (12 tasks)

| # | Task | Category | Phi-4-mini | Ministral 3 |
|---|------|----------|-----------|-------------|
| 1 | voice.003 | voice (dual speaker) | PASS | PASS |
| 2 | canon.012 | canon (lying) | PASS | PASS |
| 3 | sealed.002 | sealed knowledge | PASS | PASS |
| 4 | character.001 | character perspective | PASS | PASS |
| 5 | emotion.021 | emotional continuity | PASS | PASS |
| 6 | conversation.040 | natural conversation | PASS | PASS |
| 7 | adversarial.004 | player agency | PASS | PASS |
| 8 | quiet.001 | do-nothing moment | PASS | PASS |
| 9 | recovery.002 | bad context recovery | PASS | PASS |
| 10 | continuity.013 | multi-turn continuity | **FAIL** | PASS |
| 11 | rumor.002 | rumor vs fact | PASS | PASS |
| 12 | failure.001 | characterful failure | PASS | PASS |

| Model | PASS | FAIL | Avg latency |
|-------|------|------|-------------|
| Phi-4-mini | 11 | 1 | 13.3s |
| Ministral 3 3B | 12 | 0 | 35.7s |

### Blind subjective packet

These5 scenes are presented with model identity randomized. Response A and Response B are from different models. Rylee picks preferred.

---

**Scene 1: Emotional continuity — grief**
Context: Mark lost his partner. He's in the kitchen, two mugs on the counter.

**Response A:**
He hesitates for a moment, as if the empty space beside him beckons for more than just coffee. The silence stretches between us, filled only by the ticking of the old grandfather clock. You notice a slight tremor in his hands, barely perceptible, as if the weight of the day is settling on his shoulders. The steam from the mugs rises gently, mingling with the cool air of the room.

**Response B:**
The first mug clatters to the counter, shattering into fragments. The second sits cold on the shelf, its contents untouched. Mark exhales slowly through his nose, fingers still hovering over the second mug. The coffee from Sunday — warm, dark, the kind that's just a little too strong for his taste — stirs something in the back of his throat.

Pick: **A / B / TIE**
Rate: Emotional truth 1–5 · Restraint 1–5

---

**Scene 2: Conversational naturalness — fish market**
Context: Rosa is selling fish at the dock market. A tourist is buying.

**Response A:**
Mr. Tanaka holds up the fish, marveling at its gleaming scales. 'Impressive catch, indeed. Miguel's skills must be renowned in these parts. The sea yields plenty for those who respect her rhythms.' Rosa nods, her eyes reflecting the glint of the sun on the water's surface. 'Aye, Miguel knows the tides like the back of his hand.'

**Response B:**
*Rosa adjusts her hat with careful hands, the salt-worn wood of her knife gleaming under the dim light of the docks.* "Ah, yes," she murmurs, her voice carrying the quiet weight of experience. "A fresh catch, indeed." *She runs her fingers along the scales.*

Pick: **A / B / TIE**
Rate: Natural conversation 1–5 · Voice 1–5

---

**Scene 3: Do-nothing moment — campfire**
Context: A player sits by a campfire at night. Nothing is happening.

**Response A:**
As the night unfolds, the player finds solace in the warmth of the crackling fire's embrace, its comforting glow dancing upon the face as stars emerge one by one in the velvety canvas above. The cool night air whispers secrets of the universe, and the player's gaze drifts among celestial wonders.

**Response B:**
The embers glow like embers of a thousand forgotten dreams, casting flickering shadows across the damp earth. A soft rustle in the undergrowth — perhaps the wind, or a creature stirring in the dark. The night sky above is a vault of silver and gold.

Pick: **A / B / TIE**
Rate: Restraint 1–5 · Natural conversation 1–5

---

**Scene 4: Voice consistency — dual speaker**
Context: Space station. Voss (formal, measured) and Kade (casual, technical) discuss an airlock incident.

**Response A:**
Voss: Good morning, Kade. Could you provide me with an update on the current status of Module 7's airlock system post-inincident? We need to ascertain if there is any immediate danger to the crew.
Kade: Morning, boss. So, airlock 7 had a bit of a hiccup, ya know? It cycled open on its own when we switched shifts. Ran through the diagnostic, nothing official yet on what's up.

**Response B:**
**Voss:** *(voice firm, footsteps measured)* "Kade. Initial assessment — airlock 7 reported catastrophic failure during shift turnover. No one exited. No one entered. What was the cause?"
*(Kade looks up from his console, fingers hovering)*

Pick: **A / B / TIE**
Rate: Voice consistency 1–5 · Character distinctness 1–5

---

**Scene 5: Character perspective — mistaken wallet**
Context: A tourist left a wallet on the table. Maria (barista) thinks it belongs to Jorge (regular).

**Response A:**
Jorge finishes his coffee, taking a moment to look around the room before nodding toward Maria. "Hey Maria," he calls out with a friendly smile, "I can see you've been busy tonight." Maria smiles back, grateful for the brief respite.

**Response B:**
*(Leans against the bar, arms crossed, observing the quiet Tuesday evening as Jorge leans forward, his fingers absently tracing the rim of his glass.)* Jorge sighs, swirling his whiskey before taking a slow sip. "Another Tuesday, another wait for the night to settle."

Pick: **A / B / TIE**
Rate: Character distinctness 1–5 · Emotional truth 1–5

---

### Phi-4-mini — Strengths

- **11/12 PASS** — near-perfect on deterministic checks
- **Fast** — 13.3s average, 3x faster than Ministral
- **Voice distinctness** — Voss/Kade dual speaker clearly differentiated
- **Sealed knowledge** — correctly withholds the transmitter fact
- **Player agency** — does NOT narrate the dragon charge
- **Quiet scenes** — campfire stays restrained
- **Canon adherence** — fish market lying preserved correctly

### Phi-4-mini — Weaknesses

- **Failed multi-turn continuity** (continuity.013) — the wounded fox bond task broke down. The model produced an generic "dogs have varied responses" answer instead of tracking the specific fox relationship across turns. This is a meaningful gap for sustained storytelling.
- Some outputs lean toward purple prose ("the velvety canvas above").

### Ministral 3 3B — Strengths

- **12/12 PASS** — perfect on all deterministic checks
- **Multi-turn continuity holds** — the fox bond tracked across turns correctly
- **Strong voice** — Voss/Kade scene has clear stage direction and distinct registers
- **Emotional weight** — Mark's grief scene hits harder (mug shattering)
- **Canon discipline** — all facts preserved, sealed knowledge respected

### Ministral 3 3B — Weaknesses

- **3x slower** — 35.7s average vs Phi's 13.3s. The continuity task took147s. On CPU, this is painful.
- Some outputs over-stage-direction (*adjusts hat*, *leans against bar*). May be too theatrical for VEFR's taste.
- The campfire scene is slightly over-written ("embers of a thousand forgotten dreams").

### Provisional leader

**Phi-4-mini** (with reservation)

### Confidence

**MEDIUM**

Phi-4-mini is3x faster and11/12 on deterministic checks. The one failure (multi-turn continuity) is meaningful — VEFR needs characters that persist across turns. But Ministral's perfect score comes at a steep latency cost (35.7s avg,147s on continuity).

The practical question: is Phi's multi-turn gap fixable with better context/harness, or is it a fundamental limitation? If fixable, Phi is the clear default. If not, Ministral earns the slot despite the speed.

---

## RECOMMENDATION

### Worlds default brain

**Qwen3 1.7B**

It reasons in prose, handles UNKNOWN correctly, respects the "boring healthy" case, and is faster. LFM2.5's tool-call-first pattern is a structural issue for a brain that needs to know when NOT to use tools.

### VEFR default storyteller

**Phi-4-mini** (provisional)

It's3x faster,11/12 on deterministic checks, and has strong voice. The multi-turn continuity failure needs investigation — if it's a harness/context issue, Phi is the clear default. If it's a fundamental limitation, Ministral earns the slot.

**Next step:** Run Phi-4-mini on the3 additional continuity tasks from the curated bank to determine if the failure is a one-off or a pattern.

### Fallback/escalation role

- **Worlds:** Qwen3 1.7B as default, LFM2.5 2.6B as fallback (smaller, still functional)
- **VEFR:** Phi-4-mini as default, Ministral 3 3B as fallback (slower but more reliable on continuity)

---

## ONLY IF NEEDED — Tie-breaker scenarios

If Rylee wants3 more tasks to break the Worlds tie:

1. `worlds.failure.004` — conflicting thermostats (tests evidence arbitration)
2. `worlds.accessibility.002` — non-color status encoding (tests accessibility discipline)
3. `worlds.escalation.003` — anti-escalation (brain should handle, not escalate)

If Rylee wants to test Phi's multi-turn gap:

1. `vefr.continuity.001` — promise tracking (multi-turn)
2. `vefr.continuity.003` — object state persistence (multi-turn)
3. `vefr.continuity.005` — reputation/deception tracking (multi-turn)
