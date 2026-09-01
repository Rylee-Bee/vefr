"""The sample pack must never tell anyone's story.

The bone-strip audited the engine's code, but a pack is data - the
gate proves structure, not story absence, so the sample world
escaped the audit and carried the author's story grammar ("write
the goodbye", "her hands", the Gold Rule) into an MIT-licensed
directory. This test is the missing audit.

It reads an OPTIONAL, gitignored list of private terms
(tests/canon-strings.local.txt, one per line, case-insensitive)
and fails when any term appears in the shipped surfaces:

  - worlds/sample-world/   (the MIT demonstration pack)
  - web/                   (the served UI + shipped JS)
  - src/vefr/              (the engine)

The mechanism ships; the names stay private - on any machine
without the list, this test skips.

There are NO exceptions. If this test flags a string, the string
leaves the source - an allowlist would be a permanent blind spot
in the one gate that prevents this class of leak. History lives
in ROADMAP (the ledger), not in shipped code.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIST_FILE = Path(__file__).resolve().parent / "canon-strings.local.txt"

AUDIT_DIRS = ["worlds/sample-world", "web", "src"]
AUDIT_SUFFIXES = {".py", ".js", ".mjs", ".html", ".css", ".md", ".json", ".txt"}


def _audit_files():
    for d in AUDIT_DIRS:
        root = ROOT / d
        if not root.exists():
            continue
        for f in sorted(root.rglob("*")):
            if f.is_file() and f.suffix in AUDIT_SUFFIXES:
                yield f


def test_sample_surfaces_carry_no_private_story():
    if not LIST_FILE.exists():
        pytest.skip(
            "no tests/canon-strings.local.txt on this machine - "
            "the audit is local-only by design (the list never ships)"
        )
    terms = [
        ln.strip()
        for ln in LIST_FILE.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    assert terms, "canon list exists but is empty - it would audit nothing"

    failures = []
    for f in _audit_files():
        rel = str(f.relative_to(ROOT))
        try:
            text = f.read_text(encoding="utf-8").lower()
        except UnicodeDecodeError:
            continue
        for term in terms:
            if term.lower() in text:
                failures.append(f"  {rel}: {term!r}")

    assert not failures, (
        "private story terms found in shipped surfaces:\n"
        + "\n".join(failures)
        + "\n\nThere are no exceptions: the string leaves the source."
    )
