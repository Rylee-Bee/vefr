#!/usr/bin/env python3
"""VEFR Small-Model Benchmark — Qualification Battery

Tests each candidate model on a small set of structured tasks before
running the full VEFR suite.

Usage:
    python3 benchmark_qual.py [--model MODEL_NAME] [--all]
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

# Qualification tests
QUAL_TESTS = [
    {
        "id": "strict_json",
        "name": "Strict JSON Schema",
        "system": "Reply with ONLY a valid JSON object. No markdown, no commentary.",
        "user": 'Return exactly: {"name": "test", "count": 42, "tags": ["a", "b", "c"]}',
        "validate": lambda r: _validate_strict_json(r),
    },
    {
        "id": "unknown_probe",
        "name": "UNKNOWN/Hallucination Probe",
        "system": "You are a precise assistant. If you do not know something, say so. Reply with ONLY a JSON object.",
        "user": 'Return JSON: {"capital_of_france": "?", "capital_of_xyzland": "?", "population_of_mars": "?"}',
        "validate": lambda r: _validate_unknown(r),
    },
    {
        "id": "exact_string",
        "name": "Exact String Handling",
        "system": "Reply with ONLY the exact string requested, nothing else.",
        "user": "Return exactly: VEFR-2026-TEST-OK",
        "validate": lambda r: r.strip() == "VEFR-2026-TEST-OK",
    },
    {
        "id": "enum_selection",
        "name": "Enum Selection",
        "system": "Reply with ONLY a JSON object.",
        "user": 'Pick one color from ["red", "green", "blue"]. Return JSON: {"color": "...", "reason": "one sentence"}',
        "validate": lambda r: _validate_enum(r),
    },
    {
        "id": "multi_step",
        "name": "Multi-Step Reasoning",
        "system": "Reply with ONLY a JSON object.",
        "user": 'A world has 3 phases: "dawn", "dusk", "night". Each phase has a tone. Dawn is warm. Dusk is quiet. Night is still. Return JSON: {"phases": [{"name": "dawn", "tone": "warm"}, ...], "count": 3}',
        "validate": lambda r: _validate_phases(r),
    },
    {
        "id": "bounded_extraction",
        "name": "Bounded Extraction",
        "system": "Reply with ONLY a JSON object. Extract exactly what is asked, nothing more.",
        "user": 'From this text: "The keeper watches the tower. The bell rings at dusk. Gold waits for a kind world." Return JSON: {"speaker": "keeper", "location": "tower", "event": "bell rings", "time": "dusk"}',
        "validate": lambda r: _validate_extraction(r),
    },
]


def _validate_strict_json(response):
    """Validate strict JSON with exact fields."""
    try:
        data = json.loads(response)
        return (
            data.get("name") == "test"
            and data.get("count") == 42
            and data.get("tags") == ["a", "b", "c"]
        )
    except (json.JSONDecodeError, TypeError):
        return False


def _validate_unknown(response):
    """Validate that unknown values are marked as unknown."""
    try:
        data = json.loads(response)
        # xyzland and mars should be unknown/empty/?
        xyz = str(data.get("capital_of_xyzland", "")).lower()
        mars = str(data.get("population_of_mars", "")).lower()
        france = str(data.get("capital_of_france", "")).lower()
        # France should be known
        if "paris" not in france:
            return False
        # Unknowns should not be invented
        if xyz and xyz not in ["?", "unknown", "none", "n/a", ""]:
            return False
        if mars and mars not in ["?", "unknown", "none", "n/a", "", "0"]:
            return False
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def _validate_enum(response):
    """Validate enum selection."""
    try:
        data = json.loads(response)
        return data.get("color") in ["red", "green", "blue"]
    except (json.JSONDecodeError, TypeError):
        return False


def _validate_phases(response):
    """Validate multi-step reasoning."""
    try:
        data = json.loads(response)
        # Handle both {"phases": [...]} and direct [...] formats
        if isinstance(data, list):
            phases = data
        elif isinstance(data, dict):
            phases = data.get("phases", [])
        else:
            return False
        if len(phases) != 3:
            return False
        names = {p.get("name") for p in phases if isinstance(p, dict)}
        return names == {"dawn", "dusk", "night"}
    except (json.JSONDecodeError, TypeError):
        return False


def _validate_extraction(response):
    """Validate bounded extraction."""
    try:
        data = json.loads(response)
        return (
            data.get("speaker") == "keeper"
            and data.get("location") == "tower"
            and data.get("event") == "bell rings"
            and data.get("time") == "dusk"
        )
    except (json.JSONDecodeError, TypeError):
        return False


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
        "-c", "4096", "-t", "8", "-ngl", "0", "--jinja",
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


def call_model(system, user, max_tokens=500, model_key=None):
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
        with urllib.request.urlopen(req, timeout=120) as r:
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


_CURRENT_MODEL = None

def run_qualification(model_key):
    """Run qualification battery for a model."""
    global _CURRENT_MODEL
    _CURRENT_MODEL = model_key
    model = BENCH_MODELS[model_key]
    print(f"\n{'='*60}")
    print(f"Model: {model_key} ({model['params']}, {model['quant']})")
    print(f"{'='*60}")
    
    if not start_container(model_key):
        return {"model": model_key, "status": "FAILED", "reason": "container_start"}
    
    results = []
    try:
        for test in QUAL_TESTS:
            print(f"  Running: {test['name']}...", end=" ", flush=True)
            response, ttft, total_ms = call_model(test["system"], test["user"], model_key=model_key)
            passed = test["validate"](response)
            status = "PASS" if passed else "FAIL"
            print(f"{status} ({ttft:.0f}ms TTFT, {total_ms:.0f}ms total)")
            results.append({
                "test": test["id"],
                "name": test["name"],
                "passed": passed,
                "ttft_ms": round(ttft),
                "total_ms": round(total_ms),
                "response_preview": response[:100] if response else "",
            })
    finally:
        stop_container()
        time.sleep(2)
    
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    
    return {
        "model": model_key,
        "params": model["params"],
        "quant": model["quant"],
        "status": "PASS" if passed_count == total_count else "PARTIAL" if passed_count >= total_count // 2 else "FAIL",
        "score": f"{passed_count}/{total_count}",
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
    
    print("VEFR Small-Model Qualification Battery")
    print(f"Models to test: {', '.join(models_to_test)}")
    print(f"Port: {PORT}")
    
    all_results = []
    for model_key in models_to_test:
        if model_key not in BENCH_MODELS:
            print(f"Unknown model: {model_key}")
            continue
        result = run_qualification(model_key)
        all_results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in all_results:
        print(f"  {r['model']:<20} {r['status']:<10} {r.get('score', 'N/A')}")
    
    # Save results
    out_path = Path(__file__).parent / "benchmark_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()