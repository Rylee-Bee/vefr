"""Deterministic validators: the 'judge strictly' half.

Each validator: (task, pr, meta) -> dict of dimension flags:
  semantic, protocol, authority, unknown, help, norm
plus optional labels: tool, reasoning, evidence.

`pr` is the ParseResult from parse.parse (dict). `meta` may carry extra
session info (e.g. list of replies for multi-turn/session tasks).

The convention for tool tasks:
  protocol = the call was recognizable (any dialect, >=1 call line well-formed)
  semantic = the DECISION was right (call / don't call / which tool / args)
  A wrong-but-parseable call is protocol pass, semantic fail. The reverse
  (right decision, odd dialect) is semantic pass, protocol pass after
  normalization - and the normalization flag is preserved.

A list of forbidden values vs exact values is in task["expect"].
"""

import re

from . import parse as P

UNKNOWN_VALUES = {"", "?", "unknown", "none", "null", "n/a", "na", "unavailable"}


def _j(pr, default=None):
    return P.first_json(pr) if pr else default


def _low(v):
    return str(v).strip().lower()


def _looks_unknown(v):
    return _low(v) in UNKNOWN_VALUES or v is None


def _norm(pr):
    return bool(pr and pr.get("norm"))


def _base(pr, semantic=False, protocol=False, **kw):
    d = {
        "semantic": semantic,
        "protocol": protocol,
        "norm": _norm(pr),
        "authority": False,
        "unknown": False,
        "help": False,
    }
    d.update({k: v for k, v in kw.items() if k in d})
    for k, v in kw.items():
        if k not in d:
            d[k] = v
    return d


# --------------------------------------------------------------------------
# generic structured-output check. expect keys:
#   require   {path: value | {"any_of":[...]} | {"unknown": True}}
#   forbid    {path: value}   (must NOT equal)
#   require_keys: [...]
#   forbid_keys: [...]
#   has_tool / no_tool: bool for tool-regime tasks
#   tool_name: str expected when has_tool
#   args: {arg: value-or-any_of} for the expected tool call
# --------------------------------------------------------------------------
def v_structured(task, pr, meta=None):
    exp = task.get("expect", {})
    obj = _j(pr)
    protocol = obj is not None
    if not protocol:
        return _base(pr, semantic=False, protocol=False, evidence="no parseable JSON")
    if exp.get("no_tool"):
        called = P.has_tool_call(pr)
        return _base(
            pr,
            semantic=not called,
            protocol=True,
            unknown=True,
            tool="called" if called else "none",
            help=True,
            evidence="restraint: no call required",
        )
    req = exp.get("require", {})
    for path, spec in req.items():
        val = _deref(obj, path)
        ok = _match_spec(val, spec)
        if not ok:
            return _base(
                pr, semantic=False, protocol=True, evidence=f"{path}={val!r} failed {spec!r}"
            )
    for path, val in exp.get("forbid", {}).items():
        if _deref(obj, path) == val:
            return _base(
                pr, semantic=False, protocol=True, evidence=f"{path}=forbidden value {val!r}"
            )
    keys = set(obj.keys())
    missing = [k for k in exp.get("require_keys", []) if k not in keys]
    if missing:
        return _base(pr, semantic=False, protocol=True, evidence=f"missing keys {missing}")
    extra = [k for k in exp.get("forbid_keys", []) if k in keys]
    if extra:
        return _base(pr, semantic=False, protocol=True, evidence=f"forbidden keys present {extra}")
    return _base(pr, semantic=True, protocol=True, authority=True, unknown=True, evidence="ok")


def _deref(obj, path):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            cur = [x.get(part) if isinstance(x, dict) else None for x in cur]
            cur = cur[0] if cur else None
        else:
            return None
    return cur


def _match_spec(val, spec):
    if isinstance(spec, dict):
        if "eq" in spec:
            return val == spec["eq"]
        if "any_of" in spec:
            if isinstance(val, str):
                return _low(val) in {_low(x) for x in spec["any_of"]}
            return val in spec["any_of"]
        if "unknown" in spec:
            return spec["unknown"] and _looks_unknown(val)
        if "contains" in spec:
            return spec["contains"] in _low(val)
        if "regex" in spec:
            return re.search(spec["regex"], _low(val)) is not None
        if "lt" in spec and val is not None:
            return val < spec["lt"]
        if "gte" in spec and val is not None:
            return val >= spec["gte"]
        return False
    return val == spec


# --------------------------------------------------------------------------
# tool-call decision tasks. expect:
#   decision: "must_call_tool" | "must_not_call" | "already_have"
#   tool_name: str
#   args: {arg: spec}
#   forbidden_tool: str (wrong-tool distractor)
# --------------------------------------------------------------------------
def v_tool(task, pr, meta=None):
    exp = task.get("expect", {})
    calls = pr.get("tool_calls", []) if pr else []
    dec = exp.get("decision", "must_call_tool")

    _protocol = True
    _nums = ""
    if dec == "must_not_call":
        ok_sem = len(calls) == 0
        return _base(
            pr,
            semantic=ok_sem,
            protocol=True,
            unknown=True,
            help=True,
            tool="none" if ok_sem else calls[0]["name"],
            evidence=("restraint" if ok_sem else f"called {calls[0]['name']} incorrectly"),
        )
    if dec == "already_have":
        ok_sem = len(calls) == 0
        return _base(
            pr,
            semantic=ok_sem,
            protocol=True,
            unknown=True,
            tool="none" if ok_sem else calls[0]["name"],
            evidence=("no call (already have) " if ok_sem else f"re-looked-up {calls[0]['name']}"),
        )
    # must call
    if not calls:
        return _base(
            pr,
            semantic=False,
            protocol=True,
            tool="no-call",
            evidence="should have called a tool but did not",
        )
    name = calls[0]["name"]
    exp_name = exp.get("tool_name")
    forbidden = exp.get("forbidden_tool")
    if forbidden and name == forbidden:
        return _base(
            pr, semantic=False, protocol=True, tool=name, evidence=f"wrong-tool distractor {name}"
        )
    if exp_name and name != exp_name:
        return _base(
            pr,
            semantic=False,
            protocol=True,
            tool=name,
            evidence=f"tool mismatch: got {name}, want {exp_name}",
        )
    args = calls[0].get("arguments") or {}
    for k, spec in exp.get("args", {}).items():
        if k not in args or not _match_spec(args.get(k), spec):
            return _base(
                pr,
                semantic=False,
                protocol=True,
                tool=name,
                evidence=f"arg {k}={args.get(k)!r} failed {spec!r}",
            )
    missing = exp.get("no_extra_args", [])
    for k in missing:
        if k in args:
            return _base(
                pr, semantic=False, protocol=True, tool=name, evidence=f"hallucinated arg {k}"
            )
    return _base(
        pr, semantic=True, protocol=True, tool=name, unknown=True, evidence="correct tool + args"
    )


# --------------------------------------------------------------------------
# tool-selection: several plausible, one right
# --------------------------------------------------------------------------
def v_tool_selection(task, pr, meta=None):
    exp = task.get("expect", {})
    calls = pr.get("tool_calls", []) if pr else []
    if exp.get("want_no_call"):
        return _base(
            pr,
            semantic=len(calls) == 0,
            protocol=True,
            evidence="no-call tiebreak wrong" if calls else "ok",
        )
    if not calls:
        return _base(
            pr,
            semantic=False,
            protocol=True,
            tool="no-call",
            evidence="candidate tools existed; no call made",
        )
    got = calls[0]["name"]
    ok = got == exp.get("tool_name")
    return _base(
        pr,
        semantic=ok,
        protocol=True,
        tool=got,
        evidence=f"selected {got}" if ok else f"picked {got}, want {exp.get('tool_name')}",
    )


# --------------------------------------------------------------------------
# UNKNOWN preservation
# --------------------------------------------------------------------------
def v_unknown(task, pr, meta=None):
    exp = task.get("expect", {})
    obj = _j(pr)
    if obj is None:
        return _base(pr, semantic=False, protocol=False, evidence="no JSON")
    checks = exp.get("unknown_fields", [])
    known = exp.get("known_fields", {})
    bad_unknown = [f for f in checks if not _looks_unknown(_deref(obj, f))]
    bad_known = [f for f, v in known.items() if _deref(obj, f) != v]
    ok = not bad_unknown and not bad_known
    return _base(
        pr,
        semantic=ok,
        protocol=True,
        unknown=ok,
        evidence=(
            f"invented {bad_unknown}"
            if bad_unknown
            else f"wrong-known {bad_known}"
            if bad_known
            else "ok"
        ),
    )


# --------------------------------------------------------------------------
# session validators (multi-turn; meta carries the reply list)
#   they inspect the FINAL reply (and intermediate where useful)
# --------------------------------------------------------------------------
def v_final_reply(task, pr_all, meta=None):
    exp = task.get("expect", {})
    last = meta["final_raw"]
    lp = P.parse(last)
    need = exp.get("required_in_final", [])
    forbid = exp.get("forbidden_in_final", []) or []
    ok = all(n in last for n in need) and not any(f in last for f in forbid)
    sent_ok = True
    if exp.get("sentence_ok"):
        sentences = [s for s in re.split(r"[.?!;]\s+", last) if s]
        sent_ok = len(sentences) <= 3
        ok = ok and sent_ok
    return _base(
        lp,
        semantic=bool(ok),
        protocol=True,
        evidence=f"need={need} forbid={forbid} sentences<=3={sent_ok}",
    )


def v_no_tool_in_session(task, pr_all, meta=None):
    for raw in meta["replies"]:
        lp = P.parse(raw)
        if P.has_tool_call(lp):
            return _base(
                lp,
                semantic=False,
                protocol=True,
                tool="called",
                evidence="tool call leaked into chat session",
            )
    return _base(pr_all, semantic=True, protocol=True, evidence="no tool call in session")


def v_final_state(task, pr_all, meta=None):
    """Task-switch sessions end with a structured request; check final reply."""
    final = meta["replies"][-1]
    lp = P.parse(final)
    return v_structured(task, lp, meta)


# --------------------------------------------------------------------------
# storytelling deterministics
# --------------------------------------------------------------------------
SLOP = [
    "unveil",
    "tapestry",
    "delved",
    "revealed itself",
    "in the tapestry",
    "a symphony of",
    "she couldn't help but wonder",
    "it was more than",
    "the weight of",
    "whispered",
    "pulse quickened",
    "as if the world",
    "little did they know",
    "in that moment",
    "heart ached",
    "a dance of",
    "testament to",
    "silent sentinel",
    "oftentimes",
]
REPETITION_RE = re.compile(r"\b(\w{4,})\b \1", re.I)


def _words(t):
    return [w.lower() for w in re.findall(r"[A-Za-z']+", t)]


def v_prose_signals(task, pr, meta=None):
    """Deterministic bothersome-language signals. Raw prose from FINAL reply."""
    last = meta["final_raw"]
    words = _words(last)
    if not words:
        return _base(pr, semantic=False, protocol=True, evidence="empty story")
    slop_hits = [s for s in SLOP if s in last.lower()]
    repeats = [m.group(0) for m in REPETITION_RE.finditer(last.lower())]
    triples = {}
    for a, b, c in zip(words, words[1:], words[2:]):
        key = (a, b, c)
        triples[key] = triples.get(key, 0) + 1
    loop_triples = [k for k, v in triples.items() if v >= 3]
    lo, hi = exp_range(task, (30, 260))
    length_ok = lo <= len(words) <= hi
    signals = {
        "slop": len(slop_hits),
        "repeats": len(repeats),
        "loops": len(loop_triples),
        "words": len(words),
    }
    ok = length_ok and signals["slop"] <= 3 and signals["loops"] <= 1
    return _base(
        pr,
        semantic=ok,
        protocol=True,
        evidence=str(signals),
        **{f"prose_{k}": v for k, v in signals.items()},
    )


def exp_range(task, default):
    lo, hi = task.get("expect", {}).get("range", default)
    return lo, hi


def v_world_belief(task, pr, meta=None):
    """World truth must survive plot. meta['replies'] contains [story, probe].
    Probe answers a yes/no question; we also accept truthful state words
    ("unsafe" / "not safe") as a flip of "no" so we don't double-penalize a
    model that gives the right fact in the wrong literal."""
    replies = meta["replies"]
    if len(replies) < 2:
        return _base(pr, semantic=False, protocol=True, evidence="missing probe turn")
    probe = _low(replies[-1])
    want = _low(task["world_truth"]["probe"]["expect_low"])
    NEG_WORDS = {"no", "unsafe", "not safe", "unusable", "broken"}
    POS_WORDS = {"yes", "safe", "usable", "open"}
    if want == "no":
        ok = bool(NEG_WORDS & set(re.findall(r"[a-z]+[\s-]*[a-z]*", probe))) or "no" in probe
    elif want == "yes":
        ok = bool(POS_WORDS & set(re.findall(r"[a-z ']+", probe))) or "yes" in probe
    else:
        ok = want in probe
    story = replies[0]
    flipped = task["world_truth"]["forbid_in_story"]
    story_flip = any(f in _low(story) for f in flipped)
    if story_flip:
        return _base(
            pr,
            semantic=False,
            protocol=True,
            authority=False,
            evidence=f"story asserted world flip: {flipped}",
        )
    return _base(
        pr, semantic=ok, protocol=True, authority=ok, evidence=f"probe={probe!r} want={want}"
    )


def v_world_probe(task, pr, meta=None):
    replies = meta["replies"]
    probe = _low(replies[-1]) if replies else ""
    expect = _low(task["expect"]["probe_contains"])
    return _base(
        pr,
        semantic=expect in probe,
        protocol=True,
        evidence=f"probe={probe!r}; want contains {expect!r}",
    )


def v_dialogue_distinct(task, pr, meta=None):
    last = meta["final_raw"]
    quoted = re.findall(r'"[^"\n]{6,}"', last)
    if len(quoted) < 2:
        return _base(pr, semantic=False, protocol=True, evidence="too few lines")
    # crude distinctness: fraction of dialogue lines with a unique opening word
    opens = [_words(q)[:1] for q in quoted]
    unique = len(set(t[0] for t in opens if t))
    ratio = unique / len(opens) if opens else 0
    ok = ratio >= 0.5
    return _base(pr, semantic=ok, protocol=True, evidence=f"distinct-open ratio {ratio:.2f}")


def v_lore_use(task, pr, meta=None):
    last = meta["final_raw"]
    lore = task["expect"]["lore_keys"]
    used = [k for k in lore if k in _low(last)]
    ok = len(used) >= task["expect"].get("min_used", 1)
    return _base(pr, semantic=ok, protocol=True, evidence=f"lore hits {used}")


def v_steer(task, pr, meta=None):
    replies = meta["replies"]
    last = replies[-1]
    req = task["expect"]["steer_in_final"]
    ok = req in _low(last) and task["expect"]["no_old_in_final"] not in _low(last)
    return _base(pr, semantic=ok, protocol=True, evidence="steer check")


def v_continuity(task, pr, meta=None):
    replies = meta["replies"]
    last = replies[-1]
    keys = task["expect"]["must_keep"]
    dropped = [k for k in keys if k not in _low(last)]
    ok = not dropped
    return _base(
        pr, semantic=ok, protocol=True, evidence=f"kept {[k for k in keys if k in _low(last)]}"
    )


def v_no_em_dump(task, pr, meta=None):
    last = meta["final_raw"]
    water = [
        "she felt",
        "he felt",
        "a wave of emotion",
        "overwhelmed by",
        "his heart swelled",
        "tears welled",
        "emotion surged",
    ]
    hits = [w for w in water if w in _low(last)]
    ok = len(hits) <= 2
    return _base(pr, semantic=ok, protocol=True, evidence=f"emotion-dump hits {hits}")


# --------------------------------------------------------------------------
# assistant deterministics (inbox triage, briefs, etc.)
# --------------------------------------------------------------------------
def v_triage(task, pr, meta=None):
    last = meta["final_raw"]
    lp = P.parse(last)
    obj = _j(lp)
    if obj is None:
        return _base(lp, semantic=False, protocol=False, evidence="no JSON")
    prio = obj.get("priority", {})
    urgent = set(prio.get("urgent", []))
    wait = set(prio.get("can_wait", []))
    info = set(prio.get("informational", []))
    mapping = task["expect"]
    ok = (
        urgent == set(mapping["urgent"])
        and wait == set(mapping["can_wait"])
        and info == set(mapping["informational"])
    )
    return _base(
        lp,
        semantic=ok,
        protocol=True,
        help=True,
        evidence=f"urgent={sorted(urgent)} wait={sorted(wait)} info={sorted(info)}",
    )


def v_brief(task, pr, meta=None):
    last = meta["final_raw"]
    low = _low(last)
    must = task["expect"]["must_mention"]
    avoid = task["expect"]["avoid_mention"]
    ok = all(m in low for m in must) and not any(a in low for a in avoid)
    ok = ok and len(_words(last)) <= task["expect"].get("max_words", 180)
    return _base(
        pr,
        semantic=ok,
        protocol=True,
        help=True,
        evidence=("brief ok" if ok else "brief missed/overreached"),
    )


CLIPPY_PHRASES = [
    "would you like me to",
    "let me know if",
    "i can also",
    "shall i",
    "do you want me to",
    "feel free to",
    "i hope this helps",
    "happy to help",
    "let me know",
    "want me to",
    "if you'd like",
    "if you would like",
]


def v_clippy(task, pr, meta=None):
    """Anti-annoyance: answer the trivial request plainly. Penalize
    unsolicited offers / ceremony / length."""
    last = meta["final_raw"]
    low = _low(last)
    offers = [p for p in CLIPPY_PHRASES if p in low]
    max_words = task["expect"].get("max_words", 60)
    n = len(_words(last))
    must = _low(task["expect"].get("must_mention", ""))
    has = must in low if must else True
    ok = has and len(offers) == 0 and n <= max_words
    return _base(
        pr,
        semantic=ok,
        protocol=True,
        evidence=f"offers={offers} words={n} answer={has}",
        clippy="clean" if ok else "annoying",
    )


def v_no_invented(task, pr, meta=None):
    last = meta["final_raw"]
    low = _low(last)
    invented = [x for x in task["expect"]["must_not_claim"] if x in low]
    ok = not invented and task["expect"]["must_mention"] in low
    return _base(pr, semantic=ok, protocol=True, evidence=str(invented))


def v_default_dims(task, pr, meta=None):
    # catch-all single-turn plain check: reuse v_structured on final reply
    return v_structured(task, pr, meta)


def v_task_switch(task, pr, meta=None):
    exp = task["expect"]
    replies = meta["replies"]
    step = exp["tool_step"]
    if step >= len(replies):
        return _base(pr, semantic=False, protocol=True, evidence="missing tool step")
    lp = P.parse(replies[step])
    calls = lp.get("tool_calls", [])
    if not calls:
        return _base(pr, semantic=False, protocol=True, evidence="tool step no call")
    if calls[0]["name"] != exp["tool_name"]:
        return _base(
            pr,
            semantic=False,
            protocol=True,
            tool=calls[0]["name"],
            evidence=f"tool step picked {calls[0]['name']}",
        )
    final = _low(replies[-1])
    ukey = _low(exp["final_unknown"])
    preserved = (
        "unknown" in final
        or ukey in final
        or "?" in replies[-1]
        or "not known" in final
        or "don't know" in final
        or "don't have" in final
    )
    return _base(
        pr,
        semantic=preserved,
        protocol=True,
        tool=exp["tool_name"],
        unknown=preserved,
        evidence=(
            f"tool ok; final={replies[-1][:80]!r}" if preserved else "tool ok but fabricated final"
        ),
    )


def v_classify_then_extract(task, pr, meta=None):
    """Session that must complete 3 structured shapes in style, one per turn
    (classification -> extraction -> reasoning)."""
    replies = meta["replies"]
    exp = task["expect"]
    if len(replies) < 3:
        return _base(pr, semantic=False, protocol=True, evidence="missing turns")
    c = P.parse(replies[0])
    e = P.parse(replies[1])
    r = P.parse(replies[2])
    cj = P.first_json(c)
    ej = P.first_json(e)
    ok = (
        bool(cj)
        and cj.get("category") == exp["c0"]
        and bool(ej)
        and ej.get("item") == exp["e0"]
        and "window" in _low(r["prose"] or replies[2])
    )
    return _base(
        pr,
        semantic=ok,
        protocol=True,
        evidence=f"c={P.first_json(c) if c else None} e={P.first_json(e) if e else None}",
    )


def v_agent(task, pr, meta=None):
    """Real-agent scenario: multi-step, tools + several turn types.
    Checks intermediate state reasoning, staleness handling, no
    unnecessary tool, final bounded JSON."""
    exp = task["expect"]
    replies = meta["replies"]
    steps = {}
    for i, raw in enumerate(replies):
        steps[i] = raw
    # step3 must prefer the fresh status over the stale one
    stale_step = exp["stale_step"]
    s_raw = _low(replies[stale_step]) if stale_step < len(replies) else ""
    stale_ok = "pickup" in s_raw or "required" in s_raw
    # unnecessary-tool opportunity: no weather call anywhere
    weather_calls = []
    for raw in replies:
        c = P.parse(raw)
        for tc in c.get("tool_calls", []):
            if tc["name"] == exp.get("weather_tool"):
                weather_calls.append(raw)
    # final JSON
    lp = P.parse(replies[-1])
    obj = P.first_json(lp)
    fin_ok = False
    if obj:
        fin_ok = obj.get("order-8") == "PICKUP_REQUIRED" and _looks_unknown(obj.get("pickup_time"))
    ok = stale_ok and not weather_calls and fin_ok
    ev = f"stale_ok={stale_ok} weather_calls={len(weather_calls)} final={obj}"
    return _base(
        lp,
        semantic=ok,
        protocol=bool(obj),
        authority=stale_ok,
        unknown=fin_ok,
        evidence=ev,
        tool=("weather" if weather_calls else "none"),
    )


VALIDATORS = {
    "structured": v_structured,
    "tool": v_tool,
    "tool_selection": v_tool_selection,
    "unknown": v_unknown,
    "prose_signals": v_prose_signals,
    "world_belief": v_world_belief,
    "world_probe": v_world_probe,
    "dialogue_distinct": v_dialogue_distinct,
    "lore_use": v_lore_use,
    "steer": v_steer,
    "continuity": v_continuity,
    "no_em_dump": v_no_em_dump,
    "triage": v_triage,
    "brief": v_brief,
    "no_invented": v_no_invented,
    "clippy": v_clippy,
    "final_reply": v_final_reply,
    "no_tool_in_session": v_no_tool_in_session,
    "final_state": v_final_state,
    "task_switch": v_task_switch,
    "classify_then_extract": v_classify_then_extract,
    "agent": v_agent,
}
