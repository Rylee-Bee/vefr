"""The features catalog: one source of truth for what VEFR can do (docs/features.json).

`vefr.features` reads the catalog, checks it cannot drift from the repo, and scans a pack to say
which features it uses. `vefr features` (CLI) and `GET /api/features` (read-only route) both
return the same report; the studio draws it as two shelves.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from vefr import cli, features

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
import make_events_pack  # noqa: E402
import make_growth_pack  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "worlds" / "sample-world"
REQUIRED = {"rules", "interact", "quiet-ui", "growth", "combat", "library", "items", "fog",
            "delve", "dev-verbs", "skin", "random-floors", "gates", "album", "equipment", "acts"}


# ------------------------------------------------------------------ the catalog

def test_the_catalog_loads_and_has_the_known_features():
    cat = features.load_catalog()
    assert {f["id"] for f in cat} >= REQUIRED
    for f in cat:
        assert set(f) >= {"id", "name", "what", "status", "detect", "docs", "design", "tests"}


def test_the_real_catalog_has_no_drift():
    assert features.catalog_errors() == []


def _write(tmp_path, feats):
    d = tmp_path / "repo"
    (d / "docs").mkdir(parents=True, exist_ok=True)
    (d / "docs" / "features.json").write_text(json.dumps({"version": 1, "features": feats}))
    return d


def _f(**kw):
    base = dict(id="x", name="X", what="w", status="built", detect="none",
                docs=["a.md"], design=None, tests=["t.py"])
    base.update(kw)
    return base


@pytest.mark.parametrize("mutate,needle", [
    (lambda f: f.update(status="done"), "status"),
    (lambda f: f.update(docs=[]), "docs"),                      # built needs a guide
    (lambda f: f.update(tests=[]), "tests"),                    # built needs a test
    (lambda f: f.update(docs=["missing.md"]), "missing.md"),    # a named path must exist
    (lambda f: f.update(detect="telepathy"), "detect"),
    (lambda f: f.update(name=""), "name"),
])
def test_drift_is_named(tmp_path, mutate, needle):
    d = _write(tmp_path, [])
    (d / "a.md").write_text("x")
    (d / "t.py").write_text("x")
    f = _f()
    mutate(f)
    d = _write(tmp_path, [f])
    errors = features.catalog_errors(d)
    assert any(needle in e for e in errors), errors


def test_a_proposed_feature_needs_its_design_and_ids_are_unique(tmp_path):
    d = _write(tmp_path, [_f(id="p", status="proposed", docs=[], tests=[], design="design/p.md"),
                          _f(id="p", status="proposed", docs=[], tests=[], design=None)])
    errors = features.catalog_errors(d)
    assert any("design" in e for e in errors) and any("duplicate" in e.lower() for e in errors), errors


# ---------------------------------------------------------------- scanning a pack

def _uses(report):
    return {u["id"]: u for u in report["pack"]["uses"]}


def test_scan_a_growth_pack(tmp_path):
    pack = make_growth_pack.build(tmp_path, growth=make_growth_pack.LEVELS, xp=3)
    u = _uses(features.report(pack))
    assert u["growth"]["used"] is True and "levels" in u["growth"]["detail"]
    assert u["combat"]["used"] is True and "1" in u["combat"]["detail"]
    assert u["interact"]["used"] is True               # always on
    assert u["skin"]["used"] is False
    assert u["delve"]["used"] is None                  # not detectable from a pack: unknown, not "no"


def test_scan_the_events_pack_sees_rules_items_library(tmp_path):
    pack = make_events_pack.build(tmp_path)
    u = _uses(features.report(pack))
    assert u["rules"]["used"] is True and any(c.isdigit() for c in u["rules"]["detail"])
    assert u["items"]["used"] is True and u["library"]["used"] is True


def test_scan_the_plain_sample_world_uses_no_growth_or_rules():
    u = _uses(features.report(SAMPLE))
    assert u["growth"]["used"] is False and u["rules"]["used"] is False
    assert u["interact"]["used"] is True


def test_the_report_is_plain_json():
    rep = features.report(SAMPLE)
    assert json.loads(json.dumps(rep)) == rep
    assert rep["pack"]["name"] == "sample-world"
    assert {f["id"] for f in rep["catalog"]} >= REQUIRED
    assert features.report(None)["pack"] is None        # catalog-only report


# ----------------------------------------------------------------------- the CLI

def test_cli_json_and_table(capsys):
    rc = cli.cmd_features(SimpleNamespace(pack=str(SAMPLE), json=True))
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["pack"]["name"] == "sample-world"
    rc = cli.cmd_features(SimpleNamespace(pack=None, json=False))
    text = capsys.readouterr().out
    assert rc == 0 and "growth" in text and "proposed" in text.lower()


def test_cli_checks_the_catalog(capsys):
    assert cli.cmd_features(SimpleNamespace(pack=None, json=False, check=True)) == 0


# ------------------------------------------------------------------- the API route

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from vefr.main import app
    return TestClient(app)


def test_api_returns_the_catalog(client):
    r = client.get("/api/features")
    assert r.status_code == 200
    body = r.json()
    assert {f["id"] for f in body["catalog"]} >= REQUIRED and body["pack"] is None


def test_api_scans_a_named_world(client):
    r = client.get("/api/features", params={"pack": "sample-world"})
    assert r.status_code == 200 and r.json()["pack"]["name"] == "sample-world"


@pytest.mark.parametrize("bad", ["../etc", "/etc/passwd", "a/b", "..", "no-such-world-xyz"])
def test_api_refuses_a_path_or_unknown_world(client, bad):
    assert client.get("/api/features", params={"pack": bad}).status_code in (400, 404)


def test_api_is_read_only(client):
    assert client.post("/api/features").status_code == 405
