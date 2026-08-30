#!/usr/bin/env python3
"""old-name lab - one entry point for the whole project.

    lab tidyup                 the seven questions, old-name-shaped
    lab map validate           geometry checks against the pack
    lab map build --segments F rebuild the map from run-length rows
    lab map verify --url U     validate a live deployment
    lab deploy                 ship this checkout to bazzite, rebuild,
                               restart, health-check, map-verify
    lab backup                 git bundle -> NAS, keep the newest two
    lab test [-- extra]        the pytest suite

Run from any checkout of the repo; git decides which one.
Defaults: bazzite at 192.168.2.76:8820, NAS on homelab-vm.
"""

import argparse
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_URL = 'http://192.168.2.76:8820'
DEFAULT_DEPLOY_HOST = 'bazzite'
DEFAULT_NAS_HOST = 'homelab-vm'
NAS_DIR = '/mnt/nas/shared/backups'
BUNDLE_KEEP = 2


def repo_root() -> Path:
    try:
        top = subprocess.run(('git', 'rev-parse', '--show-toplevel'),
                             capture_output=True, text=True).stdout.strip()
        if top:
            return Path(top)
    except Exception:  # noqa: BLE001
        pass
    return Path(__file__).resolve().parents[1]


ROOT = repo_root()
sys.path.insert(0, str(ROOT / 'src'))

from old-name.maplab import load_pack, validate  # noqa: E402

DEPLOY_EXCLUDES = ('.venv', '__pycache__', '.pytest_cache', '*.egg-info', '.git')


def sh(cmd, **kw):
    print(f'+ {" ".join(str(c) for c in cmd)}')
    return subprocess.run([str(c) for c in cmd], cwd=str(ROOT), **kw)


def fetch(url, timeout=8):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


# --------------------------------------------------------------- tidyup

def git_quiet(*args):
    return subprocess.run(('git',) + args, capture_output=True, text=True,
                          cwd=str(ROOT)).stdout.strip()


def q1_sync() -> tuple:
    branch_line = git_quiet('status', '-sb').splitlines()[0]
    if 'ahead' in branch_line or 'behind' in branch_line:
        return 'OUT-OF-SYNC', branch_line
    local = git_quiet('rev-parse', 'HEAD')[:7]
    remote = git_quiet('ls-remote', 'origin', '-h', 'refs/heads/main')[:7]
    if local != remote:
        return 'OUT-OF-SYNC', f'local {local} != remote {remote}'
    return 'in-sync', f'local == remote @ {local}'


def q2_dirty() -> tuple:
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
            return 'healthy', f'container up, motto present'
        return 'degraded', f'unexpected health payload: {h}'
    except Exception as e:  # noqa: BLE001
        return 'down', f'{url}: {e}'


def q4_world(url: str) -> tuple:
    errors = validate(load_pack(ROOT / 'worlds' / 'private-canon'),
                      pack_dir=ROOT / 'worlds' / 'private-canon')
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


def q7_next() -> tuple:
    roadmap = (ROOT / 'ROADMAP.md').read_text(encoding='utf-8')
    nxt = roadmap.split('## Next')[1].split('## ')[0]
    items = [ln.strip()[6:] for ln in nxt.splitlines() if ln.strip().startswith('- [ ]')]
    short = [i.split(':')[0].strip('**').strip() for i in items]
    return 'open', f'{len(items)} open: {"; ".join(short)}'


def cmd_tidyup(args) -> int:
    rows = [
        ('Q1', 'git local + Gitea remote in sync', *q1_sync()),
        ('Q2', 'local files needing push', *q2_dirty()),
        ('Q3', 'deployment healthy (bazzite)', *q3_deployment(args.url)),
        ('Q4', 'the world validated (pack + live)', *q4_world(args.url)),
        ('Q5', 'backups fresh (NAS bundle)', *q5_backups(args.nas_host)),
        ('Q6', 'vault persisted (volume)', *q6_vault(args.deploy_host)),
        ('Q7', 'open items from the ROADMAP', *q7_next()),
    ]
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f'old-name tidyup -- {now} -- repo: {ROOT}')
    print()
    print('| Q  | Question | Status | Answer |')
    print('| -- | -------- | ------ | ------ |')
    for q, question, status, answer in rows:
        print(f'| {q} | {question} | {status} | {answer} |')
    print()
    print('the town keeps. <3')
    return 0


# ------------------------------------------------------------------ map

def cmd_map(args) -> int:
    from old-name.maplab import main as maplab_main
    rest = args.map_args
    if args.map_cmd == 'validate':
        return maplab_main(['validate', '--pack', args.pack] + rest)
    if args.map_cmd == 'build':
        return maplab_main(['build', '--segments', args.segments,
                            '--pack', args.pack] + rest)
    if args.map_cmd == 'verify':
        return maplab_main(['verify', '--url', args.url] + rest)
    return 2


# --------------------------------------------------------------- deploy

def cmd_deploy(args) -> int:
    host = args.deploy_host
    url = args.url
    excludes = []
    for e in DEPLOY_EXCLUDES:
        excludes += ['--exclude', e]
    if sh(('rsync', '-a', '--delete', *excludes, f'{ROOT}/', f'{host}:~/old-name/')).returncode:
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
    from old-name.maplab import main as maplab_main
    ok = maplab_main(['verify', '--url', url])
    print('deployed. <3' if ok == 0 else 'deployed, but map verify flagged problems.')
    return ok


# --------------------------------------------------------------- backup

def cmd_backup(args) -> int:
    date = datetime.now(timezone.utc).strftime('%Y%m%d')
    name = f'old-name-{date}.bundle'
    tmp = Path('/tmp') / name
    if sh(('git', 'bundle', 'create', str(tmp), '--all')).returncode:
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
    cmd = ('uv', 'run', '--group', 'test', 'pytest', '-q') + tuple(args.test_args)
    return sh(cmd).returncode


# ----------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(prog='lab', description=__doc__)
    ap.add_argument('--url', default=DEFAULT_URL)
    ap.add_argument('--deploy-host', default=DEFAULT_DEPLOY_HOST)
    ap.add_argument('--nas-host', default=DEFAULT_NAS_HOST)
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('tidyup').set_defaults(fn=cmd_tidyup)

    pmap = sub.add_parser('map', help='map validate / build / verify')
    pmap_sub = pmap.add_subparsers(dest='map_cmd', required=True)
    mv = pmap_sub.add_parser('validate')
    mv.add_argument('--pack', default='worlds/private-canon')
    mv.set_defaults(fn=cmd_map)
    mb = pmap_sub.add_parser('build')
    mb.add_argument('--segments', required=True)
    mb.add_argument('--pack', default='worlds/private-canon')
    mb.add_argument('--force', action='store_true')
    mb.set_defaults(fn=cmd_map)
    mr = pmap_sub.add_parser('verify')
    mr.add_argument('--url', default=DEFAULT_URL)
    mr.set_defaults(fn=cmd_map)

    pd = sub.add_parser('deploy', help='ship this checkout to bazzite')
    pd.set_defaults(fn=cmd_deploy)

    pb = sub.add_parser('backup', help='git bundle -> NAS, rotate')
    pb.set_defaults(fn=cmd_backup)

    pt = sub.add_parser('test', help='pytest suite')
    pt.add_argument('test_args', nargs='*')
    pt.set_defaults(fn=cmd_test)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == '__main__':
    sys.exit(main())
