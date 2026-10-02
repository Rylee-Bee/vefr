"""Blueprint A3, A4: packs without a Blueprint are unchanged; the lock stays out of the woven file."""

import pytest

from blueprint_helpers import ROOT, normalized_pack, vefr

pytestmark = pytest.mark.xfail(strict=True, reason="Blueprint hooks not built yet")


def test_no_blueprint_unchanged(monkeypatch):
    """A3: the hooks add nothing for a pack with no Blueprint and no lock."""
    from vefr import blueprint, cli, maplab

    pack = ROOT / "worlds" / "sample-world"
    base_errors = maplab.validate(maplab.load_pack(pack), pack_dir=pack)
    base_html = cli.weave_html(pack)
    base_check = vefr("check", "--pack", pack)

    calls = []
    monkeypatch.setattr(blueprint, "check_errors", lambda *a, **k: calls.append(a) or [])
    assert maplab.validate(maplab.load_pack(pack), pack_dir=pack) == base_errors
    assert cli.weave_html(pack) == base_html
    assert vefr("check", "--pack", pack) == base_check
    assert not (pack / "blueprint.json").exists() and not (pack / "blueprint.lock.json").exists()


def test_lock_not_in_woven_file(tmp_path):
    """A4: neither the source hash nor any provenance pointer reaches the woven player."""
    import json
    from vefr import cli

    pack = normalized_pack(tmp_path)
    lock = json.loads((pack / "blueprint.lock.json").read_text())
    html = cli.weave_html(pack)
    assert lock["source_sha256"] not in html
    assert "blueprint.lock" not in html and "/regions/" not in html
