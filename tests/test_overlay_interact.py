"""One-button Interact keeps the loop going: E / F / Space / Enter continue a
note (next page, then close) and a speech box, instead of needing a click.

The REAL woven sample world is driven in jsdom
(tests/fixtures/overlay_interact_harness.mjs). A held key must not carry on
into the next thing.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from vefr import cli

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "overlay_interact_harness.mjs"


def test_interact_keys_continue_notes_and_speech(tmp_path):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    out = tmp_path / "sample.html"
    out.write_text(cli.weave_html(ROOT / "worlds" / "sample-world"), encoding="utf-8")
    run = subprocess.run(["node", str(HARNESS), str(out)],
                         capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stderr + run.stdout
    result = json.loads(run.stdout)
    failed = [s["what"] for s in result["steps"] if not s["ok"]]
    assert result["allOk"], failed
