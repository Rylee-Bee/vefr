"""Campaign orchestration: run stages over participants, keep evidence.

Stages: qualifier (1 run), semifinal (3), final (5), full (1). Each run is a
separate TrialStore file under bench/runs/. After a stage over participants,
index.json lists runs per participant for reporting.
"""

import json
import time

from . import tasks as TASKS
from .config import RUNDIR, ensure_dirs, NGPU
from .participants import PARTICIPANTS
from .runtime import ModelServer
from .records import TrialStore, new_run_id, probe_backend
from .harness import run_tasks

STAGE_RUNS = {"qualifier": 1, "semifinal": 3, "final": 5, "full": 1,
              "single": 1, "agent": 1, "compress": 1}


def resolve_tasks(stage, cup=None, category=None, ids=None):
    if stage == "agent":
        from bench.cups.real_agent import AGENT_TASKS
        return AGENT_TASKS
    if ids:
        return [TASKS.BY_ID[i] for i in ids]
    if stage == "qualifier":
        base = TASKS.qualifier()
    else:
        base = TASKS.full()
    if cup:
        base = [t for t in base if t["cup"] == cup]
    if category:
        base = [t for t in base if t["category"] == category]
    return base


def run_participant(key, stage, cup=None, category=None, ids=None,
                    runs=None, temperature=None, guided=False,
                    attempts=2):
    ensure_dirs()
    if key not in PARTICIPANTS:
        raise SystemExit(f"unknown participant {key!r}")
    tasks_ = resolve_tasks(stage, cup, category, ids)
    if not tasks_:
        raise SystemExit("no tasks selected")
    if guided:
        from .prompts import guide_tasks
        tasks_ = guide_tasks(tasks_)
    n_runs = runs or STAGE_RUNS.get(stage, 1)
    last_err = None
    for attempt in range(attempts):
        server = ModelServer(PARTICIPANTS[key])
        server.start()
        warm_s = getattr(server, "warm_s", None)
        backend_probe = probe_backend(server.cid)
        run_t0 = time.time()
        try:
            run_ids = []
            for i in range(n_runs):
                rid = new_run_id(key, stage)
                store = TrialStore(rid, PARTICIPANTS[key], stage,
                                   samples=len(tasks_))
                store.header["compression"] = ("guided" if guided else "raw")
                store.header["warm_s"] = warm_s
                store.header["ngl"] = NGPU
                store.header["backend"] = backend_probe["backend"]
                store.header["backend_probe"] = {
                    k: v for k, v in backend_probe.items() if k != "backend"}
                store.write_header()
                try:
                    run_tasks(server, tasks_, store, stage,
                              temp_override=temperature)
                except Exception as e:
                    store.add_abort({
                        "run_id": rid, "attempt": attempt, "stage": stage,
                        "trials": store.trial_count(),
                        "exception": f"{type(e).__name__}: {e}",
                        "epoch_s": round(time.time() - run_t0, 3),
                        "backend": backend_probe["backend"],
                        "backend_probe": {
                            k: v for k, v in backend_probe.items()
                            if k != "backend"}})
                    raise
                run_ids.append(rid)
            break
        except Exception as e:
            last_err = e
            time.sleep(3)
        finally:
            server.stop()
    if last_err:
        raise last_err
    index = _load_index()
    index.setdefault(key, []).extend(run_ids)
    _save_index(index)
    return run_ids


def run_many(keys, stage, cup=None, category=None, runs=None, quiet=False):
    out = {}
    for k in keys:
        try:
            r = run_participant(k, stage, cup, category, runs=runs)
            out[k] = r
            if not quiet:
                print(f"{k}: {len(r)} run(s) -> {r}")
        except Exception as e:
            out[k] = [f"ERROR: {e}"]
            if not quiet:
                print(f"{k}: ERROR {e}")
    return out


def _index_path():
    return RUNDIR / "index.json"


def _load_index():
    p = _index_path()
    return json.loads(p.read_text()) if p.exists() else {}


def _save_index(idx):
    _index_path().write_text(json.dumps(idx, indent=1))


def list_runs(key=None):
    idx = _load_index()
    if key:
        return idx.get(key, [])
    return idx


def remove_run(run_id):
    from .records import RUNDIR  # noqa
    p = RUNDIR / f"{run_id}.jsonl"
    if p.exists():
        p.unlink()
    idx = _load_index()
    for k, v in list(idx.items()):
        while run_id in v:
            v.remove(run_id)
    _save_index(idx)
    return not p.exists()