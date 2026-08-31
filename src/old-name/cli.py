"""The raven and the smith - universal tooling, not story-shaped.

Two entry points, always the same regardless of which game or world
is built on this engine:

    raven - memory. The game and its keeping.
        raven tidyup     the seven questions, raven-shaped
        raven deploy     ship this checkout to your deploy host
        raven backup     git bundle -> NAS, keep the newest two
        raven test       the pytest suite

    old-name - the smith. Craft. Worldbuilding tools.
        old-name chat       interview a new world into existence
        old-name validate   geometry checks against the pack
        old-name build      rebuild the map from run-length rows
        old-name verify     validate a live deployment

Run from any checkout; git decides which. In the container, the
same commands serve against the deployed world (deploy and
backup need a git checkout, so they stay on the dev side).

Your own game's name never appears here - that's the point. Whatever
you build (Old Name, or anything else) sits in worlds/, and these two
commands stay the same no matter whose story they're serving.
"""

import argparse
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .maplab import load_pack, validate

DEFAULT_URL = 'http://192.168.2.76:8820'
DEFAULT_DEPLOY_HOST = 'bazzite'
DEFAULT_NAS_HOST = 'homelab-vm'
NAS_DIR = '/mnt/nas/shared/backups'
BUNDLE_KEEP = 2
DEPLOY_EXCLUDES = ('.venv', '__pycache__', '.pytest_cache', '*.egg-info', '.git')


def repo_root():
    """The checkout you run from - None when installed (container)."""
    try:
        top = subprocess.run(('git', 'rev-parse', '--show-toplevel'),
                             capture_output=True, text=True).stdout.strip()
        if top:
            return Path(top)
    except Exception:  # noqa: BLE001
        pass
    return None


def pack_root() -> Path:
    """Where worlds/ lives: a checkout, or NORN_HOME in the container."""
    r = repo_root()
    if r and (r / 'worlds').is_dir():
        return r
    from .paths import app_home
    return app_home()


def git_quiet(*args):
    r = repo_root()
    if not r:
        return ''
    return subprocess.run(('git',) + args, capture_output=True, text=True,
                          cwd=str(r)).stdout.strip()


def sh(cmd, **kw):
    print(f'+ {" ".join(str(c) for c in cmd)}')
    return subprocess.run([str(c) for c in cmd], **kw)


def fetch(url, timeout=8):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def need_repo() -> Path:
    r = repo_root()
    if not r:
        raise SystemExit('this command needs a git checkout - '
                         'it is not available inside the container')
    return r


# --------------------------------------------------------------- tidyup

def q1_sync() -> tuple:
    if not repo_root():
        return 'unavailable', 'no git checkout (container install)'
    branch_line = git_quiet('status', '-sb').splitlines()[0]
    if 'ahead' in branch_line or 'behind' in branch_line:
        return 'OUT-OF-SYNC', branch_line
    local = git_quiet('rev-parse', 'HEAD')[:7]
    remote = git_quiet('ls-remote', 'origin', '-h', 'refs/heads/main')[:7]
    if local != remote:
        return 'OUT-OF-SYNC', f'local {local} != remote {remote}'
    return 'in-sync', f'local == remote @ {local}'


def q2_dirty() -> tuple:
    if not repo_root():
        return 'unavailable', 'no git checkout'
    status = git_quiet('status', '--porcelain')
    dirty = len(status.splitlines()) if status else 0
    stashes = len(git_quiet('stash', 'list').splitlines())
    if dirty or stashes:
        return 'dirty', f'{dirty} uncommitted file(s), {stashes} stash(es)'
    return 'clean', '0 uncommitted, 0 stashes'


def q3_deployment(url: str) -> tuple:
    try:
        h = fetch(f'{url.rstrip("/")}/api/health')
        if h.get('ok') and 'purpose' in h:
            return 'healthy', 'container up, motto present'
        return 'degraded', f'unexpected health payload: {h}'
    except Exception as e:  # noqa: BLE001
        return 'down', f'{url}: {e}'


def q4_world(url: str, pack: Path) -> tuple:
    errors = validate(load_pack(pack), pack_dir=pack)
    try:
        served = fetch(f'{url.rstrip("/")}/api/world')
        town_keys = ('tile', 'map', 'legend', 'pois', 'watch', 'sanctuary_tiles',
                     'water_by_phase', 'flood_tiles', 'willow_start')
        shim = {
            'phases': served['phases'],
            'speakers': {
                s['key']: {'name': s['name'], 'at': s['at'], 'near': s['near'],
                           'seeds': s.get('seeds', {})}
                for s in served['speakers']
            },
            'voices': {},
            'town': {k: served[k] for k in town_keys if k in served},
        }
        errors += ['live: ' + e for e in validate(shim)]
    except Exception as e:  # noqa: BLE001
        return 'unreachable', f'live check failed: {e}'
    if errors:
        return 'invalid', '; '.join(errors)
    return 'validated', 'pack and live deployment both pass maplab'


def q5_backups(nas_host: str) -> tuple:
    try:
        out = subprocess.run(
            ('ssh', '-o', 'ConnectTimeout=6', nas_host,
             f'ls -t {NAS_DIR}/old-name-*.bundle 2>/dev/null | head -1'),
            capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return 'unverified', f'ssh failed: {e}'
    if not out:
        return 'unverified', f'no bundles on {nas_host}:{NAS_DIR}'
    return 'fresh', f'{Path(out).name} on {nas_host} (newest bundle)'


def q6_vault(bazzite_host: str) -> tuple:
    try:
        out = subprocess.run(
            ('ssh', '-o', 'ConnectTimeout=6', bazzite_host,
             'ls ~/old-name-data/ 2>/dev/null | wc -l'),
            capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return 'unverified', f'ssh failed: {e}'
    n = out.splitlines()[-1] if out else '0'
    return 'persisted', f'~/old-name-data present ({n} entries)'


def q7_next(pack: Path) -> tuple:
    root = pack.parent.parent
    roadmap = root / 'ROADMAP.md'
    if not roadmap.exists():
        return 'unknown', 'no ROADMAP.md in this install'
    nxt = roadmap.read_text(encoding='utf-8').split('## Next')[1].split('## ')[0]
    items = [ln.strip()[6:] for ln in nxt.splitlines() if ln.strip().startswith('- [ ]')]
    short = [i.split(':')[0].strip('**').strip() for i in items]
    return 'open', f'{len(items)} open: {"; ".join(short)}'


def cmd_tidyup(args) -> int:
    pack = pack_root() / 'worlds' / 'private-canon'
    rows = [
        ('Q1', 'git local + Gitea remote in sync', *q1_sync()),
        ('Q2', 'local files needing push', *q2_dirty()),
        ('Q3', 'deployment healthy (bazzite)', *q3_deployment(args.url)),
        ('Q4', 'the world validated (pack + live)', *q4_world(args.url, pack)),
        ('Q5', 'backups fresh (NAS bundle)', *q5_backups(args.nas_host)),
        ('Q6', 'vault persisted (volume)', *q6_vault(args.deploy_host)),
        ('Q7', 'open items from the ROADMAP', *q7_next(pack)),
    ]
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f'raven tidyup -- {now}')
    print()
    print('| Q  | Question | Status | Answer |')
    print('| -- | -------- | ------ | ------ |')
    for q, question, status, answer in rows:
        print(f'| {q} | {question} | {status} | {answer} |')
    print()
    print('the town keeps. <3')
    return 0


# ------------------------------------------------------------------ map

def cmd_chat(args) -> int:
    from . import chat as chatmod

    name = chatmod.slugify(args.name)
    scaffold = pack_root() / 'worlds' / 'sample-world'
    dest = pack_root() / 'worlds' / name
    return chatmod.run_interview(dest, scaffold)


def cmd_map(args) -> int:
    from .maplab import main as maplab_main
    if args.map_cmd == 'validate':
        argv = ['validate', '--pack', str(args.pack)]
    elif args.map_cmd == 'build':
        argv = ['build', '--segments', args.segments, '--pack', str(args.pack)]
        if args.force:
            argv.append('--force')
    elif args.map_cmd == 'verify':
        argv = ['verify', '--url', args.url]
    else:
        raise SystemExit(f'unknown map command: {args.map_cmd}')
    return maplab_main(argv)

def cmd_deploy(args) -> int:
    root = need_repo()
    host = args.deploy_host
    url = args.url
    excludes = []
    for e in DEPLOY_EXCLUDES:
        excludes += ['--exclude', e]
    if sh(('rsync', '-a', '--delete', *excludes, f'{root}/', f'{host}:~/old-name/')).returncode:
        return 1
    if sh(('ssh', host, 'cd ~/old-name && podman build -q -t localhost/old-name:latest . '
                       '&& systemctl --user restart old-name')).returncode:
        return 1
    import time
    time.sleep(2)
    try:
        h = fetch(f'{url.rstrip("/")}/api/health')
        print(f'health: {h}')
    except Exception as e:  # noqa: BLE001
        print(f'health check failed: {e}')
        return 1
    from .maplab import main as maplab_main
    ok = maplab_main(['verify', '--url', url])
    print('deployed. <3' if ok == 0 else 'deployed, but map verify flagged problems.')
    return ok


# --------------------------------------------------------------- backup

def cmd_backup(args) -> int:
    root = need_repo()
    date = datetime.now(timezone.utc).strftime('%Y%m%d')
    name = f'old-name-{date}.bundle'
    tmp = Path('/tmp') / name
    if sh(('git', '-C', str(root), 'bundle', 'create', str(tmp), '--all')).returncode:
        return 1
    if sh(('scp', '-q', str(tmp), f'{args.nas_host}:{NAS_DIR}/{name}')).returncode:
        return 1
    sh(('ssh', args.nas_host,
        f'cd {NAS_DIR} && ls -t old-name-*.bundle | tail -n +{BUNDLE_KEEP + 1} | xargs -r rm -f'))
    listing = subprocess.run(
        ('ssh', args.nas_host, f'ls -t {NAS_DIR}/old-name-*.bundle'),
        capture_output=True, text=True).stdout.strip()
    print(f'bundles on {args.nas_host}:')
    print(listing)
    tmp.unlink(missing_ok=True)
    print('backed up. <3')
    return 0


# ----------------------------------------------------------------- test

def cmd_test(args) -> int:
    need_repo()
    cmd = ('uv', 'run', '--group', 'test', 'pytest', '-q') + tuple(args.test_args)
    try:
        return sh(cmd).returncode
    except FileNotFoundError:
        print('uv not found - run raven test from a checkout with uv installed')
        return 1


# ----------------------------------------------------------------- mains

RAVEN_HELP = """raven - memory. The game and its keeping.

  raven tidyup    the seven questions, raven-shaped: git/deploy sync,
                  local files needing push, deployment health, world
                  validation, backup freshness, vault persistence,
                  open ROADMAP items
  raven deploy    rsync this checkout to --deploy-host, rebuild the
                  container, restart it, verify health + the live map
  raven backup    git bundle -> --nas-host, keep the newest two
  raven test      the pytest suite (uv run --group test pytest),
                  extra args pass through: raven test -k chat
"""

SMIDR_HELP = """old-name - the smith. Craft. Worldbuilding tools.

  old-name chat      interview a new world into existence, against your
                  local ollama - writes worlds/<name>/, validates as
                  it goes
  old-name validate  geometry checks against a pack (--pack defaults to
                  the currently selected world)
  old-name build     rebuild the map from run-length rows (--segments)
  old-name verify    validate a live deployment's served world (--url)

Universal tooling - the same four commands regardless of which world
or game is built on this engine.
"""


def raven_main() -> int:
    ap = argparse.ArgumentParser(
        prog='raven', description=RAVEN_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument('--url', default=DEFAULT_URL)
    ap.add_argument('--deploy-host', default=DEFAULT_DEPLOY_HOST)
    ap.add_argument('--nas-host', default=DEFAULT_NAS_HOST)
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('tidyup', help='the seven questions').set_defaults(fn=cmd_tidyup)

    pd = sub.add_parser('deploy', help='ship this checkout to --deploy-host')
    pd.set_defaults(fn=cmd_deploy)

    pb = sub.add_parser('backup', help='git bundle -> --nas-host, keep the newest two')
    pb.set_defaults(fn=cmd_backup)

    pt = sub.add_parser(
        'test', help='the pytest suite (extra args pass through, e.g. -k chat)'
    )
    pt.set_defaults(fn=cmd_test)

    args, extra = ap.parse_known_args()
    args.test_args = extra if args.cmd == 'test' else []
    return args.fn(args)


def smidr_main() -> int:
    ap = argparse.ArgumentParser(
        prog='old-name', description=SMIDR_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest='cmd', required=True)

    mc = sub.add_parser('chat', help='interview a new world into existence')
    mc.add_argument('--name', required=True, help='the new pack name (worlds/<name>)')
    mc.set_defaults(fn=cmd_chat)

    mv = sub.add_parser('validate', help='geometry checks against the pack')
    mv.add_argument('--pack', default=None)
    mv.set_defaults(fn=cmd_map, map_cmd='validate', segments=None, force=False)

    mb = sub.add_parser('build', help='rebuild the map from run-length rows')
    mb.add_argument('--segments', required=True)
    mb.add_argument('--pack', default=None)
    mb.add_argument('--force', action='store_true')
    mb.set_defaults(fn=cmd_map, map_cmd='build')

    mr = sub.add_parser('verify', help='validate a live deployment')
    mr.add_argument('--url', default=DEFAULT_URL)
    mr.set_defaults(fn=cmd_map, map_cmd='verify', segments=None, force=False,
                    pack=None)

    args = ap.parse_args()
    if getattr(args, 'pack', None) is None:
        args.pack = pack_root() / 'worlds' / world_name()
    return args.fn(args)


if __name__ == '__main__':
    sys.exit(raven_main())
