#!/usr/bin/env python3
"""VEFR Small-Model Benchmark — Round 2

Improvements over Round 1:
- Separate semantic correctness and protocol compliance scoring
- Multiple repetitions for repeatability measurement
- Winner-challenge battery for Qwen3.5-2B
- Real VEFR task integration

Score each task on two axes:
- SEMANTIC: Did the model solve the task correctly?
- PROTOCOL: Did the model follow the output contract?
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# All models (Round 1 + Round 2)
MODELS = {
    # Round 1 controls
    "qwen3.5-0.8b": {
        "file": "Qwen3.5-0.8B-Q4_K_M.gguf",
        "alias": "qwen3.5-0.8b-q4",
        "params": "0.8B",
        "quant": "Q4_K_M",
        "chat_template_kwargs": {"enable_thinking": False},
    },
    "qwen3.5-2b": {
        "file": "Qwen3.5-2B-Q4_K_M.gguf",
        "alias": "qwen3.5-2b-q4",
        "params": "2B",
        "quant": "Q4_K_M",
        "chat_template_kwargs": {"enable_thinking": False},
    },
    "phi-4-mini": {
        "file": "Phi-4-mini-Q4_K_M.gguf",
        "alias": "phi-4-mini-q4",
        "params": "3.8B",
        "quant": "Q4_K_M",
    },
    # Round 2 challengers
    "qwen3.5-4b": {
        "file": "Qwen3.5-4B-Q4_K_M.gguf",
        "alias": "qwen3.5-4b-q4",
        "params": "4B",
        "quant": "Q4_K_M",
        "chat_template_kwargs": {"enable_thinking": False},
    },
    "smollm3-3b": {
        "file": "SmolLM3-3B-Q4_K_M.gguf",
        "alias": "smollm3-3b-q4",
        "params": "3B",
        "quant": "Q4_K_M",
    },
    "granite-4.1-3b": {
        "file": "Granite-4.1-3B-Q4_K_M.gguf",
        "alias": "granite-4.1-3b-q4",
        "params": "3B",
        "quant": "Q4_K_M",
    },
    "gemma-3-4b": {
        "file": "Gemma-3-4B-Q4_K_M.gguf",
        "alias": "gemma-3-4b-q4",
        "params": "4B",
        "quant": "Q4_K_M",
    },
    "llama-3.2-1b": {
        "file": "Llama-3.2-1B-Q4_K_M.gguf",
        "alias": "llama-3.2-1b-q4",
        "params": "1B",
        "quant": "Q4_K_M",
    },
}

MODELS_DIR = Path.home() / "llama-server/models/bench"
PORT = 8083

# Round 2 VEFR tasks with dual-axis scoring
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

# Winner challenge tasks (adversarial)
WINNER_CHALLENGE_TASKS = [
    {
        "id": "missing_info",
        "name": "Missing Information → UNKNOWN",
        "system": "You are a precise worker. If information is missing, say so. Output ONLY JSON.",
        "user": "Return JSON: {\"keeper_name\": \"?\", \"tower_height\": \"?\", \"bell_material\": \"bronze\"}\n\nContext: The bell is made of bronze. The keeper's name is not provided. The tower height is not provided.",
        "max_tokens": 200,
        "check_semantic": lambda r: _check_missing_info(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "conflicting_evidence",
        "name": "Conflicting Evidence",
        "system": "You are a precise worker. If evidence conflicts, note the conflict. Output ONLY JSON.",
        "user": "Source A says the phase is 'dusk'. Source B says the phase is 'night'. Return JSON: {\"phase\": \"?\", \"conflict\": true}",
        "max_tokens": 200,
        "check_semantic": lambda r: _check_conflicting(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "nested_json",
        "name": "Exact Nested JSON Schema",
        "system": "Output ONLY JSON matching the exact schema requested.",
        "user": "Return JSON: {\"world\": {\"name\": \"Emberfield\", \"phases\": [{\"name\": \"dawn\", \"tone\": \"warm\"}, {\"name\": \"dusk\", \"tone\": \"quiet\"}], \"npcs\": [{\"id\": \"keeper\", \"trust\": 3}]}}",
        "max_tokens": 300,
        "check_semantic": lambda r: _check_nested_json(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "multi_condition_edit",
        "name": "Multi-Condition State Edit",
        "system": "You edit game state. Apply ALL requested changes. Preserve everything else. Output ONLY JSON.",
        "user": "Current state: {\"gold\": 10, \"npcs\": [{\"id\": \"a\", \"trust\": 1}, {\"id\": \"b\", \"trust\": 2}, {\"id\": \"c\", \"trust\": 3}], \"phase\": \"dusk\"}\n\nChanges: Set gold to 20. Set npc 'b' trust to 5. Set phase to 'night'. Return complete state.",
        "max_tokens": 300,
        "check_semantic": lambda r: _check_multi_condition_edit(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "scope_trap",
        "name": "Scope Trap",
        "system": "You are a bounded worker. Do exactly what is asked, nothing more. Output ONLY JSON.",
        "user": "Return JSON: {\"result\": \"ok\"}",
        "max_tokens": 100,
        "check_semantic": lambda r: _check_scope_trap(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
    {
        "id": "negative_instruction",
        "name": "Negative Instruction / Do-Not-Change",
        "system": "You edit game state. Follow negative instructions carefully. Output ONLY JSON.",
        "user": "Current state: {\"gold\": 10, \"phase\": \"dusk\", \"npcs\": [{\"id\": \"keeper\", \"trust\": 3}]}\n\nTask: Set gold to 20. Do NOT change the phase. Do NOT change the npc trust. Return complete state.",
        "max_tokens": 200,
        "check_semantic": lambda r: _check_negative_instruction(r),
        "check_protocol": lambda r: _protocol_json(r),
    },
]


def _extract_json(text):
    """Extract JSON from text, stripping markdown fences if present."""
    text = text.strip()
    
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try stripping markdown fences
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try finding any JSON object in the text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    
    return None


def _protocol_json(response):
    """Check if response is valid JSON (no markdown fences, no extra prose)."""
    if not response or not response.strip():
        return False
    response = response.strip()
    
    # Check for markdown fences (protocol violation)
    if response.startswith("```"):
        return False
    
    # Check for extra prose before/after JSON
    # Valid JSON should start with { and end with }
    try:
        data = json.loads(response)
        # Ensure no extra text
        if response.count("{") != response.count("}"):
            return False
        return True
    except json.JSONDecodeError:
        pass
    
    # Try extracting JSON
    data = _extract_json(response)
    if data is None:
        return False
    
    # If we had to extract, there was extra text (protocol violation)
    return False


def _semantic_npc(response):
    """Check NPC JSON has required fields."""
    data = _extract_json(response)
    if data is None:
        return False
    required = {"id", "name", "role", "personality", "location", "dialogue_seed"}
    return required.issubset(data.keys()) and isinstance(data.get("id"), str)


def _semantic_state_edit(response):
    """Check bounded state edit."""
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("gold") != 12:
        return False
    if data.get("world") != "Emberfield":
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
    """Check escalation judgments."""
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
    """Check lore generation."""
    data = _extract_json(response)
    if data is None:
        return False
    text = data.get("text", "")
    return len(text) > 50 and len(text) < 1000


def _semantic_world_extraction(response):
    """Check world data extraction."""
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("title") != "Emberfield":
        return False
    if data.get("surface") != "combat":
        return False
    if data.get("voice_count") != 1:
        return False
    phases = data.get("phases", [])
    if len(phases) != 2:
        return False
    bonds = data.get("bonds", [])
    if len(bonds) != 3:
        return False
    return True


def _semantic_rune_classification(response):
    """Check rune/phase classification."""
    data = _extract_json(response)
    if data is None:
        return False
    expected = {
        "whispers": "Fehu",
        "doubts": "Thurisaz",
        "feared": "Kenaz",
        "awed": "Sowilo",
    }
    for key, rune in expected.items():
        got = data.get(key, "")
        if isinstance(got, dict):
            got = got.get("rune", "") or got.get("name", "")
        if not isinstance(got, str):
            return False
        if got.lower() != rune.lower():
            return False
    return True


def _semantic_scope(response):
    """Check instruction scope discipline."""
    data = _extract_json(response)
    if data is None:
        return False
    if set(data.keys()) != {"status", "message"}:
        return False
    if data.get("status") != "ok":
        return False
    return True


def _semantic_unknown_preservation(response):
    """Check UNKNOWN preservation."""
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("known_capital") != "Paris":
        return False
    unknown = str(data.get("unknown_planet_capital", "")).lower()
    unestablished = str(data.get("unestablished_lore", "")).lower()
    valid_unknowns = ["", "?", "unknown", "none", "n/a", "null"]
    if unknown and unknown not in valid_unknowns:
        return False
    if unestablished and unestablished not in valid_unknowns:
        return False
    return True


def _check_missing_info(response):
    """Check missing info → UNKNOWN."""
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("bell_material") != "bronze":
        return False
    keeper = str(data.get("keeper_name", "")).lower()
    tower = str(data.get("tower_height", "")).lower()
    valid = ["", "?", "unknown", "none", "n/a", "null"]
    if keeper and keeper not in valid:
        return False
    if tower and tower not in valid:
        return False
    return True


def _check_conflicting(response):
    """Check conflicting evidence handling."""
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("conflict") is not True:
        return False
    phase = str(data.get("phase", "")).lower()
    if phase not in ["?", "unknown", "conflict", "none"]:
        return False
    return True


def _check_nested_json(response):
    """Check exact nested JSON schema."""
    data = _extract_json(response)
    if data is None:
        return False
    world = data.get("world", {})
    if world.get("name") != "Emberfield":
        return False
    phases = world.get("phases", [])
    if len(phases) != 2:
        return False
    npcs = world.get("npcs", [])
    if len(npcs) != 1:
        return False
    if npcs[0].get("id") != "keeper" or npcs[0].get("trust") != 3:
        return False
    return True


def _check_multi_condition_edit(response):
    """Check multi-condition state edit."""
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("gold") != 20:
        return False
    if data.get("phase") != "night":
        return False
    npcs = data.get("npcs", [])
    a = next((n for n in npcs if n.get("id") == "a"), None)
    b = next((n for n in npcs if n.get("id") == "b"), None)
    c = next((n for n in npcs if n.get("id") == "c"), None)
    if a is None or a.get("trust") != 1:
        return False
    if b is None or b.get("trust") != 5:
        return False
    if c is None or c.get("trust") != 3:
        return False
    return True


def _check_scope_trap(response):
    """Check scope trap."""
    data = _extract_json(response)
    if data is None:
        return False
    if set(data.keys()) != {"result"}:
        return False
    if data.get("result") != "ok":
        return False
    return True


def _check_negative_instruction(response):
    """Check negative instruction / do-not-change."""
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("gold") != 20:
        return False
    if data.get("phase") != "dusk":
        return False
    npcs = data.get("npcs", [])
    keeper = next((n for n in npcs if n.get("id") == "keeper"), None)
    if keeper is None or keeper.get("trust") != 3:
        return False
    return True


def start_container(model_key):
    """Start a llama.cpp container for the given model."""
    model = MODELS[model_key]
    model_path = MODELS_DIR / model["file"]
    
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
        print(f"  FAILED to start container: {result.stderr}")
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
    """Stop and remove the benchmark container."""
    subprocess.run(["podman", "stop", "llama-bench"], capture_output=True)
    subprocess.run(["podman", "rm", "llama-bench"], capture_output=True)


def call_model(system, user, max_tokens=500, model_key=None):
    """Call the running model and return (response, ttft_ms, total_ms)."""
    if model_key is None:
        model_key = next(iter(MODELS))
    model = MODELS.get(model_key)
    if model is None:
        return f"ERROR: model {model_key} not found", 0, 0
    
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


def run_benchmark(model_key, tasks, repetitions=1):
    """Run benchmark tasks for a model with optional repetitions."""
    model = MODELS[model_key]
    print(f"\n{'='*60}")
    print(f"Model: {model_key} ({model['params']}, {model['quant']})")
    print(f"{'='*60}")
    
    if not start_container(model_key):
        return {"model": model_key, "status": "FAILED", "reason": "container_start"}
    
    results = []
    try:
        for rep in range(repetitions):
            if repetitions > 1:
                print(f"\n  --- Run {rep + 1}/{repetitions} ---")
            
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
                
                results.append({
                    "run": rep + 1,
                    "task": task["id"],
                    "name": task["name"],
                    "semantic": semantic,
                    "protocol": protocol,
                    "ttft_ms": round(ttft),
                    "total_ms": round(total_ms),
                    "response_preview": response[:100] if response else "",
                })
    finally:
        stop_container()
        time.sleep(2)
    
    # Calculate scores
    total = len(results)
    semantic_pass = sum(1 for r in results if r["semantic"])
    protocol_pass = sum(1 for r in results if r["protocol"])
    
    # Per-task consistency (for repeated runs)
    task_consistency = {}
    for task in tasks:
        task_results = [r for r in results if r["task"] == task["id"]]
        if task_results:
            semantic_rate = sum(1 for r in task_results if r["semantic"]) / len(task_results)
            protocol_rate = sum(1 for r in task_results if r["protocol"]) / len(task_results)
            task_consistency[task["id"]] = {
                "semantic_rate": round(semantic_rate, 2),
                "protocol_rate": round(protocol_rate, 2),
                "runs": len(task_results),
            }
    
    return {
        "model": model_key,
        "params": model["params"],
        "quant": model["quant"],
        "repetitions": repetitions,
        "total_tasks": total,
        "semantic_pass": semantic_pass,
        "protocol_pass": protocol_pass,
        "semantic_rate": round(semantic_pass / total, 3) if total > 0 else 0,
        "protocol_rate": round(protocol_pass / total, 3) if total > 0 else 0,
        "task_consistency": task_consistency,
        "results": results,
    }


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="VEFR Round 2 Benchmark")
    parser.add_argument("--model", help="Specific model to test")
    parser.add_argument("--all", action="store_true", help="Test all models")
    parser.add_argument("--reps", type=int, default=1, help="Number of repetitions")
    parser.add_argument("--winner-challenge", action="store_true", help="Run winner challenge")
    parser.add_argument("--real-task", action="store_true", help="Run real VEFR task")
    args = parser.parse_args()
    
    models_to_test = []
    if args.model:
        models_to_test = [args.model]
    elif args.all:
        models_to_test = list(MODELS.keys())
    else:
        models_to_test = list(MODELS.keys())
    
    print("VEFR Round 2 Benchmark")
    print(f"Models: {', '.join(models_to_test)}")
    print(f"Repetitions: {args.reps}")
    print(f"Tasks: {len(VEFR_TASKS)}")
    
    all_results = []
    for model_key in models_to_test:
        if model_key not in MODELS:
            print(f"Unknown model: {model_key}")
            continue
        result = run_benchmark(model_key, VEFR_TASKS, repetitions=args.reps)
        all_results.append(result)
    
    # Winner challenge
    if args.winner_challenge:
        print("\n" + "="*60)
        print("WINNER CHALLENGE")
        print("="*60)
        
        challenge_models = ["qwen3.5-2b"]
        # Add best challenger if specified
        if args.model and args.model != "qwen3.5-2b":
            challenge_models.append(args.model)
        
        for model_key in challenge_models:
            if model_key not in MODELS:
                continue
            result = run_benchmark(model_key, WINNER_CHALLENGE_TASKS, repetitions=1)
            result["challenge"] = True
            all_results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in all_results:
        if "challenge" in r:
            print(f"  {r['model']:<20} CHALLENGE  semantic={r['semantic_pass']}/{r['total_tasks']}  protocol={r['protocol_pass']}/{r['total_tasks']}")
        else:
            print(f"  {r['model']:<20} semantic={r['semantic_rate']:.0%}  protocol={r['protocol_rate']:.0%}")
    
    # Save results
    out_path = Path(__file__).parent / "benchmark_r2_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()