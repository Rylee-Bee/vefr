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
def _session(html, pack, wait_ms, plant=None):
    """Open `html` (or weave `pack`) in headless Chromium and press Begin.

    Yields the page once the game is up, or None when Playwright/Chromium
    is missing (the install hint goes to STDERR and the caller returns 2).
    A pack is woven into a temp file that is always removed afterwards.
    Playwright is imported here, lazily - nothing imports it at module load.

    `plant` is a scenario's save keys (`vefr.scenarios.storage`): written
    into the page's storage before any of the game's scripts run, so the
    player reads them as its own save. Only those keys are written; no
    other storage is read, cleared or enumerated.
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
            if plant:
                page.add_init_script(_PLANT_JS % json.dumps(plant))
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


# A scenario's save keys, written before the game's own scripts run. A
# browser that blocks storage leaves the game to start fresh; the arrival
# check below then says the scenario did not take.
_PLANT_JS = """(() => {
  const keys = %s;
  try { for (const k of Object.keys(keys)) localStorage.setItem(k, keys[k]); }
  catch (e) {}
})();"""

# Walk the hero in through the player's own arrival paths, then read the
# harness's window onto play back: where the hero is, and the world name the
# planted keys had to match.
_ARRIVE_JS = """(s) => {
  let entered = false;
  if (s.depth) {
    entered = !!(window.VEFR_DESCENT && window.VEFR_DESCENT.enterDescentFloor(s.depth));
  } else if (typeof window.VEFR_ENTER_REGION === 'function') {
    window.VEFR_ENTER_REGION(s.region, s.at || null);
    entered = true;
  }
  const c = window.VEFR_COMBAT || {};
  const floor = window.VEFR_DESCENT ? window.VEFR_DESCENT.floor : null;
  return {
    entered: entered,
    world: (window.VEFR_WORLD && window.VEFR_WORLD.name) || 'world',
    region: c.region || null,
    at: (c.hero && c.hero.at) || null,
    hp: (c.hero && c.hero.hp) || null,
    gold: (typeof c.gold === 'number') ? c.gold : null,
    depth: floor ? floor.depth : null,
    card: !!(window.VEFR_DESCENT && window.VEFR_DESCENT.cardShown && window.VEFR_DESCENT.cardShown()),
  };
}"""


def scenario_boot(pack, name):
    """`(boot, None)` for a pack's scenario, or `(None, sentences)`.

    `boot` holds what a session needs: the save keys to plant, the start
    to walk the hero to, and the world name those keys were written for.
    An invalid scenario is refused with the same sentences `vefr check`
    speaks, before any browser opens.
    """
    from . import maplab, scenarios

    w = maplab.load_pack(Path(pack))
    data, why = scenarios.load(pack, name)
    if why is not None:
        return None, [why]
    problems = scenarios.check(w, data)
    if problems:
        return None, [f'scenarios/{name}.json: {p}' for p in problems]
    return {'name': name, 'storage': scenarios.storage(w, data),
            'start': data['start'], 'world': scenarios.world_name(w),
            'gold': data.get('gold')}, None


def _arrive(page, boot):
    """Walk the hero to the scenario's start; `(report, problem or None)`."""
    page.wait_for_timeout(200)
    report = page.evaluate(_ARRIVE_JS, boot['start'])
    page.wait_for_timeout(300)
    start = boot['start']
    if report['world'] != boot['world']:
        return report, (f"the woven game names this world {report['world']!r}, "
                        f"but the scenario's keys were written for "
                        f"{boot['world']!r}")
    if report['card']:
        return report, (f"scenario {boot['name']!r}: the game took the planted "
                        'state for a Release 1 save and opened its generation card')
    if boot.get('gold') is not None and report['gold'] != boot['gold']:
        return report, (f"scenario {boot['name']!r} planted {boot['gold']} gold "
                        f"and the game holds {report['gold']}")
    if not report['entered']:
        return report, f"scenario {boot['name']!r}: the game would not enter its start"
    if 'depth' in start and report['depth'] != start['depth']:
        return report, (f"scenario {boot['name']!r} asked for depth "
                        f"{start['depth']} and the hero is at depth {report['depth']}")
    if 'region' in start and report['region'] != start['region']:
        return report, (f"scenario {boot['name']!r} asked for {start['region']} "
                        f"and the hero is in {report['region']}")
    if start.get('at') and report['at'] != list(start['at']):
        return report, (f"scenario {boot['name']!r} asked for {list(start['at'])} "
                        f"and the hero stands at {report['at']}")
    return report, None


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


def _scenario_or_refusal(verb, pack, scenario):
    """`(boot or None, exit code or None)`: a scenario needs `--pack`, and
    an invalid one is refused with its sentences before a browser opens."""
    if scenario is None:
        return None, None
    if pack is None:
        print(f'vefr {verb} --scenario needs --pack: a scenario lives in its '
              'pack', file=sys.stderr)
        return None, 2
    boot, problems = scenario_boot(pack, scenario)
    if problems:
        for sentence in problems:
            print(sentence, file=sys.stderr)
        return None, 2
    return boot, None


def look(html=None, pack=None, out=None, steps='', json_out=False,
         scenario=None) -> int:
    """Screenshot the woven player and list the text standing over the map.

    Opens `html` (or weaves `pack`), presses Begin, replays the comma-
    separated `steps` keys, then screenshots to `out` (default `look.png`)
    and reports every visible leaf in the lower 40% of the viewport or in
    the toasts strip: `{id, cls, tag, y, text}`. The tool for catching
    text that has drifted onto the map.

    With `scenario` (a name in the pack's `scenarios/`), the game opens in
    that state first: its save keys planted, the hero walked to its start.
    """
    if html is None and pack is None:
        print('vefr look needs --html or --pack', file=sys.stderr)
        return 2
    boot, refused = _scenario_or_refusal('look', pack, scenario)
    if refused is not None:
        return refused

    out = Path(out or 'look.png')
    arrival = None
    with _session(html, pack, 800, plant=boot and boot['storage']) as page:
        if page is None:
            return 2
        if boot is not None:
            arrival, problem = _arrive(page, boot)
            if problem is not None:
                print(problem, file=sys.stderr)
                return 1
        for key in (k.strip() for k in steps.split(',') if k.strip()):
            page.keyboard.press(key)
            page.wait_for_timeout(250)
        page.wait_for_timeout(3000)
        page.screenshot(path=str(out))
        leaves = page.evaluate(_LEAF_JS)

    if json_out:
        report = {'screenshot': str(out), 'overlay_text': leaves}
        if arrival is not None:
            report['scenario'] = {'name': boot['name'], **arrival}
        print(json.dumps(report))
        return 0
    if arrival is not None:
        where = (f"depth {arrival['depth']}" if arrival['depth']
                 else arrival['region'])
        print(f"scenario: {boot['name']} - {where} at {arrival['at']}")
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


def probe(html=None, pack=None, fire=(), json_out=False, scenario=None) -> int:
    """Fire rule events at the woven player and read its why-log back.

    Each `event:key=value[,key=value]` spec calls the player's global
    `window.fireRule`; afterwards `window.VEFR_WHY` and the engine's
    flags are read out. A malformed spec is a usage error, refused before
    any browser is launched. With `scenario`, the events are fired in that
    scenario's state (see `look`).
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
    boot, refused = _scenario_or_refusal('probe', pack, scenario)
    if refused is not None:
        return refused

    arrival = None
    with _session(html, pack, 300, plant=boot and boot['storage']) as page:
        if page is None:
            return 2
        if boot is not None:
            arrival, problem = _arrive(page, boot)
            if problem is not None:
                print(problem, file=sys.stderr)
                return 1
        for event, data in parsed:
            page.evaluate(_FIRE_JS, {'event': event, 'data': data})
            page.wait_for_timeout(50)
        report = page.evaluate(_READ_JS)

    fired = [{'event': e, 'data': d} for e, d in parsed]
    result = {'fired': fired, 'why': report['why'], 'flags': report['flags']}
    if arrival is not None:
        result['scenario'] = {'name': boot['name'], **arrival}
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
