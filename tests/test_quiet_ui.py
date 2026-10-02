"""Quiet UI, WASD, Trade closing, the smaller hop (Rylee, 2026-10-02).

The REAL woven player is driven in jsdom (tests/fixtures/quiet_ui_harness.mjs):
WASD walks (and A/D turn note pages), E/F close Trade, the bottom text goes quiet
(how-to-move after the first step, the place name after a few seconds, the use-hint
screen-reader-only), the fight buttons show only with a monster near, and the
message stack is a collapsible corner panel. The hop is pinned in the page source.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import cli

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
import make_events_pack  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "fixtures" / "quiet_ui_harness.mjs"


@pytest.fixture(scope="module")
def woven(tmp_path_factory):
    home = tmp_path_factory.mktemp("quiet-ui")
    events = home / "events.html"
    events.write_text(cli.weave_html(make_events_pack.build(home)), encoding="utf-8")
    sample = home / "sample.html"
    sample.write_text(cli.weave_html(ROOT / "worlds" / "sample-world"), encoding="utf-8")
    return events, sample


def test_the_quiet_ui_wasd_and_trade_close(woven):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    run = subprocess.run(["node", str(HARNESS), str(woven[0]), str(woven[1])],
                         capture_output=True, text=True, timeout=240)
    assert run.returncode == 0, run.stderr + run.stdout
    result = json.loads(run.stdout)
    failed = [s["what"] for s in result["steps"] if not s["ok"]]
    assert result["allOk"] and len(result["steps"]) >= 22, failed


def test_the_hop_is_much_smaller():
    html = (ROOT / "web" / "packaged.html").read_text(encoding="utf-8")
    hop = float(re.search(r"var STEP_HOP = ([0-9.]+);", html).group(1))
    lean = float(re.search(r"var STEP_LEAN = ([0-9.]+);", html).group(1))
    squash = float(re.search(r"var STEP_SQUASH = ([0-9.]+);", html).group(1))
    # was 0.06 / 6 / 0.12; Rylee: "much smaller" (about a third)
    assert hop <= 0.025 and lean <= 2.5 and squash <= 0.05
    assert hop > 0 and lean > 0 and squash > 0      # still alive, just calm


def test_the_messages_toggle_meets_the_44px_target_floor():
    html = (ROOT / "web" / "packaged.html").read_text(encoding="utf-8")
    rule = re.search(r"\.toasts-toggle \{([^}]*)\}", html).group(1)
    assert "min-height: 44px" in rule
