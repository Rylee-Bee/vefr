"""Blueprint A11: the guide, glossary and command docs tell the truth about every format."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

def test_guide_field_tables_list_exactly_the_closed_sets():
    from vefr import blueprint

    guide = (ROOT / "docs" / "guides" / "blueprint.md").read_text()
    for name, keys in (("TOP_KEYS", blueprint.TOP_KEYS), ("FAMILY_KEYS", blueprint.FAMILY_KEYS),
                       ("FIELD_KEYS", blueprint.FIELD_KEYS), ("REGION_KEYS", blueprint.REGION_KEYS),
                       ("INSTANCE_KEYS", blueprint.INSTANCE_KEYS),
                       ("THING_KEYS", blueprint.THING_KEYS)):
        listed = set(re.findall(rf"<!-- {name}: ([^>]*?) -->", guide))
        assert listed, f"guide is missing the {name} marker"
        assert set(re.split(r",\s*", listed.pop())) == set(keys)


def test_the_format_one_top_keys_are_pinned_by_value():
    """The set formats 1 and 3 close their top level on, pinned by value
    because nothing else in the suite reads it: `TOP_KEYS` is the
    format-2 set, so a file that only ever checked `TOP_KEYS` would
    never notice format 1 start accepting `things`."""
    from vefr import blueprint

    assert blueprint.TOP_KEYS_V1 == {"blueprint", "families", "regions"}
    assert "things" not in blueprint.TOP_KEYS_V1
    assert "places" not in blueprint.TOP_KEYS_V1


def test_the_things_exit_ramp_says_what_the_code_does():
    """`tests/test_blueprint_things.py` pins the behavior: deleting the
    `things` list leaves the written item alone and takes the appended
    drop back to what the source still says. A guide sentence claiming
    the drop stays would send an author looking for a drop that is gone.
    """
    text = re.sub(r"\s+", " ", (ROOT / "docs" / "guides" / "blueprint.md").read_text())
    assert "leaves every item and every drop in place" not in text
    assert ("deleting only the `things` list leaves every written item in "
            "place") in text
    assert "the appended drop goes back to what the source still says" in text


def test_glossary_and_command_docs_name_blueprint_and_normalize():
    assert "Blueprint" in (ROOT / "docs" / "guides" / "glossary.md").read_text()
    assert "normalize" in (ROOT / "docs" / "guides" / "vefr-command.md").read_text()
