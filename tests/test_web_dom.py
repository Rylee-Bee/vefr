"""Actually executes the web UI's JS against a stubbed DOM.

`node --check` only catches syntax errors. The bug that caused the
real "stuck in house" production incident was an undeclared variable
that only failed at runtime - no syntax checker sees that class of
bug. This test runs state.js, town.js, and index.html's inline
script for real, in a node vm context, and drives the actual user
flows (tab switching, phase sync, forge+keep, movement, the bell,
the journal tab, the export button).

Skips gracefully if node isn't installed - this must never break the
"uv sync --group test" zero-setup promise in GETTING_STARTED.md for
someone without node. When node is present (it is on the author's
dev boxes), this is real coverage the schema-only tests can't give.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = Path(__file__).resolve().parent / "fixtures" / "dom_harness.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)


def test_web_ui_survives_a_full_stubbed_dom_run():
    result = subprocess.run(
        ["node", str(HARNESS), str(ROOT)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"DOM harness failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "all harness checks passed" in result.stdout
