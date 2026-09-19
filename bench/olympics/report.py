"""Report builders: participant summaries, flexibility cups, pareto, medals.

All numbers derive from trial records kept in bench/runs/. The campaign
report is generated from every run we have; individual summaries are single
participants.
"""

import json
import statistics
from collections import defaultdict
from pathlib import Path

from .config import RUNDIR, REPORTDIR
from .participants import PARTICIPANTS
from .records import summarize_run
from . import score as SC


def runs_for(key):
    idx = json.loads((RUNDIR / "index.json").read_text()) if (RUNDIR /
                                                              "index.json").exists() else {}
    rids = idx.get(key, [])
    out = []
    for rid in rids:
        p = RUNDIR / f"{rid}.jsonl"
        if p.exists():
            out.append((rid, summarize_run(rid)))
    return out


def _trials_from_runs(key):
    from .tasks import PATCHED
    runs = runs_for(key)
    trials = []
    per_run = []
    for rid, (meta, ts) in runs:
        if meta.get("stage", "").endswith("-patch"):
            pass  # patch runs always contribute
        elif any(t["task_id"] in PATCHED for t in ts):
            ts = [t for t in ts if t["task_id"] not in PATCHED]
        per_run.append(ts)
        trials.extend(ts)
    return trials, per_run


def participant_summary(key, image_mb=None):
    trials, per_run = _trials_from_runs(key)
    p = PARTICIPANTS[key]
    if not trials:
        return {"key": key, "error": "no runs"}
    agg = SC.aggregate(trials)
    rel = SC.reliability(per_run)
    flex = SC.flexibility(agg)
    total_pass = agg["total_pass"]
    score_pct = total_pass / agg["total"]
    # specialized dimensions
    def rate(cat, cup=None):
        tot = passn = 0
        for t in trials:
            if t["category"] == cat and (cup is None or t["cup"] == cup):
                tot += 1
                if t["pass"]:
                    passn += 1
        return passn / tot if tot else None

    tool_trials = [t for t in trials if t["category"] in
                   ("tool_judgment", "tool_selection", "tool_arguments")]
    tool_pct = (sum(1 for t in tool_trials if t["pass"]) / len(tool_trials)
                if tool_trials else None)
    tool_sem = SC.aggregate([{**t, "pass": t["dims"].get("semantic", False)}
                             for t in tool_trials])
    struct_trials = [t for t in trials if t["category"] in
                     ("structure", "transformation", "classification")]
    struct_pct = (sum(1 for t in struct_trials if t["pass"]) / len(struct_trials)
                  if struct_trials else None)
    clippy_trials = [t for t in trials if t["category"] == "clippy"]
    clippy_pct = (sum(1 for t in clippy_trials if t["pass"]) / len(clippy_trials)
                  if clippy_trials else None)
    unknown_trials = [t for t in trials if t["dims"].get("unknown")]
    unknown_pct = (sum(1 for t in unknown_trials if t["dims"].get("unknown"))
                   / len(unknown_trials)) if unknown_trials else None
    help_trials = [t for t in trials if t["dims"].get("help")]
    help_pct = (sum(1 for t in help_trials if t["dims"].get("help"))
                / len(help_trials)) if help_trials else None

    lats = [t["latency_s"] for t in trials if t.get("latency_s")]
    art_mb = image_mb or _size_mb(p)
    summaries = {
        "key": key, "family": p.family, "params_b": p.params_b,
        "quant": p.quant, "class_": p.class_, "kind": p.kind,
        "lineage": p.lineage,
        "runs": len(per_run), "trials": len(trials),
        "score_pct": round(score_pct, 4),
        "cup_rates": agg["cup_rates"], "rc_fail": agg["rc_fail"],
        "flex": flex,
        "reliability": rel,
        "events": agg["event_rates"],
        "tool_pct": round(tool_pct, 4) if tool_pct is not None else None,
        "tool_sem": round(tool_sem["total_pass"] / tool_sem["total"], 4)
        if tool_sem["total"] else None,
        "struct_pct": round(struct_pct, 4) if struct_pct is not None else None,
        "clippy_pct": round(clippy_pct, 4) if clippy_pct is not None else None,
        "unknown_pct": round(unknown_pct, 4) if unknown_pct is not None else None,
        "help_pct": round(help_pct, 4) if help_pct is not None else None,
        "latency_mean": round(statistics.mean(lats), 3) if lats else None,
        "latency_med": round(statistics.median(lats), 3) if lats else None,
        "artifact_mb": round(art_mb, 1),
        "speed_idx": _speed_idx(lats) if lats else None,
    }
    summaries["medals"] = SC.medals(key, {**summaries,
                                          "flex_pool": [],
                                          "score_pct": score_pct,
                                          "role_critical_fail": len(agg["rc_fail"]),
                                          "tool_score_pct": tool_pct or 0,
                                          "struct_pct": struct_pct or 0,
                                          "speed_idx": summaries["speed_idx"] or 0,
                                          "clippy_pct": clippy_pct or 0})
    return summaries


def _size_mb(p):
    from .config import MODELS_DIR
    f = MODELS_DIR / p.file
    return f.stat().st_size / 2**20 if f.exists() else None


def _speed_idx(lats):
    # relative to the fastest model in the corpus set later; fallback: inverse
    return round(0.5 / (statistics.mean(lats) + 0.1), 3)


def markdown_summary(s, title=None):
    L = [f"### {s['key']} — {s['family']} {s['params_b']}B {s['quant']} "
         f"({s['class_']})"]
    if s.get("lineage"):
        L.append(f"- lineage: {s['lineage']}")
    L.append(f"- pass: **{s['score_pct']*100:.0f}%** over {s['trials']} trials "
             f"in {s['runs']} run(s); FLEX {s['flex']}")
    L.append(f"- cups: {s['cup_rates']}")
    if s.get("rc_fail"):
        L.append(f"- **role-critical failures**: {s['rc_fail']}")
    L.append(f"- tool {s['tool_pct']}, tool-semantic {s['tool_sem']}, "
             f"structured {s['struct_pct']}, clippy {s['clippy_pct']}, "
             f"unknown {s['unknown_pct']}, help {s['help_pct']}")
    rel = s.get("reliability") or {}
    if rel.get("variable_tasks"):
        L.append(f"- variable tasks across runs: {rel['variable_tasks']}")
        L.append(f"- worst event floor (runs): {rel.get('worst_event_min')} "
                 f"({rel.get('worst_event')})")
    L.append(f"- latency mean/med {s['latency_mean']}s/{s['latency_med']}s; "
             f"artifact {s['artifact_mb']}MB")
    if s.get("medals"):
        L.append(f"- flags: {', '.join(s['medals'])}")
    return "\n".join(L)


def pareto(summ_list):
    """A dominates B if A is not larger, not slower-mean TBD, and FLEX + pass
    better. We bind size and score here; report latency separately."""
    out = []
    for s in summ_list:
        doms = []
        for o in summ_list:
            if o is s:
                continue
            if (o["params_b"] <= s["params_b"] and
                    o["flex"] > s["flex"] and o["score_pct"] > s["score_pct"]):
                doms.append(o["key"])
        s = {**s, "dominated_by": doms}
        out.append(s)
    return out


_FRONT = ["key", "score_pct", "flex", "cup_rates", "rc_fail", "tool_pct",
          "struct_pct", "clippy_pct", "latency_mean", "artifact_mb"]


def campaign_markdown(sums):
    L = ["## Campaign summary", "|" + "|".join(_FRONT).replace("|key|",
        "|participant |") + "|",
         "|" + "|".join("---" for _ in _FRONT) + "|"]
    for s in sorted(sums, key=lambda x: -x.get("flex", 0)):
        row = [s["key"]]
        row += [f"{s['score_pct']*100:.0f}%", f"{s['flex']}",
                f"{s['cup_rates']}", f"{s['rc_fail'] or '-'}",
                f"{s['tool_pct'] if s['tool_pct'] is not None else '-'}",
                f"{s['struct_pct'] if s['struct_pct'] is not None else '-'}",
                f"{s['clippy_pct'] if s['clippy_pct'] is not None else '-'}",
                f"{s['latency_mean']}s", f"{s['artifact_mb']}MB"]
        L.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(L)


def save(name, text):
    REPORTDIR.mkdir(parents=True, exist_ok=True)
    p = REPORTDIR / name
    p.write_text(text)
    return p