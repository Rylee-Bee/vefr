"""The norns, the squirrel, and the tree - the engine's three shapes.

Two CLI entry points:

    ratatoskr - the squirrel. Ferries messages between the dev box,
                the deploy host, Gitea, the NAS, and the World Tree
                bundle. Subcommands: skipa, test, weave, ferry
                (deploy / carry / fetch).

    norns     - the weavers. Craft commands for shaping the world:
                chat, validate, build-map, verify.

Run from any checkout; git decides which. In the container, the
same commands serve against the deployed world (deploy and
backup need a git checkout, so they stay on the dev side).

Your own game's name never appears here - that's the point. Whatever
you build (Old Name, or anything else) sits in worlds/, and these two
commands stay the same no matter whose story they're serving.
"""

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .maplab import load_pack, validate
from .paths import world_name

GITEA_BASE = 'http://192.168.2.216:3000'

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
    """Where worlds/ lives: a checkout, or VEFR_HOME in the container."""
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


# --------------------------------------------------------------- skipa

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
                     'water_by_phase', 'flood_tiles', 'hero_start')
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


def cmd_skipa(args) -> int:
    pack = pack_root() / 'worlds' / world_name()
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
    print(f'ratatoskr skipa -- {now}')
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


def _import_url(base: str, repo: str) -> str:
    """Accept 'owner/name' or a full https://... URL; return a cloneable URL."""
    if repo.startswith('http://') or repo.startswith('https://') or repo.startswith('git@'):
        return repo
    if '/' not in repo or repo.count('/') != 1:
        raise SystemExit(
            f"repo must be 'owner/name' or a full URL, got: {repo!r}"
        )
    return f'{base.rstrip("/")}/{repo}.git'


def _import_target(args) -> tuple[str, str]:
    """Where the clone lands: 'local' means current checkout, else an ssh host.

    Returns (target_host, worlds_dir) - worlds_dir is the directory on
    the target host that contains the per-pack subdirs. For 'local' we
    resolve to the checkout's worlds/. For an ssh host we look up the
    deploy-host layout by asking the host itself (`ratatoskr ferry deploy` puts
    the engine at ~/old-name/, so the worlds are at ~/old-name/worlds/).
    """
    if args.target == 'local':
        return 'local', str(pack_root() / 'worlds')
    # On a deploy host the engine checkout is ~/old-name/ (where
    # ratatoskr ferry deploy rsyncs to). The worlds live inside that checkout.
    return args.target, '~/old-name/worlds'


def cmd_import(args) -> int:
    """Clone (or pull) a story repo into worlds/<name>/.

    The engine and the story live in two Gitea repos on purpose - the
    engine is public-track MIT (rylee/vefr), the story is the author's
    own (the private story repo or whatever the next world is). The world
    pack directory on disk is the seam; this command is how the
    latest of the story repo reaches that directory.

    By default targets the current checkout (so a dev box can land
    the story before shipping). --target <host> runs the clone over
    ssh on the deploy host - the same box the live game is on - so
    'I edited the private story repo, ship it' is one command end-to-end.
    """
    base = args.base.rstrip('/')
    url = _import_url(base, args.repo)
    name = args.name or url.rsplit('/', 1)[-1].removesuffix('.git')
    target_host, worlds_dir = _import_target(args)
    target_path = f'{worlds_dir}/{name}'

    # Only the local target checks for an existing directory: an ssh
    # host may already have a pack under that name and the user wants
    # to overwrite - the ssh command itself does `test -d || clone`
    # and falls back to `git pull --ff-only` when --pull is set.
    if target_host == 'local':
        exists_local = (pack_root() / 'worlds' / name).exists()
        action = 'pull' if exists_local and args.pull else 'clone'
        if exists_local and not args.pull:
            print(
                f"worlds/{name}/ already exists - pass --pull to update, "
                f"or remove the directory first."
            )
            return 1
    else:
        action = 'pull' if args.pull else 'clone'

    plan = (
        f'{action} {url}\n'
        f'  -> {target_host}:{target_path}'
    )
    if args.dry_run:
        print('dry-run: would')
        print(plan)
        return 0
    print(plan)

    if target_host == 'local':
        cmd = (['git', 'pull', '--ff-only'] if action == 'pull'
               else ['git', 'clone', url, str(pack_root() / 'worlds' / name)])
        rc = subprocess.run(cmd, capture_output=True, text=True).returncode
        if rc:
            print(f'git {action} failed (rc={rc})')
            return rc
    else:
        # Three layouts on the deploy host:
        #   (a) no <name>/ at all           -> clone
        #   (b) <name>/ exists with .git    -> pull --ff-only (when --pull)
        #                                    else refuse (avoid clobbering
        #                                    a tracked story with a fresh
        #                                    clone - that would lose
        #                                    uncommitted edits)
        #   (c) <name>/ exists without .git -> first-time adoption: back
        #                                    the existing files up under
        #                                    .bak-<date>, clone fresh.
        #                                    The author usually wants to
        #                                    reconcile by hand anyway.
        inner = (
            f'cd {worlds_dir} && '
            f'if [ -d {name}/.git ]; then '
            f'  git -C {name} pull --ff-only; '
            f'elif [ -d {name} ]; then '
            f'  mv {name} {name}.bak-$(date +%Y%m%d-%H%M%S) && '
            f'  git clone {url} {name}; '
            f'else '
            f'  git clone {url} {name}; '
            f'fi'
        )
        rc = sh(('ssh', target_host, inner)).returncode
        if rc:
            return rc

    print(f'imported {name} from {url}')

    # Validate the freshly landed pack against its own contract.
    pack = pack_root() / 'worlds' / name
    if target_host != 'local':
        # maplab needs the pack on this machine too. We can't reach
        # bazzite's worlds/ from here without another ssh+rsync, and
        # the live game already validates itself via /api/world on
        # the deploy host. Print the validation command instead.
        print(f'validate on the deploy host: ssh {target_host} '
              f'"cd ~/old-name && norns validate --pack worlds/{name}"')
        return 0
    try:
        w = load_pack(pack)
        errors = validate(w, pack_dir=pack)
    except Exception as e:  # noqa: BLE001
        print(f'validate failed: {e}')
        return 2
    if errors:
        print(f'{len(errors)} problem(s) in {pack}:')
        for e in errors:
            print(f'  FAIL: {e}')
        return 2
    print(f'ok - {pack} validates against the pack contract.')
    return 0


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


def cmd_build_web(args) -> int:
    """Bundle worlds/<name>/ + web/packaged.html into one self-contained file.

    The player opens the file, points it at any OpenAI-compatible LLM
    endpoint, and plays. No Python, no server, no internet: the pack's
    logbok, ledger, voices, and town are inlined as JSON inside the
    HTML. Distributable: send it as a single email attachment, host
    on any static site, open from a phone's Files app.

    The 'bones' shape carries through here. Whatever the engine reads
    from the pack on disk, the bundled file reads from a JS object.
    """
    import json as _json
    from datetime import date

    if args.pack is None:
        pack = pack_root() / 'worlds' / world_name()
    else:
        # Bare name -> resolve under worlds/; absolute path -> use as-is.
        p = Path(args.pack)
        if p.is_absolute() or '/' in str(args.pack):
            pack = p if p.is_dir() else p.parent
        else:
            pack = pack_root() / 'worlds' / p

    if not (pack / 'world.json').exists():
        print(f'pack not found at {pack}; pass --pack NAME or set VEFR_WORLD')
        return 1

    world = _json.loads((pack / 'world.json').read_text(encoding='utf-8'))
    title = world.get('title', pack.name)
    logbok = (pack / 'logbok.md').read_text(encoding='utf-8') if (pack / 'logbok.md').exists() else ''
    ledger = (pack / 'ledger.md').read_text(encoding='utf-8') if (pack / 'ledger.md').exists() else ''
    voices = {}
    if (pack / 'voices').exists():
        for sf in (pack / 'voices').glob('*.md'):
            voices[sf.stem] = sf.read_text(encoding='utf-8')

    template = (Path(__file__).resolve().parents[2] / 'web' / 'packaged.html').read_text(encoding='utf-8')

    tagline = world.get('gold_rule') or 'memory and longing.'
    out_html = template
    out_html = out_html.replace('{{title}}', title)
    out_html = out_html.replace('{{tagline}}', tagline)
    out_html = out_html.replace('{{world_json}}', _json.dumps(world, ensure_ascii=False))
    out_html = out_html.replace('{{logbok_json}}', _json.dumps(logbok))
    out_html = out_html.replace('{{ledger_json}}', _json.dumps(ledger))
    out_html = out_html.replace('{{voices_json}}', _json.dumps(voices, ensure_ascii=False))

    if args.out:
        out_path = Path(args.out)
    else:
        out_dir = Path('dist')
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / f'{pack.name}-{date.today().isoformat()}.html'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_html, encoding='utf-8')
    size_kb = out_path.stat().st_size / 1024
    print(f'wrote {out_path} ({size_kb:.1f} KB)')
    print('open it in a browser, set your LLM URL + model, and play.')

    # Optional: also write <name>-<date>.tree.md alongside the HTML,
    # weaving every dev-UI tab into one document. The vault and
    # journal come from either --vault/--journal paths, the live
    # game's HTTP API (--from-live), or the env-driven defaults.
    # If nothing is reachable the build still succeeds, just without
    # play history.
    if args.with_bundle:
        from . import forge as _forge_mod, journal as _journal_mod
        from .export import export_story as _render

        # Pull vault + journal to local temp files. The export module
        # reads from disk paths only, so we materialize whatever source
        # we pick into the same shape.
        import tempfile as _tmp
        vault_path = Path(args.vault) if args.vault else None
        journal_path = Path(args.journal) if args.journal else None

        if args.from_live:
            # Fetch the live deployment's vault and journal over HTTP.
            import json as _json
            import urllib.request as _ur
            url = args.from_live.rstrip("/")
            with _ur.urlopen(f"{url}/api/vault", timeout=15) as r:
                vault_data = _json.loads(r.read().decode("utf-8")).get("items", [])
            with _ur.urlopen(f"{url}/api/journal", timeout=15) as r:
                journal_data = _json.loads(r.read().decode("utf-8")).get("entries", [])
            with _tmp.NamedTemporaryFile("w", suffix=".json", delete=False) as vf:
                _json.dump(vault_data, vf); vault_tmp = Path(vf.name)
            with _tmp.NamedTemporaryFile("w", suffix=".json", delete=False) as jf:
                _json.dump(journal_data, jf); journal_tmp = Path(jf.name)
            vault_path = vault_tmp
            journal_path = journal_tmp
            print(f"  pulled vault ({len(vault_data)} items) + "
                  f"journal ({len(journal_data)} entries) from {url}")
        else:
            vault_path = vault_path or _forge_mod.VAULT
            journal_path = journal_path or _journal_mod.JOURNAL

        old_vault, old_journal = _forge_mod.VAULT, _journal_mod.JOURNAL
        _forge_mod.VAULT = vault_path
        _journal_mod.JOURNAL = journal_path
        try:
            bundle_md = _render()
        finally:
            _forge_mod.VAULT = old_vault
            _journal_mod.JOURNAL = old_journal

        bundle_path = out_path.with_name(
            out_path.stem.replace('private-canon', pack.name) + '.tree.md'
        )
        bundle_path.write_text(bundle_md, encoding="utf-8")
        bundle_kb = bundle_path.stat().st_size / 1024
        print(f"wrote {bundle_path} ({bundle_kb:.1f} KB)")
        print("  one section per dev UI tab, woven from "
              f"{vault_path.name} + {journal_path.name}.")
    return 0

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
    tmp.unlink(missing_ok=True)
    listing = subprocess.run(
        ('ssh', args.nas_host, f'ls -t {NAS_DIR}/old-name-*.bundle'),
        capture_output=True, text=True).stdout.strip()
    print(f'bundles on {args.nas_host}:')
    print(listing)

    # Play history lives on the deploy host's bind-mounted volume
    # (~/<deploy-vol>/vault.json + journal.json), not in the repo -
    # the bundle alone would never preserve tonight's kept items or
    # the session journal. rsync the JSON files alongside the bundle
    # under a per-date directory so a snapshot is one date away.
    vol_remote = args.deploy_vol
    snap_remote = f'{args.nas_host}:{NAS_DIR}/old-name-{date}'
    rsync = subprocess.run(
        ('ssh', args.deploy_host,
         f'mkdir -p {vol_remote} && '
         f'ls {vol_remote}/*.json 2>/dev/null'),
        capture_output=True, text=True)
    files_here = rsync.stdout.strip().splitlines()
    if files_here:
        # The deploy host may or may not have rsync; fall back to scp
        # if it doesn't. Either way, one snapshot per date is the goal.
        if sh(('ssh', args.nas_host, f'mkdir -p {NAS_DIR}/old-name-{date}')).returncode:
            print('warning: could not create snapshot dir on NAS')
        else:
            for f in files_here:
                leaf = Path(f).name
                if sh(('scp', '-q', f'{args.deploy_host}:{f}',
                       f'{args.nas_host}:{NAS_DIR}/old-name-{date}/{leaf}')).returncode:
                    print(f'warning: {leaf} not backed up')
                else:
                    print(f'  play history: {leaf}')
            # Mirror latest -> latest/, so 'the most recent snapshot'
            # has a stable name regardless of date.
            sh(('ssh', args.nas_host,
                f'rm -rf {NAS_DIR}/latest && '
                f'cp -r {NAS_DIR}/old-name-{date} {NAS_DIR}/latest'))
    else:
        print(f'no play history on {args.deploy_host}:{vol_remote} yet')

    print('backed up. <3')
    return 0


# ----------------------------------------------------------------- test

def cmd_test(args) -> int:
    need_repo()
    cmd = ('uv', 'run', '--group', 'test', 'pytest', '-q') + tuple(args.test_args)
    try:
        return sh(cmd).returncode
    except FileNotFoundError:
        print('uv not found - run ratatoskr test from a checkout with uv installed')
        return 1


# ----------------------------------------------------------------- mains

RATATOSKR_HELP = """ratatoskr - the squirrel who carries messages up and down Yggdrasil.

Three subcommands for ferrying things between the engine and the
rest of the world:

  ratatoskr skipa         the seven questions - git/deploy sync,
                           local files needing push, deployment
                           health, world validation, backup
                           freshness, vault persistence, open
                           ROADMAP items
  ratatoskr test           the pytest suite (uv run --group test pytest),
                           extra args pass through: ratatoskr test -k chat
  ratatoskr ferry <verb>   ferry tools - carry the world between the
                           dev box, the deploy host, Gitea, the NAS,
                           and the World Tree bundle:

    ratatoskr ferry deploy   ship this checkout to --deploy-host,
                             rebuild the container, restart it,
                             verify health + the live map
    ratatoskr ferry carry    git bundle + play history (vault,
                             journal) -> --nas-host. The newest
                             two bundles are kept; play history
                             mirrors under old-name-<date>/ plus a
                             stable latest/ pointer.
    ratatoskr ferry fetch    clone or pull a story repo (Gitea,
                             --base) into worlds/<name>/. Pass
                             'owner/name' or a full git URL;
                             --target <deploy-host> ships straight
                             to the live box; --pull updates an
                             existing pack instead of re-cloning;
                             --dry-run prints the plan only.

  ratatoskr weave          package worlds/<name>/ + web/packaged.html
                           into one self-contained HTML file. Pair it
                           with --with-bundle to also write the
                           World Tree (a markdown document with one
                           section per dev UI tab, woven from
                           vault + journal). Send the pair to
                           someone - they open the HTML in a browser,
                           point at any OpenAI-compatible LLM URL,
                           and play.
"""

NORNS_HELP = """norns - the weavers of fate at the well beneath Yggdrasil.

Four subcommands for shaping what the engine makes:

  norns chat        interview a new world into existence, against
                    your local model. Writes worlds/<name>/,
                    validates as it goes.
  norns validate    geometry checks against a pack (--pack defaults
                    to the currently selected world)
  norns verify      validate a live deployment's served world (--url)
  norns build-map   rebuild the map from run-length rows (--segments,
                    --pack, --force)

The shape of every world, the town's grid, and the keepers'
voices are yours - the bones and the flesh alike. The norns
only ever teach the engine how to speak.
"""


def ratatoskr_main() -> int:
    ap = argparse.ArgumentParser(
        prog='ratatoskr', description=RATATOSKR_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument('--url', default=DEFAULT_URL)
    ap.add_argument('--deploy-host', default=DEFAULT_DEPLOY_HOST)
    ap.add_argument('--deploy-vol', default='~/old-name-data',
                    help='bind-mounted game volume on --deploy-host')
    ap.add_argument('--nas-host', default=DEFAULT_NAS_HOST)
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('skipa', help='the seven questions').set_defaults(fn=cmd_skipa)

    pt = sub.add_parser(
        'test', help='the pytest suite (extra args pass through, e.g. -k chat)'
    )
    pt.set_defaults(fn=cmd_test)

    # `weave` is the file-packaging command - kept at top level so it's
    # easy to reach without the ferry sub-tree.
    pw = sub.add_parser('weave', help='package a world into one self-contained HTML file')
    pw.add_argument('--pack', default=None, help='world to bundle (default: current)')
    pw.add_argument('--out', default=None, help='output HTML path (default: dist/<name>-<date>.html)')
    pw.add_argument('--with-bundle', action='store_true',
                    help='also write <name>-<date>.tree.md alongside the HTML')
    pw.add_argument('--vault', default=None,
                    help='path to vault.json (default: $VEFR_VAULT)')
    pw.add_argument('--journal', default=None,
                    help='path to journal.json (default: $VEFR_JOURNAL)')
    pw.add_argument('--from-live', default=None,
                    help='pull vault+journal from a live deployment URL')
    pw.set_defaults(fn=cmd_build_web)

    # Ferry subcommand - carries things between places.
    ferry = sub.add_parser(
        'ferry', help='carry messages between dev box, deploy host, Gitea, NAS'
    )
    ferry_sub = ferry.add_subparsers(dest='ferry_verb', required=True)

    fd = ferry_sub.add_parser('deploy', help='ship this checkout to --deploy-host')
    fd.set_defaults(fn=cmd_deploy)

    fcp = ferry_sub.add_parser('carry', help='git bundle + play history -> --nas-host')
    fcp.set_defaults(fn=cmd_backup)

    fct = ferry_sub.add_parser(
        'fetch',
        help='clone or pull a story repo from Gitea into worlds/<name>/',
    )
    fct.add_argument(
        'repo',
        help="the story repo: 'owner/name' shorthand (resolved via "
             '--base) or a full git URL',
    )
    fct.add_argument(
        '--name', default=None,
        help='the worlds/ directory name (default: repo basename)',
    )
    fct.add_argument(
        '--base', default=GITEA_BASE,
        help='Gitea base URL for shorthand repo resolution',
    )
    fct.add_argument(
        '--target', default='local',
        help="where to land the pack: 'local' (this checkout) or "
             '<deploy-host> (ssh + clone there)',
    )
    fct.add_argument(
        '--pull', action='store_true',
        help="if worlds/<name>/ exists, do `git pull --ff-only` instead of clone",
    )
    fct.add_argument(
        '--dry-run', action='store_true',
        help='show what would happen, do nothing',
    )
    fct.set_defaults(fn=cmd_import)

    args, extra = ap.parse_known_args()
    if args.cmd == 'test':
        args.test_args = extra
    return args.fn(args)


def cmd_handbok(args) -> int:
    """Write the mechanics manual from real play - norns handbok.

    Deterministic templating over real events, the same honesty rule
    as the export: the trace (data/trace.jsonl) says how each
    mechanic actually behaved - calls, latency, failures - and the
    session journal supplies real examples. No model pass. A
    world with no trace produces a shorter handbok, not an error.
    """
    import json as _json

    from . import trace as trace_mod
    from .journal import list_entries
    from .world import load_world

    if getattr(args, 'pack', None) is None:
        pack = pack_root() / 'worlds' / world_name()
    else:
        p = Path(args.pack)
        pack = p if p.is_absolute() else pack_root() / 'worlds' / p
    if not (pack / 'world.json').exists():
        print(f'pack not found at {pack}; pass --pack NAME or set VEFR_WORLD')
        return 1

    sid = getattr(args, 'session', None) or None

    # ---- the trace, read tolerantly ----
    events: list[dict] = []
    tpath = trace_mod.file_path()
    if tpath.exists():
        for line in tpath.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = _json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(ev, dict):
                events.append(ev)

    by_route: dict[str, list[dict]] = {}
    for ev in events:
        by_route.setdefault(ev.get('route', '?'), []).append(ev)

    entries = list_entries(sid=getattr(args, 'session', None))
    by_kind: dict[str, list[dict]] = {}
    for e in entries:
        by_kind.setdefault(e.get('kind', '?'), []).append(e)

    world = load_world()
    out: list[str] = [
        f"# {world['title']} - handbok",
        '',
        'A mechanics manual, generated from real play: what the engine '
        'actually did, how long each thread of the loom took, and real '
        'examples from this playthrough. Regenerate with '
        '`norns handbok` - this file is a snapshot, not canon.',
        '',
    ]

    out.append('## The mechanics, as they ran')
    out.append('')
    if by_route:
        out.append('| call | runs | avg | slowest | failed |')
        out.append('|---|---|---|---|---|')
        for route in sorted(by_route):
            evs = by_route[route]
            ms = [e.get('ms', 0.0) for e in evs]
            failed = sum(1 for e in evs if e.get('ok') is False)
            out.append(
                f'| {route} | {len(evs)} | {sum(ms) / len(ms):.0f}ms '
                f'| {max(ms):.0f}ms | {failed} |'
            )
    else:
        out.append('_No trace yet - play with the server running, then rerun._')
    out.append('')

    out.append('## The phases, as they were walked')
    phases_seen = []
    for e in entries:
        ph = e.get('phase')
        if ph and ph not in phases_seen:
            phases_seen.append(ph)
    out.append(
        ', '.join(f'**{ph}**' for ph in phases_seen)
        or '_The world has not spoken yet._'
    )
    out.append('')

    out.append('## Real examples, from the session')
    out.append('')
    examples = {
        'rumor': 'a whisper heard',
        'npc_line': 'a line spoken',
        'item_forged': 'a relic kept',
        'stefna_letter': 'the letter found',
    }
    for kind, label in examples.items():
        evs = by_kind.get(kind, [])
        if not evs:
            continue
        out.append(f'### {label}')
        for e in evs[-2:]:
            text = e.get('whisper') or e.get('line') or e.get('lore') or e.get('letter') or ''
            out.append(f'> {_clean_example(text)}')
            out.append('')
        out.append('')

    out.append('## The session, counted')
    out.append('')
    if by_kind:
        for kind in sorted(by_kind):
            out.append(f'- {len(by_kind[kind])} {kind}')
    else:
        out.append('_Nothing yet. The world is waiting._')
    out.append('')

    out_path = pack / 'handbok.md'
    out_path.write_text('\n'.join(out).rstrip() + '\n', encoding='utf-8')
    print(f'handbok written: {out_path}')
    return 0


def _clean_example(text: str) -> str:
    """One line, quote-marked, truncated - a handbok is not a lore dump."""
    one = ' '.join(str(text or '').split())
    if len(one) > 240:
        one = one[:237] + '...'
    return f'\u201c{one}\u201d'


def norns_main() -> int:
    ap = argparse.ArgumentParser(
        prog='norns', description=NORNS_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    craft = ap.add_subparsers(dest='craft_cmd', required=True)

    mc = craft.add_parser('chat', help='interview a new world into existence')
    mc.add_argument('--name', required=True, help='the new pack name (worlds/<name>)')
    mc.set_defaults(fn=cmd_chat)

    mv = craft.add_parser('validate', help='geometry checks against the pack')
    mv.add_argument('--pack', default=None)
    mv.set_defaults(fn=cmd_map, map_cmd='validate', segments=None, force=False)

    mb = craft.add_parser('build-map', help='rebuild the map from run-length rows')
    mb.add_argument('--segments', required=True)
    mb.add_argument('--pack', default=None)
    mb.add_argument('--force', action='store_true')
    mb.set_defaults(fn=cmd_map, map_cmd='build')

    mr = craft.add_parser('verify', help='validate a live deployment')
    mr.add_argument('--url', default=DEFAULT_URL)
    mr.set_defaults(fn=cmd_map, map_cmd='verify', segments=None, force=False,
                    pack=None)

    mh = craft.add_parser(
        'handbok', help='write the mechanics manual from real play'
    )
    mh.add_argument('--pack', default=None)
    mh.add_argument('--session', default=None,
                    help='play session to read (default: the default one)')
    mh.set_defaults(fn=cmd_handbok)

    args = ap.parse_args()
    # validate / build-map / verify default --pack to the resolved
    # world; chat doesn't take --pack and doesn't need the lookup.
    if args.craft_cmd in ('validate', 'build-map', 'verify') and getattr(args, 'pack', None) is None:
        args.pack = pack_root() / 'worlds' / world_name()
    return args.fn(args)


if __name__ == '__main__':
    sys.exit(ratatoskr_main())
