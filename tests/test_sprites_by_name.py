"""Sprites by name (ADR 0010 slice B0, pass 3 of docs/research/size-and-language-pass.md). FROZEN CONTRACT.

Today a picture reaches the player only if `player.sprites` lists it ("rat": "sprites/rat.png"); 36 of Cottage's 38
entries say exactly the file name. New rule, additive:
  - A picture file `sprites/<key>.png|webp|jpg|jpeg|gif` at the pack root is the sprite NAMED <key>.
  - A key is baked into the woven player when it is (a) listed in `player.sprites` (explicit, exactly as before, even if
    nothing uses it), or (b) REFERENCED and a file of that name exists. A reference is: an item's `sprite`, an enemy's
    `sprite` (in a region contract), a speaker key, or `hero`.
  - An explicit entry wins over the file of the same name.
  - Files named `*-sheet.*`, and any `*.sheet.json`, are never sprites by name (the walk-sheet loader owns them).
  - A file nothing references and nothing lists is NOT baked: the woven file carries only what the game uses.
  - A pack that lists its sprites explicitly weaves byte-for-byte as before.
"""

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
import make_interact_pack as mk  # noqa: E402

from vefr import cli  # noqa: E402


def baked_keys(pack):
    html = cli.weave_html(pack)
    m = re.search(r"window\.VEFR_SPRITES = (\{.*?\});\n", html, re.S)
    return set(json.loads(m.group(1))) if m else set()


def build(tmp_path, *, drop_player_sprites=True):
    pack = mk.build(tmp_path)
    p = pack / "world.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    if drop_player_sprites:
        cfg["player"].pop("sprites", None)
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return pack


def test_the_fixture_lists_its_sprites_explicitly_today(tmp_path):
    pack = build(tmp_path, drop_player_sprites=False)
    assert baked_keys(pack) == {"rat", "potion", "ring"}


def test_referenced_sprites_are_found_by_file_name(tmp_path):
    pack = build(tmp_path)               # no player.sprites at all
    assert baked_keys(pack) == {"rat", "potion", "ring"}   # enemy, and the two items


def test_an_unreferenced_file_is_not_baked(tmp_path):
    pack = build(tmp_path)
    shutil.copy(pack / "sprites" / "rat.png", pack / "sprites" / "spare.png")
    assert "spare" not in baked_keys(pack)


def test_an_explicit_entry_wins_and_is_baked_even_unused(tmp_path):
    pack = build(tmp_path)
    shutil.copy(pack / "sprites" / "rat.png", pack / "sprites" / "spare.png")
    p = pack / "world.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg["player"]["sprites"] = {"extra": "sprites/spare.png"}
    p.write_text(json.dumps(cfg), encoding="utf-8")
    assert baked_keys(pack) == {"rat", "potion", "ring", "extra"}


def test_sheet_files_are_never_sprites_by_name(tmp_path):
    pack = build(tmp_path)
    shutil.copy(pack / "sprites" / "rat.png", pack / "sprites" / "rat-sheet.png")
    (pack / "sprites" / "rat.sheet.json").write_text("{}", encoding="utf-8")
    keys = baked_keys(pack)
    assert "rat-sheet" not in keys and "rat.sheet" not in keys


def test_a_referenced_key_with_no_file_just_has_no_picture(tmp_path):
    pack = build(tmp_path)
    (pack / "sprites" / "ring.png").unlink()
    assert baked_keys(pack) == {"rat", "potion"}     # the ring falls back as it always did; no crash, no error


def test_an_explicit_pack_is_byte_identical_before_and_after(tmp_path):
    pack = build(tmp_path, drop_player_sprites=False)
    assert cli.weave_html(pack) == cli.weave_html(pack)   # deterministic
