"""The Chronicle's reading rules, executed for real.

web/js/chronicle.js decides how each kind of journal entry reads in the
Chronicle. It exists because the old page only read `whisper`/`text`,
so actions, npc lines and letters showed as blank rows. The harness
(tests/fixtures/chronicle_harness.mjs) pins every kind to its words and
pins how a run of actions folds into one line.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).resolve().parent / "fixtures" / "chronicle_harness.mjs"
CHRONICLE_JS = ROOT / "web" / "js" / "chronicle.js"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)


def test_chronicle_reads_every_kind():
    result = subprocess.run(
        ["node", str(HARNESS), str(CHRONICLE_JS)],
        capture_output=True, text=True, timeout=20
    )
    if result.returncode != 0:
        pytest.fail(f"chronicle harness failed:\n{result.stdout}\n{result.stderr}")
    assert "ALL PASS" in result.stdout, result.stdout
