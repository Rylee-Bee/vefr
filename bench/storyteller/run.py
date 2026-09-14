"""Live Storyteller benchmark (NOT part of the pytest gate).

Runs the exact same template + settings from vefr.narrate against a
live llama.cpp endpoint per candidate model, scores hard gates
deterministically against bench/storyteller/cases.json (single-turn)
and sequences.json (multi-turn continuity), and writes results.

Scoring philosophy:
  * must        = any-of acknowledgement (the authoritative outcome is
                  mentioned, however the model phrases it)
  * must_all    = each fact group (with synonym phrasings) must survive
  * must_not    = contradiction/invention detector (word-inflection
                  aware so 'feudal' never trips 'feud'); these are the
                  hard teeth
  * continuity  = turns must not CONTRADICT the authoritative facts
                  (must_not on each turn) and must acknowledge something
                  (must); re-naming every fact every turn is a CRAFT
                  matter reported as 'carry' misses, not a hard failure

Soft quality (voice, clarity, pacing, repetition) is the owner blind
rubric over saved {label}/ transcripts - not computed here.

Deterministic unit coverage lives in tests/test_narrate.py with a faked
backend. This script is evidence for the model-choice question only.

Usage (live):
    python3 bench/storyteller/run.py \
      --label smollm3-3b-q4   --url http://127.0.0.1:8088 --model smollm3-3b-q4 \
      --label ministral-3-3b-q4 --url http://127.0.0.1:8089 --model ministral-3-3b-q4 \
      --label phi-4-mini-q4   --url http://127.0.0.1:8090 --model phi-4-mini-q4

Usage (re-score saved transcripts, no model calls):
    python3 bench/storyteller/run.py --replay bench/storyteller/results
"""

import argparse
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import httpx  # noqa: E402

from vefr import narrate  # noqa: E402
from vefr.narrate import LoreRef, StoryInput  # noqa: E402


CATEGORY_OF_VIOLATION = {
    "factual_adherence": "AUTHORITY",
    "failure_narration": "AUTHORITY",
    "partial_success": "AUTHORITY",
    "object_location": "AUTHORITY",
    "dialogue_texture": "CANON",
    "forbidden_canon": "CANON",
    "uncertainty": "UNKNOWN",
    "contradiction_resistance": "CONTRADICTION",
    "player_agency": "AGENCY",
    "voice_adherence": "AUTHORITY",
    "lore_use": "LORE",
    "lore_omission": "LORE",
    "creative_freedom": "SOFT",
}


# --- helpers -------------------------------------------------------------

def _env_from(d: dict) -> StoryInput:
    raw = dict(d)
    raw["relevant_lore"] = [LoreRef(**r) if isinstance(r, dict) else r
                            for r in raw.get("relevant_lore", [])]
    return StoryInput.model_validate(raw)


def _complete(env: StoryInput, *, url: str, model: str) -> dict:
    """One completion exactly as vefr.narrate builds it. Returns the
    raw response so usage (prompt/completion tokens) is captured too."""
    tpl = narrate.load_template()
    voice = ""
    if env.voice_tone or env.voice_guidance:
        voice = env.voice_tone + (" - " + env.voice_guidance if env.voice_guidance else "")
    messages = narrate.build_messages(tpl, env, voice=voice)
    gen = tpl.get("generation", {})
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": gen.get("temperature", 0.7),
        "top_p": gen.get("top_p", 0.9),
        "max_tokens": gen.get("max_tokens", 220),
        "chat_template_kwargs": {"enable_thinking": False},
    }
    t0 = time.monotonic()
    r = httpx.post(f"{url.rstrip('/')}/v1/chat/completions", json=body, timeout=120)
    latency_ms = round((time.monotonic() - t0) * 1000, 1)
    r.raise_for_status()
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {
        "text": (content or "").strip(),
        "latency_ms": latency_ms,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
    }


# --- matching -----------------------------------------------------------

_INFLECT = ("", "s", "es", "ed", "ing", "d")


def _match(text: str, needle: str | list) -> bool:
    """Inflection-aware word match: 'groan' hits 'groans/groaned',
    'feud' does NOT hit 'feudal'. A list needle matches on any member."""
    if isinstance(needle, list):
        return any(_match(text, n) for n in needle)
    return re.search(
        r"\b" + re.escape(needle) + r"(?:" + "|".join(_INFLECT) + r")?\b",
        text.lower(),
    ) is not None


def _needle_repr(needle: str | list) -> str:
    return "/".join(needle) if isinstance(needle, list) else needle


def _missing(text: str, needles: list) -> list:
    return [m for m in needles if not _match(text, m)]


def _hits(text: str, needles: list) -> list:
    return [m for m in needles if _match(text, m)]


# --- single-turn hard gate ----------------------------------------------

def score_case(case: dict, row: dict) -> dict:
    text = row["text"]
    must = case.get("must") or []
    must_all = case.get("must_all") or []
    must_not = case.get("must_not") or []
    missing_any = _missing(text, must)
    missing_all = _missing(text, must_all)
    hits = _hits(text, must_not)
    ok = (not missing_all and not hits
          and (len(must) == 0 or len(missing_any) < len(must)))
    state = {
        "pass": ok,
        "missing_must": (missing_all + missing_any)[:3],
        "hit_must_not": hits[:3],
        "cat": case["cat"],
        "snippet": "",
    }
    if not ok:
        for m in (hits + missing_all + missing_any)[:1]:
            low = text.lower().find(_needle_repr(m).split("/")[0].lower())
            if low >= 0:
                state["snippet"] = text[max(0, low - 40): low + 60]
    return state


# --- multi-turn continuity -------------------------------------------------

def score_turn(seq: dict, turn: dict, idx: int, row: dict) -> dict:
    """A turn passes when it acknowledges the envelope (must, any-of)
    and contradicts none of it (must_not). Carry families below are
    reported as craft metrics, not gate failures."""
    text = row["text"]
    must = turn.get("must") or []
    must_not = turn.get("must_not") or []
    hits = _hits(text, must_not)
    missing_any = _missing(text, must)
    ok = (not hits and (len(must) == 0 or len(missing_any) < len(must)))
    state = {"turn": idx + 1, "pass": ok,
             "missing_must": missing_any[:3],
             "hit_must_not": hits[:3],
             "snippet": ""}
    if not ok:
        state["snippet"] = text[:200]
    return state


def _carry_report(seq: dict, turns: list[dict]) -> list[dict]:
    """For each sequence carry spec, report whether the fact family is
    NAMED from its from_turn onward. Soft metric: pros stylistically
    paraphrase; non-contradiction is gated separately."""
    report = []
    for spec in seq.get("carry", []):
        fam = spec["family"]
        from_turn = spec.get("from_turn", 1)
        present_in = []
        for idx, t in enumerate(turns):
            if idx + 1 < from_turn:
                continue
            if _match(t["text"], fam):
                present_in.append(idx + 1)
        carry_ok = len(present_in) >= len(turns) - (from_turn - 1)
        report.append({
            "fact": spec["name"],
            "family": [_needle_repr(fm) if isinstance(fm, list) else fm
                       for fm in (fam if isinstance(fam, list) and all(isinstance(x, list) for x in fam) else [fam])],
            "from_turn": from_turn,
            "named_in_turns": present_in,
            "carry_ok": carry_ok,
        })
    return report


def run_candidate(label: str, url: str, model: str,
                  cases: list[dict], sequences: list[dict]) -> dict:
    os.environ["VEFR_NARRATE_URL"] = url
    os.environ["VEFR_NARRATE_MODEL"] = model
    case_rows = []
    case_pass = 0
    violations: dict[str, list[str]] = {}
    latencies: list[float] = []
    prompt_sizes: list[int] = []
    completion_tokens: list[int] = []
    for case in cases:
        env = _env_from(case["envelope"])
        row = {"id": case["id"], "cat": case["cat"], "input": env.player_intent}
        try:
            resp = _complete(env, url=url, model=model)
        except httpx.HTTPError as e:
            row["verdict"] = "unavailable"
            row["detail"] = str(e)[:120]
            case_rows.append(row)
            continue
        row.update(resp)
        if resp["prompt_tokens"]:
            prompt_sizes.append(resp["prompt_tokens"])
        if resp["completion_tokens"]:
            completion_tokens.append(resp["completion_tokens"])
        latencies.append(resp["latency_ms"])
        state = score_case(case, row)
        row.update({k: state[k] for k in ("pass", "missing_must",
                                          "hit_must_not", "snippet")})
        row["verdict"] = "ok" if state["pass"] else "violation"
        if state["pass"]:
            case_pass += 1
        else:
            cat = CATEGORY_OF_VIOLATION.get(case["cat"], "MISC")
            for m in state["hit_must_not"] or state["missing_must"] or ["?"]:
                violations.setdefault(cat, []).append(
                    f'{case["id"]}: "{m}" in "{row["text"][:160]}"')
        case_rows.append(row)

    seq_rows = []
    seq_pass = 0
    turn_total = 0
    turn_ok = 0
    for seq in sequences:
        srow = {"id": seq["id"], "turns": []}
        all_turns_ok = True
        for idx, turn in enumerate(seq["turns"]):
            env = _env_from(turn["envelope"])
            trow = {"n": idx + 1, "input": env.player_intent}
            try:
                resp = _complete(env, url=url, model=model)
            except httpx.HTTPError as e:
                trow["verdict"] = "unavailable"
                trow["detail"] = str(e)[:120]
                all_turns_ok = False
                srow["turns"].append(trow)
                continue
            trow.update(resp)
            latencies.append(resp["latency_ms"])
            if resp["prompt_tokens"]:
                prompt_sizes.append(resp["prompt_tokens"])
            if resp["completion_tokens"]:
                completion_tokens.append(resp["completion_tokens"])
            st = score_turn(seq, turn, idx, trow)
            trow.update({k: st[k] for k in ("pass", "missing_must",
                                            "hit_must_not", "snippet")})
            trow["verdict"] = "ok" if st["pass"] else "violation"
            turn_total += 1
            if st["pass"]:
                turn_ok += 1
            else:
                all_turns_ok = False
                for m in st["hit_must_not"] or st["missing_must"] or ["?"]:
                    violations.setdefault("CONTINUITY", []).append(
                        f'{seq["id"]} t{idx + 1}: "{m}" |> {trow["text"][:140]}')
            srow["turns"].append(trow)
        srow["pass"] = all_turns_ok
        srow["carry"] = _carry_report(seq, srow["turns"])
        if all_turns_ok:
            seq_pass += 1
        seq_rows.append(srow)

    total_cases = len(cases)
    result = {
        "label": label, "model": model, "url": url,
        "cases_total": total_cases,
        "cases_pass": case_pass,
        "cases_gate_percent": round(100 * case_pass / max(total_cases, 1), 1),
        "sequences_total": len(sequences),
        "sequences_pass": seq_pass,
        "turns_total": turn_total,
        "turns_ok": turn_ok,
        "continuity_percent": round(100 * turn_ok / max(turn_total, 1), 1),
        "median_latency_ms": round(statistics.median(latencies), 1) if latencies else None,
        "avg_prompt_tokens": round(statistics.mean(prompt_sizes)) if prompt_sizes else None,
        "avg_completion_tokens": round(statistics.mean(completion_tokens)) if completion_tokens else None,
        "approx_tokens_per_sec": (
            round(statistics.mean(completion_tokens) / (statistics.median(latencies) / 1000), 1)
            if completion_tokens and latencies else None),
        "violations": violations,
        "case_rows": case_rows,
        "seq_rows": seq_rows,
    }
    return result


# --- replay: deterministic re-score of saved transcripts ----------------

def replay(dirpath: str, cases: list[dict], sequences: list[dict]) -> int:
    outdir = Path(dirpath)
    case_idx = {c["id"]: c for c in cases}
    seq_idx = {s["id"]: s for s in sequences}
    for path in sorted(outdir.glob("*.json")):
        if path.name in ("summary.json",):
            continue
        res = json.loads(path.read_text(encoding="utf-8"))
        label = res.get("label", path.stem)
        print(f"\n=== replay {label} ===")
        violations: dict[str, list[str]] = {}
        case_pass = 0
        for r in res["case_rows"]:
            if r.get("verdict") == "unavailable":
                continue
            case = case_idx.get(r["id"])
            if not case:
                continue
            st = score_case(case, r)
            for k in ("pass", "missing_must", "hit_must_not", "snippet"):
                r[k] = st[k]
            r["verdict"] = "ok" if st["pass"] else "violation"
            if st["pass"]:
                case_pass += 1
            else:
                cat = CATEGORY_OF_VIOLATION.get(case["cat"], "MISC")
                for m in st["hit_must_not"] or st["missing_must"] or ["?"]:
                    violations.setdefault(cat, []).append(
                        f'{case["id"]}: "{m}" in "{r["text"][:150]}"')
        seq_pass = 0
        turn_ok = 0
        turn_total = 0
        for s in res["seq_rows"]:
            seq = seq_idx.get(s["id"])
            if not seq:
                continue
            all_ok = True
            for idx, t in enumerate(s["turns"]):
                if t.get("verdict") == "unavailable":
                    all_ok = False
                    continue
                turn = seq["turns"][idx]
                st = score_turn(seq, turn, idx, t)
                for k in ("pass", "missing_must", "hit_must_not", "snippet"):
                    t[k] = st[k]
                t["verdict"] = "ok" if st["pass"] else "violation"
                turn_total += 1
                if st["pass"]:
                    turn_ok += 1
                else:
                    all_ok = False
                    for m in st["hit_must_not"] or st["missing_must"] or ["?"]:
                        violations.setdefault("CONTINUITY", []).append(
                            f'{seq["id"]} t{idx + 1}: "{m}" |> {t["text"][:130]}')
            s["pass"] = all_ok
            s["carry"] = _carry_report(seq, s["turns"])
            if all_ok:
                seq_pass += 1
        res["cases_pass"] = case_pass
        res["cases_gate_percent"] = round(100 * case_pass / res["cases_total"], 1)
        res["sequences_pass"] = seq_pass
        res["turns_total"] = turn_total
        res["turns_ok"] = turn_ok
        res["continuity_percent"] = round(100 * turn_ok / max(turn_total, 1), 1)
        res["violations"] = violations
        path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"single-turn gate: {case_pass}/{res['cases_total']} "
              f"({round(100 * case_pass / res['cases_total'], 1)}%)  "
              f"sequences: {seq_pass}/{res['sequences_total']}  "
              f"continuity {res['continuity_percent']}%")
        n_viol = sum(len(v) for v in violations.values())
        if n_viol:
            print(f"{n_viol} hard-gate violations:")
            for cat, items in violations.items():
                print(f"  {cat}:")
                for it in items[:5]:
                    print(f"    - {it}")
        for s in res["seq_rows"]:
            for c in s.get("carry", []):
                print(f"  carry {s['id']} {c['fact']}: "
                      + ("ok" if c["carry_ok"] else f"missed turns {c['named_in_turns']}"))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", default=str(Path(__file__).parent / "cases.json"))
    ap.add_argument("--sequences", default=str(Path(__file__).parent / "sequences.json"))
    ap.add_argument("--out", default=str(Path(__file__).parent / "results"))
    ap.add_argument("--replay", default=None,
                    help="re-score saved results/*.json without model calls")
    ap.add_argument("--label", action="append", default=[])
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--model", action="append", default=[])
    args = ap.parse_args()
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]
    sequences = json.loads(Path(args.sequences).read_text(encoding="utf-8"))["sequences"]
    if args.replay:
        return replay(args.replay, cases, sequences)
    if not (len(args.label) == len(args.url) == len(args.model)) or not args.label:
        print("need equal --label/--url/--model triples (one per candidate)")
        return 2
    os.makedirs(args.out, exist_ok=True)
    summary = {"cases": len(cases), "sequences": len(sequences)}
    for label, url, model in zip(args.label, args.url, args.model):
        print(f"\n=== {label} ({url}) ===")
        result = run_candidate(label, url, model, cases, sequences)
        summary[label] = result
        dest = Path(args.out) / f"{label}.json"
        dest.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                        encoding="utf-8")
        tx_dir = Path(args.out) / label
        tx_dir.mkdir(exist_ok=True)
        for r in result["case_rows"]:
            (tx_dir / f"c_{r['id']}.txt").write_text(
                r.get("text", "") + "\n", encoding="utf-8")
        for s in result["seq_rows"]:
            (tx_dir / f"s_{s['id']}.txt").write_text(
                "\n\n---\n\n".join(t["text"] for t in s["turns"]) + "\n",
                encoding="utf-8")
        print(f"single-turn gate: {result['cases_pass']}/{result['cases_total']} "
              f"({result['cases_gate_percent']}%)  "
              f"sequences: {result['sequences_pass']}/{result['sequences_total']}  "
              f"continuity {result['continuity_percent']}%")
        print(f"median latency {result['median_latency_ms']}ms  "
              f"avg prompt {result['avg_prompt_tokens']} tok  "
              f"avg completion {result['avg_completion_tokens']} tok  "
              f"~{result['approx_tokens_per_sec']} tok/s")
        n_viol = sum(len(v) for v in result["violations"].values())
        if n_viol:
            print(f"{n_viol} hard-gate violations:")
            for cat, items in result["violations"].items():
                print(f"  {cat}:")
                for it in items[:4]:
                    print(f"    - {it}")
    Path(args.out).joinpath("summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nresults + transcripts written to {args.out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())