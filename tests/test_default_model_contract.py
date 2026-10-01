"""One documented truth for the default storyteller, proven against code.

`GETTING_STARTED.md` is the single place the default is stated, as one
anchor line. This module binds that line to what `resolve_active()`
actually resolves, and keeps every documented `VEFR_STORYTELLER` value
a real pack id.
"""

import re
from pathlib import Path

from vefr import storyteller

ROOT = Path(__file__).resolve().parents[1]

# The anchor line in GETTING_STARTED.md. The test parses the pack id and
# model name out of it; renaming it fails loudly instead of passing on a
# stale default.
_DEFAULT_ANCHOR_RE = re.compile(
    r"^Default storyteller: pack `(?P<pack>[^`]+)`, model `(?P<model>[^`]+)`\.$"
)

# Files that must never name a made-up pack id. A fixed list on purpose:
# a glob over the whole repo would sweep in authoring examples.
_DOC_FILES = (
    "README.md",
    "GETTING_STARTED.md",
    "example.env",
    "compose.yml",
    "Containerfile",
    "deploy/vefr.container",
    "docs/guides/install.md",
    "docs/guides/bundled-brain.md",
)

# `VEFR_STORYTELLER=<value>` / `VEFR_STORYTELLER: <value>`, with an
# optional quote. The `\b` keeps `VEFR_STORYTELLER_FIXTURES` out (its
# underscore is a word character, so there is no boundary between them).
_ASSIGN_RE = re.compile(
    r"VEFR_STORYTELLER\b\s*(?P<sep>[=:])\s*[\"'`]?(?P<value>[A-Za-z0-9][A-Za-z0-9._:-]*)"
)

# A colon is only an assignment when the value is the whole rest of the
# line (allowing a trailing quote or `# comment`). Prose like
# "from VEFR_STORYTELLER: the fleet model" is not an assignment.
_COLON_TAIL_RE = re.compile(r"[\"'`]?\s*(#.*)?$")

# Placeholders that mean "no value here", never a pack id.
_PLACEHOLDER_VALUES = {"unset", "none"}


def _documented_default() -> tuple[str, str]:
    """The (pack id, model name) from GETTING_STARTED.md's anchor line."""
    text = (ROOT / "GETTING_STARTED.md").read_text(encoding="utf-8")
    matches = [
        m.groupdict()
        for line in text.splitlines()
        if (m := _DEFAULT_ANCHOR_RE.match(line))
    ]
    assert len(matches) == 1, (
        "GETTING_STARTED.md must carry exactly one default-storyteller "
        "anchor line, of the form "
        "'Default storyteller: pack `<pack id>`, model `<model name>`.' "
        f"(found {len(matches)}; the default is not documented)"
    )
    return matches[0]["pack"], matches[0]["model"]


def test_documented_default_is_what_the_engine_resolves(tmp_path, monkeypatch):
    """The documented default line names the pack the engine picks with none set."""
    documented_pack, documented_model = _documented_default()

    # A clean process: no env pin, and no installed packs for this run.
    monkeypatch.delenv("VEFR_STORYTELLER", raising=False)
    monkeypatch.delenv("VEFR_MODEL", raising=False)
    monkeypatch.setattr(storyteller, "packs_root", lambda: tmp_path)
    # ...but the real bundled packs, so a developer's install cannot lie.
    monkeypatch.setattr(
        storyteller, "_engine_packs_root", lambda: ROOT / "storyteller_packs"
    )

    active = storyteller.resolve_active()
    assert active.id == "gemma4-e2b", (
        f"resolve_active() picked {active.id!r}; docs say {documented_pack!r}"
    )
    assert active.model == documented_model, (
        f"resolve_active() resolved model {active.model!r}; "
        f"GETTING_STARTED.md documents {documented_model!r}"
    )


def test_every_documented_vefr_storyteller_is_a_real_pack_id():
    """No doc may point `VEFR_STORYTELLER` at a pack id that does not exist."""
    files = [ROOT / name for name in _DOC_FILES]
    files += sorted((ROOT / "docs" / "adr").glob("*.md"))

    found: list[tuple[str, str]] = []
    for path in files:
        assert path.is_file(), f"documented file vanished: {path}"
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            for match in _ASSIGN_RE.finditer(line):
                value = match.group("value")
                if value.lower() in _PLACEHOLDER_VALUES:
                    continue
                if match.group("sep") == ":" and not _COLON_TAIL_RE.match(
                    line[match.end() :]
                ):
                    continue
                found.append((f"{path.relative_to(ROOT)}:{lineno}", value))

    assert found, (
        "no VEFR_STORYTELLER assignment found in the documented files - "
        "the scan is broken, not the docs"
    )

    real_ids = {pack.id for pack in storyteller.list_packs()}
    # NOTE: docs/guides/storyteller-packs.md is deliberately NOT scanned.
    # Its `export VEFR_STORYTELLER=my-model-name` is the bring-your-own-model
    # authoring example - a model name with no pack behind it, by design -
    # not a claimed pack id. The exclusion is intentional, not an oversight.
    unknown = [f"{where}: {value}" for where, value in found if value not in real_ids]
    assert not unknown, (
        "documented VEFR_STORYTELLER values that are not real pack ids:\n"
        + "\n".join(f"  {item}" for item in unknown)
        + f"\n\nReal pack ids: {', '.join(sorted(real_ids))}"
    )
