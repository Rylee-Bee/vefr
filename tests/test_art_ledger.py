"""A1 (tighten-shapes), ADR 0011. FROZEN CONTRACT for src/vefr/art_ledger.py (stdlib only) and `vefr art`.

  art_ledger.ROLES                      tuple of the five role names
  art_ledger.check(ledger_dir, root)    -> list[str], one plain sentence per problem, each naming the file and
                                           picture id; [] when the ledger is good. Reads every round-*.json in
                                           ledger_dir in sorted order.
  art_ledger.credits(ledger_dir)        -> str, markdown, one line per picture in file then picture order:
                                           "- <to>: <made_with>, <style> (round <round>)"
  vefr art check --ledger D [--root R]  exit 0 and prints "ok" when good, else prints problems and exits 1
  vefr art credits --ledger D           prints credits()
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from vefr import art_ledger

ROOT = Path(__file__).resolve().parents[1]


def _png(path, data=b"picture-bytes"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _repo(tmp_path, **patch):
    sha = _png(tmp_path / "sprites" / "ladle.png")
    pic = {"id": "ladle", "role": "item-icon", "subject": "a copper ladle", "to": "sprites/ladle.png", "sha256": sha}
    led = {"ledger": 1, "round": 19, "made_with": "codex", "style": "storybook-item", "pictures": [pic]}
    for k, v in patch.items():
        led[k] = v
    d = tmp_path / "art" / "ledger"
    d.mkdir(parents=True)
    (d / "round-19.json").write_text(json.dumps(led))
    return d, led


def _write(d, led, name="round-19.json"):
    (d / name).write_text(json.dumps(led))


def test_roles():
    assert art_ledger.ROLES == ("item-icon", "creature", "tile", "sheet", "ui-part")


def test_a_good_ledger_has_no_problems(tmp_path):
    d, _ = _repo(tmp_path)
    assert art_ledger.check(d, tmp_path) == []


def test_an_unknown_picture_key_is_named(tmp_path):
    d, led = _repo(tmp_path)
    led["pictures"][0]["colour"] = "red"
    _write(d, led)
    (p,) = art_ledger.check(d, tmp_path)
    assert "colour" in p and "ladle" in p and "round-19.json" in p


def test_an_unknown_top_key_is_named(tmp_path):
    d, led = _repo(tmp_path, mood="sad")
    (p,) = art_ledger.check(d, tmp_path)
    assert "mood" in p


@pytest.mark.parametrize("key", ["id", "role", "subject", "to", "sha256"])
def test_a_missing_required_picture_key_is_named(tmp_path, key):
    d, led = _repo(tmp_path)
    del led["pictures"][0][key]
    _write(d, led)
    assert any(key in p for p in art_ledger.check(d, tmp_path))


def test_a_bad_role_names_the_choices(tmp_path):
    d, led = _repo(tmp_path)
    led["pictures"][0]["role"] = "banner"
    _write(d, led)
    (p,) = art_ledger.check(d, tmp_path)
    assert "banner" in p and "item-icon" in p


def test_a_changed_picture_fails_the_hash(tmp_path):
    d, _ = _repo(tmp_path)
    (tmp_path / "sprites" / "ladle.png").write_bytes(b"edited")
    (p,) = art_ledger.check(d, tmp_path)
    assert "sha256" in p and "ladle" in p


def test_a_missing_picture_is_named(tmp_path):
    d, _ = _repo(tmp_path)
    (tmp_path / "sprites" / "ladle.png").unlink()
    (p,) = art_ledger.check(d, tmp_path)
    assert "sprites/ladle.png" in p


def test_duplicate_ids_across_rounds_are_named(tmp_path):
    d, led = _repo(tmp_path)
    _write(d, led, "round-20.json")
    assert any("ladle" in p and "twice" in p for p in art_ledger.check(d, tmp_path))


@pytest.mark.parametrize("bad", ["/tmp/scratch/a.png", "/home/someone/a.png", "~/a.png", "../a.png", "/abs/a.png"])
def test_the_clean_credits_rule_rejects_paths_anywhere(tmp_path, bad):
    d, led = _repo(tmp_path)
    led["pictures"][0]["ref"] = bad
    _write(d, led)
    assert any("ref" in p and bad in p for p in art_ledger.check(d, tmp_path))


def test_a_note_is_checked_too(tmp_path):
    d, led = _repo(tmp_path)
    led["pictures"][0]["note"] = "made in /tmp/x"
    _write(d, led)
    assert any("note" in p for p in art_ledger.check(d, tmp_path))


def test_not_json_is_one_sentence_not_a_traceback(tmp_path):
    d, _ = _repo(tmp_path)
    (d / "round-21.json").write_text("{nope")
    (p,) = art_ledger.check(d, tmp_path)
    assert "round-21.json" in p


def test_credits_are_generated_in_order(tmp_path):
    d, _ = _repo(tmp_path)
    assert art_ledger.credits(d).strip() == "- sprites/ladle.png: codex, storybook-item (round 19)"


def _cli(*args):
    code = "import sys; from vefr.cli import vefr_main; sys.argv = ['vefr'] + sys.argv[1:]; sys.exit(vefr_main())"
    return subprocess.run([sys.executable, "-c", code, *args], capture_output=True, text=True, cwd=ROOT)


def test_cli_check_ok_and_failing(tmp_path):
    d, _ = _repo(tmp_path)
    r = _cli("art", "check", "--ledger", str(d), "--root", str(tmp_path))
    assert (r.returncode, r.stdout.strip()) == (0, "ok")
    (tmp_path / "sprites" / "ladle.png").write_bytes(b"edited")
    r = _cli("art", "check", "--ledger", str(d), "--root", str(tmp_path))
    assert r.returncode == 1 and "sha256" in r.stdout


def test_cli_credits(tmp_path):
    d, _ = _repo(tmp_path)
    r = _cli("art", "credits", "--ledger", str(d))
    assert r.returncode == 0 and "sprites/ladle.png: codex" in r.stdout
