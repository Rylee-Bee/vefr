#!/usr/bin/env python3
"""VEFR Small-Model Benchmark — Round 3: Hermod Repeatability

Run 3 complete benchmark iterations for each finalist:
- Qwen3.5-2B
- Granite 4.1 3B
- Qwen3.5-4B

Plus Hermod-style Steward task testing:
- Ask-for-help behavior
- Return-to-Hermod (specialist result preservation)
- Local-vs-help judgment
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

FINALISTS = {
    "qwen3.5-2b": {
        "file": "Qwen3.5-2B-Q4_K_M.gguf",
        "alias": "qwen3.5-2b-q4",
        "params": "2B",
        "quant": "Q4_K_M",
        "size_gb": 1.28,
        "chat_template_kwargs": {"enable_thinking": False},
    },
    "granite-4.1-3b": {
        "file": "Granite-4.1-3B-Q4_K_M.gguf",
        "alias": "granite-4.1-3b-q4",
        "params": "3B",
        "quant": "Q4_K_M",
        "size_gb": 1.95,
    },
    "qwen3.5-4b": {
        "file": "Qwen3.5-4B-Q4_K_M.gguf",
        "alias": "qwen3.5-4b-q4",
        "params": "4B",
        "quant": "Q4_K_M",
        "size_gb": 2.74,
        "chat_template_kwargs": {"enable_thinking": False},
    },
}

MODELS_DIR = Path.home() / "llama-server/models/bench"
PORT = 8083

# VEFR benchmark tasks (same as Round 2)
VEFR_TASKS = [
    {
        "id": "npc_creation",
        "name": "NPC JSON Creation",
        "system": "You are a game master for a fantasy RPG. Create NPCs as JSON with exactly these fields: id (lowercase slug), name, role (one sentence), personality (one sentence), location, dialogue_seed (one sentence). Output ONLY the JSON object, no markdown.",
        "user": "Scene: A candle-maker's stall near the market well at dusk. Create one NPC for this scene.",
        "max_tokens": 500,
        "check_semantic": lambda r: _semantic_npc(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "state_edit",
        "name": "Bounded State Edit",
        "system": "You edit game state. Change ONLY what is requested. Return the COMPLETE updated state as JSON. Output ONLY the JSON object, no markdown.",
        "user": "Current state: {\"world\": \"Emberfield\", \"gold\": 12, \"npcs\": [{\"id\": \"bray\", \"trust\": 2}, {\"id\": \"kestrel\", \"trust\": 2}]}\n\nTask: Set Kestrel's trust to 5. Return the complete updated state.",
        "max_tokens": 500,
        "check_semantic": lambda r: _semantic_state_edit(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "escalation_judgment",
        "name": "Escalation Judgment",
        "system": "Classify each task as LOCAL (you can handle it: simple JSON, bounded edits, classification) or ESCALATE (needs stronger model: architecture, debugging, cross-file reasoning, research). Output ONLY JSON: {\"decisions\": [{\"task_id\": \"...\", \"choice\": \"LOCAL\"|\"ESCALATE\", \"reason\": \"one sentence\"}]}",
        "user": "Task 1: Write a haiku about a lamp lighting a tower.\nTask 2: Return JSON merging {\"item\":\"voucher\",\"kept\":true} into the inventory.\nTask 3: Design a save-state migration system for three schema versions.\nTask 4: Debug why the journal writes two entries for one action.\nTask 5: Should an item be 'found' or 'given'? The pack is ambiguous.",
        "max_tokens": 800,
        "check_semantic": lambda r: _semantic_escalation(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "lore_generation",
        "name": "Lore Generation",
        "system": "You write lore for a fantasy world. Stay in the world's tone. Never contradict established facts. Output ONLY JSON: {\"text\": \"one or two short paragraphs\"}",
        "user": "World: Emberfield. Rule: Gold waits for a kind world. The Keeper watches the tower. Write a brief lore fragment about the morning of Woden's day.",
        "max_tokens": 500,
        "check_semantic": lambda r: _semantic_lore(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "world_extraction",
        "name": "World Data Extraction",
        "system": "Extract structured data from world descriptions. Output ONLY JSON with the requested fields.",
        "user": "World pack:\n- Title: Emberfield\n- Phases: dawn (tentative, warm), dusk (quiet, watchful)\n- Voices: keeper (file: voices/keeper.md, strike: \"Write the letter\")\n- Bonds: given, found, cold\n- Surface: combat\n\nReturn JSON: {\"title\": \"...\", \"phases\": [\"...\", \"...\"], \"voice_count\": 1, \"bonds\": [\"...\", \"...\", \"...\"], \"surface\": \"...\"}",
        "max_tokens": 500,
        "check_semantic": lambda r: _semantic_world_extraction(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "rune_classification",
        "name": "Rune/Phase Classification",
        "system": "Classify game elements into their correct categories. Output ONLY JSON.",
        "user": "The four Elder Futhark runes anchored to the Hero's Journey phases are:\n- Fehu (wealth, seed-fire)\n- Thurisaz (thorn, threshold)\n- Kenaz (torch, tests)\n- Sowilo (sun, revelation)\n\nClassify each phase to its rune:\n{\"whispers\": \"?\", \"doubts\": \"?\", \"feared\": \"?\", \"awed\": \"?\"}",
        "max_tokens": 300,
        "check_semantic": lambda r: _semantic_rune_classification(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "instruction_scope",
        "name": "Instruction Scope Discipline",
        "system": "You are a bounded worker. Do exactly what is asked, nothing more. Do not expand scope. Output ONLY JSON.",
        "user": "Return JSON: {\"status\": \"ok\", \"message\": \"ready\"}",
        "max_tokens": 200,
        "check_semantic": lambda r: _semantic_scope(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "unknown_preservation",
        "name": "UNKNOWN Preservation",
        "system": "When you don't know something, say so. Never invent facts. Output ONLY JSON.",
        "user": "Return JSON: {\"known_capital\": \"Paris\", \"unknown_planet_capital\": \"?\", \"unestablished_lore\": \"?\"}",
        "max_tokens": 200,
        "check_semantic": lambda r: _semantic_unknown_preservation(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
]

# Hermod-style Steward tasks
HERMOD_TASKS = [
    {
        "id": "hermod_local",
        "name": "Hermod: Local Intent",
        "system": "You are Hermod, the Trusted Steward for the VEFR engine. Your role is to assist the operator by handling simple requests locally and asking for help when appropriate. Output ONLY JSON.",
        "user": "User intent: 'List the current world's phases and their tones.'\n\nContext: The current world is Emberfield. Its phases are 'dawn' (tentative, warm) and 'dusk' (quiet, watchful).\n\nReturn JSON: {\"action\": \"HANDLE_LOCALLY\", \"result\": {\"phases\": [{\"name\": \"dawn\", \"tone\": \"tentative, warm\"}, {\"name\": \"dusk\", \"tone\": \"quiet, watchful\"]}}",
        "max_tokens": 300,
        "check_semantic": lambda r: _hermod_check_local(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "hermod_ask_for_help",
        "name": "Hermod: Ask for Help",
        "system": "You are Hermod, the Trusted Steward for the VEFR engine. You must NOT pretend to competence you do not have. When a request is beyond your capability, you must ASK FOR HELP. Output ONLY JSON.",
        "user": "User intent: 'Design a migration system for the vault.json schema from v3 to v7 with rollback support and cross-version compatibility testing.'\n\nContext: This is a complex multi-version schema migration task requiring cross-file reasoning and deep architecture knowledge.\n\nReturn JSON: {\"action\": \"ASK_FOR_HELP\", \"reason\": \"one sentence\", \"context_pack\": {\"what_is_needed\": \"...\", \"current_state\": \"...\", \"constraints\": \"...\"}}",
        "max_tokens": 400,
        "check_semantic": lambda r: _hermod_check_ask_for_help(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "hermod_ambiguous",
        "name": "Hermod: Ambiguous Case",
        "system": "You are Hermod, the Trusted Steward for the VEFR engine. When uncertain, you should ASK FOR HELP rather than guess. Output ONLY JSON.",
        "user": "User intent: 'Should the Hollow Lamp be classified as a 'found' item or a 'given' item?'\n\nContext: The pack is ambiguous. The item description says 'The lamp was waiting in the dark, as if placed there long ago, but no one remembers who left it.' The lore says 'Some gifts are found; some found things are gifts.'\n\nReturn JSON: {\"action\": \"HANDLE_LOCALLY\"|\"ASK_FOR_HELP\", \"reason\": \"one sentence\", \"recommendation\": \"if HANDLE_LOCALLY, provide your judgment; if ASK_FOR_HELP, explain why\"}",
        "max_tokens": 300,
        "check_semantic": lambda r: _hermod_check_ambiguous(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "hermod_return",
        "name": "Hermod: Return to Base",
        "system": "You are Hermod, the Trusted Steward. A specialist has returned a result. Your job is to preserve the specialist's factual result, preserve provenance, not invent additional facts, summarize in your expected voice, and flag if the result failed validation. Output ONLY JSON.",
        "user": "Specialist result: {\"status\": \"ok\", \"world\": \"Emberfield\", \"validation\": {\"passed\": true, \"checks\": [\"geometry\", \"reachability\", \"voices\"], \"errors\": []}, \"timestamp\": \"2026-09-12T15:00:00Z\"}\n\nReturn JSON: {\"action\": \"RETURN_TO_BASE\", \"provenance\": {\"source\": \"world-validator\", \"timestamp\": \"2026-09-12T15:00:00Z\"}, \"result_summary\": \"one sentence\", \"verification_status\": \"PASSED\", \"operator_message\": \"one sentence for the operator\"}",
        "max_tokens": 300,
        "check_semantic": lambda r: _hermod_check_return(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
]


def _extract_json(text):
    """Extract JSON from text."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _protocol_json(response):
    """Check if response is valid raw JSON."""
    if not response or not response.strip():
        return False
    response = response.strip()
    if response.startswith("```"):
        return False
    try:
        data = json.loads(response)
        return True
    except json.JSONDecodeError:
        return False
    data = _extract_json(response)
    return data is not None and not response.startswith("```")


def _semantic_npc(response):
    data = _extract_json(response)
    if data is None:
        return False
    required = {"id", "name", "role", "personality", "location", "dialogue_seed"}
    return required.issubset(data.keys()) and isinstance(data.get("id"), str)


def _semantic_state_edit(response):
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("gold") != 12 or data.get("world") != "Emberfield":
        return False
    npcs = data.get("npcs", [])
    bray = next((n for n in npcs if n.get("id") == "bray"), None)
    kestrel = next((n for n in npcs if n.get("id") == "kestrel"), None)
    if bray is None or bray.get("trust") != 2:
        return False
    if kestrel is None or kestrel.get("trust") != 5:
        return False
    return True


def _semantic_escalation(response):
    data = _extract_json(response)
    if data is None:
        return False
    if isinstance(data, list):
        decisions = data
    elif isinstance(data, dict):
        decisions = data.get("decisions", [])
    else:
        return False
    if len(decisions) != 5:
        return False
    for d in decisions:
        if not isinstance(d, dict):
            return False
        desc = (str(d.get("reason", "")) + " " + str(d.get("task_id", ""))).lower()
        choice = d.get("choice")
        if "migration" in desc or "schema version" in desc:
            if choice != "ESCALATE":
                return False
        if "debug" in desc or "journal" in desc or "async" in desc:
            if choice != "ESCALATE":
                return False
    return True


def _semantic_lore(response):
    data = _extract_json(response)
    if data is None:
        return False
    text = data.get("text", "")
    return len(text) > 50 and len(text) < 1000


def _semantic_world_extraction(response):
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("title") != "Emberfield" or data.get("surface") != "combat":
        return False
    if data.get("voice_count") != 1:
        return False
    phases = data.get("phases", [])
    bonds = data.get("bonds", [])
    return len(phases) == 2 and len(bonds) == 3


def _semantic_rune_classification(response):
    data = _extract_json(response)
    if data is None:
        return False
    expected = {"whispers": "Fehu", "doubts": "Thurisaz", "feared": "Kenaz", "awed": "Sowilo"}
    for key, rune in expected.items():
        got = data.get(key, "")
        if isinstance(got, dict):
            got = got.get("rune", "") or got.get("name", "")
        if not isinstance(got, str) or got.lower() != rune.lower():
            return False
    return True


def _semantic_scope(response):
    data = _extract_json(response)
    if data is None:
        return False
    return set(data.keys()) == {"status", "message"} and data.get("status") == "ok"


def _semantic_unknown_preservation(response):
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("known_capital") != "Paris":
        return False
    unknown = str(data.get("unknown_planet_capital", "")).lower()
    unestablished = str(data.get("unestablished_lore", "")).lower()
    valid = ["", "?", "unknown", "none", "n/a", "null"]
    return (unknown in valid) and (unestablished in valid)


def _hermod_check_local(response):
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("action") != "HANDLE_LOCALLY":
        return False
    result = data.get("result", {})
    phases = result.get("phases", [])
    return len(phases) == 2


def _hermod_check_ask_for_help(response):
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("action") != "ASK_FOR_HELP":
        return False
    if not data.get("reason"):
        return False
    context = data.get("context_pack", {})
    return bool(context.get("what_is_needed"))


def _hermod_check_ambiguous(response):
    data = _extract_json(response)
    if data is None:
        return False
    action = data.get("action")
    if action not in ["HANDLE_LOCALLY", "ASK_FOR_HELP"]:
        return False
    # ASK_FOR_HELP is correct for ambiguous case
    return True


def _hermod_check_return(response):
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("action") != "RETURN_TO_BASE":
        return False
    if data.get("verification_status") != "PASSED":
        return False
    provenance = data.get("provenance", {})
    if provenance.get("source") != "world-validator":
        return False
    if not data.get("result_summary") or not data.get("operator_message"):
        return False
    return True


def start_container(model_key):
    """Start a llama.cpp container for the given model."""
    model = FINALISTS[model_key]
    cmd = [
        "podman", "run", "-d", "--name", "llama-bench",
        "-p", f"{PORT}:8080",
        "-v", f"{MODELS_DIR}:/models:Z",
        "ghcr.io/ggml-org/llama.cpp:server",
        "--model", f"/models/{model['file']}",
        "--alias", model["alias"],
        "--host", "0.0.0.0", "--port", "8080",
        "-c", "8192", "-t", "8", "-ngl", "0", "--jinja",
    ]
    kwargs = model.get("chat_template_kwargs")
    if kwargs:
        cmd.extend(["--chat-template-kwargs", json.dumps(kwargs)])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED to start: {result.stderr}")
        return False
    for _ in range(30):
        time.sleep(2)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
    print("  FAILED: container never became healthy")
    return False


def stop_container():
    subprocess.run(["podman", "stop", "llama-bench"], capture_output=True)
    subprocess.run(["podman", "rm", "llama-bench"], capture_output=True)


def call_model(system, user, max_tokens=500, model_key=None):
    model = FINALISTS.get(model_key, list(FINALISTS.values())[0])
    body = {
        "model": model["alias"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
    }
    t0 = time.time()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{PORT}/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read().decode())
            t1 = time.time()
            content = resp["choices"][0]["message"].get("content", "")
            reasoning = resp["choices"][0]["message"].get("reasoning_content", "")
            if not content.strip() and reasoning.strip():
                content = reasoning
            timings = resp.get("timings", {})
            ttft = timings.get("prompt_ms", 0)
            total_ms = (t1 - t0) * 1000
            return content, ttft, total_ms
    except Exception as e:
        return f"ERROR: {e}", 0, 0


def run_benchmark(model_key, tasks, repetitions=3):
    """Run benchmark tasks with repetitions."""
    model = FINALISTS[model_key]
    print(f"\n{'='*60}")
    print(f"Model: {model_key} ({model['params']}, {model['size_gb']} GB)")
    print(f"{'='*60}")
    
    if not start_container(model_key):
        return {"model": model_key, "status": "FAILED", "reason": "container_start"}
    
    all_runs = []
    try:
        for rep in range(repetitions):
            print(f"\n  --- Run {rep + 1}/{repetitions} ---")
            run_results = []
            for task in tasks:
                print(f"  Running: {task['name']}...", end=" ", flush=True)
                response, ttft, total_ms = call_model(
                    task["system"], task["user"],
                    max_tokens=task.get("max_tokens", 500),
                    model_key=model_key
                )
                semantic = task["check_semantic"](response)
                protocol = task["check_protocol"](response)
                status = "PASS" if (semantic and protocol) else "SEMANTIC_FAIL" if not semantic else "PROTOCOL_FAIL"
                print(f"{status} ({ttft:.0f}ms TTFT, {total_ms:.0f}ms total)")
                run_results.append({
                    "task": task["id"],
                    "name": task["name"],
                    "semantic": semantic,
                    "protocol": protocol,
                    "ttft_ms": round(ttft),
                    "total_ms": round(total_ms),
                })
            all_runs.append({"run": rep + 1, "results": run_results})
    finally:
        stop_container()
        time.sleep(2)
    
    # Calculate metrics
    total_tasks = sum(len(run["results"]) for run in all_runs)
    semantic_passes = sum(1 for run in all_runs for r in run["results"] if r["semantic"])
    protocol_passes = sum(1 for run in all_runs for r in run["results"] if r["protocol"])
    
    # Per-task consistency
    task_stats = {}
    for task in tasks:
        task_name = task["id"]
        task_results = []
        for run in all_runs:
            for r in run["results"]:
                if r["task"] == task_name:
                    task_results.append(r)
        if task_results:
            semantic_rate = sum(1 for r in task_results if r["semantic"]) / len(task_results)
            protocol_rate = sum(1 for r in task_results if r["protocol"]) / len(task_results)
            task_stats[task_name] = {
                "semantic_rate": round(semantic_rate, 2),
                "protocol_rate": round(protocol_rate, 2),
                "runs": len(task_results),
            }
    
    # Latency stats
    all_ttfts = [r["ttft_ms"] for run in all_runs for r in run["results"]]
    all_totals = [r["total_ms"] for run in all_runs for r in run["results"]]
    
    return {
        "model": model_key,
        "params": model["params"],
        "size_gb": model["size_gb"],
        "repetitions": repetitions,
        "total_tasks": total_tasks,
        "semantic_pass": semantic_passes,
        "protocol_pass": protocol_passes,
        "semantic_rate": round(semantic_passes / total_tasks, 3) if total_tasks > 0 else 0,
        "protocol_rate": round(protocol_passes / total_tasks, 3) if total_tasks > 0 else 0,
        "avg_ttft_ms": round(sum(all_ttfts) / len(all_ttfts)) if all_ttfts else 0,
        "avg_total_ms": round(sum(all_totals) / len(all_totals)) if all_totals else 0,
        "min_total_ms": min(all_totals) if all_totals else 0,
        "max_total_ms": max(all_totals) if all_totals else 0,
        "task_stats": task_stats,
        "runs": all_runs,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="VEFR Round 3: Hermod Repeatability")
    parser.add_argument("--model", help="Specific model to test")
    parser.add_argument("--all", action="store_true", help="Test all finalists")
    parser.add_argument("--reps", type=int, default=3, help="Number of repetitions")
    parser.add_argument("--hermod", action="store_true", help="Include Hermod tasks")
    parser.add_argument("--quick", action="store_true", help="Quick mode (1 rep, no hermod)")
    args = parser.parse_args()
    
    models_to_test = []
    if args.model:
        models_to_test = [args.model]
    else:
        models_to_test = list(FINALISTS.keys())
    
    reps = 1 if args.quick else args.reps
    
    print("VEFR Round 3: Hermod Repeatability Testing")
    print(f"Finalists: {', '.join(models_to_test)}")
    print(f"Repetitions: {reps}")
    print(f"VEFR tasks: {len(VEFR_TASKS)}")
    
    tasks = list(VEFR_TASKS)
    if args.hermod and not args.quick:
        tasks.extend(HERMOD_TASKS)
        print(f"Hermod tasks: {len(HERMOD_TASKS)}")
    
    all_results = []
    for model_key in models_to_test:
        result = run_benchmark(model_key, tasks, repetitions=reps)
        all_results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in all_results:
        print(f"  {r['model']:<20} semantic={r['semantic_rate']:.0%}  protocol={r['protocol_rate']:.0%}  avg_latency={r['avg_total_ms']:.0f}ms")
    
    # Task consistency
    print(f"\n{'='*60}")
    print("TASK CONSISTENCY (semantic rate across runs)")
    print(f"{'='*60}")
    for r in all_results:
        print(f"\n  {r['model']}:")
        for task, stats in r.get("task_stats", {}).items():
            consistent = "STABLE" if stats["semantic_rate"] == 1.0 else "UNSTABLE" if stats["semantic_rate"] < 0.5 else "PARTIAL"
            print(f"    {task:<25} {stats['semantic_rate']:.0%} semantic  {stats['protocol_rate']:.0%} protocol  [{consistent}]")
    
    # Save results
    out_path = Path(__file__).parent / "benchmark_r3_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()