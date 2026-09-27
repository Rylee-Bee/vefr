"""bench.jobs: full logs, honest status, and one GPU job at a time."""
import importlib.util
import json
import sys
import threading
import time
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "bench_jobs", Path(__file__).resolve().parents[1] / "bench" / "jobs.py")
jobs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jobs)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("VEFR_JOBS_DIR", str(tmp_path))
    return tmp_path


def _status(tmp, name):
    return json.loads((tmp / name / "status.json").read_text())


def test_a_job_keeps_every_line_and_its_ending(isolated):
    code = jobs.run("hello", [sys.executable, "-c", "for i in range(50): print('line', i)"])
    st = _status(isolated, "hello")
    assert code == 0 and st["state"] == "done" and st["exit"] == 0
    log = (isolated / "hello" / "log").read_text()
    assert "line 0" in log and "line 49" in log          # nothing trimmed
    assert st["last_line"] == "line 49"


def test_a_failure_is_labelled_not_hidden(isolated):
    code = jobs.run("boom", [sys.executable, "-c", "raise SystemExit('loss is nan at step 0')"])
    st = _status(isolated, "boom")
    assert code == 1 and st["state"] == "failed" and "nan" in st["last_line"]


def test_timeout_stops_the_job(isolated):
    code = jobs.run("slow", [sys.executable, "-c", "import time; time.sleep(30)"], timeout=1)
    assert code == 124 and _status(isolated, "slow")["state"] == "timed-out"


def test_two_gpu_jobs_never_overlap(isolated):
    spans = {}

    def job(name):
        stamp = isolated / f"{name}.span"
        jobs.run(name, [sys.executable, "-c",
                        f"import time; s=time.time(); time.sleep(0.6); open(r'{stamp}','w').write(f'{{s}} {{time.time()}}')"],
                 gpu=True)
        spans[name] = tuple(map(float, stamp.read_text().split()))

    a = threading.Thread(target=job, args=("painter",))
    b = threading.Thread(target=job, args=("student",))
    a.start()
    time.sleep(0.1)
    b.start()
    a.join()
    b.join()
    (s1, e1), (s2, e2) = sorted(spans.values())
    assert e1 <= s2, "the second GPU job started before the first ended"


def test_a_waiting_job_says_who_holds_the_card(isolated):
    held = jobs.GpuLock("painter")
    held.acquire()
    seen = []
    t = threading.Thread(target=lambda: jobs.run("student", [sys.executable, "-c", "print('ok')"], gpu=True))
    t.start()
    for _ in range(50):
        try:
            st = _status(isolated, "student")
        except (OSError, ValueError):
            st = {}
        if st.get("state") == "waiting":
            seen.append(st["waiting_for"])
            break
        time.sleep(0.05)
    held.release()
    t.join(timeout=10)
    assert seen and seen[0].startswith("painter")
    assert _status(isolated, "student")["state"] == "done"


def test_ls_and_tail(isolated, capsys):
    jobs.run("one", [sys.executable, "-c", "print('first'); print('last words')"])
    jobs.main(["ls"])
    assert "one: done" in capsys.readouterr().out
    jobs.main(["tail", "one", "-n", "1"])
    assert capsys.readouterr().out.strip() == "last words"
