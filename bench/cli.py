"""bench CLI - the Small Model Olympics commander.

Usage is reviewed with `python3 bench/cli.py --help`; subcommands:
  list                            participants + model file status
  tasks [--cup C] [--ids]         task registry
  run KEY --stage S ...           run one participant
  many KEYS --stage S             run a batch
  agent KEY                       real-agent mini test
  score KEY                       summary for one participant
  campaign                        table across participants with runs
  compare A B                     head-to-head
  inspect RUN [TASK]              replay one task's transcript
  report [KEY...]                 markdown summaries to bench/reports/
  pairs [--tasks A,B|--story]     human blind-comparison packs
  download [--check]              report missing artifacts
  parsertest                      run parser unit tests
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench.olympics.participants import PARTICIPANTS, missing_files  # noqa: E402
from bench.olympics import tasks as TASKS  # noqa: E402
from bench.olympics import run as RUN  # noqa: E402
from bench.olympics import report as REP  # noqa: E402
from bench.olympics.config import MODELS_DIR  # noqa: E402


def cmd_list(_):
    miss = missing_files()
    print(f"registered participants: {len(PARTICIPANTS)}")
    print(f"models dir: {MODELS_DIR}")
    for k in sorted(PARTICIPANTS):
        p = PARTICIPANTS[k]
        f = MODELS_DIR / p.file
        ok = "ok" if f.exists() else "MISSING"
        print(f"  {k:34s} {p.class_:20s} {p.params_b}B/{p.quant:8s} "
              f"{ok:8s} {p.family}")
    if miss:
        print(f"\n{len(miss)} missing:\n" + "\n".join(f"  {m}" for m in miss))


def cmd_tasks(a):
    ts = TASKS.ALL_TASKS if not a.cup else TASKS.category(cup=a.cup)
    if a.category:
        ts = [t for t in ts if t["category"] == a.category]
    print(f"{len(ts)} tasks")
    for t in ts:
        rc = "RC" if t.get("role_critical") else "  "
        qu = "Q" if t["id"] in TASKS.QUALS else " "
        print(f"  [{qu}{rc}] {t['id']:32s} {t['category']:18s} "
              f"{t['capability']:14s} {t.get('name','')}")


def cmd_run(a):
    rids = RUN.run_participant(a.key, a.stage, cup=a.cup, category=a.category,
                               ids=a.ids, runs=a.runs, temperature=a.temp,
                               guided=a.guided)
    for rid in rids:
        _print_run_summary(rid)


def cmd_many(a):
    keys = a.keys or []
    RUN.run_many(keys, a.stage, cup=a.cup, category=a.category, runs=a.runs)


def cmd_compress(a):
    """Agentic compression: same tasks RAW vs GUIDED, report delta."""
    from bench.olympics import score as SC
    from bench.olympics.records import load_trials
    from bench.cups.real_agent import AGENT_TASKS
    ids = a.ids or ["hermod.inst4", "hermod.struct2", "hermod.tj1",
                    "hermod.tj4", "hermod.ts1", "hermod.src1",
                    "hermod.contra2", "assist.triage1", "assist.brief1",
                    "assist.reconcile1", "flex.switch1"]
    ids = ids + [AGENT_TASKS[0]["id"]]
    raw = RUN.run_participant(a.key, "compress-raw", ids=ids, runs=1)
    gui = RUN.run_participant(a.key, "compress-guided", ids=ids, runs=1,
                              guided=True)

    def rates(runs_):
        trs = [t for r in runs_ for t in load_trials(r)]
        return len(trs), sum(1 for t in trs if t["pass"])
    n, pr = rates(raw)
    ng, pg = rates(gui)
    print(f"\nCOMPRESSION for {a.key} over {n} tasks:")
    print(f"  RAW     {pr}/{n} ({pr/n*100:.0f}%)")
    print(f"  GUIDED  {pg}/{ng} ({pg/ng*100:.0f}%)")
    if a.flagged:
        delta = pg - pr
        print(f"  delta   {delta:+d} ({delta/n*100:+.0f}%)")

    # per-task diff
    raw_t = {t["task_id"]: t for r in raw for t in load_trials(r)}
    gui_t = {t["task_id"]: t for r in gui for t in load_trials(r)}
    print("  per-task: " + ", ".join(
        f"{k}: {raw_t[k]['pass']}->{gui_t[k]['pass']}" if k in gui_t else f"{k}: rg"
        for k in raw_t))


def cmd_patch(a):
    """Re-run the patched task ids for one participant so summaries supersede."""
    from bench.olympics.tasks import PATCHED
    if not PATCHED:
        print("no patched tasks")
        return
    rids = RUN.run_participant(a.key, "patch", ids=list(PATCHED), runs=1)
    for rid in rids:
        _print_run_summary(rid)


def cmd_agent(a):
    rid = RUN.run_participant(a.key, "agent", runs=1)
    _print_run_summary(rid[0])


def cmd_score(_):
    pass  # handled in cmd_campaign/cmd_report too; kept for --key style future


def cmd_campaign(a):
    sums = _all_summaries()
    print(REP.campaign_markdown(sums))
    print()
    for s in sorted(sums, key=lambda x: -x.get("flex", 0)):
        if len(sums) <= 20:
            print(REP.markdown_summary(s), "\n")


def cmd_compare(a):
    sA = REP.participant_summary(a.a)
    sB = REP.participant_summary(a.b)
    for tag, s in (("A", sA), ("B", sB)):
        print(f"{tag} {REP.markdown_summary(s)}\n")
    if "error" in sA or "error" in sB:
        return
    print("deltas (A - B):")
    for k in ("score_pct", "flex", "tool_pct", "clippy_pct", "latency_mean"):
        va, vb = sA.get(k), sB.get(k)
        if va is not None and vb is not None:
            print(f"  {k:14s} {va - vb:+.4f}")


def cmd_inspect(a):
    from bench.olympics.records import summarize_run, load_trials
    trials = load_trials(a.run)
    if not trials:
        print("no trials in run", a.run)
        return
    want = a.task
    for t in trials:
        if want and t["task_id"] != want:
            continue
        print("=" * 78)
        print(f"{t['task_id']}  {t['cup']}/{t['category']} | pass="
              f"{t['pass']} sem={t['dims'].get('semantic')} "
              f"proto={t['dims'].get('protocol')} ev={t['dims'].get('evidence')}")
        replies = t.get("replies") or []
        j = 0
        for msg in t["messages"]:
            print(f"--- {msg['role']}: {msg['content'][:400]}")
            if msg["role"] == "user" and j < len(replies):
                print(f"---- reply: {replies[j][:400]}")
                j += 1
    if want:
        return


def cmd_report(a):
    keys = a.keys or list(sorted(_all_summaries()))
    texts = []
    for k in keys:
        s = REP.participant_summary(k)
        texts.append(f"{REP.markdown_summary(s)}\n")
    body = "\n".join(texts)
    p = REP.save(f"report-{'-'.join(keys[:4])}.md", body)
    print(f"wrote {p}")


def cmd_pairs(a):
    """Blind human comparison packs from actual run transcripts. Models are
    anonymized as Output A/B (shuffled per question); the key is written to a
    separate solutions file so the reader stays blind."""
    import random
    from bench.cups.storyteller_tasks import STORYTELLER_TASKS
    from bench.olympics.records import load_trials
    pool = {t["id"]: t for t in TASKS.ALL_TASKS}
    tids = a.tasks.split(",") if a.tasks else \
        ["story.world1", "story.cont1", "assist.brief1", "assist.triage1"]
    usable = [k for k in sorted(PARTICIPANTS) if RUN.list_runs().get(k)]
    rng = random.Random(a.seed)
    pairs = []
    for i in range(0, len(usable) - 1, 2):
        pairs.append([usable[i], usable[i + 1]])
    if len(usable) % 2:
        pairs.append([usable[-1]])
    if not pairs:
        print("no models with runs yet for pairs")
        return
    text = ["# Blind human comparison pack", "",
            "Each item shows the same task to two models, anonymized. Write "
            "better: A / B / tie, and one line why."]
    sol = ["# Pair key (do not read before judging)"]
    qn = 0
    for pi, pr in enumerate(pairs):
        if len(pr) < 2:
            continue
        text.append(f"\n## Pair {pi+1} ({len(tids)} questions)")
        for tid in tids:
            if tid not in pool:
                continue
            qn += 1
            halves = list(pr)
            rng.shuffle(halves)
            swaps = {}
            order = {m: ("A" if halves[0] == m else "B") for m in pr}
            text.append(f"\n### Q{qn} — task `{tid}` ({pool[tid]['name']})")
            text.append(f"prompt:\n> {pool[tid].get('user') or pool[tid]['session'][0]['user']}")
            for who in pr:
                trial = _first_trial(who, tid)
                out = trial["replies"][-1] if trial else "(no run data)"
                text.append(f"\n**Output {order[who]}**\n\n{out}")
            text.append("\nverdict: better **A** / **B** / tie — reason: ______")
            sol.append(f"Q{qn}: {tid} -> {order[pr[0]]}={pr[0]}, {order[pr[1]]}={pr[1]}")
    for label, body in (("pairs-human", "\n".join(text)),
                        ("pairs-solutions", "\n".join(sol))):
        p = REP.save(f"{label}.md", body)
        print(f"wrote {p}")


def _first_trial(key, task_id):
    from bench.olympics.records import load_trials
    for rid in RUN.list_runs().get(key, []):
        for t in load_trials(rid):
            if t["task_id"] == task_id:
                return t
    return None


def cmd_download(a):
    miss = missing_files()
    if a.check:
        print(f"{len(miss)} missing -> " + ", ".join(miss))
        return
    print("missing:", len(miss))
    for m in miss:
        print("  url-to-src", m)


def cmd_parsertest(_):
    from bench.tests.test_parse import run
    sys.exit(run())


def _print_run_summary(rid):
    from bench.olympics.records import summarize_run
    meta, trials = summarize_run(rid)
    if not trials:
        print(f"{rid}: no trials")
        return
    n = len(trials)
    p = sum(1 for t in trials if t["pass"])
    print(f"{rid}: {p}/{n} ({p/n*100:.0f}%) participant={meta.get('participant')} "
          f"stage={meta.get('stage')}")


def _all_summaries():
    keys = sorted(PARTICIPANTS)
    out = []
    idx = RUN.list_runs()
    for k in keys:
        if k in idx:
            s = REP.participant_summary(k)
            if "error" not in s:
                out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser(prog="bench")
    sub = ap.add_subparsers(dest="cmd")
    sp = sub.add_parser("list")
    sp.set_defaults(fn=cmd_list)

    sp = sub.add_parser("tasks")
    sp.add_argument("--cup")
    sp.add_argument("--category")
    sp.set_defaults(fn=cmd_tasks)

    sp = sub.add_parser("run")
    sp.add_argument("key")
    sp.add_argument("--stage", default="qualifier",
                    choices=["qualifier", "semifinal", "final", "full",
                             "single"])
    sp.add_argument("--cup")
    sp.add_argument("--category")
    sp.add_argument("--ids", nargs="*")
    sp.add_argument("--runs", type=int)
    sp.add_argument("--temp", type=float)
    sp.add_argument("--guided", action="store_true")
    sp.set_defaults(fn=cmd_run)

    sp = sub.add_parser("many")
    sp.add_argument("keys", nargs="*")
    sp.add_argument("--stage", default="qualifier")
    sp.add_argument("--cup")
    sp.add_argument("--category")
    sp.add_argument("--runs", type=int)
    sp.set_defaults(fn=cmd_many)

    sp = sub.add_parser("agent")
    sp.add_argument("key")
    sp.set_defaults(fn=cmd_agent)

    sp = sub.add_parser("compress")
    sp.add_argument("key")
    sp.add_argument("--ids", nargs="*")
    sp.add_argument("--flagged", action="store_true")
    sp.set_defaults(fn=cmd_compress)

    sp = sub.add_parser("patch")
    sp.add_argument("key")
    sp.set_defaults(fn=cmd_patch)

    sp = sub.add_parser("campaign")
    sp.set_defaults(fn=cmd_campaign)

    sp = sub.add_parser("compare")
    sp.add_argument("a")
    sp.add_argument("b")
    sp.set_defaults(fn=cmd_compare)

    sp = sub.add_parser("inspect")
    sp.add_argument("run")
    sp.add_argument("task", nargs="?")
    sp.set_defaults(fn=cmd_inspect)

    sp = sub.add_parser("report")
    sp.add_argument("keys", nargs="*")
    sp.set_defaults(fn=cmd_report)

    sp = sub.add_parser("pairs")
    sp.add_argument("--tasks", default="story.world1,story.cont1,"
                                       "assist.brief1,assist.triage1")
    sp.add_argument("--n", type=int, default=2)
    sp.add_argument("--story", action="store_true")
    sp.add_argument("--seed", type=int, default=20260913)
    sp.set_defaults(fn=cmd_pairs)

    sp = sub.add_parser("download")
    sp.add_argument("--check", action="store_true")
    sp.set_defaults(fn=cmd_download)

    sp = sub.add_parser("parsertest")
    sp.set_defaults(fn=cmd_parsertest)

    args = ap.parse_args()
    if not getattr(args, "fn", None):
        ap.print_help()
        return
    args.fn(args)


if __name__ == "__main__":
    main()