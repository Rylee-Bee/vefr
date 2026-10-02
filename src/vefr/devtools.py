"""`vefr publish` and the doctor's tooling checks.

The logic behind the front door's developer verbs (the cmd_find/vefr.find
split): `vefr.cli.cmd_publish` only resolves `--pack` and hands the rest
here. Nothing in this module touches the network or a model; the gallery
CLI is the only external process, and it is optional.

`publish` weaves the pack into a fresh, world-readable temp dir (nginx
served tempfile.mkdtemp's 0700 as 403) and asks the gallery to build it.
`tooling_checks` answers, honestly, which optional dev tools this machine
has and how to install the ones it does not.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Where an absent gallery is documented - one hint, one place.
GALLERY_HINT = 'see ~/.agents/skills/gallery'


def _gallery_bin(which=shutil.which, home=None):
    """The gallery CLI, or None.

    `$VEFR_GALLERY` wins when set - even a broken path, so a wrong
    override is refused instead of silently falling through to the
    bundled one. Otherwise PATH, then `~/.agents/bin/gallery`.
    """
    home = Path.home() if home is None else Path(home)
    env = os.environ.get('VEFR_GALLERY')
    if env:
        return env if Path(env).exists() else None
    found = which('gallery')
    if found:
        return found
    bundled = home / '.agents' / 'bin' / 'gallery'
    if bundled.exists():
        return str(bundled)
    return None


def _git_sha(pack: Path) -> str:
    """`git rev-parse --short HEAD` in `pack`, or `nogit`."""
    try:
        out = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=pack, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return 'nogit'
    return out.stdout.strip() or 'nogit'


def publish(pack, project=None, sha=None, live=False, dry_run=False) -> int:
    """Weave `pack` and hand the built file to the gallery CLI.

    The pack is woven into `index.html` inside a fresh temp dir, then
    the gallery's own `build` command carries it to the site. `dry_run`
    prints the command it would run and stops; otherwise the gallery's
    exit code passes straight through and the temp dir is always
    cleaned up.
    """
    from .cli import weave_html

    pack = Path(pack)
    project = project or pack.name
    if sha is None:
        sha = _git_sha(pack)
    gallery = _gallery_bin()
    if not gallery:
        print('gallery not found: set VEFR_GALLERY, put gallery on PATH, '
              f'or install it under ~/.agents/bin ({GALLERY_HINT})',
              file=sys.stderr)
        return 2

    dist = tempfile.mkdtemp(prefix='vefr-publish-')
    try:
        os.chmod(dist, 0o755)
        index = Path(dist) / 'index.html'
        index.write_text(weave_html(pack), encoding='utf-8')
        os.chmod(index, 0o644)

        cmd = [gallery, 'build', project, dist, '--sha', sha]
        if live:
            cmd.append('--live')
        if dry_run:
            print('would run: ' + ' '.join(cmd))
            return 0
        return subprocess.run(cmd).returncode
    finally:
        shutil.rmtree(dist, ignore_errors=True)


def tooling_checks(root, which=shutil.which, home=Path.home()) -> list[tuple[str, str, str]]:
    """Rows `(name, ok|missing, detail)` for the optional dev tools.

    `ok` means the tool was found and the detail says where; `missing`
    means the detail is the command that installs it. Informational
    only - a missing tool is never an error.
    """
    root = Path(root)
    home = Path(home)
    rows: list[tuple[str, str, str]] = []

    node = which('node')
    rows.append(('node', 'ok', node) if node
                else ('node', 'missing', 'install Node.js'))

    jsdom = root / 'node_modules' / 'jsdom'
    rows.append(('jsdom', 'ok', str(jsdom)) if jsdom.exists()
                else ('jsdom', 'missing', 'run npm ci'))

    chromium = sorted(home.glob('.cache/ms-playwright/chromium*'))
    rows.append(('chromium', 'ok', str(chromium[0])) if chromium
                else ('chromium', 'missing', 'run uv run playwright install chromium'))

    gallery = _gallery_bin(which=which, home=home)
    rows.append(('gallery', 'ok', gallery) if gallery
                else ('gallery', 'missing', GALLERY_HINT))
    return rows
