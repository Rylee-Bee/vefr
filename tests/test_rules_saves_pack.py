"""Durable rule saves: the pack field and its docs (S11, S13, S14). FROZEN CONTRACT.

`saves` is an optional top-level block in world.json:
  "saves": {"rules": "persist" | "reset", "legacy": "fresh" | "from-log"}
Absent means reset. See docs/plans/durable-rule-saves-plan.md.
"""

import sys
from pathlib import Path

import pytest

from vefr import maplab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_rules_pack as mk  # noqa: E402


def errors_for(tmp_path, saves):
    pack = mk.build_saves(tmp_path, saves=saves)
    return maplab.validate(maplab.load_pack(pack), pack_dir=pack)


def test_s11_an_absent_block_is_unchanged(tmp_path):
    assert errors_for(tmp_path, None) == []


@pytest.mark.parametrize("saves", [
    {"rules": "persist"}, {"rules": "reset"}, {}, {"rules": "persist", "legacy": "fresh"},
    {"rules": "persist", "legacy": "from-log"}, {"legacy": "from-log"},
])
def test_s11_valid_blocks_pass(tmp_path, saves):
    assert errors_for(tmp_path, saves) == []


@pytest.mark.parametrize("saves,needle", [
    ("persist", "saves"), (1, "saves"), ([], "saves"),
    ({"rules": "always"}, "saves.rules"), ({"rules": 1}, "saves.rules"),
    ({"rules": "persist", "legacy": "maybe"}, "saves.legacy"),
    ({"legacy": 3}, "saves.legacy"),
    ({"rules": "persist", "extra": True}, "saves"),
])
def test_s11_and_s14_invalid_blocks_fail_with_one_plain_sentence(tmp_path, saves, needle):
    errors = errors_for(tmp_path, saves)
    assert len(errors) == 1 and needle in errors[0]


def test_load_pack_carries_a_declared_block_through(tmp_path):
    pack = mk.build_saves(tmp_path, saves={"rules": "persist"})
    assert maplab.load_pack(pack)["saves"] == {"rules": "persist"}
    plain = mk.build_saves(tmp_path / "x", saves=None)
    assert "saves" not in maplab.load_pack(plain)


def test_s13_docs_name_the_block_both_values_and_the_default():
    rules = (ROOT / "docs" / "guides" / "rules.md").read_text(encoding="utf-8")
    for needle in ("saves.rules", "persist", "reset", "saves.legacy", "from-log", "fresh"):
        assert needle in rules, needle
    assert "default" in rules.lower()
    glossary = (ROOT / "docs" / "guides" / "glossary.md").read_text(encoding="utf-8")
    assert "Rule saves" in glossary


def test_the_one_rule_fires_at_most_once_sentence_is_true_in_both_modes():
    """rules.md:76 says a once rule fires at most once. After the change it must say in which mode."""
    rules = (ROOT / "docs" / "guides" / "rules.md").read_text(encoding="utf-8")
    line = next(ln for ln in rules.splitlines() if "fires at most" in ln or "at most once" in ln)
    assert "reload" in rules.split(line, 1)[1][:600].lower() or "reload" in line.lower()
