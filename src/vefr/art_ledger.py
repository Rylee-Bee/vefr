"""The art ledger (ADR 0011): schema checks and generated credits.

A pack may keep ``art/ledger/round-NN.json``, one file per round. This
module is the whole contract: ``ROLES``, ``check`` and ``credits``.
It is stdlib only and never raises on bad input - every malformed
ledger becomes one plain problem sentence.

    check(ledger_dir, root)  -> list[str], [] when the ledger is good
    credits(ledger_dir)      -> markdown, one line per picture

See ``docs/adr/0011-art-ledger.md``.
"""

import hashlib
import json
from pathlib import Path

# The five role names a picture may carry.
ROLES = ("item-icon", "creature", "tile", "sheet", "ui-part")

# Closed key sets (ADR "Decision").
_TOP_ALLOWED = ("ledger", "round", "made_with", "style", "date", "pictures")
_TOP_REQUIRED = ("ledger", "round", "made_with", "style", "pictures")
_PIC_ALLOWED = ("id", "role", "subject", "variants", "ref", "pick",
                "to", "size", "grid", "sha256", "status", "note")
_PIC_REQUIRED = ("id", "role", "subject", "to", "sha256")

# Required-field types. Optional fields are left alone: the ADR fixes
# required names, not the shape of every optional value.
_TOP_TYPES = {"ledger": int, "round": int, "made_with": str, "style": str}
_PIC_TYPES = {"id": str, "role": str, "subject": str, "to": str,
              "sha256": str}


def _is_scratch(text):
    """True when a string carries a scratch/absolute path fragment."""
    return (text.startswith("/") or "~" in text or "/tmp" in text
            or "/home" in text or ".." in text)


def _iter_strings(value):
    """Yield every string inside a JSON-ish value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_strings(item)


def _type_name(value):
    return type(value).__name__


def _scan_strings(container, filename, label, problems):
    """The clean-credits rule over a dict's string values.

    ``pictures`` is skipped: each picture gets its own pass, so its
    strings are reported once, with the picture id for a pointer.
    """
    for key, value in container.items():
        if key == "pictures":
            continue
        for found in _iter_strings(value):
            if _is_scratch(found):
                where = f'picture "{label}" ' if label is not None else ""
                problems.append(
                    f'{filename}: {where}key "{key}" contains a scratch '
                    f'path: "{found}".'
                )


def _check_mapping(data, filename, allowed, required, types, problems,
                   label=None):
    """Closed key set + required keys + required-field types.

    One problem per offending key; ``label`` is the picture id (or its
    index) for a nested picture.
    """
    where = f'picture "{label}" ' if label is not None else ""
    for key in data:
        if key not in allowed:
            problems.append(
                f'{filename}: {where}has unknown key "{key}".'
            )
    for key in required:
        if key not in data:
            problems.append(
                f'{filename}: {where}is missing required key "{key}".'
            )
        elif key in types and not isinstance(data[key], types[key]):
            problems.append(
                f'{filename}: {where}key "{key}" has type '
                f'{_type_name(data[key])}, expected {types[key].__name__}.'
            )


def _check_one_file(path, root, problems, seen_ids, reported_dups):
    filename = path.name
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        problems.append(f'{filename}: is not readable.')
        return
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        problems.append(f"{filename}: is not valid JSON.")
        return
    if not isinstance(data, dict):
        problems.append(f"{filename}: top level is not a JSON object.")
        return

    _check_mapping(data, filename, _TOP_ALLOWED, _TOP_REQUIRED,
                   _TOP_TYPES, problems)
    _scan_strings(data, filename, None, problems)

    pictures = data.get("pictures")
    if not isinstance(pictures, list):
        problems.append(f'{filename}: "pictures" is not a list.')
        return

    for index, picture in enumerate(pictures):
        if not isinstance(picture, dict):
            problems.append(
                f"{filename}: picture {index} is not a JSON object."
            )
            continue
        raw_id = picture.get("id")
        label = raw_id if isinstance(raw_id, str) else f"#{index}"
        _check_mapping(picture, filename, _PIC_ALLOWED, _PIC_REQUIRED,
                       _PIC_TYPES, problems, label=label)
        _scan_strings(picture, filename, label, problems)

        role = picture.get("role")
        if isinstance(role, str) and role not in ROLES:
            problems.append(
                f'{filename}: picture "{label}" has role "{role}"; '
                f'expected one of {", ".join(ROLES)}.'
            )

        if isinstance(raw_id, str):
            if raw_id in seen_ids and raw_id not in reported_dups:
                reported_dups.add(raw_id)
                problems.append(
                    f'{filename}: picture id "{raw_id}" appears twice '
                    f"(first in {seen_ids[raw_id]})."
                )
            else:
                seen_ids.setdefault(raw_id, filename)

        to = picture.get("to")
        recorded = picture.get("sha256")
        if isinstance(to, str) and isinstance(recorded, str):
            target = root / to
            try:
                digest = hashlib.sha256(target.read_bytes()).hexdigest()
            except OSError:
                problems.append(
                    f'{filename}: picture "{label}" points at missing '
                    f'file "{to}".'
                )
            else:
                if digest != recorded:
                    problems.append(
                        f'{filename}: picture "{label}" sha256 does not '
                        f'match "{to}".'
                    )


def check(ledger_dir, root):
    """Validate every ``round-*.json`` under ``ledger_dir``.

    Returns one plain sentence per problem, each naming the file and
    the picture id where there is one; ``[]`` when everything is good.
    Never raises on bad input.
    """
    problems = []
    seen_ids = {}
    reported_dups = set()
    try:
        paths = sorted(Path(ledger_dir).glob("round-*.json"),
                       key=lambda p: p.name)
    except OSError:
        paths = []
    for path in paths:
        try:
            _check_one_file(path, Path(root), problems, seen_ids,
                            reported_dups)
        except OSError:
            problems.append(f"{path.name}: is not readable.")
    return problems


def credits(ledger_dir):
    """Generated credits as markdown, one line per picture.

    Files are read in sorted filename order, pictures in file order:

        "- <to>: <made_with>, <style> (round <round>)"
    """
    lines = []
    try:
        paths = sorted(Path(ledger_dir).glob("round-*.json"),
                       key=lambda p: p.name)
    except OSError:
        return ""
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        made_with = data.get("made_with", "?")
        style = data.get("style", "?")
        rnd = data.get("round", "?")
        pictures = data.get("pictures")
        if not isinstance(pictures, list):
            continue
        for picture in pictures:
            if not isinstance(picture, dict):
                continue
            to = picture.get("to", "?")
            lines.append(
                f"- {to}: {made_with}, {style} (round {rnd})"
            )
    return "\n".join(lines) + ("\n" if lines else "")
