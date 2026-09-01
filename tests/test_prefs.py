"""The reading-and-sound preferences API, executed for real.

web/prefs.js is shipped JS - the packaged ratatoskr weave file inlines
it next to state.js, so it's the contract for every device that ever
plays the story. The shipped-JS test pattern (test_web_packaged.py
+ tests/fixtures/pool_harness.mjs) treats the JS itself as the source
of truth and drives it in a node vm sandbox with a stubbed DOM and
localStorage. This test follows the same shape for prefs.js.

The harness (tests/fixtures/prefs_harness.mjs) covers the full contract:
defaults are the inclusive-forward floor, get() is a deep clone,
set() persists and updates the data-prefs attribute, preview() is
ephemeral, shareLink() round-trips through applyFromUrl(), reset()
restores defaults, and a partial set() preserves other keys.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).resolve().parent / "fixtures" / "prefs_harness.mjs"
PREFS_JS = ROOT / "web" / "prefs.js"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)


def test_prefs_contract():
    assert PREFS_JS.exists(), f"prefs.js missing at {PREFS_JS}"
    result = subprocess.run(
        ["node", str(HARNESS), str(PREFS_JS)],
        capture_output=True, text=True, timeout=20
    )
    if result.returncode != 0:
        pytest.fail(
            f"prefs harness failed:\nSTDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
    assert "ALL PASS" in result.stdout, (
        f"harness did not report ALL PASS:\n{result.stdout}\n{result.stderr}"
    )
