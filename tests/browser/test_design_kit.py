"""The style kit's one command works offline: the passing page passes, the failing page fails with a plain reason.

A learner runs `python3 -m bench.design.run --html FILE --brief gallery-project` (no model, no key, no network).
This test runs it the same way against the two pages that ship in `bench/design/kit-template/`.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "bench" / "design" / "kit-template"


def _run(page: str, out: Path):
    return subprocess.run(
        [sys.executable, "-m", "bench.design.run", "--html", str(KIT / page), "--brief", "gallery-project", "--out", str(out)],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )


def test_the_passing_page_passes_and_leaves_a_screenshot(tmp_path):
    r = _run("passing.html", tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout
    assert (tmp_path / "passing.png").is_file()


def test_the_failing_page_fails_and_says_so_in_plain_words(tmp_path):
    r = _run("failing.html", tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "fail" in r.stdout
    assert "5 of 6" in r.stdout
