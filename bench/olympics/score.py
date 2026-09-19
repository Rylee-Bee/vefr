"""Scoring: transparent dimensions, per-event rates, flexibility, medals.

No single mysterious number. A run produces:
  per-trial dims (from validators) - semantic/protocol/authority/unknown/help
  per-event pass rates (cup+category)
  per-cup pass rates
  role-critical failures (can override aggregates)
  FLEXIBILITY = breadth * worst-event-floor * role-critical-survival
  RELIABILITY = min-over-runs event pass rate (stable limitation evidence)
  SPEED/MEMORY from wire + artifact stats
  OVERALL SUITABILITY = weighted, shown with all components

Every number here is a pure function of trial records (deterministic).
"""

from collections import defaultdict


def trial_pass(t):
    return bool(t.get("pass"))


def aggregate(trials):
    """Return event/cup stats for a list of trial records."""
    ev = defaultdict(lambda: {"n": 0, "pass": 0, "rc": 0, "lat": 0.0})
    cup = defaultdict(lambda: {"n": 0, "pass": 0, "rc": 0})
    rc_fail = []
    lat = 0.0
    for t in trials:
        key = (t["cup"], t["category"])
        ev[key]["n"] += 1
        if trial_pass(t):
            ev[key]["pass"] += 1
        if t.get("role_critical"):
            ev[key]["rc"] += 1
            cup[t["cup"]]["rc"] += 1
            if not trial_pass(t):
                rc_fail.append(t["task_id"])
        cup[t["cup"]]["n"] += 1
        if trial_pass(t):
            cup[t["cup"]]["pass"] += 1
        lat += t.get("latency_s", 0)
    event_rates = {}
    for k, v in ev.items():
        event_rates[k] = round(v["pass"] / max(v["n"], 1), 4)
    cup_rates = {c: round(v["pass"] / max(v["n"], 1), 4) for c, v in cup.items()}
    return {
        "events": ev, "event_rates": event_rates, "cup_rates": cup_rates,
        "rc_fail": rc_fail, "total": len(trials),
        "total_pass": sum(1 for t in trials if trial_pass(t)),
        "latency_s": round(lat, 2),
    }


def flexibility(agg):
    """FLEX = breadth * floor * (1 - rc_fail_weight) * switch_survival.
    breadth: fraction of events with pass >= 0.5
    floor: minimum event rate (with >=2 trials) - punishes one weak family
    rc: presence of any role-critical failure halts the score reward
    """
    ev = agg["event_rates"]
    n_ev = len(ev)
    if n_ev == 0:
        return 0.0
    breadth = sum(1 for r in ev.values() if r >= 0.5) / n_ev
    eligible = {k: v for k, v in ev.items()
                if agg["events"][k]["n"] >= 2}
    floor = min(eligible.values()) if eligible else 0.0
    rc_ok = 1.0 if not agg["rc_fail"] else 0.55
    score = breadth * (floor ** 0.6) * rc_ok
    return round(score, 4)


def reliability(trials_by_run):
    """Across runs: worst event pass rate (stable-limitation signal) and
    per-task pass variance."""
    if len(trials_by_run) < 2:
        return {"runs": len(trials_by_run), "worst_event": None,
                "stable": None, "variance_tasks": []}
    ev_runs = []
    task_pass = defaultdict(list)
    for trials in trials_by_run:
        ev = aggregate(trials)
        ev_runs.append(ev["event_rates"])
        for t in trials:
            task_pass[t["task_id"]].append(1 if trial_pass(t) else 0)
    all_keys = set()
    for e in ev_runs:
        all_keys |= set(e)
    worst = {}
    for k in all_keys:
        vals = [e.get(k) or 0.0 for e in ev_runs]
        worst[k] = round(min(vals), 4)
    worst_ev = min(worst.values()) if worst else 0.0
    var_tasks = [tid for tid, vals in task_pass.items()
                 if max(vals) != min(vals)]
    return {"runs": len(trials_by_run), "worst_event": worst,
            "worst_event_min": round(worst_ev, 4),
            "variable_tasks": var_tasks,
            "task_pass_patterns": {tid: tuple(vals)
                                   for tid, vals in task_pass.items()}}


# --------------------------------------------------------------------------
# Medals (humorous but evidence-stamped)
# --------------------------------------------------------------------------
def medals(participant_key, stats):
    """stats: dict of relevant numbers for a participant summary."""
    m = []
    a = stats
    if a.get("flex") and a["flex"] == max(a["flex_pool"] or [0]):
        m.append("FLEXIBILITY CHAMPION candidate")
    if a.get("score_pct", 0) >= 0.9 and a.get("flex", 0) >= 0.8:
        m.append("OVERALL SUITABLE")
    if a.get("role_critical_fail", 0) == 0:
        m.append("no role-critical failure")
    if a.get("tool_score_pct", 0) >= 0.85:
        m.append("TOOL STRONG")
    if a.get("struct_pct", 0) >= 0.9:
        m.append("STRUCTURED STRONG")
    if a.get("speed_idx", 0) >= 0.8:
        m.append("SPEED DEMON")
    if a.get("clippy_pct", 0) == 1.0:
        m.append("CLIPPY-FREE")
    if a.get("rc_fail") and any("tool" in t for t in a["rc_fail"]):
        m.append("role-critical TOOL failure")
    return m


PARETO_LABELS = {
    "featherweight": "FEATHER (<0.5B)", "bantamweight": "BANTAM (0.5-1B)",
    "lightweight": "LIGHT (1-1.49B)", "welterweight": "WELTER (1.5-2.4B)",
    "middleweight": "MIDDLE (2.5-4B)",}