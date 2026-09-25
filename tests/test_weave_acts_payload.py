"""Weave must bake the resolved pack shape, not the raw world.json root.

Regression for the acts-shape defect: for acts packs (town/speakers/creed live
under acts/<id>/), cmd_build_web baked the raw world.json, so the woven player
got no town block (blank canvas) and no root speakers (no npc: pools). The
build now merges load_pack(pack) over the raw root, matching the CLI's live
world shape.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from vefr.cli import cmd_build_web
from vefr.maplab import load_pack


def _write_act_pack(root):
    """Acts-shape pack: root world.json is a shell; content lives in acts/.

    Mirrors worlds/sample-world's on-disk layout: acts/<id>/world.json holds
    regions + speakers, and the town metadata lives in the region contract.
    """
    (root / "world.json").write_text(
        json.dumps(
            {
                "name": "Weave Act Pack",
                "title": "Weave Act Pack",
                "phases": {"whispers": "", "doubts": ""},
                "gold_rule": "Walk softly.",
                "hero_start": {"x": 1, "y": 1},
            }
        ),
        encoding="utf-8",
    )
    act = root / "acts" / "act-1"
    region = act / "town"
    region.mkdir(parents=True)
    (act / "world.json").write_text(
        json.dumps(
            {
                "id": "act-1",
                "title": "Act I",
                "regions": {"town": {}},
                "speakers": {
                    "The Cook": {
                        "aliases": ["cook"],
                        "kind": "person",
                        "voice": "default",
                        "memory_key": "the_cook",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (region / "contract.json").write_text(
        json.dumps({"hero_start": [1, 1], "legend": {"#": {"solid": True}}}),
        encoding="utf-8",
    )
    (region / "map.md").write_text("# #\n# .\n", encoding="utf-8")
    return root


def test_load_pack_resolves_act_speakers_and_cre(tmp_path):
    """load_pack is the unified shape weave bakes: town + speakers + creed."""
    pack = _write_act_pack(tmp_path)
    resolved = load_pack(pack)

    assert "The Cook" in resolved["speakers"]
    assert resolved["town"]["map"] == ["# #", "# ."]
    assert resolved["creed"] == "Walk softly."  # gold_rule read-fallback


def test_weave_bakes_resolved_world(tmp_path, monkeypatch):
    """The woven window.VEFR_WORLD carries town, speakers, and the creed."""
    pack = _write_act_pack(tmp_path)
    out = tmp_path / "woven.html"

    monkeypatch.setattr("vefr.cli.pack_root", lambda: tmp_path)
    args = SimpleNamespace(
        pack=str(pack), out=str(out), pool=0, with_bundle=False,
        vault=None, journal=None, from_live=None,
    )
    assert cmd_build_web(args) == 0

    html = out.read_text(encoding="utf-8")
    marker = "window.VEFR_WORLD = "
    start = html.index(marker) + len(marker)
    end = html.index("\n", start)
    baked = json.loads(html[start:end].rstrip(";"))

    assert baked["town"]["map"] == ["# #", "# ."]  # previously absent -> blank canvas
    assert baked["speakers"]["The Cook"]  # previously absent -> no npc: pools
    assert baked["creed"] == "Walk softly."  # previously the default tagline
    assert baked["phases"] == {"whispers": "", "doubts": ""}
    assert baked["hero_start"] == {"x": 1, "y": 1}  # raw root fields ride along


def test_weave_keeps_acts_for_relative_out_of_root_pack(tmp_path, monkeypatch):
    """A relative --pack outside the engine's worlds root still bakes acts.

    Regression: `ratatoskr weave --pack ../<other-repo>/worlds/<pack>` dropped
    VEFR_WORLD.acts (load_world joined the relative path under worlds/ and the
    failure was swallowed), so the player's act router never saw the act's
    ruleset and fell back to the town surface.
    """
    engine = tmp_path / "engine"
    engine.mkdir()
    (tmp_path / "elsewhere").mkdir()
    pack = _write_act_pack(tmp_path / "elsewhere")
    act_json = pack / "acts" / "act-1" / "world.json"
    data = json.loads(act_json.read_text(encoding="utf-8"))
    data["ruleset"] = "cooking"
    act_json.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "woven.html"

    monkeypatch.setattr("vefr.cli.pack_root", lambda: engine)
    monkeypatch.chdir(engine)
    args = SimpleNamespace(
        pack="../elsewhere", out=str(out), pool=0, with_bundle=False,
        vault=None, journal=None, from_live=None,
    )
    assert cmd_build_web(args) == 0

    html = out.read_text(encoding="utf-8")
    marker = "window.VEFR_WORLD = "
    start = html.index(marker) + len(marker)
    baked = json.loads(html[start:html.index("\n", start)].rstrip(";"))

    assert [a.get("ruleset") for a in baked.get("acts") or []] == ["cooking"]
