#!/usr/bin/env python3
"""VEFR Small-Model Benchmark — Full VEFR Suite

Runs the actual VEFR task battery against candidate models.
Based on the Spark benchmark (2026-09-06) and existing VEFR test patterns.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BENCH_MODELS = {
    "qwen3.5-0.8b": {
        "file": "Qwen3.5-0.8B-Q4_K_M.gguf",
        "alias": "qwen3.5-0.8b-q4",
        "params": "~0.8B",
        "quant": "Q4_K_M",
        "chat_template_kwargs": {"enable_thinking": False},
    },
    "qwen3.5-2b": {
        "file": "Qwen3.5-2B-Q4_K_M.gguf",
        "alias": "qwen3.5-2b-q4",
        "params": "~2B",
        "quant": "Q4_K_M",
        "chat_template_kwargs": {"enable_thinking": False},
    },
    "gemma-3-1b": {
        "file": "Gemma-3-1B-Q4_K_M.gguf",
        "alias": "gemma-3-1b-q4",
        "params": "~1B",
        "quant": "Q4_K_M",
    },
    "llama-3.2-3b": {
        "file": "Llama-3.2-3B-Q4_K_M.gguf",
        "alias": "llama-3.2-3b-q4",
        "params": "~3B",
        "quant": "Q4_K_M",
    },
    "ministral-3-3b": {
        "file": "Ministral-3-3B-Q4_K_M.gguf",
        "alias": "ministral-3-3b-q4",
        "params": "~3.4B",
        "quant": "Q4_K_M",
    },
    "phi-4-mini": {
        "file": "Phi-4-mini-Q4_K_M.gguf",
        "alias": "phi-4-mini-q4",
        "params": "~3.8B",
        "quant": "Q4_K_M",
    },
}

MODELS_DIR = Path.home() / "llama-server/models/bench"
PORT = 8083

# VEFR Benchmark tasks
VEFR_TESTS = [
    {
        "id": "npc_creation",
        "name": "NPC JSON Creation",
        "category": "structured_output",
        "system": "You are a game master for a fantasy RPG. Create NPCs as JSON with exactly these fields: id (lowercase slug), name, role (one sentence), personality (one sentence), location, dialogue_seed (one sentence). Output ONLY the JSON object, no markdown.",
        "user": "Scene: A candle-maker's stall near the market well at dusk. Create one NPC for this scene.",
        "validate": lambda r: _validate_npc(r),
    },
    {
        "id": "state_edit",
        "name": "Bounded State Edit",
        "category": "state_manipulation",
        "system": "You edit game state. Change ONLY what is requested. Return the COMPLETE updated state as JSON. Output ONLY the JSON object, no markdown.",
        "user": "Current state: {\"world\": \"Emberfield\", \"gold\": 12, \"npcs\": [{\"id\": \"bray\", \"trust\": 2}, {\"id\": \"kestrel\", \"trust\": 2}]}\n\nTask: Set Kestrel's trust to 5. Return the complete updated state.",
        "validate": lambda r: _validate_state_edit(r),
    },
    {
        "id": "escalation_judgment",
        "name": "Escalation Judgment",
        "category": "routing",
        "system": "Classify each task as LOCAL (you can handle it: simple JSON, bounded edits, classification) or ESCALATE (needs stronger model: architecture, debugging, cross-file reasoning, research). Output ONLY JSON: {\"decisions\": [{\"task_id\": \"...\", \"choice\": \"LOCAL\"|\"ESCALATE\", \"reason\": \"one sentence\"}]}",
        "user": "Task 1: Write a haiku about a lamp lighting a tower.\nTask 2: Return JSON merging {\"item\":\"voucher\",\"kept\":true} into the inventory.\nTask 3: Design a save-state migration system for three schema versions.\nTask 4: Debug why the journal writes two entries for one action.\nTask 5: Should an item be 'found' or 'given'? The pack is ambiguous.",
        "validate": lambda r: _validate_escalation(r),
    },
    {
        "id": "lore_generation",
        "name": "Lore Generation",
        "category": "creative",
        "system": "You write lore for a fantasy world. Stay in the world's tone. Never contradict established facts. Output ONLY JSON: {\"text\": \"one or two short paragraphs\"}",
        "user": "World: Emberfield. Rule: Gold waits for a kind world. The Keeper watches the tower. Write a brief lore fragment about the morning of Woden's day.",
        "validate": lambda r: _validate_lore(r),
    },
    {
        "id": "world_extraction",
        "name": "World Data Extraction",
        "category": "extraction",
        "system": "Extract structured data from world descriptions. Output ONLY JSON with the requested fields.",
        "user": "World pack:\n- Title: Emberfield\n- Phases: dawn (tentative, warm), dusk (quiet, watchful)\n- Voices: keeper (file: voices/keeper.md, strike: \"Write the letter\")\n- Bonds: given, found, cold\n- Surface: combat\n\nReturn JSON: {\"title\": \"...\", \"phases\": [\"...\", \"...\"], \"voice_count\": 1, \"bonds\": [\"...\", \"...\", \"...\"], \"surface\": \"...\"}",
        "validate": lambda r: _validate_world_extraction(r),
    },
    {
        "id": "rune_classification",
        "name": "Rune/Phase Classification",
        "category": "classification",
        "system": "Classify game elements into their correct categories. Output ONLY JSON.",
        "user": "The four Elder Futhark runes anchored to the Hero's Journey phases are:\n- Fehu (wealth, seed-fire)\n- Thurisaz (thorn, threshold)\n- Kenaz (torch, tests)\n- Sowilo (sun, revelation)\n\nClassify each phase to its rune:\n{\"whispers\": \"?\", \"doubts\": \"?\", \"feared\": \"?\", \"awed\": \"?\"}",
        "validate": lambda r: _validate_rune_classification(r),
    },
    {
        "id": "instruction_scope",
        "name": "Instruction Scope Discipline",
        "category": "instruction_following",
        "system": "You are a bounded worker. Do exactly what is asked, nothing more. Do not expand scope. Output ONLY JSON.",
        "user": "Return JSON: {\"status\": \"ok\", \"message\": \"ready\"}",
        "validate": lambda r: _validate_scope(r),
    },
    {
        "id": "unknown_preservation",
        "name": "UNKNOWN Preservation",
        "category": "honesty",
        "system": "When you don't know something, say so. Never invent facts. Output ONLY JSON.",
        "user": "Return JSON: {\"known_capital\": \"Paris\", \"unknown_planet_capital\": \"?\", \"unestablished_lore\": \"?\"}",
        "validate": lambda r: _validate_unknown_preservation(r),
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
    # ```json\n...\n```
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


def _validate_npc(response):
    """Validate NPC JSON with required fields."""
    data = _extract_json(response)
    if data is None:
        return False
    required = {"id", "name", "role", "personality", "location", "dialogue_seed"}
    return required.issubset(data.keys()) and isinstance(data.get("id"), str)


def _validate_state_edit(response):
    """Validate bounded state edit."""
    data = _extract_json(response)
    if data is None:
        return False
    # Check gold unchanged, kestrel trust changed, bray unchanged
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


def _validate_escalation(response):
    """Validate escalation judgments."""
    data = _extract_json(response)
    if data is None:
        return False
    
    # Handle both {"decisions": [...]} and direct [...] formats
    if isinstance(data, list):
        decisions = data
    elif isinstance(data, dict):
        decisions = data.get("decisions", [])
    else:
        return False
    
    if len(decisions) != 5:
        return False
    
    # Check load-bearing: migrate and debug must be ESCALATE
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


def _validate_lore(response):
    """Validate lore generation."""
    data = _extract_json(response)
    if data is None:
        return False
    text = data.get("text", "")
    return len(text) > 50 and len(text) < 1000


def _validate_world_extraction(response):
    """Validate world data extraction."""
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


def _validate_rune_classification(response):
    """Validate rune/phase classification."""
    data = _extract_json(response)
    if data is None:
        return False
    # whispers -> Fehu, doubts -> Thurisaz, feared -> Kenaz, awed -> Sowilo
    expected = {
        "whispers": "Fehu",
        "doubts": "Thurisaz",
        "feared": "Kenaz",
        "awed": "Sowilo",
    }
    for key, rune in expected.items():
        got = data.get(key, "")
        # Handle nested values
        if isinstance(got, dict):
            got = got.get("rune", "") or got.get("name", "")
        if not isinstance(got, str):
            return False
        if got.lower() != rune.lower():
            return False
    return True


def _validate_scope(response):
    """Validate instruction scope discipline."""
    data = _extract_json(response)
    if data is None:
        return False
    # Should only have status and message, nothing extra
    if set(data.keys()) != {"status", "message"}:
        return False
    if data.get("status") != "ok":
        return False
    return True


def _validate_unknown_preservation(response):
    """Validate UNKNOWN preservation."""
    data = _extract_json(response)
    if data is None:
        return False
    if data.get("known_capital") != "Paris":
        return False
    # Unknown values should be empty, ?, or "unknown"
    unknown = str(data.get("unknown_planet_capital", "")).lower()
    unestablished = str(data.get("unestablished_lore", "")).lower()
    valid_unknowns = ["", "?", "unknown", "none", "n/a", "null"]
    if unknown and unknown not in valid_unknowns:
        return False
    if unestablished and unestablished not in valid_unknowns:
        return False
    return True


def start_container(model_key):
    """Start a llama.cpp container for the given model."""
    model = BENCH_MODELS[model_key]
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
    
    # Add chat template kwargs if needed
    kwargs = model.get("chat_template_kwargs")
    if kwargs:
        cmd.extend(["--chat-template-kwargs", json.dumps(kwargs)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED to start container: {result.stderr}")
        return False
    
    # Wait for health
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


def call_model(system, user, max_tokens=800, model_key=None):
    """Call the running model and return (response, ttft_ms, total_ms)."""
    if model_key is None:
        model_key = next(iter(BENCH_MODELS))
    model = BENCH_MODELS.get(model_key)
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
            
            # Extract content (handle reasoning_content if present)
            content = resp["choices"][0]["message"].get("content", "")
            reasoning = resp["choices"][0]["message"].get("reasoning_content", "")
            
            # If content is empty but reasoning has content, the model is thinking
            if not content.strip() and reasoning.strip():
                content = reasoning  # Use reasoning as fallback
            
            timings = resp.get("timings", {})
            ttft = timings.get("prompt_ms", 0)
            total_ms = (t1 - t0) * 1000
            
            return content, ttft, total_ms
    except Exception as e:
        return f"ERROR: {e}", 0, 0


def run_vefr_benchmark(model_key):
    """Run VEFR benchmark for a model."""
    model = BENCH_MODELS[model_key]
    print(f"\n{'='*60}")
    print(f"Model: {model_key} ({model['params']}, {model['quant']})")
    print(f"{'='*60}")
    
    if not start_container(model_key):
        return {"model": model_key, "status": "FAILED", "reason": "container_start"}
    
    results = []
    try:
        for test in VEFR_TESTS:
            print(f"  Running: {test['name']}...", end=" ", flush=True)
            response, ttft, total_ms = call_model(
                test["system"], test["user"], model_key=model_key
            )
            passed = test["validate"](response)
            status = "PASS" if passed else "FAIL"
            print(f"{status} ({ttft:.0f}ms TTFT, {total_ms:.0f}ms total)")
            results.append({
                "test": test["id"],
                "name": test["name"],
                "category": test["category"],
                "passed": passed,
                "ttft_ms": round(ttft),
                "total_ms": round(total_ms),
                "response_preview": response[:150] if response else "",
            })
    finally:
        stop_container()
        time.sleep(2)
    
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    
    # Category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"passed": 0, "total": 0}
        categories[cat]["total"] += 1
        if r["passed"]:
            categories[cat]["passed"] += 1
    
    return {
        "model": model_key,
        "params": model["params"],
        "quant": model["quant"],
        "status": "PASS" if passed_count == total_count else "PARTIAL" if passed_count >= total_count // 2 else "FAIL",
        "score": f"{passed_count}/{total_count}",
        "categories": categories,
        "tests": results,
    }


def main():
    """Main entry point."""
    if "--help" in sys.argv:
        print(__doc__)
        return
    
    models_to_test = []
    if "--all" in sys.argv:
        models_to_test = list(BENCH_MODELS.keys())
    elif "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            models_to_test = [sys.argv[idx + 1]]
    else:
        # Default: test all
        models_to_test = list(BENCH_MODELS.keys())
    
    print("VEFR Small-Model Benchmark — Full VEFR Suite")
    print(f"Models to test: {', '.join(models_to_test)}")
    print(f"Port: {PORT}")
    
    all_results = []
    for model_key in models_to_test:
        if model_key not in BENCH_MODELS:
            print(f"Unknown model: {model_key}")
            continue
        result = run_vefr_benchmark(model_key)
        all_results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in all_results:
        print(f"  {r['model']:<20} {r['status']:<10} {r.get('score', 'N/A')}")
        if "categories" in r:
            for cat, scores in r["categories"].items():
                print(f"    {cat:<25} {scores['passed']}/{scores['total']}")
    
    # Save results
    out_path = Path(__file__).parent / "benchmark_vefr_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()