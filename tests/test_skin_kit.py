"""A skin kit manifest is DATA. FROZEN CONTRACT for src/vefr/skin_kit.py (stdlib only).

  skin_kit.KitError              ValueError carrying ONE plain sentence, never a traceback
  skin_kit.load_kit(path)        -> dict, the manifest as read; KitError on any problem
  skin_kit.report(kit, src)      -> list[str], one line per piece in manifest order,
                                   f'{name}: {status}' where status is drawn | derived | missing
  skin_kit.run(kit_path, src)    -> int, prints the report then the total line
                                   f'{N} of {M} pieces drawn, {K} chosen, {D} derived'
                                   0 when every required piece is drawn or derived, else 1

A piece is a JSON object: name, kind, size, make are required; slice, fill and
required are optional. make is draw, copy, or derive:<recipe>, where a recipe is
tint(r,g,b,amount) or flip-knob. A derived piece needs a base: the piece in the
same kit whose name is the LONGEST PROPER PREFIX of the derived piece's name,
compared on the stem (the part before the extension) - so button.webp bases
button-hover.webp, and toggle-on.webp bases nothing.

The derive tests pin the contract of tools/art/derive.py, which is written by
another worker. They skip cleanly when Pillow is absent; they never skip for any
other reason - a missing derive module is a failure, not a skip.
"""
import json
import os
import sys
from pathlib import Path

import pytest

from vefr import skin_kit


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _write(tmp_path, data, name="kit.json"):
    """Write a manifest (dict or raw text) and return its path."""
    path = tmp_path / name
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _good():
    """A good two-piece kit: a drawn button and a tint of it."""
    return {
        "schema": 1,
        "kit": "cottage",
        "pieces": [
            {"name": "button.webp", "kind": "box", "size": [96, 40], "slice": 14,
             "fill": "parchment", "make": "draw"},
            {"name": "button-hover.webp", "kind": "box", "size": [96, 40], "slice": 14,
             "make": "derive:tint(255,255,255,0.10)"},
        ],
    }


def _one_sentence(exc):
    """Assert `exc` is one plain sentence and hand the text back."""
    text = str(exc)
    assert isinstance(exc, skin_kit.KitError)
    assert isinstance(exc, ValueError)
    assert text.strip() == text, "the sentence has leading or trailing space"
    assert "\n" not in text, f"the sentence is more than one line: {text!r}"
    assert "Traceback" not in text
    assert text.endswith("."), f"the sentence does not end in a full stop: {text!r}"
    assert len(text.splitlines()) == 1
    return text


def _bad(tmp_path, data, name="kit.json"):
    """A manifest that must be refused, as one plain sentence."""
    with pytest.raises(skin_kit.KitError) as caught:
        skin_kit.load_kit(_write(tmp_path, data, name))
    return _one_sentence(caught.value)


def _src(tmp_path, *names):
    """A picture directory holding a file per name (contents do not matter)."""
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    for name in names:
        (src / name).write_bytes(b"picture-bytes")
    return src


# --------------------------------------------------------------------------
# 1. a good manifest loads
# --------------------------------------------------------------------------

def test_a_good_manifest_loads_with_its_schema_kit_and_every_piece(tmp_path):
    kit = skin_kit.load_kit(_write(tmp_path, _good()))
    assert kit["schema"] == 1
    assert kit["kit"] == "cottage"
    assert len(kit["pieces"]) == 2
    assert kit["pieces"][0] == {
        "name": "button.webp", "kind": "box", "size": [96, 40],
        "slice": 14, "fill": "parchment", "make": "draw",
    }
    assert kit["pieces"][1]["make"] == "derive:tint(255,255,255,0.10)"


def test_a_good_manifest_loads_when_optional_keys_are_absent(tmp_path):
    kit = {
        "schema": 1,
        "pieces": [{"name": "parchment.png", "kind": "copy", "size": [0, 0],
                    "make": "copy"}],
    }
    loaded = skin_kit.load_kit(_write(tmp_path, kit))
    assert loaded == kit
    assert "kit" not in loaded
    assert "slice" not in loaded["pieces"][0]


def test_a_null_fill_is_allowed(tmp_path):
    kit = _good()
    kit["pieces"][0]["fill"] = None
    assert skin_kit.load_kit(_write(tmp_path, kit))["pieces"][0]["fill"] is None


# --------------------------------------------------------------------------
# 2. every rule refuses a bad manifest with ONE sentence
# --------------------------------------------------------------------------

def test_an_unknown_top_level_key_is_refused(tmp_path):
    kit = _good()
    kit["palette"] = ["red"]
    assert "palette" in _bad(tmp_path, kit)


def test_a_missing_schema_key_is_refused(tmp_path):
    kit = _good()
    del kit["schema"]
    assert "schema" in _bad(tmp_path, kit)


def test_a_schema_that_is_not_one_is_refused(tmp_path):
    kit = _good()
    kit["schema"] = 2
    _bad(tmp_path, kit)


def test_a_schema_that_is_not_an_integer_is_refused(tmp_path):
    kit = _good()
    kit["schema"] = "1"
    _bad(tmp_path, kit)


def test_a_missing_pieces_key_is_refused(tmp_path):
    kit = _good()
    del kit["pieces"]
    assert "pieces" in _bad(tmp_path, kit)


def test_an_empty_pieces_list_is_refused(tmp_path):
    kit = _good()
    kit["pieces"] = []
    _bad(tmp_path, kit)


def test_pieces_that_is_not_a_list_is_refused(tmp_path):
    kit = _good()
    kit["pieces"] = {"name": "button.webp"}
    _bad(tmp_path, kit)


def test_an_empty_kit_name_is_refused(tmp_path):
    kit = _good()
    kit["kit"] = ""
    _bad(tmp_path, kit)


def test_a_kit_name_that_is_not_a_string_is_refused(tmp_path):
    kit = _good()
    kit["kit"] = 7
    _bad(tmp_path, kit)


def test_a_top_level_that_is_not_an_object_is_refused(tmp_path):
    _bad(tmp_path, "[1, 2, 3]")


def test_a_file_that_is_not_json_at_all_is_refused(tmp_path):
    sentence = _bad(tmp_path, "this is not json {")
    assert "kit.json" in sentence


def test_a_missing_manifest_file_is_refused_as_one_sentence(tmp_path):
    with pytest.raises(skin_kit.KitError) as caught:
        skin_kit.load_kit(tmp_path / "nowhere" / "kit.json")
    _one_sentence(caught.value)


def test_an_unknown_piece_key_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["colour"] = "red"
    assert "colour" in _bad(tmp_path, kit)


def test_a_piece_that_is_not_an_object_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][1] = "button-hover.webp"
    _bad(tmp_path, kit)


def test_a_missing_piece_name_is_refused(tmp_path):
    kit = _good()
    del kit["pieces"][0]["name"]
    assert "name" in _bad(tmp_path, kit)


def test_a_missing_piece_kind_is_refused(tmp_path):
    kit = _good()
    del kit["pieces"][0]["kind"]
    assert "kind" in _bad(tmp_path, kit)


def test_a_missing_piece_size_is_refused(tmp_path):
    kit = _good()
    del kit["pieces"][0]["size"]
    assert "size" in _bad(tmp_path, kit)


def test_a_missing_piece_make_is_refused(tmp_path):
    kit = _good()
    del kit["pieces"][0]["make"]
    assert "make" in _bad(tmp_path, kit)


def test_a_duplicate_piece_name_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][1]["name"] = "button.webp"
    sentence = _bad(tmp_path, kit)
    assert "button.webp" in sentence


def test_a_name_with_a_forward_slash_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["name"] = "art/button.webp"
    assert "art/button.webp" in _bad(tmp_path, kit)


def test_a_name_with_a_backslash_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["name"] = "art\\button.webp"
    _bad(tmp_path, kit)


def test_a_name_that_is_a_dot_directory_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["name"] = ".."
    _bad(tmp_path, kit)


def test_an_empty_piece_name_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["name"] = ""
    _bad(tmp_path, kit)


def test_a_name_that_is_not_a_string_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["name"] = 12
    _bad(tmp_path, kit)


def test_a_kind_outside_box_strip_copy_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["kind"] = "blob"
    sentence = _bad(tmp_path, kit)
    assert "blob" in sentence


def test_a_size_that_is_not_two_integers_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["size"] = [96]
    _bad(tmp_path, kit)


def test_a_size_with_a_non_integer_element_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["size"] = [96, "40"]
    _bad(tmp_path, kit)


def test_a_negative_size_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["size"] = [-1, 40]
    _bad(tmp_path, kit)


def test_a_slice_that_is_not_an_integer_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["slice"] = "14"
    _bad(tmp_path, kit)


def test_a_negative_slice_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["slice"] = -3
    _bad(tmp_path, kit)


def test_a_fill_that_is_neither_a_string_nor_null_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["fill"] = 4
    _bad(tmp_path, kit)


def test_an_empty_fill_string_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["fill"] = ""
    _bad(tmp_path, kit)


def test_a_required_that_is_not_a_boolean_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["required"] = "no"
    _bad(tmp_path, kit)


def test_a_make_outside_draw_copy_derive_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][0]["make"] = "paint"
    sentence = _bad(tmp_path, kit)
    assert "paint" in sentence


def test_a_derive_with_an_unknown_recipe_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][1]["make"] = "derive:blur(3)"
    assert "blur" in _bad(tmp_path, kit)


def test_a_tint_recipe_with_the_wrong_number_of_arguments_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][1]["make"] = "derive:tint(255,255,255)"
    _bad(tmp_path, kit)


def test_a_tint_recipe_with_a_non_numeric_argument_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][1]["make"] = "derive:tint(255,255,white,0.1)"
    _bad(tmp_path, kit)


def test_a_tint_recipe_with_a_channel_above_255_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][1]["make"] = "derive:tint(256,255,255,0.1)"
    _bad(tmp_path, kit)


def test_a_tint_amount_above_one_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][1]["make"] = "derive:tint(255,255,255,1.5)"
    _bad(tmp_path, kit)


def test_a_tint_amount_below_zero_is_refused(tmp_path):
    kit = _good()
    kit["pieces"][1]["make"] = "derive:tint(255,255,255,-0.1)"
    _bad(tmp_path, kit)


def test_a_derived_piece_with_no_base_is_refused(tmp_path):
    kit = {
        "schema": 1,
        "pieces": [
            {"name": "panel.webp", "kind": "box", "size": [8, 8], "make": "draw"},
            {"name": "hover.webp", "kind": "box", "size": [8, 8],
             "make": "derive:tint(255,255,255,0.1)"},
        ],
    }
    sentence = _bad(tmp_path, kit)
    assert "hover.webp" in sentence


def test_a_sibling_name_is_not_a_base_for_a_derived_piece(tmp_path):
    # toggle-on is not a proper prefix of toggle-off, so nothing is a base.
    kit = {
        "schema": 1,
        "pieces": [
            {"name": "toggle-on.webp", "kind": "strip", "size": [8, 8], "make": "draw"},
            {"name": "toggle-off.webp", "kind": "strip", "size": [8, 8],
             "make": "derive:flip-knob"},
        ],
    }
    _bad(tmp_path, kit)


def test_a_shared_stem_makes_a_base_of_a_derived_piece(tmp_path):
    # "button" is a proper prefix of "button-hover", so button.webp is the
    # base of button-hover.webp and the kit loads.
    kit = {
        "schema": 1,
        "pieces": [
            {"name": "button.webp", "kind": "box", "size": [8, 8], "make": "draw"},
            {"name": "button-hover.webp", "kind": "box", "size": [8, 8],
             "make": "derive:tint(255,255,255,0.1)"},
        ],
    }
    kit_loaded = skin_kit.load_kit(_write(tmp_path, kit))
    src = _src(tmp_path, "button.webp")
    assert skin_kit.report(kit_loaded, src) == [
        "button.webp: drawn",
        "button-hover.webp: derived",
    ]


def test_the_longest_prefix_wins_when_two_names_both_prefix_the_derived_one(tmp_path):
    kit = {
        "schema": 1,
        "pieces": [
            {"name": "button.webp", "kind": "box", "size": [8, 8], "make": "draw"},
            {"name": "button-hover.webp", "kind": "box", "size": [8, 8],
             "make": "derive:tint(255,255,255,0.1)"},
            {"name": "button-hover-pressed.webp", "kind": "box", "size": [8, 8],
             "make": "derive:tint(255,255,255,0.2)"},
        ],
    }
    src = _src(tmp_path, "button.webp")
    kit_loaded = skin_kit.load_kit(_write(tmp_path, kit))
    # Two names are a prefix of the third - "button" and "button-hover" - and
    # the longer one wins. So the third piece rests on button-hover.webp's
    # picture, and is missing while only button.webp is on disk.
    assert skin_kit.report(kit_loaded, src) == [
        "button.webp: drawn",
        "button-hover.webp: derived",
        "button-hover-pressed.webp: missing",
    ]
    src2 = _src(tmp_path, "button.webp", "button-hover.webp")
    # A derive: piece is derived, never drawn, even with its own picture there.
    assert skin_kit.report(kit_loaded, src2) == [
        "button.webp: drawn",
        "button-hover.webp: derived",
        "button-hover-pressed.webp: derived",
    ]


def test_a_base_named_toggle_is_a_base_for_toggle_off(tmp_path):
    kit = {
        "schema": 1,
        "pieces": [
            {"name": "toggle.webp", "kind": "strip", "size": [64, 32], "make": "draw"},
            {"name": "toggle-off.webp", "kind": "strip", "size": [64, 32],
             "make": "derive:flip-knob"},
        ],
    }
    assert len(skin_kit.load_kit(_write(tmp_path, kit))["pieces"]) == 2


def test_a_derived_piece_may_be_listed_before_its_base(tmp_path):
    kit = {
        "schema": 1,
        "pieces": [
            {"name": "toggle-off.webp", "kind": "strip", "size": [64, 32],
             "make": "derive:flip-knob"},
            {"name": "toggle.webp", "kind": "strip", "size": [64, 32], "make": "draw"},
        ],
    }
    assert len(skin_kit.load_kit(_write(tmp_path, kit))["pieces"]) == 2


# --------------------------------------------------------------------------
# 3. completeness: report and the total line
# --------------------------------------------------------------------------

def _four(tmp_path, present=("button.webp", "button-hover.webp", "toggle.webp")):
    """Four pieces, three of them present in src; parchment.png is absent.

    button.webp        draw              box   present -> drawn
    button-hover.webp  derive:tint(...) box   present, base present -> derived
    toggle.webp        draw              strip present -> drawn
    parchment.png      copy              copy  absent -> missing
    """
    kit = {
        "schema": 1,
        "kit": "cottage",
        "pieces": [
            {"name": "button.webp", "kind": "box", "size": [96, 40], "slice": 14,
             "make": "draw"},
            {"name": "button-hover.webp", "kind": "box", "size": [96, 40], "slice": 14,
             "make": "derive:tint(255,255,255,0.10)"},
            {"name": "toggle.webp", "kind": "strip", "size": [64, 32], "make": "draw"},
            {"name": "parchment.png", "kind": "copy", "size": [0, 0], "make": "copy",
             "required": False},
        ],
    }
    return _write(tmp_path, kit), _src(tmp_path, *present), kit


def test_report_names_every_piece_in_manifest_order_with_its_status(tmp_path):
    path, src, _ = _four(tmp_path)
    kit = skin_kit.load_kit(path)
    assert skin_kit.report(kit, src) == [
        "button.webp: drawn",
        "button-hover.webp: derived",
        "toggle.webp: drawn",
        "parchment.png: missing",
    ]


def test_report_prints_nothing_and_does_not_mutate_the_kit(tmp_path, capsys):
    path, src, _ = _four(tmp_path)
    kit = skin_kit.load_kit(path)
    before = json.dumps(kit, sort_keys=True)
    skin_kit.report(kit, src)
    assert capsys.readouterr().out == ""
    assert json.dumps(kit, sort_keys=True) == before


def test_run_prints_the_report_then_the_total_line(tmp_path, capsys):
    path, src, _ = _four(tmp_path)
    code = skin_kit.run(path, src)
    out = capsys.readouterr().out.splitlines()
    # N = 2 drawn, M = 4 pieces, K = 2 (the drawn box and the drawn strip;
    # the drawn copy is not a chosen piece), D = 1 derived.
    assert code == 0
    assert out == [
        "button.webp: drawn",
        "button-hover.webp: derived",
        "toggle.webp: drawn",
        "parchment.png: missing",
        "2 of 4 pieces drawn, 2 chosen, 1 derived",
    ]


def test_a_derived_piece_is_missing_when_its_base_picture_is_absent(tmp_path):
    path, src, _ = _four(tmp_path, present=("button-hover.webp", "toggle.webp"))
    kit = skin_kit.load_kit(path)
    assert skin_kit.report(kit, src) == [
        "button.webp: missing",
        "button-hover.webp: missing",
        "toggle.webp: drawn",
        "parchment.png: missing",
    ]


def test_a_derived_piece_does_not_need_its_own_picture_to_be_reported_derived(tmp_path):
    path, src, _ = _four(tmp_path, present=("button.webp", "toggle.webp"))
    kit = skin_kit.load_kit(path)
    lines = skin_kit.report(kit, src)
    assert lines[1] == "button-hover.webp: derived"


def test_report_tolerates_a_hand_built_kit_with_a_junk_piece(tmp_path):
    src = _src(tmp_path, "button.webp")
    kit = {"schema": 1, "pieces": ["button.webp", {"make": "draw"}]}
    assert skin_kit.report(kit, src) == ["#0: missing", "#1: missing"]


def test_a_copied_texture_is_drawn_but_not_chosen(tmp_path, capsys):
    path, src, _ = _four(tmp_path, present=("button.webp", "button-hover.webp",
                                            "toggle.webp", "parchment.png"))
    assert skin_kit.run(path, src) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "3 of 4 pieces drawn, 2 chosen, 1 derived"


# --------------------------------------------------------------------------
# 4. the exit code
# --------------------------------------------------------------------------

def _two(tmp_path, present=("slider.webp",)):
    """button.webp is never written to src, so it is missing unless optional."""
    kit = {
        "schema": 1,
        "kit": "cottage",
        "pieces": [
            {"name": "button.webp", "kind": "box", "size": [96, 40], "make": "draw"},
            {"name": "slider.webp", "kind": "strip", "size": [64, 32], "make": "draw"},
        ],
    }
    return _write(tmp_path, kit), _src(tmp_path, *present), kit


def test_a_missing_required_piece_makes_run_exit_one(tmp_path, capsys):
    path, src, _ = _two(tmp_path)
    assert skin_kit.run(path, src) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "button.webp: missing"
    assert out[-1] == "1 of 2 pieces drawn, 1 chosen, 0 derived"


def test_the_same_kit_with_the_missing_piece_optional_exits_zero(tmp_path, capsys):
    path, src, kit = _two(tmp_path)
    kit["pieces"][0]["required"] = False
    _write(tmp_path, kit)
    assert skin_kit.run(path, src) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "button.webp: missing"
    assert out[-1] == "1 of 2 pieces drawn, 1 chosen, 0 derived"


def test_a_bad_manifest_makes_run_exit_one_with_one_line_on_stderr(tmp_path, capsys):
    kit = _good()
    kit["pieces"][0]["kind"] = "blob"
    path = _write(tmp_path, kit)
    src = _src(tmp_path, "button.webp", "button-hover.webp")
    assert skin_kit.run(path, src) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    err = captured.err
    assert len(err.splitlines()) == 1
    assert "Traceback" not in err
    _one_sentence(skin_kit.KitError(err.strip()))


# --------------------------------------------------------------------------
# 5. tools/art/derive.py (skipped cleanly when Pillow is absent)
# --------------------------------------------------------------------------

def _derive():
    """Import tools/art/derive.py, the way tests/art_cut/test_process_ui.py does."""
    pytest.importorskip("PIL")
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(os.path.dirname(here), "tools", "art"))
    import derive
    return derive


def _gradient(path, width=8, height=4):
    """An RGBA image whose pixels are unique, so a flip is visible."""
    from PIL import Image
    img = Image.new("RGBA", (width, height))
    for y in range(height):
        for x in range(width):
            img.putpixel((x, y), (x * 10, y * 10, 30, 255))
    img.save(path)
    return img


def test_derive_tint_blends_toward_the_colour_and_keeps_size_and_mode(tmp_path):
    derive = _derive()
    img = _gradient(tmp_path / "in.png")
    full = derive.tint(img, 255, 255, 255, 1.0)
    assert full.mode == img.mode
    assert full.size == img.size
    assert full.getpixel((3, 2)) == (255, 255, 255, 255)
    half = derive.tint(img, 255, 255, 255, 0.5)
    assert half.size == img.size
    assert half.mode == img.mode
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            red = img.getpixel((x, y))[0]
            assert abs(half.getpixel((x, y))[0] - (red + 255) / 2) <= 1


def test_derive_flip_knob_mirrors_left_to_right_and_keeps_size_and_mode(tmp_path):
    derive = _derive()
    img = _gradient(tmp_path / "in.png", width=8, height=3)
    out = derive.flip_knob(img)
    assert out.size == img.size
    assert out.mode == img.mode
    width = img.size[0]
    for x in range(width):
        for y in range(img.size[1]):
            assert out.getpixel((x, y)) == img.getpixel((width - 1 - x, y))


def test_derive_one_writes_the_variant_named_by_the_recipe_and_returns_the_path(tmp_path):
    derive = _derive()
    from PIL import Image
    src = tmp_path / "button.png"
    original = _gradient(src, width=12, height=6)
    out_path = tmp_path / "button-hover.png"
    recipe = "tint(255,255,255,0.10)"
    returned = derive.derive_one(src, out_path, recipe)
    assert Path(returned) == out_path
    assert out_path.exists()
    with Image.open(out_path) as written:
        assert written.size == original.size


def test_derive_one_is_deterministic_across_two_calls_and_across_rewrites(tmp_path):
    derive = _derive()
    src = tmp_path / "button.png"
    _gradient(src, width=10, height=5)
    first = tmp_path / "a.png"
    second = tmp_path / "b.png"
    recipe = "tint(255,255,255,0.10)"
    derive.derive_one(src, first, recipe)
    derive.derive_one(src, second, recipe)
    assert first.read_bytes() == second.read_bytes()
    again = derive.derive_one(src, first, recipe)
    assert Path(again).read_bytes() == second.read_bytes()


def test_every_derived_result_keeps_the_input_size(tmp_path):
    derive = _derive()
    from PIL import Image
    src = tmp_path / "toggle.png"
    original = _gradient(src, width=16, height=7)
    for recipe, name in (("tint(255,255,255,0.10)", "tint.png"),
                         ("flip-knob", "flip.png")):
        out = tmp_path / name
        derive.derive_one(src, out, recipe)
        with Image.open(out) as written:
            assert written.size == original.size
