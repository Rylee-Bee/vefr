"""The woven pool - real generations baked in for serverless play."""

import json
from types import SimpleNamespace

from vefr.pool import build_pool, ensure_current_world


def _fake_world(monkeypatch):
    from vefr import world as world_mod

    monkeypatch.setattr(
        world_mod, "load_world",
        lambda name=None: {
            "title": "T",
            "phases": {"whispers": "", "doubts": ""},
            "speakers": {"ferry": {"name": "the ferryman"}, "katla": {"name": "Katla"}},
        },
    )


def _fake_generators(monkeypatch, rumor=None, line=None, letter=None, forge=None):
    import vefr.forge as forge_mod
    import vefr.generator as gen_mod
    import vefr.npc as npc_mod
    import vefr.stefna as stefna_mod

    rumor = rumor or (lambda ph: SimpleNamespace(
        speaker="the ferryman", whisper=f"w-{ph}", is_true=True))
    line = line or (lambda ph, key: SimpleNamespace(speaker="the ferryman", line=f"l-{ph}-{key}"))
    letter = letter or (lambda: SimpleNamespace(letter="For you."))
    forge = forge or (lambda: SimpleNamespace(
        model_dump=lambda: {"name": "knife", "bond": "assigned"}))
    monkeypatch.setattr(gen_mod, "generate_rumor", rumor)
    monkeypatch.setattr(npc_mod, "generate_line", line)
    monkeypatch.setattr(stefna_mod, "generate_letter", letter)
    monkeypatch.setattr(forge_mod, "forge_item", forge)


def test_build_pool_shapes_and_counts(monkeypatch):
    _fake_world(monkeypatch)
    _fake_generators(monkeypatch)
    p = build_pool(samples=5, specials=3)
    assert set(p) == {"rumor:whispers", "rumor:doubts",
                      "npc:whispers:ferry", "npc:whispers:katla",
                      "npc:doubts:ferry", "npc:doubts:katla",
                      "letter", "forge"}
    assert len(p["rumor:whispers"]) == 5
    assert p["rumor:doubts"][0]["whisper"] == "w-doubts"
    assert p["npc:doubts:katla"][0]["line"] == "l-doubts-katla"
    assert p["letter"][0] == {"letter": "For you."}
    assert p["forge"][0] == {"name": "knife", "bond": "assigned"}


def test_pool_tolerates_a_cold_model(monkeypatch):
    _fake_world(monkeypatch)

    def cold_rumor(ph):
        raise RuntimeError("model cold")

    _fake_generators(monkeypatch, rumor=cold_rumor)
    p = build_pool(samples=5, specials=3)
    assert p["rumor:whispers"] == []
    # The rest of the pool still wove.
    assert len(p["npc:whispers:ferry"]) == 5
    assert len(p["letter"]) == 3


def test_progress_callback_reports(monkeypatch):
    _fake_world(monkeypatch)
    _fake_generators(monkeypatch)
    seen = {}
    build_pool(samples=2, specials=1, progress=lambda k, n: seen.update({k: n}))
    assert seen["rumor:whispers"] == 2
    assert seen["letter"] == 1


def test_ensure_current_world_points_generation_at_pack(monkeypatch):
    monkeypatch.delenv("VEFR_WORLD", raising=False)
    ensure_current_world("sample-world")
    import os

    assert os.environ["VEFR_WORLD"] == "sample-world"


def test_weave_bakes_pool_into_html(tmp_path, monkeypatch):
    import vefr.cli as cli

    pack = tmp_path / "worlds" / "poolworld"
    pack.mkdir(parents=True)
    (pack / "world.json").write_text(json.dumps(
        {"title": "Pool", "phases": {"whispers": ""}}), encoding="utf-8")
    (pack / "logbok.md").write_text("# canon", encoding="utf-8")
    (pack / "ledger.md").write_text("", encoding="utf-8")
    (pack / "voices").mkdir()
    (pack / "voices" / "ferry.md").write_text("voice", encoding="utf-8")

    monkeypatch.setattr(cli, "pack_root", lambda: tmp_path)
    from vefr import world as world_mod

    monkeypatch.setattr(world_mod, "load_world", lambda name=None: {
        "title": "Pool", "phases": {"whispers": ""},
        "speakers": {"ferry": {"name": "the ferryman"}}})
    _fake_generators(monkeypatch)

    out = tmp_path / "out.html"
    args = type("A", (), {"pack": str(pack), "out": str(out), "pool": 2,
                          "with_bundle": False, "vault": None,
                          "journal": None, "from_live": None})()
    rc = cli.cmd_build_web(args)
    assert rc == 0
    html = out.read_text(encoding="utf-8")
    assert "{{pool_json}}" not in html
    assert "window.VEFR_POOL" in html
    assert "w-doubts" in html or "w-whispers" in html


def test_weave_without_pool_leaves_empty_pool(tmp_path, monkeypatch):
    import vefr.cli as cli

    pack = tmp_path / "worlds" / "plain"
    pack.mkdir(parents=True)
    (pack / "world.json").write_text(json.dumps({"title": "P", "phases": {}}),
                                     encoding="utf-8")
    (pack / "logbok.md").write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "pack_root", lambda: tmp_path)
    from vefr import world as world_mod

    monkeypatch.setattr(world_mod, "load_world",
                        lambda name=None: {"title": "P", "phases": {}})

    out = tmp_path / "out.html"
    args = type("A", (), {"pack": str(pack), "out": str(out), "pool": 0,
                          "with_bundle": False, "vault": None,
                          "journal": None, "from_live": None})()
    rc = cli.cmd_build_web(args)
    assert rc == 0
    assert "window.VEFR_POOL = {}" in out.read_text(encoding="utf-8")
