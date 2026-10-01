"""Start over's pure core, executed for real, plus the shipped wiring.

The start-over block in web/packaged.html removes every vefr- save the
site keeps and returns the keys it removed, in order. This extracts the
REAL block between its marker comments and runs it in a node vm sandbox
that needs no npm packages, against a fake storage; then it checks the
shipped markup and handlers that call it. What runs here is exactly
what ships, not a copy.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGED = ROOT / "web" / "packaged.html"
HARNESS = Path(__file__).resolve().parent / "fixtures" / "startover_harness.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not installed - this repo's engine tests never require it",
)


def _run() -> dict:
    result = subprocess.run(
        ["node", str(HARNESS), str(PACKAGED)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"startover harness failed:\n{result.stdout}\n{result.stderr}")
    return json.loads(result.stdout)


def test_only_vefr_keys_are_removed_in_the_order_found():
    out = _run()
    assert out["removed"] == [
        "vefr-hp-town", "vefr-slain-town",
        "vefr-floor-town", "vefr-packaged-combat",
    ]


def test_keys_from_other_apps_survive():
    out = _run()
    assert out["survivors"] == [
        "keep-me", "myPrefs", "notvefr-thing", "some-other-app",
    ]


def test_running_it_twice_is_safe():
    out = _run()
    assert out["removedAgain"] == []


def test_a_storage_that_refuses_is_skipped_not_fatal():
    out = _run()
    assert out["refusedThrew"] is False
    assert out["refusedResult"] == []


def test_the_pure_block_is_pure_and_present_exactly_once():
    src = PACKAGED.read_text(encoding="utf-8")
    assert src.count("// -- startover start --") == 1
    assert src.count("// -- startover end --") == 1
    block = src.split("// -- startover start --", 1)[1].split(
        "// -- startover end --", 1)[0]
    assert "document" not in block
    assert "window.location" not in block
    assert "Date" not in block


def test_the_menu_item_and_handlers_are_wired():
    src = PACKAGED.read_text(encoding="utf-8")
    assert 'data-panel="startover"' in src
    assert 'data-panel-body="startover"' in src
    assert 'id="startover-cancel"' in src
    assert 'id="startover-confirm"' in src
    assert "window.startoverKeys(localStorage)" in src