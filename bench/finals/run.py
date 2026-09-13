"""Small Model Finals — runner for curated task banks.

Runs the finalized Worlds Brain and VEFR Storyteller task suites against
the four finalist models. Uses the existing olympics harness infrastructure.

Usage:
  uv run python -m bench.finals.run --suite worlds --participant lfm2.5-2.6b
  uv run python -m bench.finals.run --suite vefr --participant phi-4-mini
  uv run python -m bench.finals.run --suite worlds --all
  uv run python -m bench.finals.run --suite vefr --all
  uv run python -m bench.finals.run --all --all-participants

Each invocation runs ONE participant on ONE suite (or all), producing:
  bench/finals/runs/<suite>-<participant>-<timestamp>.jsonl
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add parent to path for bench imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bench.olympics.participants import PARTICIPANTS
from bench.olympics.runtime import ModelServer
from bench.olympics.records import probe_backend
from bench.olympics.harness import run_tasks
from bench.olympics import parse as P
from bench.olympics.validators import VALIDATORS

SUITE_DIR = Path(__file__).parent.parent / "taskbank"
RUNS_DIR = Path(__file__).parent / "runs"

SUITES = {
    "worlds": SUITE_DIR / "worlds-finalized.jsonl",
    "vefr": SUITE_DIR / "vefr-curated-final.jsonl",
}

WORLDS_PARTICIPANTS = ["lfm2.5-2.6b", "qwen3-1.7b"]
VEFR_PARTICIPANTS = ["phi-4-mini", "ministral-3-3b"]


def load_suite(name):
    path = SUITES[name]
    tasks = []
    with open(path) as f:
        for line in f:
            t = json.loads(line)
            # Adapt task format to olympics harness format
            tasks.append(adapt_task(t, name))
    return tasks


def adapt_task(task, suite):
    """Convert task-bank format to olympics harness format."""
    if suite == "worlds":
        # Worlds tasks: build system/user from setup + input
        system = build_worlds_system(task)
        user = build_worlds_user(task)
        adapted = {
            "id": task["id"],
            "cup": "finals-worlds",
            "category": task["category"],
            "capability": task["category"],
            "name": task.get("id", ""),
            "system": system,
            "user": user,
            "validator": "structured",
            "expect": {"require": {}, "forbid_keys": []},
            "role_critical": True,
            "weight": 1,
            "temperature": 0.2,
            "max_tokens": 512,
        }
    else:
        # VEFR tasks: build scene packet
        system = build_vefr_system(task)
        user = build_vefr_user(task)
        adapted = {
            "id": task["id"],
            "cup": "finals-vefr",
            "category": task["category"],
            "capability": task["category"],
            "name": task.get("id", ""),
            "system": system,
            "user": user,
            "validator": "prose_signals",
            "expect": task.get("expect", {}),
            "role_critical": True,
            "weight": 1,
            "temperature": 0.85,
            "max_tokens": 520,
        }
        # Multi-turn continuity tasks
        if task.get("turns"):
            adapted["session"] = build_vefr_session(task)
    return adapted


def build_worlds_system(task):
    """Build system prompt for Worlds Brain task."""
    context_items = task.get("available_context", [])
    tools = task.get("available_tools", [])
    context_str = "\n".join(f"- {c}" for c in context_items) if context_items else "(none)"
    tools_str = "\n".join(f"- {t}" for t in tools) if tools else "(none)"
    return (
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
        "- Fail closed when authorization is ambiguous.\n\n"
        f"Available context:\n{context_str}\n\n"
        f"Available tools/capabilities:\n{tools_str}"
    )


def build_worlds_user(task):
    """Build user prompt for Worlds Brain task."""
    setup = task.get("setup", "")
    inp = task.get("input", "")
    return f"Situation: {setup}\n\nRequest: {inp}"


def build_vefr_system(task):
    """Build system prompt for VEFR Storyteller task."""
    speaker = task.get("setup", "").split("\n")[0] if task.get("setup") else "A character"
    speaker_rules = task.get("speaker_rules", [])
    rules_str = "\n".join(f"- {r}" for r in speaker_rules) if speaker_rules else ""
    canon = task.get("canon", [])
    canon_str = "\n".join(f"- {c}" for c in canon) if canon else "(none supplied)"
    sealed = task.get("sealed_knowledge", [])
    sealed_str = "\n".join(f"- {s}" for s in sealed) if sealed else "(none)"
    return (
        "You are a storyteller in a playable world. VEFR owns the facts; "
        "you imagine the response.\n\n"
        f"WHO YOU ARE\n{speaker}\n\n"
        f"VOICE RULES\n{rules_str}\n\n"
        f"WORLD TRUTH (canonical, do not contradict)\n{canon_str}\n\n"
        f"SEALED KNOWLEDGE (you must NOT reveal these)\n{sealed_str}"
    )


def build_vefr_user(task):
    """Build user prompt for VEFR Storyteller task."""
    inp = task.get("input", "")
    scene = task.get("setup", "")
    return f"Scene:\n{scene}\n\n{inp}"


def build_vefr_session(task):
    """Build multi-turn session for continuity tasks."""
    turns = task.get("turns", [])
    system = build_vefr_system(task)
    session = [{"system": system}]
    for turn in turns:
        session.append({"user": turn.get("input", "")})
    return session


def run_suite(suite_name, participant_key, n_runs=3):
    """Run one suite against one participant."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    tasks = load_suite(suite_name)
    participant = PARTICIPANTS[participant_key]

    print(f"\n{'='*60}")
    print(f"FINALS RUN: {suite_name} × {participant_key}")
    print(f"Tasks: {len(tasks)}, Runs: {n_runs}")
    print(f"{'='*60}\n")

    server = ModelServer(participant)
    server.start()
    backend_probe = probe_backend(server.cid)

    results = []
    for run_idx in range(n_runs):
        run_id = f"final-{suite_name}-{participant_key}-r{run_idx+1}-{int(time.time())}"
        print(f"  Run {run_idx+1}/{n_runs}: {run_id}")

        for task in tasks:
            trial = _run_one_task(server, task, backend_probe)
            trial["suite"] = suite_name
            trial["run_idx"] = run_idx
            trial["run_id"] = run_id
            results.append(trial)
            status = "PASS" if trial.get("verdict", {}).get("semantic") else "FAIL"
            print(f"    {task['id']}: {status}")

    # Write results
    outfile = RUNS_DIR / f"{suite_name}-{participant_key}-{int(time.time())}.jsonl"
    with open(outfile, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    server.stop()
    print(f"\nResults: {outfile}")
    return outfile


def _run_one_task(server, task, backend_probe):
    """Run one task, return trial dict."""
    t0 = time.time()
    session = task.get("session")

    if session:
        # Multi-turn
        replies = []
        for turn in session:
            if turn.get("system"):
                msgs = [{"role": "system", "content": turn["system"]},
                        {"role": "user", "content": turn.get("user", "")}]
            elif turn.get("user"):
                msgs = [{"role": "user", "content": turn["user"]}]
            else:
                continue
            raw = server.generate(msgs, max_tokens=task.get("max_tokens", 512),
                                  temperature=task.get("temperature", 0.85))
            replies.append(raw)
        final_raw = replies[-1] if replies else ""
        meta = {"replies": replies, "final_raw": final_raw}
    else:
        # Single-turn
        msgs = [{"role": "system", "content": task["system"]},
                {"role": "user", "content": task["user"]}]
        final_raw = server.generate(msgs, max_tokens=task.get("max_tokens", 512),
                                    temperature=task.get("temperature", 0.2))
        meta = {"final_raw": final_raw}

    # Parse
    pr = P.parse(final_raw)

    # Validate
    validator_name = task.get("validator", "structured")
    validator = VALIDATORS.get(validator_name)
    if validator:
        verdict = validator(task, pr, meta)
    else:
        verdict = {"semantic": False, "protocol": False, "evidence": "no validator"}

    latency = time.time() - t0
    return {
        "task_id": task["id"],
        "raw": final_raw,
        "parsed": pr,
        "verdict": verdict,
        "latency_s": round(latency, 3),
        "backend": backend_probe.get("backend", "unknown"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Small Model Finals runner")
    parser.add_argument("--suite", choices=["worlds", "vefr", "all"])
    parser.add_argument("--participant", help="Participant key")
    parser.add_argument("--all-participants", action="store_true")
    parser.add_argument("--runs", type=int, default=3, help="Runs per participant")
    args = parser.parse_args()

    suites = [args.suite] if args.suite != "all" else ["worlds", "vefr"]

    if args.all_participants:
        participants = WORLDS_PARTICIPANTS + VEFR_PARTICIPANTS
    elif args.participant:
        participants = [args.participant]
    else:
        parser.error("Specify --participant or --all-participants")

    for suite in suites:
        suite_participants = (
            WORLDS_PARTICIPANTS if suite == "worlds" else VEFR_PARTICIPANTS
        )
        for p in participants:
            if p in suite_participants:
                run_suite(suite, p, args.runs)
