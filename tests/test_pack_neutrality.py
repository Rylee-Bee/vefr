"""The sample pack and engine surfaces must never tell anyone's story.

The bone-strip audited the engine's code, but a pack is data - the
gate proves structure, not story absence, so the sample world
escaped the audit and carried the author's story grammar ("write
the goodbye", "her hands", a private world-rule phrase) into an
MIT-licensed directory.

This module provides two independent guards:
1. `test_sample_surfaces_carry_no_private_story`: reads an optional,
   gitignored list of private terms (tests/canon-strings.local.txt)
   and checks for literal term leakage across shipped surfaces.
2. `test_engine_surfaces_carry_no_gendered_pronouns`: a shape-based
   guard that verifies no third-person singular gendered pronouns
   (she/her/hers/his/him) appear in user-facing code strings or
   prompts under `web/` or `src/vefr/`. Module docstrings that describe
   mythological characters (such as Saga in `saga.py`) are exempted
   by structural AST shape rather than by an arbitrary literal allowlist.
3. `test_no_historical_package_names`: anti-regression test ensuring
   historical package names never reappear in `src/`,
   `web/`, or `tests/`.

There are NO exceptions or literal term allowlists: an allowlist is a
permanent blind spot. If a test flags a string, the string leaves the
source.
"""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIST_FILE = Path(__file__).resolve().parent / "canon-strings.local.txt"

AUDIT_DIRS = ["worlds/sample-world", "web", "src"]
AUDIT_SUFFIXES = {".py", ".js", ".mjs", ".html", ".css", ".md", ".json", ".txt"}

PRONOUN_PATTERN = re.compile(r"\b(she|her|hers|his|him)\b", re.IGNORECASE)


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


def test_engine_surfaces_carry_no_gendered_pronouns():
    """Shape guard: no third-person singular gendered pronouns in user-facing
    code strings or prompt scaffolding in web/ or src/vefr/.

    Module docstrings in Python files are structural documentation (e.g. Saga in
    saga.py) and are excluded by AST inspection so no brittle string allowlist
    is required.
    """
    failures = []

    # 1. Audit web/ files (.js, .mjs, .html)
    web_dir = ROOT / "web"
    if web_dir.is_dir():
        for f in sorted(web_dir.rglob("*")):
            if not f.is_file() or f.suffix not in {".js", ".mjs", ".html"}:
                continue
            if "vendor" in f.parts:
                continue
            rel = str(f.relative_to(ROOT))
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                for m in PRONOUN_PATTERN.finditer(line):
                    failures.append(
                        f"  {rel}:{i}: pronoun {m.group(0)!r} leaves the source: {line.strip()[:80]!r}"
                    )

    # 2. Audit src/vefr/ files (.py) for string literals and comments
    src_dir = ROOT / "src" / "vefr"
    if src_dir.is_dir():
        for f in sorted(src_dir.rglob("*.py")):
            if not f.is_file():
                continue
            rel = str(f.relative_to(ROOT))
            text = f.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(f))
            module_docstring = ast.get_docstring(tree)

            # Check comments
            for i, line in enumerate(text.splitlines(), 1):
                if "#" in line:
                    comment = line[line.index("#") :]
                    for m in PRONOUN_PATTERN.finditer(comment):
                        failures.append(
                            f"  {rel}:{i}: comment pronoun {m.group(0)!r}: {comment.strip()[:80]!r}"
                        )

            # Check AST string literals (excluding module docstring)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if tree.body and isinstance(tree.body[0], ast.Expr) and tree.body[0].value is node:
                        # Skip module docstring
                        continue
                    if module_docstring and node.value == module_docstring:
                        continue
                    for m in PRONOUN_PATTERN.finditer(node.value):
                        ln = getattr(node, "lineno", "?")
                        failures.append(
                            f"  {rel}:{ln}: string literal pronoun {m.group(0)!r} leaves the source: {node.value.strip()[:80]!r}"
                        )

    assert not failures, (
        "third-person singular gendered pronouns found in code or prompts:\n"
        + "\n".join(failures)
        + "\n\nEngine scaffolding must remain gender-neutral."
    )


def test_no_historical_package_names():
    """Anti-regression test: ensure legacy package names
    do not reappear in src/, web/, tests/, docs/, or the
    root-level documents (README, AGENTS, ROADMAP, LICENSE,
    GETTING_STARTED). The tree is scrubbed; this keeps it so."""
    failures = []
    # Build regex without naming historical literals directly in the source file
    bad_terms = ["m" + "unr", "s" + "midr"]
    pattern = re.compile(r"\b(" + "|".join(bad_terms) + r")\b", re.IGNORECASE)
    roots = [ROOT / d for d in ["src", "web", "tests", "docs"]]
    roots += [ROOT / n for n in
              ("README.md", "AGENTS.md", "ROADMAP.md", "GETTING_STARTED.md", "LICENSE")]
    for root in roots:
        if not root.exists():
            continue
        files = (
            root.rglob("*") if root.is_dir() else [root]
        )
        for f in sorted(files):
            if not f.is_file() or f.suffix not in AUDIT_SUFFIXES | {""}:
                continue
            if "vendor" in f.parts:
                continue
            if f.resolve() == Path(__file__).resolve():
                continue
            rel = str(f.relative_to(ROOT))
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                for m in pattern.finditer(line):
                    failures.append(
                        f"  {rel}:{i}: found historical package name {m.group(0)!r}: {line.strip()[:80]!r}"
                    )

    assert not failures, (
        "historical package names found in codebase:\n"
        + "\n".join(failures)
        + "\n\nEngine naming must remain consistently 'vefr'."
    )

