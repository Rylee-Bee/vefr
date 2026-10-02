"""Blueprint core: malformed sources fail with a plain BlueprintError, never a raw crash.

Not part of the frozen A1-A12 contract; these guard the type checks the core adds.
"""

import copy
import subprocess
import sys

import pytest

from blueprint_helpers import ROOT, mk
from vefr import blueprint


@pytest.mark.parametrize("path,value,pointer", [
    ("families.beetle.defaults", 5, "/families/beetle/defaults"),
    ("families.beetle.extends", ["x"], "/families/beetle/extends"),
    ("families", [], "/families"),
    ("regions", [], "/regions"),
    ("regions.act-1/cave-2.enemies", {}, "/regions/act-1~1cave-2/enemies"),
    ("regions.act-1/cave-2.enemies.0", "b1", "/regions/act-1~1cave-2/enemies/0"),
    ("regions.act-1/cave-2.enemies.0.family", ["beetle"], "/regions/act-1~1cave-2/enemies/0/family"),
    ("regions.act-1/cave-2.enemies.0.id", "", "/regions/act-1~1cave-2/enemies/0/id"),
    ("regions.act-1/cave-2.enemies.0.id", 7, "/regions/act-1~1cave-2/enemies/0/id"),
    ("regions.act-1/cave-2.enemies.0.at", [1], "/regions/act-1~1cave-2/enemies/0/at"),
    ("regions.act-1/cave-2.enemies.0.at", [True, 2], "/regions/act-1~1cave-2/enemies/0/at"),
    ("regions.act-1/cave-2.enemies.0.properties", [], "/regions/act-1~1cave-2/enemies/0/properties"),
])
def test_wrong_types_raise_a_blueprint_error_with_a_pointer(tmp_path, path, value, pointer):
    # region keys contain '/', so address them by splitting on the first two dots only
    source = copy.deepcopy(mk.STD_BLUEPRINT)
    keys = path.replace("act-1/cave-2", "act-1\0cave-2").split(".")
    node = source
    for key in keys[:-1]:
        key = key.replace("\0", "/")
        node = node[int(key)] if isinstance(node, list) else node[key]
    last = keys[-1].replace("\0", "/")
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value
    with pytest.raises(blueprint.BlueprintError) as err:
        blueprint.expand(source, pack_dir=mk.build(tmp_path))
    assert err.value.pointer == pointer


def test_a_non_object_source_and_a_bad_version_are_plain_errors(tmp_path):
    pack = mk.build(tmp_path)
    for bad in ([], "x", None, {"blueprint": True}):
        with pytest.raises(blueprint.BlueprintError):
            blueprint.expand(bad, pack_dir=pack)


def test_importing_blueprint_does_not_import_cli():
    """cli will import blueprint in the hook PR; blueprint must not need cli at import time."""
    code = "import sys; import vefr.blueprint; print('vefr.cli' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT)
    assert out.stdout.strip() == "False", out.stderr


def test_records_do_not_share_objects(tmp_path):
    pack = mk.build(tmp_path)
    got = blueprint.expand(mk.STD_BLUEPRINT, pack_dir=pack)
    a, b = got["act-1/cave-3"]
    a["at"].append(99)
    assert b["at"] == [6, 4]
    assert mk.STD_BLUEPRINT["families"]["beetle"]["defaults"]["hp"] == 3
