"""Skin loader, K1 (design/ui-skin.md rules 1, 5, 6): a pack may name a skin folder.

`"skin": "skins/<name>"` in world.json points at a folder inside the pack with a `skin.json`.
`maplab.validate` refuses a bad skin with a plain sentence; the bake carries a good one into the
woven file as data URIs (`window.VEFR_SKIN`); a pack with no skin bakes `window.VEFR_SKIN = null;`.
"""

import copy
import json
import re
import sys
from pathlib import Path

import pytest

from vefr import cli, maplab

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
import make_skin_pack as mk  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def errors(pack):
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def has(errs, *needles):
    return any(all(n.lower() in e.lower() for n in needles) for e in errs)


def test_a_good_skin_validates_and_loads(tmp_path):
    pack = mk.build(tmp_path)
    assert errors(pack) == []
    assert maplab.load_pack(pack)["skin"] == "skins/test-skin"


def test_a_pack_without_a_skin_is_unchanged():
    assert "skin" not in maplab.load_pack(ROOT / "worlds" / "sample-world")


@pytest.mark.parametrize("mutate,needles", [
    (lambda s: s.pop("name"), ("skin", "name")),
    (lambda s: s.update(credit=""), ("skin", "credit")),
    (lambda s: s["parts"].update(sparkle={"file": "panel.png"}), ("sparkle",)),
    (lambda s: s["parts"]["panel"].update(file="nope.png"), ("nope.png",)),
    (lambda s: s["parts"]["panel"].update(file="panel.gif"), (".gif",)),
    (lambda s: s["parts"]["panel"].update(slice=0), ("slice",)),
    (lambda s: s["parts"]["panel"].update(slice="wide"), ("slice",)),
    (lambda s: s["parts"]["panel"].update(slice=40), ("slice",)),     # a 64 px panel: at most 32
    (lambda s: s["ink"].update(on_panel="brown"), ("ink",)),
    (lambda s: s["parts"]["button"].update(hover="gone.png"), ("gone.png",)),
])
def test_a_bad_skin_is_named(tmp_path, mutate, needles):
    skin = copy.deepcopy(mk.SKIN)
    mutate(skin)
    files = dict(mk.FILES)
    if skin["parts"]["panel"].get("file") == "panel.gif":
        files["panel.gif"] = (64, 64)
    assert has(errors(mk.build(tmp_path, skin=skin, files=files)), *needles), needles


def test_a_missing_skin_json_or_folder(tmp_path):
    pack = mk.build(tmp_path)
    (pack / "skins" / "test-skin" / "skin.json").unlink()
    assert has(errors(pack), "skin.json")
    world = json.loads((pack / "world.json").read_text())
    world["skin"] = "skins/not-here"
    (pack / "world.json").write_text(json.dumps(world))
    assert has(errors(pack), "skin")


def test_a_skin_may_not_leave_the_pack(tmp_path):
    pack = mk.build(tmp_path)
    world = json.loads((pack / "world.json").read_text())
    for bad in ("../outside", "/etc", "skins/../../x"):
        world["skin"] = bad
        (pack / "world.json").write_text(json.dumps(world))
        assert has(errors(pack), "skin"), bad


def test_a_huge_picture_is_refused(tmp_path):
    pack = mk.build(tmp_path)
    (pack / "skins" / "test-skin" / "panel.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 400_000)
    assert has(errors(pack), "panel.png", "big")


def _baked(html):
    m = re.search(r"window\.VEFR_SKIN = (.*);\n", html)
    assert m, "no VEFR_SKIN line"
    return m.group(1)


def test_the_bake_carries_a_skin_as_data_uris(tmp_path):
    html = cli.weave_html(mk.build(tmp_path))
    skin = json.loads(_baked(html))
    assert skin["name"] == "test-skin" and skin["credit"].startswith("Rylee and Claude")
    assert skin["parts"]["panel"]["file"].startswith("data:image/png;base64,")
    assert skin["parts"]["panel"]["slice"] == 16
    assert skin["parts"]["button"]["hover"].startswith("data:image/png;base64,")
    assert skin["ink"]["on_panel"] == "#2B2118"
    assert "http://" not in _baked(html) and "https://" not in _baked(html)   # one file, offline


def test_a_pack_with_no_skin_bakes_null():
    html = cli.weave_html(ROOT / "worlds" / "sample-world")
    assert _baked(html) == "null"
