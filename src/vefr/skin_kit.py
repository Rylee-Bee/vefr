"""The skin kit manifest (schema 1): load, validate, report.

A skin kit is DATA: a JSON manifest listing the pictures a skin is built
from, and how each one is made - drawn, copied, or derived from another
piece of the same kit by a recipe. This module is the whole contract, and
it is stdlib only. Every manifest problem is ONE plain sentence raised as
``KitError``; there is no traceback and never a list of complaints.

    load_kit(path)  -> dict, the manifest as read; raises KitError
    report(kit, src) -> list[str], f'{name}: {status}' per piece, in order
    run(kit_path, src) -> int, prints the report and the total line

``src`` is the directory holding the kit's pictures. A piece is drawn when
``make`` is draw or copy and ``src/<name>`` is a file; it is derived when
``make`` is ``derive:<recipe>`` and the base piece's picture exists; it is
missing otherwise. A derived piece's base is the piece in the same kit whose
name is the LONGEST PROPER PREFIX of the derived piece's name, compared
on the STEM - the part before the extension. ``button.webp`` bases
``button-hover.webp`` and ``toggle.webp`` bases ``toggle-off.webp``;
``toggle-on.webp`` bases nothing, because "toggle-on" is not a prefix of
"toggle-off". That is the data-driven link between a variant and its base,
with no extra key to keep in step.
"""

import json
import sys
from pathlib import Path

# The three kinds of piece a skin knows how to use.
KINDS = ("box", "strip", "copy")

# The kinds a skin CHOOSES between: a box, a strip, or a state variant of
# one. A copy is a texture, never something a skin chooses.
_CHOSEN_KINDS = ("box", "strip")

# Closed key sets.
_TOP_ALLOWED = ("schema", "kit", "pieces")
_TOP_REQUIRED = ("schema", "pieces")
_PIECE_ALLOWED = ("name", "kind", "size", "slice", "fill", "make", "required")
_PIECE_REQUIRED = ("name", "kind", "size", "make")

# The only schema this module reads.
SCHEMA = 1

_DRAW = "draw"
_COPY = "copy"
_DERIVE = "derive:"


class KitError(ValueError):
    """A manifest problem, as ONE plain sentence. Never a traceback."""


def _say(value):
    """One line of plain text: no newline, no runaway length, ever."""
    text = " ".join(str(value).split())
    if not text:
        return "(empty)"
    if len(text) > 60:
        text = text[:57] + "..."
    return text


def _is_int(value):
    """True for a real int; ``True`` is not a number here."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_nonempty_str(value):
    """True for a string with something in it."""
    return isinstance(value, str) and value.strip() != ""


def _label(piece, index):
    """The piece name when it is usable, its position when it is not."""
    if isinstance(piece, dict) and _is_nonempty_str(piece.get("name")):
        return _say(piece["name"])
    return f"#{index}"


def _refuse(filename, sentence):
    """Raise the one sentence, prefixed with the manifest's name."""
    raise KitError(f"{filename}: {sentence}")


def _check_piece(piece, pieces, index, filename):
    """Every rule about one piece; raises on the first one it breaks."""
    where = f'piece "{_label(piece, index)}"'
    for key in piece:
        if key not in _PIECE_ALLOWED:
            _refuse(filename,
                    f'the {where} has an unknown key "{_say(key)}".')
    for key in _PIECE_REQUIRED:
        if key not in piece:
            _refuse(filename,
                    f'the {where} is missing the required key "{key}".')

    name = piece["name"]
    if not _is_nonempty_str(name):
        _refuse(filename, f'the {where} has a name that is not a non-empty string.')
    if "/" in name or "\\" in name:
        _refuse(filename,
                f'the piece name "{_say(name)}" must not contain a path separator.')
    if name in (".", ".."):
        _refuse(filename,
                f'the piece name "{name}" is not a file name.')

    if piece["kind"] not in KINDS:
        _refuse(filename,
                f'the {where} has kind "{_say(piece["kind"])}"; expected one of '
                f'{", ".join(KINDS)}.')

    size = piece["size"]
    if not (isinstance(size, list) and len(size) == 2
            and all(_is_int(side) for side in size)):
        _refuse(filename,
                f'the {where} has a size that is not a list of two integers.')
    if any(side < 0 for side in size):
        _refuse(filename, f'the {where} has a negative size.')

    if "slice" in piece and not _is_int(piece["slice"]):
        _refuse(filename, f'the {where} has a slice that is not an integer.')
    if "slice" in piece and piece["slice"] < 0:
        _refuse(filename, f'the {where} has a negative slice.')

    if "fill" in piece:
        fill = piece["fill"]
        if fill is not None and not _is_nonempty_str(fill):
            _refuse(filename,
                    f'the {where} has a fill that is neither a non-empty string '
                    f'nor null.')

    if "required" in piece and not isinstance(piece["required"], bool):
        _refuse(filename, f'the {where} has a required that is not a boolean.')

    _check_make(piece, pieces, filename, where)


def _check_make(piece, pieces, filename, where):
    """``draw``, ``copy``, or ``derive:`` plus a recipe we know."""
    make = piece["make"]
    if not isinstance(make, str):
        _refuse(filename, f'the {where} has a make that is not a string.')
    if make in (_DRAW, _COPY):
        return
    if not make.startswith(_DERIVE):
        _refuse(filename,
                f'the {where} has make "{_say(make)}"; expected {_DRAW}, {_COPY}, '
                f'or derive:<recipe>.')

    recipe = make[len(_DERIVE):]
    if recipe != "flip-knob":
        _check_tint(recipe, filename, where)

    # Every derive: recipe rests on a base, the one piece whose name is the
    # longest proper prefix of this piece's name (on the stem - see
    # _base_name). "toggle-on.webp" bases nothing, so a kit that derives a
    # toggle's off state has to list the toggle itself.
    if _base_name(pieces, piece["name"]) is None:
        _refuse(filename,
                f'the derived piece "{_say(piece["name"])}" has no base piece; '
                f'a derived piece needs another piece whose name is a proper '
                f'prefix of its own.')


def _check_tint(recipe, filename, where):
    """``tint(r,g,b,amount)``: three integer channels and one amount."""
    if not recipe.startswith("tint(") or not recipe.endswith(")"):
        _refuse(filename, f'the {where} has the unknown recipe "{_say(recipe)}".')
    parts = recipe[len("tint("):-1].split(",")
    if len(parts) != 4:
        _refuse(filename,
                f'the {where} has a tint recipe that is not '
                f'tint(r,g,b,amount) with four numbers.')
    try:
        red, green, blue, amount = (float(part) for part in parts)
    except ValueError:
        _refuse(filename,
                f'the {where} has a tint recipe that is not '
                f'tint(r,g,b,amount) with four numbers.')
    if not all(0 <= channel <= 255 and channel.is_integer()
               for channel in (red, green, blue)):
        _refuse(filename,
                f'the {where} has a tint channel that is not an integer from 0 to 255.')
    if not 0 <= amount <= 1:
        _refuse(filename, f'the {where} has a tint amount outside 0 to 1.')


def _stem(name):
    """The part of a piece name before its extension.

    "button.webp" -> "button", "toggle" -> "toggle". The dot in ".webp" is an
    extension, not a link, so a variant is named after its base's stem.
    """
    return name.rsplit(".", 1)[0] if "." in name else name


def _base_name(pieces, name):
    """The longest proper prefix of `name` among the other pieces' names.

    The comparison is on the STEM, the part before the extension, so the rule
    links a variant to its base the way the examples ask: "button.webp" bases
    "button-hover.webp", and "toggle.webp" bases "toggle-off.webp" because
    "toggle" is a prefix of "toggle-off". "toggle-on.webp" bases nothing -
    "toggle-on" is not a prefix of "toggle-off" - which is why a kit that
    derives an off state has to list the toggle itself as a piece.
    """
    stem = _stem(name)
    best = None
    for piece in pieces:
        if not isinstance(piece, dict):
            continue
        other = piece.get("name")
        if not isinstance(other, str) or other == name:
            continue
        other_stem = _stem(other)
        if other_stem == stem or not stem.startswith(other_stem):
            continue
        if best is None or len(other_stem) > len(_stem(best)):
            best = other
    return best


def load_kit(path):
    """Read and validate the manifest at `path`. Raises KitError.

    Returns the manifest as read, untouched. Any problem - unreadable file,
    bad JSON, an unknown key, a bad value, a derived piece with no base -
    is ONE plain sentence.
    """
    path = Path(path)
    filename = path.name
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        _refuse(filename, "the skin kit manifest could not be read.")
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        _refuse(filename, "the skin kit manifest is not valid JSON.")
    if not isinstance(data, dict):
        _refuse(filename, "the top level of the skin kit manifest is not a JSON object.")

    for key in data:
        if key not in _TOP_ALLOWED:
            _refuse(filename, f'the skin kit manifest has an unknown key "{_say(key)}".')
    for key in _TOP_REQUIRED:
        if key not in data:
            _refuse(filename,
                    f'the skin kit manifest is missing the required key "{key}".')

    if not _is_int(data["schema"]) or data["schema"] != SCHEMA:
        _refuse(filename, f'"schema" must be the integer {SCHEMA}.')
    if "kit" in data and not _is_nonempty_str(data["kit"]):
        _refuse(filename, '"kit" must be a non-empty string.')

    pieces = data["pieces"]
    if not isinstance(pieces, list):
        _refuse(filename, '"pieces" must be a list.')
    if not pieces:
        _refuse(filename, '"pieces" is empty; a skin kit needs at least one piece.')

    seen = {}
    for index, piece in enumerate(pieces):
        if not isinstance(piece, dict):
            _refuse(filename, f"piece #{index} is not a JSON object.")
        _check_piece(piece, pieces, index, filename)
        name = piece["name"]
        if name in seen:
            _refuse(filename,
                    f'the piece name "{_say(name)}" is used by more than one piece.')
        seen[name] = index

    return data


def _status(piece, pieces, src):
    """drawn, derived or missing for one piece, and the base it rests on."""
    make = piece.get("make")
    name = piece.get("name")
    if not isinstance(name, str) or not name:
        return "missing", None
    if isinstance(make, str) and make.startswith(_DERIVE):
        base = _base_name(pieces, name)
        if base is None or not (src / base).is_file():
            return "missing", base
        return "derived", base
    if make not in (_DRAW, _COPY):
        return "missing", None
    return ("drawn" if (src / name).is_file() else "missing"), None


def _statuses(kit, src):
    """(name, kind, required, status) per piece, in manifest order.

    A kit handed in by hand rather than by load_kit may hold a piece that is
    not an object; it is reported as missing under its index rather than
    crashing the report.
    """
    src = Path(src)
    pieces = kit.get("pieces") or []
    out = []
    for index, piece in enumerate(pieces):
        if not isinstance(piece, dict):
            out.append((f"#{index}", None, True, "missing"))
            continue
        status, _base = _status(piece, pieces, src)
        name = piece.get("name")
        out.append((name if isinstance(name, str) else f"#{index}",
                    piece.get("kind"),
                    piece.get("required", True) is not False,
                    status))
    return out


def report(kit: dict, src) -> list[str]:
    """One line per piece, in manifest order: f'{name}: {status}'.

    `drawn` when make is draw or copy and the picture is in `src`; `derived`
    when make is derive:<recipe> and the base piece's picture is in `src`;
    `missing` otherwise. Prints nothing and never mutates `kit`.
    """
    return [f"{name}: {status}" for name, _, _, status in _statuses(kit, src)]


def run(kit_path, src) -> int:
    """Print the report, then the total line. Return the exit code.

    The total line is f'{N} of {M} pieces drawn, {K} chosen, {D} derived',
    where K counts the drawn boxes and strips - the pieces a skin chooses
    from. Returns 0 when every piece that is not optional is drawn or
    derived, 1 when a required piece is missing, and 1 with the one plain
    KitError sentence on stderr when the manifest itself is bad.
    """
    try:
        kit = load_kit(kit_path)
    except KitError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    statuses = _statuses(kit, src)
    for name, _, _, status in statuses:
        print(f"{name}: {status}")

    total = len(statuses)
    drawn = sum(1 for _, _, _, status in statuses if status == "drawn")
    derived = sum(1 for _, _, _, status in statuses if status == "derived")
    chosen = sum(1 for _, kind, _, status in statuses
                 if status == "drawn" and kind in _CHOSEN_KINDS)
    print(f"{drawn} of {total} pieces drawn, {chosen} chosen, {derived} derived")

    for _, _, required, status in statuses:
        if required and status not in ("drawn", "derived"):
            return 1
    return 0
