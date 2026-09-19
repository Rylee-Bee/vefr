#!/usr/bin/env python3
"""VEFR Small-Model Benchmark — Round 4

Tests new challengers against Granite 4.1 3B control.
Focus: smallest suitable replaceable brain for Hermod Trusted Steward role.
"""

import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path

# Models to test
MODELS = {
    # Control (current winner)
    "granite-4.1-3b": {
        "file": "Granite-4.1-3B-Q4_K_M.gguf",
        "alias": "granite-4.1-3b",
        "params": "3B",
        "quant": "Q4_K_M",
        "size_gb": 1.95,
        "reasoning_default": False,
    },
    # New challengers
    "granite-4.2-3b": {
        "file": "granite-4.2-3b-Q4_K_M.gguf",
        "alias": "granite-4.2-3b",
        "params": "4B",
        "quant": "Q4_K_M",
        "size_gb": 2.15,
        "reasoning_default": True,
        "chat_template_kwargs": {"enable_thinking": False},
    },
    "lfm2.5-2.6b": {
        "file": "LFM2.5-2.6B-Q4_K_M.gguf",
        "alias": "lfm2.5-2.6b",
        "params": "2.6B",
        "quant": "Q4_K_M",
        "size_gb": 1.55,
        "reasoning_default": False,
    },
    # Re-test previous candidates
    "ministral-3-3b": {
        "file": "Ministral-3-3B-Q4_K_M.gguf",
        "alias": "ministral-3-3b",
        "params": "3.4B",
        "quant": "Q4_K_M",
        "size_gb": 2.15,
        "reasoning_default": False,
    },
    "smollm3-3b": {
        "file": "SmolLM3-3B-Q4_K_M.gguf",
        "alias": "smollm3-3b",
        "params": "3B",
        "quant": "Q4_K_M",
        "size_gb": 1.92,
        "reasoning_default": False,
    },
}

MODELS_DIR = Path.home() / "llama-server/models/bench"
PORT = 8083

# Tasks
TASKS = [
    {
        "id": "npc_creation",
        "name": "NPC JSON Creation",
        "system": "You are a game master for a fantasy RPG. Create NPCs as JSON with exactly these fields: id (lowercase slug), name, role (one sentence), personality (one sentence), location, dialogue_seed (one sentence). Output ONLY the JSON object, no markdown.",
        "user": "Scene: A candle-maker's stall near the market well at dusk. Create one NPC for this scene.",
        "max_tokens": 500,
        "check": lambda r: _semantic_npc(r) and _protocol_json(r),
    },
    {
        "id": "state_edit",
        "name": "Bounded State Edit",
        "system": "You edit game state. Change ONLY what is requested. Return the COMPLETE updated state as JSON. Output ONLY the JSON object, no markdown.",
        "user": "Current state: {\"world\": \"Emberfield\", \"gold\": 12, \"npcs\": [{\"id\": \"bray\", \"trust\": 2}, {\"id\": \"kestrel\", \"trust\": 2}]}\n\nTask: Set Kestrel's trust to 5. Return the complete updated state.",
        "max_tokens": 500,
        "check": lambda r: _semantic_state_edit(r) and _protocol_json(r),
    },
    {
        "id": "escalation_ambiguous",
        "name": "Ambiguous Escalation",
        "system": "You are Hermod. When uncertain, ASK FOR HELP rather than guess. Output ONLY JSON.",
        "user": "User intent: 'Should the Hollow Lamp be classified as a found item or a given item?'\n\nContext: The pack is ambiguous. The item description says 'The lamp was waiting in the dark, as if placed there long ago, but no one remembers who left it.' The lore says 'Some gifts are found; some found things are gifts.'\n\nReturn JSON: {\"action\": \"HANDLE_LOCALLY\"|\"ASK_FOR_HELP\", \"reason\": \"one sentence\"}",
        "max_tokens": 300,
        "check": lambda r: _semantic_escalation_ambiguous(r),
    },
    {
        "id": "rune_classification",
        "name": "Rune Classification",
        "system": "Classify game elements into their correct categories. Output ONLY JSON.",
        "user": "The four Elder Futhark runes anchored to the Hero's Journey phases are:\n- Fehu (wealth, seed-fire)\n- Thurisaz (thorn, threshold)\n- Kenaz (torch, tests)\n- Sowilo (sun, revelation)\n\nClassify each phase to its rune:\n{\"whispers\": \"?\", \"doubts\": \"?\", \"feared\": \"?\", \"awed\": \"?\"}",
        "max_tokens": 300,
        "check": lambda r: _semantic_rune_classification(r) and _protocol_json(r),
    },
    {
        "id": "unknown_preservation",
        "name": "UNKNOWN Preservation",
        "system": "When you don't know something, say so. Never invent facts. Output ONLY JSON.",
        "user": "Return JSON: {\"known_capital\": \"Paris\", \"unknown_planet_capital\": \"?\", \"unestablished_lore\": \"?\"}",
        "max_tokens": 200,
        "check": lambda r: _semantic_unknown_preservation(r),
    },
    {
        "id": "instruction_scope",
        "name": "Instruction Scope",
        "system": "You are a bounded worker. Do exactly what is asked, nothing more. Output ONLY JSON.",
        "user": "Return JSON: {\"status\": \"ok\", \"message\": \"ready\"}",
        "max_tokens": 100,
        "check": lambda r: _semantic_scope(r),
    },
]


def _extract_json(text):
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown fences
    cleaned = re.sub(r'```(?:json)?\s*\n?', '', text).strip()
    try:
        return json.loads(cleaned)
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
    if not response or not response.strip():
        return False
    response = response.strip()
    if response.startswith("```"):
        return False
    try:
        json.loads(response)
        return True
    except json.JSONDecodeError:
        return False


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


def _semantic_escalation_ambiguous(response):
    data = _extract_json(response)
    if data is None:
        return False
    action = data.get("action")
    return action in ["HANDLE_LOCALLY", "ASK_FOR_HELP"]


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


def _semantic_scope(response):
    data = _extract_json(response)
    if data is None:
        return False
    return set(data.keys()) == {"status", "message"} and data.get("status") == "ok"


def start_container(model_key):
    model = MODELS[model_key]
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
    subprocess.run(["podman", "rm", "-f", "llama-bench"], capture_output=True)


def call_model(system, user, max_tokens=500, model_key=None):
    model = MODELS.get(model_key, list(MODELS.values())[0])
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
            timings = resp.get("timings", {})
            ttft = timings.get("prompt_ms", 0)
            total_ms = (t1 - t0) * 1000
            return content, ttft, total_ms
    except Exception as e:
        return f"ERROR: {e}", 0, 0


def run_benchmark(model_key, tasks):
    model = MODELS[model_key]
    print(f"\n{'='*60}")
    print(f"Model: {model_key} ({model['params']}, {model['size_gb']} GB)")
    print(f"{'='*60}")
    
    if not start_container(model_key):
        return {"model": model_key, "status": "FAILED", "reason": "container_start"}
    
    results = []
    try:
        for task in tasks:
            print(f"  Running: {task['name']}...", end=" ", flush=True)
            response, ttft, total_ms = call_model(
                task["system"], task["user"],
                max_tokens=task.get("max_tokens", 500),
                model_key=model_key
            )
            passed = task["check"](response)
            print(f"{'PASS' if passed else 'FAIL'} ({total_ms:.0f}ms)")
            results.append({
                "task": task["id"],
                "name": task["name"],
                "passed": passed,
                "ttft_ms": round(ttft),
                "total_ms": round(total_ms),
            })
    finally:
        stop_container()
        time.sleep(2)
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    avg_total = sum(r["total_ms"] for r in results) / total if total > 0 else 0
    
    return {
        "model": model_key,
        "params": model["params"],
        "size_gb": model["size_gb"],
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 3) if total > 0 else 0,
        "avg_total_ms": round(avg_total),
        "results": results,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="VEFR Round 4 Benchmark")
    parser.add_argument("--model", help="Specific model to test")
    parser.add_argument("--all", action="store_true", help="Test all models")
    args = parser.parse_args()
    
    models_to_test = []
    if args.model:
        models_to_test = [args.model]
    else:
        models_to_test = list(MODELS.keys())
    
    print("VEFR Round 4 Benchmark")
    print(f"Models: {', '.join(models_to_test)}")
    print(f"Tasks: {len(TASKS)}")
    
    # Cleanup any stale container
    stop_container()
    time.sleep(1)
    
    all_results = []
    for model_key in models_to_test:
        if model_key not in MODELS:
            print(f"Unknown model: {model_key}")
            continue
        result = run_benchmark(model_key, TASKS)
        if result.get("status") == "FAILED":
            print("  SKIPPED (container start failed)")
            continue
        all_results.append(result)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in all_results:
        print(f"  {r['model']:<20} {r['passed']}/{r['total']} ({r['pass_rate']:.0%})  avg={r['avg_total_ms']:.0f}ms")
    
    out_path = Path(__file__).resolve().parent / "round4_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()