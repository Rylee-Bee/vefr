"""Weave template resolution: checkout, wheel package data, container.

cmd_build_web reads web/packaged.html. A source checkout has it at
the repo root; a pip-installed wheel (a pack author running
`ratatoskr weave` from their own repo) has it only as package data;
containers keep it under VEFR_HOME. _template_candidates() must
cover all three, in that preference order - and the wheel config
must actually ship the file.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from vefr import cli
from vefr.paths import app_home


def test_candidates_cover_all_three_layouts_in_order():
    here = Path(cli.__file__).resolve()
    expected = [
        here.parents[2] / "web" / "packaged.html",   # source checkout
        here.parent / "web" / "packaged.html",        # wheel package data
        app_home() / "web" / "packaged.html",         # container / VEFR_HOME
    ]
    assert cli._template_candidates() == expected


def test_checkout_template_exists():
    """In a source checkout (dev box and CI) candidate 1 must be real."""
    checkout = Path(cli.__file__).resolve().parents[2] / "web" / "packaged.html"
    assert checkout.exists()
    assert any(p.exists() for p in cli._template_candidates())


def test_wheel_config_ships_template_as_package_data():
    """The wheel must force-include the template - that is what makes
    the package-data candidate true for an installed engine.

    Without this pin the wheel-layout candidate silently points at a
    file nobody ships and weave breaks again for pack authors.
    """
    repo = Path(cli.__file__).resolve().parents[2]
    cfg = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = cfg["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include["web/packaged.html"] == "vefr/web/packaged.html"
