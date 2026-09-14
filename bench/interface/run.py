"""Live Interface Translator benchmark (NOT part of the pytest gate).

Runs the exact same template + settings from vefr.interface against a
live llama.cpp endpoint for each candidate model, scores against
bench/interface/cases.json, and writes results. Deterministic unit
coverage lives in tests/test_interface.py with a faked backend - this
script is evidence for the model-choice question only.

Usage:
    python3 bench/interface/run.py \
      --label qwen2.5-1.5b-q4 --url http://127.0.0.1:8085 \
        --model qwen2.5-1.5b-instruct-q4 \
      --label qwen3.5-0.8b-q4 --url http://127.0.0.1:8086 \
        --model qwen3.5-0.8b-q4
"""

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import httpx  # noqa: E402

from vefr import interface  # noqa: E402
from vefr.interface import InterfaceMalformed, InterfaceUnavailable  # noqa: E402


def _token_rate(url: str, model: str) -> float:
    """Approximate output tok/s from one timed JSON completion."""
    tpl = interface.load_template()
    msgs = interface.build_messages(tpl, "look around")
    body = {
        "model": model,
        "messages": msgs,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "vefr_intent", "schema": interface._ENVELOPE_SCHEMA,
            "strict": True}},
        "stream": False, "temperature": 0.0, "max_tokens": 200,
    }
    t0 = time.monotonic()
    r = httpx.post(f"{url.rstrip('/')}/v1/chat/completions", json=body, timeout=90)
    dt = time.monotonic() - t0
    r.raise_for_status()
    usage = r.json().get("usage", {})
    n = usage.get("completion_tokens") or 1
    return round(n / dt, 1)


def run_candidate(label: str, url: str, model: str, cases: list[dict]) -> dict:
    os.environ["VEFR_INTERFACE_URL"] = url
    os.environ["VEFR_INTERFACE_MODEL"] = model
    rows = []
    schema_valid = 0
    correct = 0
    clarifications = 0
    unsafe_fp = 0
    latencies: list[float] = []
    for case in cases:
        row = {"id": case["id"], "cat": case["cat"], "input": case["input"]}
        try:
            intent, meta = interface.translate(case["input"])
        except InterfaceMalformed as e:
            row["verdict"] = "invalid"
            row["detail"] = str(e)[:120]
            rows.append(row)
            continue
        except InterfaceUnavailable as e:
            row["verdict"] = "unavailable"
            row["detail"] = str(e)[:120]
            rows.append(row)
            continue
        row["latency_ms"] = meta["latency_ms"]
        latencies.append(meta["latency_ms"])
        schema_valid += 1
        expected = case["expect_action"]
        if intent.needs_clarification:
            row["verdict"] = "clarification"
            row["clarification"] = intent.clarification
            clarifications += 1
            # Clarifying an out-of-vocabulary verb (e.g. "distract") is
            # valid routing when the case allows it.
            if expected == "clarification" or case.get("accept_clarification"):
                correct += 1
                row["correct"] = True
            else:
                row["correct"] = False
                if case.get("unsafe"):
                    unsafe_fp += 1
            rows.append(row)
            continue
        ok = intent.action == expected
        for key, sub in (case.get("expect") or {}).items():
            if key == "topic_substr":
                where = intent.topic
            elif key == "direction_substr":
                where = intent.direction or intent.target
            elif key == "target_substr":
                where = intent.target
                if intent.action == "move":
                    where = intent.target or intent.direction
            else:
                where = None
            if not (where and sub.lower() in where.lower()):
                ok = False
        if not ok:
            # watch the alt-matching for "hurl X at Y" style arg ambiguity
            for alt in case.get("expect_any") or []:
                matched = True
                for key, sub in alt.items():
                    hay = {"target_substr": intent.target,
                           "direction_substr": intent.direction or intent.target,
                           "topic_substr": intent.topic}
                    val = hay.get(key)
                    if not (val and sub.lower() in val.lower()):
                        matched = False
                        break
                if matched:
                    ok = True
                    break
        row["verdict"] = "ok" if ok else "wrong_action"
        row["intent"] = intent.model_dump()
        row["correct"] = ok
        if ok:
            correct += 1
        elif expected != "clarification":
            row["wrong_detail"] = f"expected {expected}"
        if expected == "clarification" and not intent.needs_clarification:
            unsafe_fp += 1
        rows.append(row)
    median_latency = round(statistics.median(latencies), 1) if latencies else None
    try:
        tps = _token_rate(url, model)
    except Exception as e:  # noqa: BLE001
        tps = None
    total = len(cases)
    result = {
        "label": label, "model": model, "url": url,
        "total": total, "schema_valid": schema_valid,
        "correct": correct, "clarification": clarifications,
        "unsafe_false_positives": unsafe_fp,
        "median_latency_ms": median_latency,
        "approx_tokens_per_sec": tps,
        "safe_percent": round(100 * correct / max(total, 1), 1),
        "schema_percent": round(100 * schema_valid / max(total, 1), 1),
        "rows": rows,
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", default=str(Path(__file__).parent / "cases.json"))
    ap.add_argument("--out", default=str(Path(__file__).parent / "results"))
    ap.add_argument("--label", action="append", default=[])
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--model", action="append", default=[])
    args = ap.parse_args()
    if not (len(args.label) == len(args.url) == len(args.model)) or not args.label:
        print("need equal --label/--url/--model triples (one per candidate)")
        return 2
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    os.makedirs(args.out, exist_ok=True)
    summary = {"cases": len(cases)}
    for label, url, model in zip(args.label, args.url, args.model):
        print(f"\n=== {label} ({url}) ===")
        result = run_candidate(label, url, model, cases)
        summary[label] = result
        dest = Path(args.out) / f"{label}.json"
        dest.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                        encoding="utf-8")
        print(f"total={result['total']} schema_valid={result['schema_valid']} "
              f"correct={result['correct']} clarifications={result['clarification']} "
              f"unsafe_fp={result['unsafe_false_positives']} "
              f"median_latency={result['median_latency_ms']}ms "
              f"tps={result['approx_tokens_per_sec']}")
        print(f"safe: {result['safe_percent']}%  schema: {result['schema_percent']}%")
        bad = [r for r in result["rows"] if r.get("verdict") == "wrong_action"
               or r.get("correct") is False]
        for r in bad:
            print("  MISMATCH", r["id"], r.get("verdict"), r.get("intent", {}).get("action"),
                  r.get("detail", ""))
    Path(args.out).joinpath("summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nresults written to {args.out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())