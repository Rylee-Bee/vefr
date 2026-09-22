"""Storyteller provider seam + audition harness tests.

Covers the model-neutral boundary, the per-pack manifest format, the
bundled sample fixture, the fixture-dir seam, the blind-map helper,
and the SKIPPED-on-missing-model behavior. HTTP paths are
monkeypatched; no live backend needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vefr import storyteller_test
from vefr.storyteller import (
    Capabilities,
    InstallMeta,
    Provider,
    ScenePacket,
    Storyteller,
    Tier,
    find_pack,
    list_packs,
    render_scene_packet,
    resolve_active,
)


def test_tier_enum_matches_spec():
    assert Tier.STORYTELLER == 1
    assert Tier.STRUCTURED == 2
    assert Tier.AGENTIC == 3


def test_provider_enum_is_two_values():
    assert Provider.OPENAI_COMPATIBLE.value == "openai-compatible"
    assert Provider.OLLAMA.value == "ollama"
    assert {p.value for p in Provider} == {"openai-compatible", "ollama"}


def test_capabilities_derive_tier():
    assert Capabilities(text=True).tier == Tier.STORYTELLER
    assert Capabilities(text=True, structured_output=True).tier == Tier.STRUCTURED
    assert Capabilities(text=True, tools=True).tier == Tier.AGENTIC
    assert Capabilities(text=True, structured_output=True, tools=False).tier == Tier.STRUCTURED


def test_scene_packet_renders_expected_sections():
    p = ScenePacket(
        speaker="The forge's caretaker",
        speaker_knows="the bell rang after the forge went cold",
        speaker_does_not_know="who left the sealed letter",
        scene="the forge, closed for the night",
        relationship="the player returned a lost tool yesterday",
        recent_action="the player asked who rang the bell",
        open_threads="the morning delivery has not come",
    )
    text = p.render()
    assert "WHO YOU ARE" in text and "caretaker" in text
    assert "WHAT YOU KNOW" in text
    assert "WHAT YOU DO NOT KNOW" in text and "sealed letter" in text
    assert "CURRENT SCENE" in text and "forge" in text
    assert "RELATIONSHIP" in text
    assert "WHAT JUST HAPPENED" in text
    assert "OPEN THREADS" in text
    assert "WRITE" in text


def test_scene_packet_omits_blank_sections():
    p = ScenePacket(
        speaker="Caretaker",
        speaker_knows="x",
        speaker_does_not_know="",
        scene="y",
    )
    text = p.render()
    assert "WHAT YOU DO NOT KNOW" not in text
    assert "RELATIONSHIP" not in text
    assert "WHAT JUST HAPPENED" not in text


def test_manifest_parser_reads_bundled_packs():
    """Every tracked storyteller_packs/<name>/storyteller.toml must load."""
    packs = list_packs()
    ids = {p.id for p in packs}
    # Four audition packs + Gryphe creative ref + engine reference.
    # qwen25-3b is an eval-only pack under data/storytellers/
    # (gitignored, research-only license) - it is asserted separately,
    # only when that per-machine install exists.
    assert "gpt-oss-20b-reference" in ids
    assert "gemma4-e2b" in ids
    assert "gemma4-e4b" in ids
    assert "ministral3-3b" in ids
    assert "gryphe-style-gemma-12b" in ids


def test_manifest_parser_routes_provider_via_enum():
    for st in list_packs():
        assert isinstance(st.model_provider, Provider)
        assert st.model_provider in (Provider.OPENAI_COMPATIBLE, Provider.OLLAMA)


def test_manifest_parser_requires_model():
    """A pack.toml with no [model].model must raise a useful error."""
    from vefr.storyteller import _manifest_to_storyteller

    with pytest.raises(ValueError, match="missing required field 'model.model'"):
        _manifest_to_storyteller("broken", {"model": {}})


def test_manifest_parser_rejects_unknown_provider():
    from vefr.storyteller import _manifest_to_storyteller

    with pytest.raises(ValueError, match="invalid model.provider"):
        _manifest_to_storyteller(
            "bogus",
            {"model": {"model": "x", "provider": "lm-studio-private"}},
        )


def test_license_metadata_recorded():
    gpt = find_pack("gpt-oss-20b-reference")
    assert gpt is not None
    assert gpt.license is not None
    assert gpt.license.spdx == "Apache-2.0"
    assert gpt.license.commercial_use == "allowed"

    # The qwen eval pack is a per-machine install (data/storytellers/
    # is gitignored - research-only license). When it is installed,
    # the harness must surface its non-commercial terms.
    qwen = find_pack("qwen25-3b")
    if qwen is None:
        pytest.skip("qwen25-3b not installed on this machine (eval-only pack)")
    assert qwen.license.commercial_use == "no"
    assert "Research" in qwen.license.spdx or "research" in qwen.license.notes.lower()


def test_install_metadata_optional():
    """A pack with no [install] block must still load cleanly."""
    gpt = find_pack("gpt-oss-20b-reference")
    assert gpt is not None
    assert gpt.install is not None
    # gpt-oss pack does ship install metadata in our bundled set,
    # but a missing block would yield an empty InstallMeta - either
    # outcome is valid.
    assert isinstance(gpt.install, InstallMeta)


def test_resolve_active_returns_a_storyteller():
    st = resolve_active()
    assert isinstance(st, Storyteller)
    assert st.model != ""


def test_render_scene_packet_uses_pack_template(tmp_path, monkeypatch):
    """A pack with a scene template containing {packet} must substitute.

    The fake pack is created under the engine's `data/storytellers/`
    install location (resolved via VEFR_HOME) so `resolve_active()`
    actually sees it via `list_packs()`.
    """
    import os

    home = tmp_path / "vefr-home"
    pack_dir = home / "data" / "storytellers" / "fake"
    pack_dir.mkdir(parents=True)
    (pack_dir / "storyteller.toml").write_text(
        'id = "fake"\n'
        'name = "Fake"\n'
        'version = "0.0.0"\n'
        '[model]\n'
        'provider = "openai-compatible"\n'
        'model = "fake-model"\n',
        encoding="utf-8",
    )
    (pack_dir / "system.md").write_text("system-template", encoding="utf-8")
    (pack_dir / "scene.md").write_text("WRAP: {packet}", encoding="utf-8")

    monkeypatch.setenv("VEFR_HOME", str(home))

    old = os.environ.get("VEFR_STORYTELLER")
    os.environ["VEFR_STORYTELLER"] = "fake-model"
    try:
        packet = ScenePacket(speaker="x", speaker_knows="y", speaker_does_not_know="", scene="z")
        rendered = render_scene_packet(packet)
        assert rendered.startswith("WRAP:")
        assert "WHO YOU ARE" in rendered
    finally:
        if old is None:
            os.environ.pop("VEFR_STORYTELLER", None)
        else:
            os.environ["VEFR_STORYTELLER"] = old


def test_sample_fixture_loads_and_builds_packet():
    fixtures = storyteller_test.list_fixtures()
    assert "sample-scene" in fixtures
    scene = storyteller_test.load_fixture("sample-scene")
    packet = scene.to_packet()
    # Sanity: the sample scene's fields survive the round trip.
    assert "caretaker" in packet.speaker
    assert "bell" in packet.speaker_knows
    assert "sealed letter" in packet.speaker_does_not_know
    assert "forge" in packet.scene
    assert "lost tool" in packet.relationship
    assert "Who rang the bell" in packet.recent_action


def test_env_fixture_dir_adds_pack_scenes(tmp_path, monkeypatch):
    """VEFR_STORYTELLER_FIXTURES dirs join the search (PATH-style, D6)."""
    import os

    d1 = tmp_path / "pack-one"
    d2 = tmp_path / "pack-two"
    d1.mkdir()
    d2.mkdir()
    base = {
        "speaker": "A pack-supplied speaker.",
        "speaker_knows": "Pack knowledge.",
        "speaker_does_not_know": "Pack ignorance.",
        "scene": "A pack scene.",
        "relationship": "None yet.",
        "recent_action": "The player arrived.",
        "open_threads": "One thread.",
    }
    (d1 / "pack-scene.json").write_text(
        json.dumps({"id": "pack-scene", **base}), encoding="utf-8"
    )
    (d2 / "second-scene.json").write_text(
        json.dumps({"id": "second-scene", **base}), encoding="utf-8"
    )

    monkeypatch.setenv(
        "VEFR_STORYTELLER_FIXTURES", f"{d1}{os.pathsep}{d2}"
    )
    fixtures = storyteller_test.list_fixtures()
    assert "pack-scene" in fixtures
    assert "second-scene" in fixtures
    # The engine's bundled sample is still available alongside them.
    assert "sample-scene" in fixtures
    scene = storyteller_test.load_fixture("pack-scene")
    assert scene.speaker == "A pack-supplied speaker."


def test_env_fixture_dir_shadows_engine_fixture(tmp_path, monkeypatch):
    """An env-dir fixture wins a colliding id: runtime config beats repo data."""
    pack_dir = tmp_path / "pack-fixtures"
    pack_dir.mkdir()
    (pack_dir / "sample-scene.json").write_text(
        json.dumps({
            "id": "sample-scene",
            "speaker": "Shadowed by the pack.",
            "speaker_knows": "k",
            "speaker_does_not_know": "d",
            "scene": "s",
            "relationship": "r",
            "recent_action": "a",
            "open_threads": "t",
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("VEFR_STORYTELLER_FIXTURES", str(pack_dir))
    scene = storyteller_test.load_fixture("sample-scene")
    assert scene.speaker == "Shadowed by the pack."


def test_audition_one_skips_on_missing_model(monkeypatch):
    """A 'model not found' HTTP failure must become SKIPPED, not crash.

    The harness imports storytell lazily inside audition_one(), so the
    monkeypatch must target the symbol in the generator module - not
    in storyteller_test, which has no `storytell` attribute at all.
    """
    import vefr.generator as gen_mod

    def fake_storytell(*_args, **_kwargs):
        raise RuntimeError("404 model 'gemma-4-e2b' not found")

    monkeypatch.setattr(gen_mod, "storytell", fake_storytell)

    pack = find_pack("gemma4-e2b")
    scene = storyteller_test.load_fixture("sample-scene")
    result = storyteller_test.audition_one(pack, scene)
    assert result.status == "skipped"
    assert "not found" in result.skip_reason.lower()


def test_audition_one_returns_ok_with_response(monkeypatch):
    import vefr.generator as gen_mod

    def fake_storytell(*_args, **_kwargs):
        return "The caretaker set down the lamp. 'The bell rang once.'"

    monkeypatch.setattr(gen_mod, "storytell", fake_storytell)

    pack = find_pack("gemma4-e2b")
    scene = storyteller_test.load_fixture("sample-scene")
    result = storyteller_test.audition_one(pack, scene)
    assert result.status == "ok"
    assert "caretaker" in result.response
    assert result.latency_s >= 0
    assert result.pack_id == "gemma4-e2b"


def test_blind_map_assigns_unique_labels():
    results = [
        storyteller_test.RunResult(
            pack_id="a", model="m", provider="openai-compatible",
            scene_id="s", scene_version="0", run_number=1,
            seed=None, status="ok",
        ),
        storyteller_test.RunResult(
            pack_id="b", model="n", provider="openai-compatible",
            scene_id="s", scene_version="0", run_number=1,
            seed=None, status="ok",
        ),
        storyteller_test.RunResult(
            pack_id="a", model="m", provider="openai-compatible",
            scene_id="s", scene_version="0", run_number=2,
            seed=None, status="ok",
        ),
    ]
    mapping = storyteller_test.build_blind_map(results)
    assert mapping["a"] == "Storyteller A"
    assert mapping["b"] == "Storyteller B"
    assert len(set(mapping.values())) == 2


def test_write_artifacts_creates_manifest_and_pack_files(tmp_path):
    results = [
        storyteller_test.RunResult(
            pack_id="pack-a", model="m", provider="openai-compatible",
            scene_id="sample-scene", scene_version="0.1.0",
            run_number=1, seed=None, status="ok",
            response="the caretaker answers", latency_s=1.23,
        ),
        storyteller_test.RunResult(
            pack_id="pack-a", model="m", provider="openai-compatible",
            scene_id="sample-scene", scene_version="0.1.0",
            run_number=2, seed=None, status="skipped",
            skip_reason="model not found",
        ),
    ]
    out = storyteller_test.write_artifacts(results, out_dir=tmp_path / "run")
    assert (out / "manifest.json").is_file()
    assert (out / "pack-a.txt").is_file()
    manifest = json.loads((out / "manifest.json").read_text())
    assert len(manifest) == 2
    prose = (out / "pack-a.txt").read_text()
    assert "the caretaker answers" in prose
    assert "SKIPPED" in prose


def test_bundled_packs_have_per_pack_templates():
    """Per-pack templates mean every audition pack owns its own .md siblings."""
    repo = Path(__file__).resolve().parents[1]
    for pack_id in ("gemma4-e2b", "gemma4-e4b", "ministral3-3b"):
        pack_dir = repo / "storyteller_packs" / pack_id
        assert (pack_dir / "storyteller.toml").is_file(), pack_id
        assert (pack_dir / "system.md").is_file(), pack_id
        assert (pack_dir / "scene.md").is_file(), pack_id


def test_qwen_eval_pack_lives_under_data_not_tracked_packs():
    """Qwen2.5-3B's research license means it must not ship as a default.

    The pack is a per-machine eval install under data/storytellers/
    (gitignored). Two invariants hold regardless of whether the
    operator has pulled it: it is never bundled in storyteller_packs/,
    and when it IS installed it lands under data/storytellers/.
    """
    repo = Path(__file__).resolve().parents[1]
    assert not (repo / "storyteller_packs" / "qwen25-3b").is_dir()
    installed = repo / "data" / "storytellers" / "qwen25-3b" / "storyteller.toml"
    if installed.is_file():
        assert find_pack("qwen25-3b") is not None


def test_gitignore_excludes_data_storytellers():
    gi = (Path(__file__).resolve().parents[1] / ".gitignore").read_text()
    assert "/data/storytellers/" in gi
