"""Throwaway probe, never merged (2026-10-09): proves the required browser check blocks a merge."""
import os

import pytest


def test_the_browser_gate_probe_fails_only_in_the_browser_job():
    if os.environ.get("VEFR_BROWSER_REQUIRED") != "1":
        pytest.skip("the probe runs only in the browser job")
    pytest.fail("gate probe: this PR must not be mergeable")
