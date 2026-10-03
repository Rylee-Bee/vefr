"""Blueprint in the feature catalog: `vefr features` can tell whether a pack uses it."""

from pathlib import Path

from blueprint_helpers import ROOT, mk
from vefr import features


def _use(pack):
    return next(u for u in features.scan_pack(pack) if u["id"] == "blueprint")


def test_the_catalog_lists_blueprint_with_a_real_detector():
    catalog = features.load_catalog()
    entry = next(f for f in catalog if f["id"] == "blueprint")
    assert entry["detect"] == "blueprint" and entry["status"] == "built"
    assert "blueprint" in features.VALID_DETECTS
    assert features.catalog_errors() == []


def test_a_pack_with_a_blueprint_uses_it_and_a_plain_pack_does_not(tmp_path):
    used = _use(mk.build(tmp_path, blueprint=mk.STD_BLUEPRINT))
    assert used["used"] is True and "2 regions" in used["detail"]
    plain = _use(Path(ROOT) / "worlds" / "sample-world")
    assert plain["used"] is False
