"""A descent block is pack data, so `vefr check` speaks about it.

Slice E1 adds the `descent`, `descent entry` and `section` rows to the
schema table and the door onto them in the validator. This is that door:
the fixture pack validates green, and each way a descent can be wrong is
one plain sentence naming the field.
"""

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

from vefr import cli, maplab

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
import make_descent_pack  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not installed")

def _pack(tmp_path, descent=None):
    return make_descent_pack.build(tmp_path, descent=descent)


def _errors(pack):
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def _with(tmp_path, mutate):
    """The fixture pack with its descent block changed by `mutate`."""
    pack = _pack(tmp_path)
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    mutate(world)
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")
    return pack


def test_the_fixture_descent_validates_green(tmp_path):
    assert _errors(_pack(tmp_path)) == []


def test_a_pack_with_no_descent_says_nothing(tmp_path):
    # The sample world itself: no descent, no sentence about one.
    sample = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"
    assert maplab.descent_errors(json.loads(
        (sample / "world.json").read_text(encoding="utf-8"))) == []
    assert "descent" not in maplab.descent_errors({})


def test_a_descent_without_a_run_seed_is_named(tmp_path):
    pack = _with(tmp_path, lambda w: w["descent"].pop("run_seed"))
    assert any("run_seed" in e for e in _errors(pack)), _errors(pack)


def test_a_descent_with_an_unknown_key_is_named(tmp_path):
    pack = _with(tmp_path, lambda w: w["descent"].update(omns=3))
    assert any("omns" in e for e in _errors(pack)), _errors(pack)


def test_an_entry_that_is_not_a_tile_is_named(tmp_path):
    pack = _with(tmp_path,
                 lambda w: w["descent"]["entry"].update(at="7,5"))
    assert any("at" in e for e in _errors(pack)), _errors(pack)


def test_a_section_without_floors_is_named(tmp_path):
    def mutate(world):
        world["descent"]["sections"][0].pop("floors")
    pack = _with(tmp_path, mutate)
    errors = _errors(pack)
    assert any("floors" in e for e in errors), errors
    assert any("/sections/0" in e for e in errors), errors


def test_a_section_named_by_id_must_exist_beside_the_pack(tmp_path):
    # Naming a Section reads `sections/<id>.json`, so a name with no file
    # is said out loud rather than quietly treated as an empty Section.
    pack = _with(tmp_path, lambda w: w["descent"].update(sections=["cellar"]))
    errors = _errors(pack)
    assert any("cellar.json" in e for e in errors), errors


def test_a_section_may_name_a_file_beside_the_pack(tmp_path):
    # The Sections a pack keeps in `sections/<id>.json` are resolved by the
    # same check the bake reads, so the two can never disagree.
    pack = _pack(tmp_path)
    world = json.loads((pack / "world.json").read_text(encoding="utf-8"))
    cellar = copy.deepcopy(world["descent"]["sections"][0])
    (pack / "sections").mkdir(exist_ok=True)
    (pack / "sections" / "cellar.json").write_text(json.dumps(cellar))
    world["descent"]["sections"] = ["cellar"]
    (pack / "world.json").write_text(json.dumps(world), encoding="utf-8")
    assert _errors(pack) == []
    assert json.loads(_def_of(cli.weave_html(pack)))["sections"][0]["id"] == "cellar"


def test_the_bake_carries_the_block_and_the_engine_legend(tmp_path):
    pack = _pack(tmp_path)
    html = cli.weave_html(pack)
    head = html.split("window.VEFR_DESCENT_DEF = ")[1].split("\n")[0]
    block = json.loads(head.rstrip(";"))
    assert block["run_seed"] == "run-a"
    assert block["sections"][0]["id"] == "cellar"
    assert block["legend"]["#"]["solid"] is True
    assert block["legend"]["d"]["tile"] == "dungeon-stairs-down"


def test_a_pack_with_no_descent_bakes_null(tmp_path):
    sample = Path(__file__).resolve().parents[1] / "worlds" / "sample-world"
    html = cli.weave_html(sample)
    assert "window.VEFR_DESCENT_DEF = null;" in html

def _def_of(html):
    """The descent block a woven file carries, as JSON."""
    head = html.split("window.VEFR_DESCENT_DEF = ")[1].split("\n")[0]
    return head.rstrip(";")
