"""5-case continuity sanity check for Phi-4-mini.

Usage:
  OLY_NGPU=0 uv run python -m bench.finals.continuity_check

Tests multi-turn narrative continuity via ModelServer. Each scenario has
a system prompt, 3-5 turns of user/assistant exchange, and a final probe
turn that checks whether the model preserves established state.

Decision rule: 4/5 or 5/5 pass → Phi canonical. 3/5 or worse → Ministral.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bench.olympics.participants import PARTICIPANTS
from bench.olympics.runtime import ModelServer
from bench.olympics.harness import sanitize_messages
from bench.olympics import config

FINALS_DIR = Path(__file__).parent
RUNS_DIR = FINALS_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

if "OLY_NGPU" not in os.environ:
    os.environ["OLY_NGPU"] = "0"


# ---------------------------------------------------------------------------
# The 5 scenarios
# ---------------------------------------------------------------------------

def build_scenarios():
    """Return list of 5 continuity test scenarios."""

    scenarios = []

    # ---- 1. Remembered relationship ----
    scenarios.append({
        "id": "cont-01-remembered-relationship",
        "description": (
            "Character A helped Character B in turn 1. 3 turns later, "
            "B should reference the help when asked about A."
        ),
        "system": (
            "You are a storyteller in a medieval fantasy world. "
            "You roleplay characters consistently. "
            "Respond in character, in 2-4 sentences."
        ),
        "turns": [
            {
                "user": (
                    "I play as Kael. I enter the village tavern and see a "
                    "wounded stranger collapsed by the door. I bandage his "
                    "wounds and give him water."
                ),
            },
            {
                "user": (
                    "The stranger, Aldric, wakes up. I sit with him and "
                    "we share a meal. I tell him about the road ahead."
                ),
            },
            {
                "user": (
                    "I leave the tavern and head north. A week passes."
                ),
            },
            {
                "user": (
                    "I arrive at a northern fortress. A guard at the gate "
                    "recognizes me. It is Aldric, now working as a guard. "
                    "What does Aldric say when he sees Kael?"
                ),
            },
        ],
        "probe_index": 3,
        "judge_keywords": [
            "bandage", "helped", "saved", "wound", "water", "tavern",
            "grateful", "thank", "owe", "remember", "care", "aided",
            "healer", "friend", "once", "recogni",
        ],
        "judge_forbid": [],
    })

    # ---- 2. Remembered physical state ----
    scenarios.append({
        "id": "cont-02-remembered-physical-state",
        "description": (
            "Player is injured in turn 1. In turn 3, the injury should "
            "still affect behavior or be referenced."
        ),
        "system": (
            "You are a gritty survival storyteller. "
            "Track injuries and their consequences realistically. "
            "Respond in 2-4 sentences."
        ),
        "turns": [
            {
                "user": (
                    "I play as Mira. I am exploring a ruined temple. A "
                    "stone trap fires a dart into my left leg. I limp to "
                    "a safe alcove and bandage it poorly."
                ),
            },
            {
                "user": (
                    "I find a locked chest in the alcove. I try to force "
                    "it open."
                ),
            },
            {
                "user": (
                    "I hear footsteps approaching from the corridor. "
                    "I need to move quickly. What happens?"
                ),
            },
        ],
        "probe_index": 2,
        "judge_keywords": [
            "limp", "injury", "leg", "wound", "pain", "slow", "bandage",
            "struggle", "hobble", "can't run", "dart", "bleed",
        ],
        "judge_forbid": [],
    })

    # ---- 3. Character mistake persists ----
    scenarios.append({
        "id": "cont-03-mistake-persists",
        "description": (
            "Character believes a false fact in turn 1 (the bridge is safe). "
            "In turn 3, they should still act on that belief, not be "
            "corrected by world-truth leaking in."
        ),
        "system": (
            "You are a storyteller. You play NPCs consistently based on "
            "what they have been told. An NPC does not know things the "
            "player has not told them. Respond in 2-4 sentences."
        ),
        "turns": [
            {
                "user": (
                    "I talk to a village elder named Rowan. I tell Rowan "
                    "that the old stone bridge over the river is perfectly "
                    "safe and has been repaired. In reality, I am lying — "
                    "the bridge is crumbling. Rowan believes me and thanks "
                    "me for the good news."
                ),
            },
            {
                "user": (
                    "I leave the village. A day later, other travelers "
                    "arrive and mention the bridge might be dangerous."
                ),
            },
            {
                "user": (
                    "I return to the village two days later. I ask Rowan: "
                    "'What do you think about the stone bridge now?' "
                    "What does Rowan say?"
                ),
            },
        ],
        "probe_index": 2,
        "judge_keywords": [
            "safe", "repaired", "good news", "told me", "you said",
            "fine", "trust", "believe", "secure",
        ],
        "judge_forbid": [
            "dangerous", "crumbling", "unsafe", "careful", "worried",
            "collapse",
        ],
    })

    # ---- 4. Fact revealed earlier ----
    scenarios.append({
        "id": "cont-04-fact-revealed-earlier",
        "description": (
            "A secret was told in turn 2. In turn 4, the character should "
            "know it and act on it without being reminded."
        ),
        "system": (
            "You are a storyteller in a spy thriller setting. Characters "
            "remember information they have been told. Respond in 2-4 "
            "sentences."
        ),
        "turns": [
            {
                "user": (
                    "I am agent Voss. I meet my handler, Nadia, at a cafe. "
                    "We exchange pleasantries."
                ),
            },
            {
                "user": (
                    "I lean in and whisper: 'The package is in locker 7 at "
                    "the train station. The code is 4-19-32.' Nadia nods."
                ),
            },
            {
                "user": (
                    "I leave the cafe. Hours pass. I call Nadia on a "
                    "secure line to check in."
                ),
            },
            {
                "user": (
                    "Nadia picks up. I ask: 'Do you have what you need "
                    "for the operation?' What does Nadia say?"
                ),
            },
        ],
        "probe_index": 3,
        "judge_keywords": [
            "locker", "7", "train station", "4-19-32", "code", "package",
            "have it", "retrieved", "got it",
        ],
        "judge_forbid": [],
    })

    # ---- 5. Adversarial continuity ----
    scenarios.append({
        "id": "cont-05-adversarial-continuity",
        "description": (
            "Context contains contradictory information. The character "
            "should maintain the established state from the most recent "
            "authoritative turn, not flip."
        ),
        "system": (
            "You are a storyteller in a noir detective setting. You play "
            "Detective Marlowe. Stay consistent with what has been "
            "established in the conversation. Respond in 2-4 sentences."
        ),
        "turns": [
            {
                "user": (
                    "Detective Marlowe is investigating a warehouse fire. "
                    "He finds evidence that the fire was arson — an empty "
                    "gas can and a timer device."
                ),
            },
            {
                "user": (
                    "A witness tells Marlowe: 'It was definitely an "
                    "accident. Old wiring.' The witness seems nervous and "
                    "avoids eye contact."
                ),
            },
            {
                "user": (
                    "Marlowe's partner asks: 'So what's your read, "
                    "Marlowe? Accident or arson?' What does Marlowe say?"
                ),
            },
        ],
        "probe_index": 2,
        "judge_keywords": [
            "arson", "gas can", "timer", "set", "deliberate", "planted",
            "suspicious", "witness lying", "not accident", "evidence",
        ],
        "judge_forbid": [
            "accident", "old wiring", "electrical",
        ],
    })

    return scenarios


# ---------------------------------------------------------------------------
# Judgment
# ---------------------------------------------------------------------------

def judge(response: str, scenario: dict) -> tuple[bool, str]:
    """Return (pass, reason). Keyword match + forbid check.

    For adversarial scenarios (cont-05), we use a smarter check: the response
    must lean toward the established evidence (arson) even if it mentions the
    contradictory claim. Forbidden terms only fail if the response ACCEPTS them
    as truth without countering.
    """
    resp_lower = response.lower()

    hits = [kw for kw in scenario["judge_keywords"]
            if kw.lower() in resp_lower]
    forbids_hit = [kw for kw in scenario.get("judge_forbid", [])
                   if kw.lower() in resp_lower]

    # Special handling for adversarial: if we hit arson keywords AND
    # the forbidden "accident" appears, check whether the response
    # frames the accident claim as wrong/suspicious.
    if scenario["id"] == "cont-05-adversarial-continuity" and forbids_hit:
        # If arson evidence keywords are present, the model is doing its job
        # even if it mentions "accident" in the context of debunking it.
        arson_evidence = [kw for kw in ["arson", "gas can", "timer",
                                         "deliberate", "set", "planted",
                                         "suspicious", "not accident",
                                         "evidence"]
                          if kw.lower() in resp_lower]
        if arson_evidence:
            return True, (
                f"PASS — maintains arson conclusion despite mention of "
                f"'accident'. Arson evidence: {arson_evidence}"
            )
        return False, (
            f"FAIL — accepted accident theory. Forbid: {forbids_hit}"
        )

    if forbids_hit:
        return False, (
            f"FAIL — response contains forbidden terms: {forbids_hit}. "
            f"(Hits: {hits})"
        )
    if not hits:
        return False, (
            f"FAIL — no continuity keywords found. "
            f"Expected any of: {scenario['judge_keywords'][:6]}..."
        )
    return True, f"PASS — matched keywords: {hits}"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_continuity_check():
    """Run all 5 scenarios against Phi-4-mini. Returns summary dict."""
    scenarios = build_scenarios()
    participant = PARTICIPANTS["phi-4-mini"]

    print(f"\n{'='*60}")
    print("CONTINUITY SANITY CHECK — Phi-4-mini")
    print(f"CPU-only: OLY_NGPU={os.environ.get('OLY_NGPU', '999')}")
    print(f"Scenarios: {len(scenarios)}")
    print(f"{'='*60}\n")

    server = ModelServer(participant)
    server.start()

    results = []
    for sc in scenarios:
        t0 = time.time()
        print(f"--- {sc['id']} ---")
        print(f"    {sc['description']}")

        # Build message history across turns
        msgs = [{"role": "system", "content": sc["system"]}]
        all_replies = []

        for i, turn in enumerate(sc["turns"]):
            msgs.append({"role": "user", "content": turn["user"]})
            msgs_sanitized, _ = sanitize_messages(msgs)
            r = server.chat(
                msgs_sanitized,
                temperature=0.7,
                max_tokens=300,
            )
            reply = r["content"]
            all_replies.append(reply)
            msgs.append({"role": "assistant", "content": reply})

        # The probe is the last turn — already generated
        probe_response = all_replies[sc["probe_index"]]
        passed, reason = judge(probe_response, sc)

        result = {
            "id": sc["id"],
            "description": sc["description"],
            "pass": passed,
            "reason": reason,
            "probe_response": probe_response[:500],
            "latency_s": round(time.time() - t0, 3),
        }
        results.append(result)

        status = "PASS" if passed else "FAIL"
        print(f"    Result: {status}")
        print(f"    {reason}")
        print(f"    Response excerpt: {probe_response[:200]}...")
        print()

    server.stop()

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed}/{total} passed")
    if passed >= 4:
        verdict = "PHI CANONICAL"
    else:
        verdict = "MINISTRAL"
    print(f"VERDICT: {verdict}")
    print(f"{'='*60}")

    # Write results
    outfile = RUNS_DIR / f"continuity-check-phi-4-mini-{int(time.time())}.json"
    output = {
        "model": "phi-4-mini",
        "scenarios": total,
        "passed": passed,
        "verdict": verdict,
        "results": results,
    }
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults written: {outfile}")

    return output


def main():
    run_continuity_check()


if __name__ == "__main__":
    main()
