"""The SAMPLE affix list may not drift (ADR 0014, "Owner decisions" 4).

`tests/fixtures/make_affix_pack.py` writes the sample `affixes.json` the
owner edits. The names live there and nowhere else: the engine ships only
the neutral ids, so this test pins the rules each record holds and, with
them, the last one - that no cozy name has leaked into `src/` or `web/`.

Rules, straight from the ADR's "Affix." shape:

- `id` and `label` required; `id` unique and a lowercase slug;
- `label` carries the literal `{name}` and still names the threat in
  plain words (a label of just "Plump" would name no threat at all);
- `hp`, `atk`, `xp` in [1.0, 2.0] and `scale` in [1.0, 1.5], all in whole
  hundredths, because a stat is scaled by integer arithmetic in two
  languages;
- `sight` and `extra_drops` whole numbers in [0, 2];
- no `moves` key - reserved until the AI can grant an extra move.

The first five are also checked through `vefr.shapes.check_affixes`,
which is the validator the engine itself runs, so the fixture cannot
pass here and fail there. The two rules `shapes` does not speak to - the
id being a lowercase slug, and the label naming the threat - are
asserted directly, and the leak check walks `src/` and `web/` itself.
"""

import json
import re
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
import make_affix_pack  # noqa: E402

from vefr import shapes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# The four cozy names the ADR's owner decision names, and the three
# neutral ids the engine tests already use in `elites.affixes`
# (`tests/test_floor_v3_properties.py`), so a pack can be built that
# satisfies the existing test packs.
COZY = ("plump", "prickly", "sparkly", "grumpy")
NEUTRAL = ("big", "quick", "glowing")

SLUG = re.compile(r"^[a-z][a-z0-9_]*$")

# The list as the pack holds it: built into a temp root and read back as
# JSON, not read from the builder's constant, so a builder that stops
# writing the file fails here too.
_PACK = make_affix_pack.build(Path(tempfile.mkdtemp()))
LIST = json.loads((_PACK / "affixes.json").read_text(encoding="utf-8"))


def records() -> list:
    """The sample list, for the tests below."""
    return LIST


def test_the_list_covers_the_named_ids():
    """Plump, Prickly, Sparkly, Grumpy, plus big, quick, glowing."""
    ids = [r["id"] for r in records()]
    assert set(COZY) <= set(ids)
    assert set(NEUTRAL) <= set(ids)


def test_every_record_is_accepted_by_the_validator(tmp_path):
    """`shapes.check_affixes` is the engine's own read of the list.

    The Section names no affix, so this checks the records themselves:
    closed keys, required keys, ranges, whole hundredths, and the
    literal `{name}` in every label.
    """
    pack = make_affix_pack.build(tmp_path)
    written = json.loads((pack / "affixes.json").read_text(encoding="utf-8"))
    problems = shapes.check_affixes({}, written)
    assert problems == [], "\n".join(
        f"{p.pointer} {p.sentence}" for p in problems)


def test_no_record_carries_moves():
    """`moves` is reserved and refused as the unknown key it is today."""
    for record in records():
        assert "moves" not in record, record["id"]


def test_every_id_is_a_neutral_lowercase_slug():
    """A neutral id, and each its own."""
    seen = set()
    for record in records():
        rid = record["id"]
        assert SLUG.match(rid), f"{rid!r} is not a lowercase slug"
        assert rid not in seen, f"{rid!r} is used twice"
        seen.add(rid)


def test_every_label_names_the_threat():
    """The literal `{name}` is there, and the label says more than the name.

    `{name}` alone is required and not enough: the ADR wants a plain
    label that still names the threat ("Plump {name}"), because the
    player has to be able to read the fight off the word.
    """
    for record in records():
        label = record["label"]
        assert "{name}" in label, record["id"]
        assert label.replace("{name}", "").strip(), (
            f"{record['id']} names no threat: {label!r}")


def test_multipliers_are_whole_hundredths_in_range():
    """The ADR's ranges, and the whole hundredths the pack writes in.

    Whole hundredths is a property of the value, not of how it is
    written: `1.5` is 150 hundredths and is fine, `1.234` is not. So a
    multiplier is checked by scaling it to hundredths and asking for a
    whole number, and the range is that whole number's.
    """
    for record in records():
        for key, hi in (("hp", 200), ("atk", 200), ("xp", 200), ("scale", 150)):
            if key not in record:
                continue
            value = record[key]
            hundredths = Decimal(str(value)) * 100
            assert hundredths == hundredths.to_integral_value(), (
                f"{record['id']}.{key}={value!r} is not whole hundredths")
            assert 100 <= hundredths <= hi, f"{record['id']}.{key}={value!r}"


def test_sight_and_extra_drops_are_whole_numbers_in_range():
    """Both are whole numbers in [0, 2]."""
    for record in records():
        for key in ("sight", "extra_drops"):
            if key not in record:
                continue
            value = record[key]
            assert isinstance(value, int) and not isinstance(value, bool), (
                f"{record['id']}.{key}={value!r} is not a whole number")
            assert 0 <= value <= 2, f"{record['id']}.{key}={value!r}"


def test_quick_is_sight_only():
    """`quick` carries no `moves` until the AI can grant an extra move.

    Whether it can is still UNKNOWN, so the sample says `sight: 1` and
    stops there (ADR 0014, "Affix.").
    """
    quick = next(r for r in records() if r["id"] == "quick")
    assert quick["sight"] == 1
    assert "moves" not in quick


def test_no_name_reached_the_engine():
    """The one rule that matters: the names live in the pack, not the code.

    Walks every file under `src/` and `web/` for a cozy name,
    case-insensitively - the same search the task's acceptance runs, done
    here over the filesystem so an untracked file cannot slip past.
    """
    cozy = re.compile("|".join(COZY), re.IGNORECASE)
    hits = []
    for root in ("src", "web"):
        for path in sorted((ROOT / root).rglob("*")):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if cozy.search(text):
                hits.append(str(path.relative_to(ROOT)))
    assert hits == [], f"a cozy name is in the engine: {hits}"


def test_the_only_place_a_cozy_name_lives_is_the_fixture():
    """And the names are in the fixture, so the leak test has teeth.

    Without this, emptying the fixture would make the leak test above
    pass for the wrong reason.
    """
    source = (ROOT / "tests" / "fixtures" / "make_affix_pack.py").read_text(
        encoding="utf-8")
    for name in COZY:
        assert name in source, name
