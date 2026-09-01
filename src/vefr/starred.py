"""Starred entries - the player-marked 'these are good' tier.

Three kinds of star-target exist:
  - rumor:        appended under ## <phase> in starred-whispers.md
  - npc_line:     same file, under ## <phase>
  - item_forged:  appended under ## kept-items (no phase)
  - stefna_letter: appended under ## letters (under 'awed' phase)

The file lives at <pack>/starred-whispers.md. It's part of the
pack on disk like logbok.md - committed to the story repo and
pulled by `ratatoskr ferry fetch --pull`, so stars survive restarts and
follow the deploy box's pack.

A star entry records what the player kept, when, and from which
journal timestamp. The format is markdown bullets:

    ## <phase>

    - "<whisper text>" - <speaker>, kept 2026-08-31T03:24:59

Idempotent: starring the same journal entry twice appends a
second line. The author can deduplicate by hand if they care;
the engine never reads this file (yet), so the duplication is
only cosmetic.
"""

from datetime import datetime, timezone
from pathlib import Path

from .paths import pack_dir

FILE_NAME = "starred-whispers.md"

# Phase labels for non-rumor/npc kinds. Item_forged is phase-less
# by design (the forge is its own beat); stefna letters always live
# under the 'awed' phase because that's when the summons is answered.
FALLBACK_PHASE = {
    "item_forged": "kept-items",
    "stefna_letter": "awed",
}


def _path() -> Path:
    return pack_dir() / FILE_NAME


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _section_for(entry: dict) -> str:
    """Pick the heading this entry belongs under."""
    if entry.get("kind") in FALLBACK_PHASE:
        return FALLBACK_PHASE[entry["kind"]]
    return entry.get("phase") or "whispers"


def _text_for(entry: dict) -> str:
    """Pull the displayable text out of an entry."""
    kind = entry.get("kind")
    if kind == "rumor":
        return entry.get("whisper", "")
    if kind == "npc_line":
        return entry.get("line", "")
    if kind == "item_forged":
        return f"{entry.get('name', '')} - {entry.get('lore', '')}".strip(" -")
    if kind == "stefna_letter":
        # Letters are formatted in prose elsewhere; preserve them as
        # a single quoted block.
        return entry.get("letter", "").replace("\n", " / ")
    return str(entry)


def star(entry: dict) -> dict:
    """Append this journal entry's text to the starred file.

    Returns a small summary the API can echo back so the UI can
    confirm the write landed.
    """
    section = _section_for(entry)
    text = _text_for(entry).strip()
    if not text:
        return {"starred": False, "reason": "empty entry"}
    speaker = entry.get("speaker", "")
    at = entry.get("at", _now())
    quoted = " / ".join(line.strip() for line in text.splitlines() if line.strip())

    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""

    # Insert under the right heading. If the file exists but lacks
    # the heading, append a fresh one at the bottom. If the file
    # is brand-new, start with the heading.
    heading = f"## {section}"
    line = (
        f'\n- "{quoted}"'
        + (f" - {speaker}" if speaker else "")
        + f", kept {at[:19]}"
    )

    if not existing.strip():
        new = f"# Starred whispers\n\n{heading}\n{line}\n"
    elif heading in existing:
        new = existing.rstrip("\n") + "\n" + line + "\n"
    else:
        new = existing.rstrip("\n") + "\n\n" + heading + "\n" + line + "\n"

    tmp = path.with_suffix(".tmp")
    tmp.write_text(new, encoding="utf-8")
    tmp.replace(path)
    return {"starred": True, "section": section, "file": str(path)}


def list_starred() -> list[dict]:
    """Best-effort reverse-lookup: which journal entries are starred.

    Reads the starred file, splits out the bullet lines, returns
    them as a list of {text, section, kept_at} dicts. The UI uses
    this to mark already-starred entries.
    """
    path = _path()
    if not path.exists():
        return []
    out: list[dict] = []
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("- \""):
            # Strip the wrapping quote and any trailing metadata.
            inner = line[3:].rstrip()
            if inner.endswith('"'):
                inner = inner[:-1]
            out.append({"text": inner, "section": section})
    return out