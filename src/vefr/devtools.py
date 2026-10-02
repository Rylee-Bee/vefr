"""`vefr publish` / `vefr look` / `vefr probe`, and the doctor's tooling checks.

The logic behind the front door's developer verbs (the cmd_find/vefr.find
split): `vefr.cli.cmd_publish` only resolves `--pack` and hands the rest
here. Nothing in this module touches the network or a model; the gallery
CLI is the only external process, and it is optional.

`publish` weaves the pack into a fresh, world-readable temp dir (nginx
served tempfile.mkdtemp's 0700 as 403) and asks the gallery to build it.
`look` screenshots the woven player and lists the text sitting over the
map; `probe` fires rule events and reads the player's why-log back.
`tooling_checks` answers, honestly, which optional dev tools this machine
has and how to install the ones it does not.
"""

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# The install hint for the browser both devtools verbs drive.
BROWSER_HINT = 'uv run playwright install chromium'

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


# ------------------------------------------------------------ look / probe

def _no_browser() -> None:
    """The one missing-browser message, on STDERR; callers return 2."""
    print(f'Playwright / Chromium not available: run `{BROWSER_HINT}`',
          file=sys.stderr)


@contextlib.contextmanager
def _session(html, pack, wait_ms):
    """Open `html` (or weave `pack`) in headless Chromium and press Begin.

    Yields the page once the game is up, or None when Playwright/Chromium
    is missing (the install hint goes to STDERR and the caller returns 2).
    A pack is woven into a temp file that is always removed afterwards.
    Playwright is imported here, lazily - nothing imports it at module load.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception:  # noqa: BLE001 - not installed is a report, not a crash
        _no_browser()
        yield None
        return

    temp = None
    if html is None:
        from .cli import weave_html

        fd, tmp = tempfile.mkstemp(prefix='vefr-devtools-', suffix='.html')
        os.close(fd)
        temp = Path(tmp)
        temp.write_text(weave_html(Path(pack)), encoding='utf-8')
        html = temp
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception:  # noqa: BLE001 - Chromium not installed
                _no_browser()
                yield None
                return
            page = browser.new_page(viewport={'width': 1280, 'height': 800})
            page.goto(Path(html).resolve().as_uri())
            page.click('#ts-enter')
            page.wait_for_timeout(wait_ms)
            try:
                yield page
            finally:
                browser.close()
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


# Visible leaves whose top is in the lower 40% of the viewport, or that
# sit in the toasts strip. `children.length === 0` is the leaf test.
_LEAF_JS = """() => {
  const floor = window.innerHeight * 0.6;
  const out = [];
  document.querySelectorAll('body *').forEach((el) => {
    if (el.children.length) return;
    const text = (el.innerText || '').trim();
    if (!text) return;
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return;
    const rect = el.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    if (!el.closest('.toasts') && rect.top < floor) return;
    out.push({
      id: el.id || '',
      cls: (typeof el.className === 'string' ? el.className : ''),
      tag: el.tagName.toLowerCase(),
      y: Math.round(rect.top),
      text: text.slice(0, 90),
    });
  });
  return out;
}"""


def look(html=None, pack=None, out=None, steps='', json_out=False) -> int:
    """Screenshot the woven player and list the text standing over the map.

    Opens `html` (or weaves `pack`), presses Begin, replays the comma-
    separated `steps` keys, then screenshots to `out` (default `look.png`)
    and reports every visible leaf in the lower 40% of the viewport or in
    the toasts strip: `{id, cls, tag, y, text}`. The tool for catching
    text that has drifted onto the map.
    """
    if html is None and pack is None:
        print('vefr look needs --html or --pack', file=sys.stderr)
        return 2

    out = Path(out or 'look.png')
    with _session(html, pack, 800) as page:
        if page is None:
            return 2
        for key in (k.strip() for k in steps.split(',') if k.strip()):
            page.keyboard.press(key)
            page.wait_for_timeout(250)
        page.wait_for_timeout(3000)
        page.screenshot(path=str(out))
        leaves = page.evaluate(_LEAF_JS)

    if json_out:
        print(json.dumps({'screenshot': str(out), 'overlay_text': leaves}))
        return 0
    print(f'screenshot: {out}')
    print(f'{"y":>6}  {"tag":<6} {"id":<18} text')
    for e in leaves:
        print(f'{e["y"]:>6}  {e["tag"]:<6} {e["id"]:<18} {e["text"]}')
    return 0


def _parse_fire(spec: str):
    """`event:key=value[,key=value]` -> (event, data), or None if malformed.

    An integer-looking value becomes an int; anything else stays a string.
    """
    event, sep, rest = spec.partition(':')
    if not sep or not event:
        return None
    data = {}
    for pair in rest.split(','):
        key, eq, value = pair.partition('=')
        if not eq or not key:
            return None
        try:
            data[key] = int(value)
        except ValueError:
            data[key] = value
    return event, data


_FIRE_JS = '(s) => { if (window.fireRule) window.fireRule(s.event, s.data); }'
_READ_JS = """() => ({
  why: Array.isArray(window.VEFR_WHY) ? window.VEFR_WHY : [],
  flags: (window.VEFR_RULES_STATE && window.VEFR_RULES_STATE.flags) || {},
})"""


def probe(html=None, pack=None, fire=(), json_out=False) -> int:
    """Fire rule events at the woven player and read its why-log back.

    Each `event:key=value[,key=value]` spec calls the player's global
    `window.fireRule`; afterwards `window.VEFR_WHY` and the engine's
    flags are read out. A malformed spec is a usage error, refused before
    any browser is launched.
    """
    parsed = []
    for spec in fire:
        event_data = _parse_fire(spec)
        if event_data is None:
            print('use event:key=value', file=sys.stderr)
            return 2
        parsed.append(event_data)

    if html is None and pack is None:
        print('vefr probe needs --html or --pack', file=sys.stderr)
        return 2

    with _session(html, pack, 300) as page:
        if page is None:
            return 2
        for event, data in parsed:
            page.evaluate(_FIRE_JS, {'event': event, 'data': data})
            page.wait_for_timeout(50)
        report = page.evaluate(_READ_JS)

    fired = [{'event': e, 'data': d} for e, d in parsed]
    result = {'fired': fired, 'why': report['why'], 'flags': report['flags']}
    if json_out:
        print(json.dumps(result))
        return 0
    for e in fired:
        print(f'fired {e["event"]} {e["data"]}')
    for w in result['why']:
        print(f'why {w.get("id")}: {w.get("why")}')
    for key, value in result['flags'].items():
        print(f'flag {key} = {value}')
    return 0


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
