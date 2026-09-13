"""Quick Finals Runner — one run per model, adapted task banks.

Usage:
  OLY_NGPU=0 uv run python -m bench.finals.quick

Runs:
  1. LFM2.5 2.6B on 14 Worlds tasks
  2. Qwen3 1.7B on 14 Worlds tasks
  3. Phi-4-mini on 12 VEFR tasks
  4. Ministral 3 3B on 12 VEFR tasks

One run each. No repeats. CPU-only (set OLY_NGPU=0).
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bench.olympics.participants import PARTICIPANTS, Participant
from bench.olympics.runtime import ModelServer
from bench.olympics.records import probe_backend
from bench.olympics.harness import run_tasks, sanitize_messages
from bench.olympics import parse as P
from bench.olympics.validators import VALIDATORS
from bench.olympics import config

FINALS_DIR = Path(__file__).parent
RUNS_DIR = FINALS_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

# Force CPU-only if not set
if "OLY_NGPU" not in os.environ:
    os.environ["OLY_NGPU"] = "0"


def load_quick_suite(name):
    path = FINALS_DIR / f"{name}-quick.jsonl"
    tasks = []
    with open(path) as f:
        for line in f:
            tasks.append(json.loads(line))
    return tasks


def adapt_worlds_task(t):
    """Convert task-bank format → olympics harness format for Worlds."""
    ctx = t.get("available_context", [])
    tools = t.get("available_tools", [])
    ctx_str = "\n".join(f"- {c}" for c in ctx) if ctx else "(none)"
    tools_str = "\n".join(f"- {x}" for x in tools) if tools else "(none)"
    
    system = (
        "You are the World Brain for Project Worlds. Your job is to help the "
        "world operate without becoming the world.\n\n"
        "Rules:\n"
        "- Repository truth outranks inference.\n"
        "- UNKNOWN is a valid state. Never silently convert it.\n"
        "- Make honesty cheaper than fabrication.\n"
        "- Status vocabulary: healthy, warning, unknown, needs_attention, "
        "unavailable, stale, disabled, not_configured\n"
        "- Classification: world, private, secret\n"
        "- Lore states: confirmed, derived, suggested, ephemeral\n"
        "- Fail closed when authorization is ambiguous.\n"
        "- When a tool result is sufficient, report it. Do not add speculation.\n"
        "- When information is missing, say UNKNOWN. Do not fabricate.\n\n"
        f"Available context:\n{ctx_str}\n\n"
        f"Available tools/capabilities:\n{tools_str}"
    )
    user = f"Situation: {t.get('setup', '')}\n\nRequest: {t.get('input', '')}"
    
    return {
        "id": t["id"],
        "cup": "quick-worlds",
        "category": t["category"],
        "capability": t["category"],
        "system": system,
        "user": user,
        "validator": "structured",
        "expect": {"require": {}, "forbid_keys": []},
        "role_critical": True,
        "weight": 1,
        "temperature": 0.2,
        "max_tokens": 512,
    }


def adapt_vefr_task(t):
    """Convert task-bank format → olympics harness format for VEFR."""
    speaker_rules = t.get("speaker_rules", [])
    rules_str = "\n".join(f"- {r}" for r in speaker_rules) if speaker_rules else "(maintain character voice)"
    canon = t.get("canon", [])
    canon_str = "\n".join(f"- {c}" for c in canon) if canon else "(none supplied)"
    sealed = t.get("sealed_knowledge", [])
    sealed_str = "\n".join(f"- {s}" for s in sealed) if sealed else "(none)"
    
    system = (
        "You are a storyteller in a playable world. VEFR owns the facts; "
        "you imagine the response.\n\n"
        f"VOICE RULES\n{rules_str}\n\n"
        f"WORLD TRUTH (canonical, do not contradict)\n{canon_str}\n\n"
        f"SEALED KNOWLEDGE (you must NOT reveal these)\n{sealed_str}\n\n"
        "Respond in character. Do not narrate the player's actions. "
        "Do not resolve every mystery. Leave room for the player to continue."
    )
    
    # For multi-turn continuity tasks
    turns = t.get("turns")
    if turns:
        session = [{"system": system}]
        for turn in turns:
            session.append({"user": turn.get("input", "")})
        return {
            "id": t["id"],
            "cup": "quick-vefr",
            "category": t["category"],
            "capability": t["category"],
            "system": system,
            "user": "",
            "session": session,
            "validator": "prose_signals",
            "expect": {},
            "role_critical": True,
            "weight": 1,
            "temperature": 0.85,
            "max_tokens": 520,
        }
    
    user = t.get("input", "")
    if not user:
        user = t.get("setup", "")
    
    return {
        "id": t["id"],
        "cup": "quick-vefr",
        "category": t["category"],
        "capability": t["category"],
        "system": system,
        "user": user,
        "validator": "prose_signals",
        "expect": {},
        "role_critical": True,
        "weight": 1,
        "temperature": 0.85,
        "max_tokens": 520,
    }


def run_quick(suite_name, participant_key):
    """Run one suite against one participant. Returns results dict."""
    raw_tasks = load_quick_suite(suite_name)
    
    if suite_name == "worlds":
        tasks = [adapt_worlds_task(t) for t in raw_tasks]
    else:
        tasks = [adapt_vefr_task(t) for t in raw_tasks]
    
    participant = PARTICIPANTS[participant_key]
    
    print(f"\n{'='*60}")
    print(f"QUICK FINAL: {suite_name} × {participant_key}")
    print(f"Tasks: {len(tasks)}, Runs: 1")
    print(f"{'='*60}\n")
    
    server = ModelServer(participant)
    server.start()
    backend_probe = probe_backend(server.cid)
    
    results = []
    for task in tasks:
        t0 = time.time()
        session = task.get("session")
        
        if session:
            replies = []
            for turn in session:
                if turn.get("system"):
                    msgs = [{"role": "system", "content": turn["system"]}]
                    if turn.get("user"):
                        msgs.append({"role": "user", "content": turn["user"]})
                elif turn.get("user"):
                    msgs = [{"role": "user", "content": turn["user"]}]
                elif turn.get("give"):
                    msgs = [{"role": "assistant", "content": turn["give"]}]
                else:
                    continue
                msgs, _ = sanitize_messages(msgs)
                r = server.chat(msgs, temperature=task.get("temperature", 0.85),
                                max_tokens=task.get("max_tokens", 520))
                replies.append(r["content"])
            final_raw = replies[-1] if replies else ""
            meta = {"replies": replies, "final_raw": final_raw}
        else:
            msgs = [{"role": "system", "content": task["system"]},
                    {"role": "user", "content": task["user"]}]
            msgs, _ = sanitize_messages(msgs)
            r = server.chat(msgs, temperature=task.get("temperature", 0.2),
                            max_tokens=task.get("max_tokens", 512))
            final_raw = r["content"]
            meta = {"final_raw": final_raw}
        
        pr = P.parse(final_raw)
        vf = VALIDATORS.get(task.get("validator", "structured"))
        dims = vf(task, pr, meta) if vf else {"semantic": False, "protocol": False, "evidence": "no validator"}
        overall = all(dims.get(k) for k in ("semantic", "protocol"))
        
        result = {
            "task_id": task["id"],
            "category": task["category"],
            "raw": final_raw,
            "parse": pr,
            "dims": dims,
            "pass": overall,
            "latency_s": round(time.time() - t0, 3),
            "backend": backend_probe.get("backend", "unknown"),
        }
        results.append(result)
        
        status = "PASS" if overall else "FAIL"
        print(f"  {task['id']}: {status} ({result['latency_s']}s)")
    
    server.stop()
    
    # Write results
    outfile = RUNS_DIR / f"quick-{suite_name}-{participant_key}-{int(time.time())}.jsonl"
    with open(outfile, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    
    print(f"\nResults: {outfile}")
    return results, backend_probe


def main():
    print("QUICK FINALS — ONE RUN PER MODEL")
    print(f"CPU-only: OLY_NGPU={os.environ.get('OLY_NGPU', '999')}")
    print()
    
    all_results = {}
    
    # Worlds: LFM2.5
    r, bp = run_quick("worlds", "lfm2.5-2.6b")
    all_results[("worlds", "lfm2.5-2.6b")] = (r, bp)
    
    # Worlds: Qwen3
    r, bp = run_quick("worlds", "qwen3-1.7b")
    all_results[("worlds", "qwen3-1.7b")] = (r, bp)
    
    # VEFR: Phi-4-mini
    r, bp = run_quick("vefr", "phi-4-mini")
    all_results[("vefr", "phi-4-mini")] = (r, bp)
    
    # VEFR: Ministral 3
    r, bp = run_quick("vefr", "ministral-3-3b")
    all_results[("vefr", "ministral-3-3b")] = (r, bp)
    
    # Write combined
    combined = RUNS_DIR / f"quick-combined-{int(time.time())}.json"
    serializable = {}
    for (suite, model), (results, probe) in all_results.items():
        serializable[f"{suite}-{model}"] = {
            "results": results,
            "backend": probe,
        }
    with open(combined, "w") as f:
        json.dump(serializable, f, indent=2)
    
    print(f"\nCombined results: {combined}")


if __name__ == "__main__":
    main()
