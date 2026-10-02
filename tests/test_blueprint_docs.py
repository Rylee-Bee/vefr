"""Blueprint A11: the guide, glossary and command docs tell the truth about format 1."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

def test_guide_field_tables_list_exactly_the_closed_sets():
    from vefr import blueprint

    guide = (ROOT / "docs" / "guides" / "blueprint.md").read_text()
    for name, keys in (("TOP_KEYS", blueprint.TOP_KEYS), ("FAMILY_KEYS", blueprint.FAMILY_KEYS),
                       ("FIELD_KEYS", blueprint.FIELD_KEYS), ("REGION_KEYS", blueprint.REGION_KEYS),
                       ("INSTANCE_KEYS", blueprint.INSTANCE_KEYS)):
        listed = set(re.findall(rf"<!-- {name}: ([^>]*?) -->", guide))
        assert listed, f"guide is missing the {name} marker"
        assert set(re.split(r",\s*", listed.pop())) == set(keys)


def test_glossary_and_command_docs_name_blueprint_and_normalize():
    assert "Blueprint" in (ROOT / "docs" / "guides" / "glossary.md").read_text()
    assert "normalize" in (ROOT / "docs" / "guides" / "vefr-command.md").read_text()
