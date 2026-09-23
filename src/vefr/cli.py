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
story you point the engine at (your pack, someone else's, or none)
sits in worlds/, and these two commands stay the same no matter
whose story they're serving.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .maplab import load_pack, validate
from .paths import world_name

GITEA_BASE = os.environ.get('VEFR_GITEA_URL', 'http://localhost:3000')

DEFAULT_URL = os.environ.get('VEFR_LIVE_URL', 'http://127.0.0.1:8820')
DEFAULT_DEPLOY_HOST = os.environ.get(
    'VEFR_DEPLOY_HOST',
    os.environ.get('VEFR_DEFAULT_DEPLOY_HOST', ''),
)
DEFAULT_BACKUP_LOCATION = os.environ.get(
    'VEFR_DEFAULT_BACKUP_LOCATION', '')
DEFAULT_BACKUP_HOST, _, NAS_DIR = DEFAULT_BACKUP_LOCATION.partition(':')

# Engine-shipped pack names: when one of these sits in the deploy
# host's rw bind (~/vefr-worlds/), it shadows the freshly built
# template and the running pack goes stale on every engine update
# (the 2026-09-01 deploy-day find).
ENGINE_PACKS = ('sample-world', 'lore')


def _deploy_toml(root: Path | None = None) -> dict:
    """deploy.toml - the per-host twin of deploy.toml.example - read
    with stdlib tomllib. The wrapper consumes it so the file is
    load-bearing config instead of documentation: host and image
    resolve from here whenever --flags and env are silent, and
    norns doctor falls back to its url for the live check. A
    missing or malformed file is an empty dict - a bad toml must
    never take the deploy path down."""
    base = root or repo_root() or Path.cwd()
    p = base / 'deploy.toml'
    if not p.exists():
        return {}
    try:
        import tomllib
        return tomllib.loads(p.read_text(encoding='utf-8'))
    except Exception:  # noqa: BLE001 - broken config, not a broken deploy
        return {}
if not DEFAULT_BACKUP_LOCATION:
    # No silent defaults. Carry refuses to ssh an empty host and the
    # operator must declare VEFR_DEFAULT_BACKUP_LOCATION or pass
    # --nas-host + --backup-path. The deploy wrapper has the same
    # fail-closed shape (see cmd_deploy near line 747).
    DEFAULT_BACKUP_HOST, NAS_DIR = '', ''
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
        return 'unavailable', 'no git checkout (container install)'
    status = git_quiet('status', '--porcelain')
    dirty = len(status.splitlines()) if status else 0
    stashes = len(git_quiet('stash', 'list').splitlines())
    if dirty or stashes:
        return 'dirty', f'{dirty} uncommitted file(s), {stashes} stash(es)'
    # The reading row's fonts are tracked since 2026-09-01; an empty
    # web/fonts/ means the woff2 binaries never landed - the panel
    # 404s silently and the packaged file ships without them.
    fonts_dir = repo_root() / 'web' / 'fonts'
    have = len(list(fonts_dir.glob('*.woff2'))) if fonts_dir.is_dir() else 0
    fonts = f'fonts {have}/4' if have < 4 else 'fonts ok'
    return 'clean', f'0 uncommitted, 0 stashes; {fonts}'


def q3_deployment(url: str, deploy_host: str | None = None) -> tuple:
    try:
        h = fetch(f'{url.rstrip("/")}/api/health')
        if not (h.get('ok') and 'purpose' in h):
            return 'degraded', f'unexpected health payload: {h}'
    except Exception as e:  # noqa: BLE001
        return 'down', f'{url}: {e}'
    # The shadow check: an engine-shipped pack in the deploy host's
    # rw bind hides the freshly built template, so the running pack
    # goes stale on every engine update. A green deploy that serves
    # old content is worse than a red one.
    if not deploy_host:
        return 'healthy', 'container up, motto present'
    try:
        out = subprocess.run(
            ('ssh', '-o', 'ConnectTimeout=6', deploy_host,
             'ls ~/vefr-worlds/ 2>/dev/null'),
            capture_output=True, text=True, timeout=15).stdout.split()
    except Exception as e:  # noqa: BLE001
        return 'healthy', f'container up, motto present (shadow check skipped: {e})'
    shadowed = [p for p in out if p in ENGINE_PACKS]
    if shadowed:
        return ('shadowed',
                f'container up, but engine pack(s) {", ".join(shadowed)} in '
                f'~/vefr-worlds/ shadow the template - move them aside and '
                f'restart, or the running pack goes stale')
    return 'healthy', 'container up, motto present, no pack shadows'


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
             f'ls -t {NAS_DIR}/vefr-*.bundle 2>/dev/null | head -1'),
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
             'ls ~/vefr-data/ 2>/dev/null | wc -l'),
            capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return 'unverified', f'ssh failed: {e}'
    n = out.splitlines()[-1] if out else '0'
    return 'persisted', f'~/vefr-data present ({n} entries)'


def q7_next(pack: Path) -> tuple:
    root = pack.parent.parent
    roadmap = root / 'ROADMAP.md'
    if not roadmap.exists():
        return 'unknown', 'no ROADMAP.md in this install'
    text = roadmap.read_text(encoding='utf-8')
    if '## Next' not in text:
        return 'unknown', 'no ## Next section in ROADMAP.md'
    nxt = text.split('## Next')[1].split('## ')[0]
    items = [ln.strip()[6:] for ln in nxt.splitlines() if ln.strip().startswith('- [ ]')]
    short = [i.split(':')[0].strip('**').strip() for i in items]
    return 'open', f'{len(items)} open: {"; ".join(short)}'


def cmd_skipa(args) -> int:
    pack = pack_root() / 'worlds' / world_name()
    url = args.url
    if url == DEFAULT_URL:
        # The silent default is the dev box itself, not the deploy
        # host. deploy.toml's url is the declared live endpoint.
        url = _deploy_toml().get('url') or url
    rows = [
        ('Q1', 'git local + Gitea remote in sync', *q1_sync()),
        ('Q2', 'local files needing push', *q2_dirty()),
        ('Q3', 'deployment healthy (bazzite)',
         *q3_deployment(url, args.deploy_host)),
        ('Q4', 'the world validated (pack + live)', *q4_world(url, pack)),
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


def cmd_migrate(args) -> int:
    """Migrate a flat-shape world pack to the acts tree.

    A flat pack has its `town`, `speakers`, and `map.md` at the
    top level. The acts shape splits these into per-region
    directories under `acts/<id>/<region>/`. The migrator
    creates the acts tree and rewrites `world.json` to the
    pack-level contract; the flat `town` data moves into
    `acts/<id>/town/` (a `town/contract.json` is written for
    town metadata; `map.md` is the walkable grid; `voices/`
    is the auto-discovered region voices).

    This is the safe path for the author's own canon: the
    migration is a copy, not a destructive move, and the engine
    supports both on-disk shapes indefinitely.
    """
    import json
    import shutil

    pack_name = args.pack
    src = pack_root() / 'worlds' / pack_name
    if not (src / 'world.json').exists():
        print(f'pack not found: {src}')
        return 1
    if (src / 'acts').is_dir():
        print(f'{src} is already in the acts shape - nothing to migrate')
        return 0
    config = json.loads((src / 'world.json').read_text(encoding='utf-8'))
    if 'town' not in config:
        print(f'{src} has no `town` block - is this a flat pack?')
        return 1

    acts_root = src / 'acts' / (args.act_id or 'act-1')
    town_dir = acts_root / 'town'
    town_dir.mkdir(parents=True, exist_ok=True)

    # town contract: every town-metadata field except `map` and
    # `voices` (those move into separate files). The canary shape.
    town_block = config['town']
    town_contract = {k: v for k, v in town_block.items()
                     if k not in ('map',)}
    act_contract = {
        'id': acts_root.name,
        'title': config.get('title', src.name),
        'regions': ['town'],
        'town': town_contract,
        'speakers': config.get('speakers', {}),
        'enemies': config.get('enemies', []),
        'bosses': config.get('bosses', []),
        'transitions': config.get('transitions', []),
    }
    (acts_root / 'world.json').write_text(
        json.dumps(act_contract, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    # map.md: the walkable grid as a plain text file.
    if town_block.get('map'):
        (town_dir / 'map.md').write_text(
            '\n'.join(town_block['map']) + '\n',
            encoding='utf-8',
        )

    # voices/: move any existing pack-level voices into the
    # region's voices dir. The loader discovers them by
    # convention; voice_file paths in the speaker contract
    # still resolve via resolve_voice_file().
    src_voices = src / 'voices'
    if src_voices.is_dir():
        dst_voices = town_dir / 'voices'
        dst_voices.mkdir(parents=True, exist_ok=True)
        for vf in src_voices.glob('*.md'):
            shutil.copy2(vf, dst_voices / vf.name)

    # Rewrite the pack-level world.json: keep metadata + canon,
    # remove town/speakers/map (they're in the act now).
    pack_contract = {
        k: v for k, v in config.items()
        if k not in ('town', 'speakers', 'enemies', 'bosses', 'transitions')
    }
    (src / 'world.json').write_text(
        json.dumps(pack_contract, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    # Validate the migrated pack end-to-end. We pass the absolute
    # pack path so tests (which monkeypatch pack_root) work, and
    # the production path resolves the same way through pack_root.
    from .maplab import load_pack as _load_pack
    from .maplab import validate as _validate
    unified = _load_pack(src)
    errors = _validate(unified, pack_dir=src)
    if errors:
        print(f'migrated but validation flagged {len(errors)} issue(s):')
        for e in errors:
            print(f'  FAIL: {e}')
        return 2
    print(f'migrated {src} to the acts shape - '
          f'{acts_root}/, {town_dir}/, pack-level world.json rewritten.')
    print('validates against the engine contract.')
    return 0


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
    the engine at ~/vefr/, so the worlds are at ~/vefr/worlds/).
    """
    if args.target == 'local':
        return 'local', str(pack_root() / 'worlds')
    # On a deploy host the engine checkout is ~/vefr/ (where
    # ratatoskr ferry deploy rsyncs to). The worlds live inside that checkout.
    return args.target, '~/vefr/worlds'


def cmd_import(args) -> int:
    """Clone (or pull) a story repo into worlds/<name>/.

    The engine and the story live in two Gitea repos on purpose - the
    engine is public-track MIT (rylee/vefr), the story is your own
    story pack. The world pack directory on disk is the seam; this command
    is how the latest of the story repo reaches that directory.

    By default targets the current checkout (so a dev box can land
    the story before shipping). --target <host> runs the clone over
    ssh on the deploy host - the same box the live game is on - so
    'I edited my story pack, ship it' is one command end-to-end.
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
              f'"cd ~/vefr && norns validate --pack worlds/{name}"')
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


def _template_candidates() -> list[Path]:
    """Where web/packaged.html may live, in preference order.

    A source checkout has it at the repo root. A pip-installed wheel
    ships it as package data (hatch force-include: vefr/web/), which
    is what a pack author's repo sees when it runs `ratatoskr weave`
    against an installed engine. Container installs keep it under
    VEFR_HOME. Try all three and prefer whichever actually exists.
    """
    from .paths import app_home

    here = Path(__file__).resolve()
    return [
        here.parents[2] / 'web' / 'packaged.html',   # source checkout
        here.parent / 'web' / 'packaged.html',        # wheel package data
        app_home() / 'web' / 'packaged.html',         # container / VEFR_HOME
    ]


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

    # The player template reads town geometry, speakers, and creed off
    # VEFR_WORLD - all three live in acts/<id>/ for an acts-shape pack
    # and are invisible to the raw root file (a raw-only bake left the
    # town canvas blank and the tagline on its generic default).
    # load_pack is the validator's unified shape; it carries the
    # gold_rule read-fallback through creed_from, and raw root fields
    # ride along underneath.
    world = {
        **_json.loads((pack / 'world.json').read_text(encoding='utf-8')),
        **load_pack(pack),
    }
    # The packaged player reads the acts contract (verbs, floor,
    # tone, ruleset, cooking) straight off the baked world. The
    # validator's unified shape doesn't carry acts, so pull them
    # from the loader when the pack resolves under a worlds root;
    # packs woven from elsewhere keep the old behavior (defaults).
    if not world.get('acts'):
        from .world import load_world as _load_world
        try:
            loaded = _load_world(pack)
        except Exception:
            loaded = {}
        if loaded.get('acts'):
            world['acts'] = loaded['acts']
            world.setdefault('_current_act', 0)
    title = world.get('title', pack.name)
    logbok = (pack / 'logbok.md').read_text(encoding='utf-8') if (pack / 'logbok.md').exists() else ''
    ledger = (pack / 'ledger.md').read_text(encoding='utf-8') if (pack / 'ledger.md').exists() else ''
    voices = {}
    if (pack / 'voices').exists():
        for sf in (pack / 'voices').glob('*.md'):
            if sf.name.endswith('.fragments.md'):
                continue
            voices[sf.stem] = sf.read_text(encoding='utf-8')
    # The offline whisper banks: per-speaker fragments the composer
    # re-splices when a package has no pool and no model. The same
    # convention walk as voice discovery (pack root + act regions).
    from .world import fragments_for_pack
    fragments = fragments_for_pack(pack)

    template_candidates = _template_candidates()
    template_path = next(
        (p for p in template_candidates if p.exists()), template_candidates[0])
    template = template_path.read_text(encoding='utf-8')

    tagline = world.get('creed') or 'the loom is strung; the world provides the thread.'
    out_html = template
    out_html = out_html.replace('{{title}}', title)
    out_html = out_html.replace('{{tagline}}', tagline)
    out_html = out_html.replace('{{world_json}}', _json.dumps(world, ensure_ascii=False))
    out_html = out_html.replace('{{logbok_json}}', _json.dumps(logbok))
    out_html = out_html.replace('{{ledger_json}}', _json.dumps(ledger))
    out_html = out_html.replace('{{voices_json}}', _json.dumps(voices, ensure_ascii=False))
    out_html = out_html.replace('{{fragments_json}}', _json.dumps(fragments, ensure_ascii=False))

    # The woven pool: real generations baked into the file, so a
    # player with no LLM endpoint still hears the world. Zero by
    # default - the pool costs real generation time at weave.
    pool = {}
    pool_n = getattr(args, 'pool', 0) or 0
    if pool_n:
        import os as _os

        from . import pool as pool_mod

        old_world_env = _os.environ.get('VEFR_WORLD')
        pool_mod.ensure_current_world(pack.name)
        try:
            print(f'weaving the pool: ~{pool_n} real generations per '
                  'combination - this takes a few minutes against the '
                  'live model...')
            pool = pool_mod.build_pool(
                samples=pool_n,
                pack_name=pack,
                progress=lambda combo, count: print(f'  {combo}: {count}'),
            )
        finally:
            # The weave is a visitor in this world - put back whichever
            # world the author had selected before it started.
            if old_world_env is None:
                _os.environ.pop('VEFR_WORLD', None)
            else:
                _os.environ['VEFR_WORLD'] = old_world_env
        total = sum(len(v) for v in pool.values())
        print(f'pool woven: {total} lines across {len(pool)} combinations')
    out_html = out_html.replace('{{pool_json}}', _json.dumps(pool, ensure_ascii=False))

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
                _json.dump(vault_data, vf)
                vault_tmp = Path(vf.name)
            with _tmp.NamedTemporaryFile("w", suffix=".json", delete=False) as jf:
                _json.dump(journal_data, jf)
                journal_tmp = Path(jf.name)
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

        bundle_path = out_path.with_name(out_path.stem + '.tree.md')
        bundle_path.write_text(bundle_md, encoding="utf-8")
        bundle_kb = bundle_path.stat().st_size / 1024
        print(f"wrote {bundle_path} ({bundle_kb:.1f} KB)")
        print("  one section per dev UI tab, woven from "
              f"{vault_path.name} + {journal_path.name}.")
    return 0

def cmd_deploy(args) -> int:
    """Ship this checkout to the deploy host.

    Behavior, in order:

      1. `--init` writes deploy.toml.example + the deploy guide,
         then exits. Does not touch the deploy host.
      2. Resolve the deploy host from --deploy-host / env. Refuse
         to run with the silent 'bazzite' default; force the user
         to declare their topology.
      3. Pre-flight (unless --skip-tests): the pytest suite +
         `norns validate --pack sample-world`. A broken main never
         reaches bazzite.
      4. rsync the checkout (DEPLOY_EXCLUDES hides .venv, caches,
         .git).
      5. `podman build` UNLESS the remote image's `vefr.engine_sha`
         label already matches the local HEAD (--rebuild forces it).
      6. `systemctl --user restart vefr` + ensure the ro/rw named
         volumes exist.
      7. /api/health probe + `maplab verify` (unless --no-health).

    Image name is `VEFR_DEPLOY_IMAGE` (default `localhost/vefr:latest`).
    The remote SHA check reads the `vefr.engine_sha` label that the
    Containerfile writes so a no-op deploy is one rsync + one
    restart, not a full image rebuild.
    """
    root = need_repo()

    if args.init:
        return _deploy_init(root)

    cfg = _deploy_toml(root)
    host = args.deploy_host
    declared_env = bool(os.environ.get('VEFR_DEPLOY_HOST'))
    declared_toml = 'host' in cfg
    if host == DEFAULT_DEPLOY_HOST and not declared_env and declared_toml:
        # --flag and env are silent: deploy.toml is the third voice.
        host = cfg['host']
    if not host and not declared_env and not declared_toml:
        # The silent default of 'bazzite' was a leak: a fresh
        # checkout would `ssh bazzite` and explode against a host
        # it cannot resolve. Force the operator to declare.
        print(
            'refusing to deploy: the deploy host is not declared.\n'
            '\n'
            '  export VEFR_DEPLOY_HOST=<your-host-or-ssh-alias>\n'
            '  uv run ratatoskr ferry deploy\n'
            '\n'
            'First time?  `uv run ratatoskr ferry deploy --init` writes\n'
            'deploy.toml.example + docs/guides/deploy.md to this checkout,\n'
            'or add host = "<your-host>" to deploy.toml.'
        )
        return 2

    url = args.url
    image = (os.environ.get('VEFR_DEPLOY_IMAGE')
             or cfg.get('image') or 'localhost/vefr:latest')

    if not args.skip_tests:
        if sh(('uv', 'run', '--group', 'test', 'pytest', '-q')).returncode:
            print('pre-flight: pytest failed; refusing to deploy')
            return 1
        if sh(('uv', 'run', '--group', 'test', 'norns', 'validate',
               '--pack', 'sample-world')).returncode:
            print('pre-flight: sample-world validate failed; refusing to deploy')
            return 1

    excludes = []
    for e in DEPLOY_EXCLUDES:
        excludes += ['--exclude', e]
    if sh(('rsync', '-a', '--delete', *excludes, f'{root}/',
           f'{host}:~/vefr/')).returncode:
        return 1

    if not args.rebuild:
        head_sha = subprocess.run(('git', '-C', str(root), 'rev-parse', 'HEAD'),
                                  capture_output=True, text=True).stdout.strip()
        inspect = subprocess.run(
            ('ssh', host, f'podman inspect --format "{{{{index .Config.Labels \\"vefr.engine_sha\\"}}}}" {image}'),
            capture_output=True, text=True)
        remote_sha = inspect.stdout.strip()
        if remote_sha and remote_sha == head_sha:
            print(f'image {image} already at HEAD ({head_sha[:12]}); skipping build')
        else:
            args.rebuild = True  # fall through to build below

    if args.rebuild:
        head_sha = subprocess.run(('git', '-C', str(root), 'rev-parse', 'HEAD'),
                                  capture_output=True, text=True).stdout.strip()
        if sh(('ssh', host,
               f'cd ~/vefr && podman build -q -t {image} '
               f'--build-arg ENGINE_SHA={head_sha} .')).returncode:
            return 1
    if sh(('ssh', host, 'systemctl --user restart vefr')).returncode:
        return 1

    # The ro + rw volumes may not exist on a fresh deploy host. The
    # engine boots fine without them (the image ships the template
    # at /app/worlds-template/ and an empty /app/worlds/), but the
    # canonical post-deploy state is both volumes present. Create
    # them so a `ratatoskr volumes list` from the deploy host shows
    # the right shape.
    sh(('ssh', host,
        'podman volume exists vefr-template 2>/dev/null || '
        'podman volume create vefr-template'))
    sh(('ssh', host,
        'podman volume exists vefr-worlds 2>/dev/null || '
        'podman volume create vefr-worlds'))

    if args.no_health:
        print('deployed (health check skipped). <3')
        return 0

    # Probe the deploy via an SSH-tunnelled localhost when the
    # operator didn't pass --url. This avoids depending on the dev
    # box's local DNS or /etc/hosts for the deploy host (the
    # "bazzite alias resolved to 192.168.2.145" failure mode).
    import os as _os
    if url == DEFAULT_URL:
        local_port = '8820'
        ssh_args = ('ssh', '-o', 'ExitOnForwardFailure=yes',
                    '-L', f'{local_port}:127.0.0.1:8820', host)
        # No `-f`: ssh must stay in the foreground of this Popen so
        # the finally below can actually terminate it. `-fN` forks
        # past the captured pid, and every tunnel outlived its
        # deploy (the 2026-09-01 orphaned-tunnel find).
        forward = subprocess.Popen(('ssh', '-N', *ssh_args[1:]))
        try:
            probe_url = f'http://127.0.0.1:{local_port}'
        except Exception:
            forward.terminate()
            raise
        try:
            h = _wait_for_health(probe_url)
            print(f'health (via tunnel): {h}')
            from .maplab import main as maplab_main
            ok = maplab_main(['verify', '--url', probe_url])
            print('deployed. <3' if ok == 0
                  else 'deployed, but map verify flagged problems.')
            return ok
        finally:
            subprocess.run(('ssh', '-O', 'exit', host),
                           capture_output=True)
            try:
                _os.kill(forward.pid, 0)
            except (ProcessLookupError, OSError):
                pass
            forward.terminate()
    else:
        h = _wait_for_health(url)
        print(f'health: {h}')
        from .maplab import main as maplab_main
        ok = maplab_main(['verify', '--url', url])
        print('deployed. <3' if ok == 0
              else 'deployed, but map verify flagged problems.')
        return ok


def _wait_for_health(url: str, attempts: int = 20, delay: float = 1.5) -> str:
    """Poll /api/health up to `attempts` times, sleeping `delay` between.

    A fresh uvicorn + FastAPI cold start takes ~5-10s; the old fixed
    2s sleep gave up before the server was actually listening.
    Raises the last urllib error on exhaustion.
    """
    import time as _time
    last_err: Exception | None = None
    for _ in range(attempts):
        try:
            return fetch(f'{url.rstrip("/")}/api/health')
        except Exception as e:  # noqa: BLE001
            last_err = e
            _time.sleep(delay)
    raise RuntimeError(
        f'health check never went green after {attempts * delay:.0f}s: {last_err}'
    )


def _deploy_init(root: Path) -> int:
    """Write deploy.toml.example + docs/guides/deploy.md scaffolding.

    Idempotent: refuses to overwrite an existing deploy.toml.example
    unless --force is passed (currently via the CLI). Prints the
    next-step commands.
    """
    target = root / 'deploy.toml.example'
    if target.exists():
        print(f'{target} already exists; remove it first or pass --force.')
        return 1
    target.write_text(_DEPLOY_TOML_EXAMPLE, encoding='utf-8')
    print(f'wrote {target}')
    print('next:')
    print(f'  cp {target} {root / "deploy.toml"}')
    print(f'  edit {root / "deploy.toml"} to match your host')
    print(f'  export VEFR_DEPLOY_HOST=$(grep ^host {root / "deploy.toml"} | cut -d\\" -f2)')
    print('  uv run ratatoskr ferry deploy --skip-tests   # smoke test')
    return 0


_DEPLOY_TOML_EXAMPLE = '''\
# vefr deploy configuration (example - rename to deploy.toml and edit)
#
# This file is read by YOU; ratatoskr ferry deploy reads from
# environment variables. The convention below lets you keep your
# host + image names in one place and export them with one shell
# snippet. deploy.toml itself is gitignored.
#
# Required:
#   host   - SSH alias or user@host reachable from this dev box.
#            Must be reachable as `ssh <host>` without arguments.
#   image  - the podman image name/tag the quadlet runs. Defaults
#            to localhost/vefr:latest.
#
# Optional:
#   url    - the engine's HTTP endpoint (used for /api/health +
#            maplab verify after deploy). Defaults to
#            http://<host>:8820.

host  = "deploy-host"
image = "localhost/vefr:latest"
url   = "http://deploy-host:8820"
'''


# --------------------------------------------------------------- backup

def cmd_backup(args) -> int:
    root = need_repo()
    date = datetime.now(timezone.utc).strftime('%Y%m%d')
    name = f'vefr-{date}.bundle'
    tmp = Path('/tmp') / name
    if sh(('git', '-C', str(root), 'bundle', 'create', str(tmp), '--all')).returncode:
        return 1
    if sh(('scp', '-q', str(tmp), f'{args.nas_host}:{NAS_DIR}/{name}')).returncode:
        return 1
    # Clean up old bundles, preserving both historical
    # and current (vefr-*) bundles up to BUNDLE_KEEP.
    sh(('ssh', args.nas_host,
        f'cd {NAS_DIR} && ls -t vefr-*.bundle 2>/dev/null '
        f'| tail -n +{BUNDLE_KEEP + 1} | xargs -r rm -f'))
    tmp.unlink(missing_ok=True)
    listing = subprocess.run(
        ('ssh', args.nas_host, f'ls -t {NAS_DIR}/vefr-*.bundle'),
        capture_output=True, text=True).stdout.strip()
    print(f'bundles on {args.nas_host}:')
    print(listing)

    # Play history lives on the deploy host's bind-mounted volume
    # (~/<deploy-vol>/vault.json + journal.json), not in the repo -
    # the bundle alone would never preserve tonight's kept items or
    # the session journal. rsync the JSON files alongside the bundle
    # under a per-date directory so a snapshot is one date away.
    vol_remote = args.deploy_vol
    rsync = subprocess.run(
        ('ssh', args.deploy_host,
         f'mkdir -p {vol_remote} && '
         f'ls {vol_remote}/*.json 2>/dev/null'),
        capture_output=True, text=True)
    files_here = rsync.stdout.strip().splitlines()
    if files_here:
        # The deploy host may or may not have rsync; fall back to scp
        # if it doesn't. Either way, one snapshot per date is the goal.
        if sh(('ssh', args.nas_host, f'mkdir -p {NAS_DIR}/vefr-{date}')).returncode:
            print('warning: could not create snapshot dir on NAS')
        else:
            for f in files_here:
                leaf = Path(f).name
                if sh(('scp', '-q', f'{args.deploy_host}:{f}',
                       f'{args.nas_host}:{NAS_DIR}/vefr-{date}/{leaf}')).returncode:
                    print(f'warning: {leaf} not backed up')
                else:
                    print(f'  play history: {leaf}')
            # Mirror latest -> latest/, so 'the most recent snapshot'
            # has a stable name regardless of date.
            sh(('ssh', args.nas_host,
                f'rm -rf {NAS_DIR}/latest && '
                f'cp -r {NAS_DIR}/vefr-{date} {NAS_DIR}/latest'))
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

Subcommands for ferrying things between the engine and the
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
                             mirrors under vefr-<date>/ plus a
                             stable latest/ pointer.
    ratatoskr ferry fetch    clone or pull a story repo (Gitea,
                             --base) into worlds/<name>/. Pass
                             'owner/name' or a full git URL;
                             --target <deploy-host> ships straight
                             to the live box; --pull updates an
                             existing pack instead of re-cloning;
                             --dry-run prints the plan only.

  ratatoskr spark         the resident small brain and its service:

    ratatoskr spark install  acquire the pinned model (verified by
                             size + sha256), install + start the
                             quadlet, wire VEFR_SPARK_URL into the
                             engine, wait for health, smoke test.
                             --profile quality (Phi-4-mini Q4_K_M,
                             default) or tiny (Qwen3.5-0.8B Q8_0).
    ratatoskr spark status   model verified? service active? health?
    ratatoskr spark smoke    four functional probes through the live
                             engine's /api/spark routes: health,
                             NPC JSON, state-edit preservation,
                             escalation judgment.

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

Subcommands for shaping what the engine makes:

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


# --------------------------------------------------------------- volumes

def cmd_volumes_list(args) -> int:
    """List every pack the engine can see, with the source tagged.

    Source is 'canon' (rw volume, author-owned) or 'template'
    (ro volume, engine-owned). The same list the builder UI
    uses, in human-readable form.
    """
    from . import volumes as vol_mod
    rows = vol_mod.list_packs()
    if not rows:
        print("no packs found")
        return 0
    print(f"{'pack':<24} {'source':<10} path")
    print(f"{'----':<24} {'------':<10} ----")
    for r in rows:
        print(f"{r['name']:<24} {r['source']:<10} {r['path']}")
    return 0


def cmd_volumes_migrate(args) -> int:
    """Split a legacy ~/vefr-worlds/ bind mount into ro + rw
    Docker volumes. Idempotent; safe to re-run.
    """
    from . import volumes as vol_mod
    legacy = Path(args.legacy_root).expanduser() if args.legacy_root else None
    return vol_mod.migrate(legacy_root=legacy, dry_run=args.dry_run)


def cmd_volumes_export(args) -> int:
    """Export a pack to a host-side git repo for editing.

    The destination gets the pack's full file tree in
    engine-native layout (acts or flat), plus a README and
    an initial commit. After editing + committing, run
    `volumes import --pack <name> --from <dest>` to write
    the change back into the engine's volume.
    """
    from . import volumes as vol_mod
    return 0 if vol_mod.export_pack(
        args.pack, Path(args.dest).expanduser().resolve(),
        init_git=not args.no_git,
    ) else 1


def cmd_volumes_import(args) -> int:
    """Import a pack from a host-side directory into the volume.

    Validates the source via the engine's loader first; rejects
    packs that wouldn't pass maplab. Then copies the tree into
    the rw volume (or the dev-box engine checkout).
    """
    from . import volumes as vol_mod
    try:
        vol_mod.import_pack(
            args.pack, Path(args.from_path).expanduser().resolve(),
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        print(f"import failed: {e}")
        return 1
    return 0


def cmd_volumes_shell(args) -> int:
    """Drop into a shell inside the engine container.

    `--pack <name>` cds into the pack's volume path. No shell
    on the dev box; this is a bazzite/deploy-host convenience.
    """
    from . import volumes as vol_mod
    return vol_mod.shell(args.pack)


def ratatoskr_main() -> int:
    ap = argparse.ArgumentParser(
        prog='ratatoskr', description=RATATOSKR_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument('--url', default=DEFAULT_URL)
    ap.add_argument('--deploy-host', default=DEFAULT_DEPLOY_HOST)
    ap.add_argument('--deploy-vol', default='~/vefr-data',
                    help='bind-mounted game volume on --deploy-host')
    ap.add_argument('--nas-host', default=DEFAULT_BACKUP_HOST)
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
    pw.add_argument('--pool', type=int, default=0, metavar='N',
                    help='pre-generate N real outputs per mechanic/phase/'
                         'speaker combination and bake them into the file '
                         'as the offline fallback pool (needs a live model)')
    pw.add_argument('--from-live', default=None,
                    help='pull vault+journal from a live deployment URL')
    pw.set_defaults(fn=cmd_build_web)

    # Ferry subcommand - carries things between places.
    ferry = sub.add_parser(
        'ferry', help='carry messages between dev box, deploy host, Gitea, NAS'
    )
    ferry_sub = ferry.add_subparsers(dest='ferry_verb', required=True)

    # Volumes subcommand - manage the ro/rw volume split on the
    # deploy host. `list` shows what's loaded; `migrate` does the
    # one-shot split of a legacy bind mount.
    volumes = sub.add_parser(
        'volumes',
        help='manage the ro template + rw canon Docker volumes',
    )
    volumes_sub = volumes.add_subparsers(dest='volumes_verb', required=True)
    volumes_list = volumes_sub.add_parser(
        'list', help='list every pack the engine can see'
    )
    volumes_list.set_defaults(fn=cmd_volumes_list)
    volumes_migrate = volumes_sub.add_parser(
        'migrate', help='split a legacy ~/vefr-worlds/ bind into ro+rw volumes'
    )
    volumes_migrate.add_argument(
        '--legacy-root', default=None,
        help='legacy worlds root (default: ~/vefr-worlds)',
    )
    volumes_migrate.add_argument(
        '--dry-run', action='store_true',
        help='print what would happen; do nothing',
    )
    volumes_migrate.set_defaults(fn=cmd_volumes_migrate)

    volumes_export = volumes_sub.add_parser(
        'export',
        help='export a pack to a host-side git repo for editing in vim',
    )
    volumes_export.add_argument('--pack', required=True,
                                 help='the world pack to export')
    volumes_export.add_argument('--dest', required=True,
                                 help='destination directory (created if missing)')
    volumes_export.add_argument('--no-git', action='store_true',
                                 help='skip the git init / initial commit')
    volumes_export.set_defaults(fn=cmd_volumes_export)

    volumes_import = volumes_sub.add_parser(
        'import',
        help='import a pack from a host-side directory into the rw volume',
    )
    volumes_import.add_argument('--pack', required=True,
                                 help='the world pack name to import as')
    volumes_import.add_argument('--from', dest='from_path', required=True,
                                 help='source directory (engine-native layout)')
    volumes_import.add_argument('--dry-run', action='store_true',
                                 help='validate only; do not write')
    volumes_import.set_defaults(fn=cmd_volumes_import)

    volumes_shell = volumes_sub.add_parser(
        'shell',
        help='drop into a shell inside the engine container',
    )
    volumes_shell.add_argument('--pack', default=None,
                                help='cd into the pack\'s volume path')
    volumes_shell.set_defaults(fn=cmd_volumes_shell)

    fd = ferry_sub.add_parser(
        'deploy',
        help='ship this checkout to --deploy-host (build image + restart + healthcheck)',
    )
    fd.add_argument(
        '--init', action='store_true',
        help="write deploy.toml.example + docs/guides/deploy.md scaffolding; "
             "does not contact the deploy host. Run once per checkout.",
    )
    fd.add_argument(
        '--skip-tests', action='store_true',
        help='skip the pytest + sample-world validate pre-flight gate',
    )
    fd.add_argument(
        '--rebuild', action='store_true',
        help='force `podman build` even when the image SHA matches the checkout '
             'HEAD (default: skip the build when nothing changed)',
    )
    fd.add_argument(
        '--no-health', action='store_true',
        help='skip the post-deploy /api/health probe + maplab verify',
    )
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

    fs = ferry_sub.add_parser(
        'scaffold',
        help='export the active pack as a standalone git repo, ready for a new author',
    )
    fs.add_argument('dest', help='destination directory (created, must be empty)')
    fs.add_argument('--name', default=None,
                    help='the pack to export (default: the resolved world)')
    fs.add_argument('--push', action='store_true',
                    help='create a private Gitea repo and push, using this '
                         "checkout's origin credentials")
    fs.set_defaults(fn=cmd_scaffold)

    # Spark - the resident small brain and its service lifecycle.
    spark = sub.add_parser(
        'spark',
        help='VEFR\'s resident Spark: install, status, smoke',
    )
    spark_sub = spark.add_subparsers(dest='spark_verb', required=True)

    si = spark_sub.add_parser(
        'install',
        help='acquire the pinned model, install + start the quadlet, '
             'wire the engine, verify health (idempotent)',
    )
    si.add_argument('--profile', default='quality', choices=('quality', 'tiny'),
                    help="spark-quality (Phi-4-mini Q4_K_M, default) or "
                         "spark-tiny (Qwen3.5-0.8B Q8_0)")
    si.add_argument('--host', default=DEFAULT_DEPLOY_HOST,
                    help='the machine Spark lives on (declared like ferry deploy)')
    si.add_argument('--image', default=None,
                    help='llama.cpp server image ref (default: pinned by digest)')
    si.set_defaults(fn=cmd_spark_install)

    ss = spark_sub.add_parser(
        'status',
        help='model verified? service active? health green?',
    )
    ss.add_argument('--profile', default='quality', choices=('quality', 'tiny'))
    ss.add_argument('--host', default=DEFAULT_DEPLOY_HOST)
    ss.add_argument('--spark-url', default=None,
                    help='probe this Spark endpoint instead of the default')
    ss.set_defaults(fn=cmd_spark_status)

    smo = spark_sub.add_parser(
        'smoke',
        help='functional proof through the live engine\'s /api/spark routes',
    )
    smo.add_argument('--url', default=None,
                     help='the live engine URL (default: deploy.toml url)')
    smo.set_defaults(fn=cmd_spark_smoke)

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


# ----------------------------------------------------------------- scaffold

def cmd_scaffold(args) -> int:
    """Export the active pack as a standalone, git-ready repo - ferry scaffold.

    For handing a world to someone who will make it their own: the
    pack's files as-is (canon, voices, map, ledger - the author's
    content), a README explaining what vefr is and which files are
    meant to be replaced with real art, and a fresh git history so
    their work starts at commit one. --push creates the Gitea repo
    and pushes, reusing whatever credentials the engine checkout's
    own origin carries.
    """
    dest = Path(args.dest).resolve()
    if dest.exists() and any(dest.iterdir()):
        print(f'refusing: {dest} exists and is not empty')
        return 1

    name = args.name or world_name()
    src = pack_root() / 'worlds' / name
    if not (src / 'world.json').exists():
        print(f'pack not found at {src}; pass --name or set VEFR_WORLD')
        return 1

    # Derived artifacts regenerate on the next run; stash files are
    # transient. Everything else the author touched ships as-is.
    EXCLUDE = {'world-tree.md', 'handbok.md'}
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in EXCLUDE or item.name.endswith('.tmp') or item.name.endswith('.rewind.json'):
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)

    engine_sha = 'unknown'
    root = subprocess.run(
        ('git', 'rev-parse', '--show-toplevel'),
        capture_output=True, text=True, cwd=str(Path(__file__).resolve().parent),
    )
    if root.returncode == 0:
        sha = subprocess.run(
            ('git', '-C', root.stdout.strip(), 'rev-parse', '--short', 'HEAD'),
            capture_output=True, text=True,
        )
        if sha.returncode == 0:
            engine_sha = sha.stdout.strip()

    # The engine's home, derived from this checkout's own origin -
    # runtime identity, never a hardcoded one.
    origin_url = ''
    if root.returncode == 0:
        o = subprocess.run(
            ('git', '-C', root.stdout.strip(), 'remote', 'get-url', 'origin'),
            capture_output=True, text=True,
        )
        if o.returncode == 0:
            u = o.stdout.strip()
            if u.startswith('git@'):
                u = 'https://' + u[4:].replace(':', '/', 1)
            origin_url = u.removesuffix('.git')

    engine_line = 'A world pack for vefr - a rumor engine for playable\nworlds, exported from engine commit'
    if origin_url:
        engine_line += f' [`{engine_sha}`]({origin_url}).'
    else:
        engine_line += f' `{engine_sha}`.'

    readme = f"""# {name}

{engine_line}

## What each file is

| File | What it is | Replaceable? |
|---|---|---|
| `world.json` | the world's shape: town, phases, voices, bonds | the schema is the engine's; the contents are yours |
| `logbok.md` | canon - the rules the story must never break | yours, entirely |
| `ledger.md` | the whispers the engine matches cadence against | yours, entirely |
| `voices/*.md` | each speaker's system prompt | yours, entirely |
| `map.md` | the walkable map (run-length rows + legend) | yours, entirely |

## Running it

```sh
git clone {origin_url if origin_url else '<the vefr engine checkout>'}
cd vefr && uv sync --group test
VEFR_WORLD={name} uv run uvicorn vefr.main:app --app-dir src --port 8820
```

Or point this directory's name at `worlds/` inside a vefr clone.

## Making it yours

This scaffold is a starting point, not a finished thing: drop in
your own artwork, rewrite the voices, replace the map. The engine
reads whatever the pack gives it.
"""
    (dest / 'README.md').write_text(readme, encoding='utf-8')
    if not (dest / 'LICENSE').exists() and not (dest / 'LICENSE.md').exists():
        (dest / 'LICENSE.md').write_text(
            f'{name} - all rights reserved by its author.\n'
            'Replace this file with the license you choose before sharing.\n',
            encoding='utf-8',
        )

    if sh(('git', '-C', str(dest), 'init', '-b', 'main')).returncode:
        print('git init failed - the files are copied; init by hand')
        return 1
    sh(('git', '-C', str(dest), 'add', '-A'))
    # Inline identity: the scaffolded repo is a fresh export, and the
    # exporting machine (or CI runner) may have no global git config.
    # Scoped via -c so we never touch the user's real config.
    if sh(('git', '-C', str(dest), '-c', 'user.name=vefr scaffold',
           '-c', 'user.email=vefr@scaffold.local', 'commit', '-m',
           f'world pack {name}, exported from vefr {engine_sha}')).returncode:
        print('commit failed - files are staged; commit by hand')
        return 1

    if not args.push:
        print(f'scaffold ready: {dest} (git main, 1 commit)')
        return 0

    # --push: create the Gitea repo from the engine checkout's own
    # credentials, then push the new repo's main there.
    origin = subprocess.run(
        ('git', '-C', str(need_repo()), 'remote', 'get-url', 'origin'),
        capture_output=True, text=True,
    ).stdout.strip()
    creds = urllib.parse.urlparse(origin)
    if not creds.username:
        print(f'no credentials in {origin}; push by hand:')
        print(f'  git -C {dest} remote add origin <your repo url>')
        print(f'  git -C {dest} push -u origin main')
        return 1
    base = f'{creds.scheme}://{creds.netloc.rsplit("@", 1)[1]}'
    owner = creds.path.strip('/').split('/')[0]
    token = creds.password or ''
    dest_name = dest.name
    import urllib.error
    import urllib.parse

    req = urllib.request.Request(
        f'{base}/api/v1/repos/{owner}',
        data=json.dumps({'name': dest_name, 'private': True}).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    import base64 as _b64
    req.add_header('Authorization', 'Basic ' + _b64.b64encode(
        f'{creds.username}:{token}'.encode()).decode())
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode())
        print(f'gitea repo created: {body.get("full_name", dest_name)}')
    except urllib.error.HTTPError as e:
        if e.code == 409:
            print(f'repo {owner}/{dest_name} already exists - pushing to it')
        else:
            print(f'repo create failed: HTTP {e.code}')
            return 1
    remote = f'{creds.scheme}://{creds.username}:{token}@{creds.netloc.rsplit("@", 1)[1]}/{owner}/{dest_name}.git'
    if sh(('git', '-C', str(dest), 'remote', 'add', 'origin', remote)).returncode:
        sh(('git', '-C', str(dest), 'remote', 'set-url', 'origin', remote))
    if sh(('git', '-C', str(dest), 'push', '-u', 'origin', 'main')).returncode:
        print('push failed - the commit exists locally; push by hand')
        return 1
    print(f'pushed: {owner}/{dest_name}')
    return 0


# --------------------------------------------------------------- spark

def _spark_host(args) -> str:
    """The host Spark lives on, resolved like ferry deploy: --flag,
    then env, then deploy.toml. The silent 'bazzite' default is still
    refused - one resident llama.cpp process deserves a declared home."""
    host = getattr(args, 'host', None)
    cfg = _deploy_toml()
    declared_env = bool(os.environ.get('VEFR_DEPLOY_HOST'))
    declared_toml = 'host' in cfg
    if host == DEFAULT_DEPLOY_HOST and not declared_env and declared_toml:
        host = cfg['host']
    if host == 'bazzite' and not declared_env and not declared_toml:
        raise SystemExit(
            'refusing: the Spark host is not declared.\n'
            '  export VEFR_DEPLOY_HOST=<your-host-or-ssh-alias>\n'
            'or add host = "<your-host>" to deploy.toml.'
        )
    return host


def _k2_health(host: str) -> str:
    """K2's /health via ssh - recorded before and after every Spark
    service change. K2 is the escalation target; it must never be
    destabilized by Spark work."""
    out = subprocess.run(
        ('ssh', '-o', 'ConnectTimeout=6', host,
         'curl -s -m 5 http://127.0.0.1:8081/health'),
        capture_output=True, text=True, timeout=20).stdout.strip()
    return out or 'no answer'


def _quadlet_text(profile: dict, image: str) -> str:
    """The spark quadlet for one profile - CPU-only, loopback-only,
    pinned image, model-native template flags from spark.PROFILES."""
    kwargs = profile.get('chat_template_kwargs') or {}
    extra = ''
    if kwargs:
        import json as _json
        extra = " --chat-template-kwargs '" + _json.dumps(kwargs) + "'"
    alias = profile['alias']
    return f"""\
[Unit]
Description=spark - VEFR's resident small brain ({profile['key']} profile, CPU-only)

[Container]
Image={image}
ContainerName=spark
Network=host
Volume=%h/spark/models:/models:Z
Exec=--model /models/{profile['file']} --alias {alias} --host 127.0.0.1 --port 8082 -c 8192 -t 8 -ngl 0 --jinja{extra}

[Service]
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""


def _spark_model_ensure(host: str, profile: dict) -> str:
    """The model file on the Spark host, verified. Copies from the
    benchmark cache when present (no re-download), else pulls the
    pinned artifact from Hugging Face with resume. Returns the
    verification detail. Never commits the GGUF - it lives on the host."""
    remote_dir = '~/spark/models'
    repo, fname = profile['repo'], profile['file']
    # Fast path: the benchmark cache already has the pinned artifact.
    cache = f'~/llama-server/vefr-spark/models/{fname}'
    probe = subprocess.run(
        ('ssh', '-o', 'ConnectTimeout=6', host,
         f'test -f {cache} && echo cached || echo absent'),
        capture_output=True, text=True, timeout=20).stdout.strip()
    if probe == 'cached':
        print(f'  model found in benchmark cache: {cache}')
        rc = sh(('ssh', host,
                 f'mkdir -p {remote_dir} && '
                 f'cp -n {cache} {remote_dir}/{fname}')).returncode
    else:
        print(f'  downloading {fname} from huggingface.co/{repo} (resumes on retry)')
        rc = sh(('ssh', host,
                 f'mkdir -p {remote_dir} && curl -sS -L -C - '
                 f'--retry 5 --retry-delay 5 -o {remote_dir}/{fname} '
                 f'https://huggingface.co/{repo}/resolve/main/{fname}')).returncode
    if rc:
        return f'DOWNLOAD FAILED (rc={rc})'
    check = subprocess.run(
        ('ssh', host,
         f'sha256sum {remote_dir}/{fname}'),
        capture_output=True, text=True, timeout=120)
    got = check.stdout.strip().split()[0] if check.stdout.strip() else ''
    if not got:
        return f'HASH CHECK FAILED: {check.stderr.strip()[:200]}'
    if got != profile['sha256']:
        return (f'VERIFICATION FAILED: sha {got[:12]}... != pinned '
                f'{profile["sha256"][:12]} - remove the file and re-run')
    size_out = subprocess.run(
        ('ssh', host, f'stat -c %s {remote_dir}/{fname}'),
        capture_output=True, text=True, timeout=20).stdout.strip()
    return f'verified against pinned sha256 ({int(size_out or 0) / 1e9:.2f} GB)'


def _spark_image_ref(host: str) -> str:
    """The llama.cpp server image, pinned by digest so a re-run of
    `ratatoskr spark install` reconciles to the same artifact."""
    out = subprocess.run(
        ('ssh', '-o', 'ConnectTimeout=6', host,
         'podman images --digests --format "{{.Repository}}@{{.Digest}}" '
         '| grep "ghcr.io/ggml-org/llama.cpp" | head -1'),
        capture_output=True, text=True, timeout=20).stdout.strip()
    return out or 'ghcr.io/ggml-org/llama.cpp:server'


def cmd_spark_install(args) -> int:
    """One command from 'no Spark' to 'boring resident service':
    acquire the pinned model, verify it, install + start the quadlet,
    wire VEFR_SPARK_URL into the engine's environment, verify health,
    and leave K2 exactly as it was."""
    host = _spark_host(args)
    from . import spark as spark_mod
    prof = spark_mod.profile(args.profile)
    image = args.image or _spark_image_ref(host)

    print(f'spark install: profile={prof["key"]} host={host}')
    k2_pre = _k2_health(host)
    print(f'  k2 pre : {k2_pre}')

    detail = _spark_model_ensure(host, prof)
    print(f'  model: {detail}')
    if 'FAILED' in detail or 'mismatch' in detail:
        return 1

    quadlet = _quadlet_text(prof, image)
    rc = sh(('ssh', host,
             'mkdir -p ~/.config/containers/systemd ~/spark/models && '
             f"cat > ~/.config/containers/systemd/spark.container <<'QUADLET'\n"
             f'{quadlet}QUADLET')).returncode
    if rc:
        return rc
    # The engine learns Spark's endpoint from its own environment -
    # one configuration path, no machine-specific URLs in code.
    sh(('ssh', host,
        'grep -q VEFR_SPARK_URL ~/.config/containers/systemd/vefr.container || '
        'echo "Environment=VEFR_SPARK_URL=http://127.0.0.1:8082" '
        '>> ~/.config/containers/systemd/vefr.container'))
    sh(('ssh', host,
        'grep -q VEFR_SPARK_PROFILE ~/.config/containers/systemd/vefr.container || '
        f'echo "Environment=VEFR_SPARK_PROFILE={prof["key"]}" '
        '>> ~/.config/containers/systemd/vefr.container'))
    # Quadlet units are generated by systemd from the .container file:
    # daemon-reload materializes them and the [Install] section already
    # wires boot persistence. `systemctl enable` refuses generated
    # units ("transient or generated") - start is the correct verb.
    if sh(('ssh', host,
           'systemctl --user daemon-reload && '
           'systemctl --user start spark')).returncode:
        print('systemd start failed - check: ssh %s systemctl --user status spark' % host)
        return 1

    # llama.cpp loads the model before /health answers; poll long enough
    # for a cold page-in of a ~2.5 GB file from disk.
    print('  waiting for model load + health...')
    import time as _time
    up = False
    for _ in range(90):
        probe = subprocess.run(
            ('ssh', host, 'curl -s -m 3 http://127.0.0.1:8082/health'),
            capture_output=True, text=True, timeout=15).stdout.strip()
        if '"ok"' in probe:
            up = True
            break
        _time.sleep(2)
    if not up:
        print('spark never went healthy - logs: '
              f'ssh {host} podman logs spark')
        return 1
    smoke = subprocess.run(
        ('ssh', host,
         'curl -s -m 120 http://127.0.0.1:8082/v1/chat/completions '
         '-H "Content-Type: application/json" '
         '-d \'{"messages":[{"role":"user","content":"Reply with exactly: SPARK-OK"}],'
         '"max_tokens":16}\' | grep -o "SPARK-OK" | head -1'),
        capture_output=True, text=True, timeout=140).stdout.strip()
    sh(('ssh', host, 'systemctl --user restart vefr'))

    k2_post = _k2_health(host)
    ok = 'SPARK-OK' in smoke
    print(f'  smoke: {"SPARK-OK" if ok else "FAILED - " + smoke!r}')
    print(f'  k2 post: {k2_post}')
    print('spark installed. <3' if ok and k2_post == k2_pre
          else 'spark installed with warnings - see above.')
    return 0 if ok else 1


def cmd_spark_status(args) -> int:
    """The four facts: model verified? service running? health green?
    does Spark still know what is not its job?"""
    host = _spark_host(args)
    from . import spark as spark_mod
    prof = spark_mod.profile(args.profile)
    rows = []
    ok, detail = spark_mod.verify_model(prof)
    rows.append(('model', 'ok' if ok else 'FAIL', detail))
    svc = subprocess.run(
        ('ssh', '-o', 'ConnectTimeout=6', host,
         'systemctl --user is-active spark'),
        capture_output=True, text=True, timeout=15).stdout.strip() or 'unknown'
    rows.append(('service', 'ok' if svc == 'active' else svc, f'systemctl --user is-active -> {svc}'))
    try:
        h = spark_mod.health(timeout=5, url=args.spark_url or None)
        rows.append(('health', 'ok', f'{h["status"]} in {h["probe_ms"]}ms'))
    except Exception as exc:  # noqa: BLE001
        rows.append(('health', 'DOWN', f'{exc.__class__.__name__}'))
    print(f'ratatoskr spark status (profile={prof["key"]}, host={host})')
    for name, status, detail in rows:
        print(f'  {name:<8} {status:<8} {detail}')
    return 0 if all(s == 'ok' for _, s, _ in rows) else 1


def cmd_spark_smoke(args) -> int:
    """The functional proof, through the real integrated path: the
    live engine's /api/spark routes. Four probes: health, structured
    NPC generation, state-edit preservation, escalation judgment.
    Exit 0 only when all four hold."""
    url = (args.url or _deploy_toml().get('url') or DEFAULT_URL).rstrip('/')
    import json as _json
    import urllib.request as _ur

    def post(path: str, body: dict) -> dict:
        req = _ur.Request(f'{url}{path}', _json.dumps(body).encode(),
                          {'Content-Type': 'application/json'})
        with _ur.urlopen(req, timeout=300) as r:
            return _json.loads(r.read().decode())

    rows = []
    h = fetch(f'{url}/api/spark/health', timeout=10)
    rows.append(('health', 'ok' if h.get('ok') else 'FAIL',
                 f'{h.get("spark")} model={h.get("model")} {h.get("probe_ms", "?")}ms'))

    npc = post('/api/spark/task', {
        'task': 'npc',
        'user': 'Scene: dusk in Emberfield, a candle-maker\'s stall near the '
                'market well. Create one new NPC for this scene.'})
    npc_ok = (npc.get('ok') and isinstance(npc.get('result'), dict)
              and set(npc['result']) == {'id', 'name', 'role', 'personality',
                                         'location', 'dialogue_seed'})
    rows.append(('npc_json', 'ok' if npc_ok else 'FAIL', str(npc.get('result', npc.get('error', '')))[:90]))

    state = {'world': 'Emberfield', 'gold': 12,
             'npcs': [{'id': 'bray', 'trust': 2}, {'id': 'kestrel', 'trust': 2}]}
    edit = post('/api/spark/task', {
        'task': 'state_edit',
        'user': 'Update the world state: Kestrel now trusts the player completely. '
                "Set Kestrel's trust to 5. Return the complete updated state JSON and nothing else.",
        'state': state})
    kept = edit.get('ok') and edit.get('result', {}).get('npcs', [{}])[0].get('trust') == 2 \
        and edit.get('result', {}).get('npcs', [{}])[-1].get('trust') == 5 \
        and edit.get('result', {}).get('gold') == 12
    rows.append(('state_edit', 'ok' if kept else 'FAIL',
                 'target changed, rest preserved' if kept else 'preservation broken'))

    esc = post('/api/spark/escalate', {})
    rows.append(('escalation', 'ok' if esc.get('ok') else 'FAIL', esc.get('escalation', '')))

    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f'ratatoskr spark smoke -- {now} ({url})')
    print()
    print('| probe | status | detail |')
    print('| -- | ------ | ------ |')
    for name, status, detail in rows:
        print(f'| {name} | {status} | {detail} |')
    failed = sum(1 for _, s, _ in rows if s != 'ok')
    print()
    print('spark smoke: all green. <3' if not failed else f'spark smoke: {failed} failed')
    return 0 if not failed else 1


# ---------------------------------------------------------------- doctor

def _pytest_summary(repo: Path) -> tuple:
    """Run the gate quietly; return (status, detail)."""
    try:
        r = subprocess.run(
            (sys.executable, '-m', 'pytest', '-q', '--tb=no'),
            capture_output=True, text=True, cwd=str(repo), timeout=600,
        )
    except FileNotFoundError:
        return 'skip', 'pytest not installed - uv sync --group test'
    lines = (r.stdout or '').strip().splitlines()
    summary = lines[-1] if lines else 'no output'
    return ('ok', summary) if r.returncode == 0 else ('FAIL', summary)


def cmd_doctor(args) -> int:
    """Session-start health check - norns doctor.

    One command instead of the manual checklist: git sync state,
    the working tree, the test gate, the current pack's geometry,
    and (when VEFR_LIVE_URL is set) a running stack's /api/health.
    Neutral words only. Exit 1 only when something local is broken
    (tests, pack); a remote that answers slowly is reported, not
    failed.
    """
    rows: list[tuple] = [('git',) + q1_sync()]
    tree = q2_dirty()
    if tree[0] != 'unavailable':
        rows.append(('tree',) + tree)

    repo = repo_root()
    if repo:
        rows.append(('tests',) + _pytest_summary(repo))
    else:
        rows.append(('tests', 'skip', 'no git checkout (container install)'))

    pack = Path(args.pack)
    if not pack.is_absolute():
        pack = pack_root() / 'worlds' / pack
    try:
        w = load_pack(pack)
        errors = validate(w, pack_dir=pack)
        if errors:
            rows.append(('pack', 'FAIL',
                         f'{pack.name}: {len(errors)} problem(s) - '
                         f'norns validate --pack {pack}'))
        else:
            rows.append(('pack', 'ok',
                         f'{pack.name}: geometry, reachability, voices pass'))
    except Exception as exc:  # a missing/broken pack is doctor's business
        rows.append(('pack', 'FAIL', f'{pack.name}: {exc}'))

    live = os.environ.get('VEFR_LIVE_URL')
    if not live and repo:
        # No env var? deploy.toml's url is the operator's declared
        # live endpoint - one command tells the whole truth.
        live = _deploy_toml(repo).get('url')
    if not live:
        rows.append(('live', 'skip',
                     'set VEFR_LIVE_URL (or add url to deploy.toml) '
                     'to check a running stack'))
    else:
        try:
            payload = fetch(live.rstrip('/') + '/api/health', timeout=5)
            ok = bool(payload.get('ok'))
            rows.append(('live', 'ok' if ok else 'DOWN', live))
        except Exception as exc:
            rows.append(('live', 'DOWN', f'{live} - {exc.__class__.__name__}'))

    print('norns doctor')
    for name, status, detail in rows:
        print(f'  {name:<6} {status:<12} {detail}')
    failed = sum(1 for r in rows if r[1] == 'FAIL')
    skipped = sum(1 for r in rows if r[1] == 'skip')
    ok_n = len(rows) - failed - skipped
    print(f'doctor: {ok_n} ok, {failed} failed, {skipped} skipped')
    return 1 if failed else 0


def cmd_storyteller_test(args) -> int:
    """norns storyteller-test - run a scene through one or all packs.

    Single-model: --model <id>
    Matrix: --matrix
    """
    from .storyteller import find_pack, list_packs
    from .storyteller_test import (
        audition_one,
        build_blind_map,
        list_fixtures,
        load_fixture,
        write_artifacts,
    )

    scene_id = getattr(args, "scene", None) or "sample-scene"
    available = list_fixtures()
    if scene_id not in available:
        print(f"unknown scene {scene_id!r}. available:")
        for sid in available:
            print(f"  - {sid}")
        if not available:
            print(
                "  (none found - set VEFR_STORYTELLER_FIXTURES to a "
                "directory of scene fixtures)"
            )
        return 1
    scene = load_fixture(scene_id)

    runs_per = max(1, int(getattr(args, "runs", 1) or 1))
    seed = getattr(args, "seed", None)
    if seed is not None:
        seed = int(seed)
    blind = bool(getattr(args, "blind", False))

    if getattr(args, "matrix", False):
        packs = list_packs()
    else:
        target = getattr(args, "model", None)
        if not target:
            print("--model <pack_id> is required (or pass --matrix)")
            return 1
        pack = find_pack(target)
        if pack is None:
            print(f"unknown storyteller pack {target!r}.")
            print("available packs:")
            for p in list_packs():
                print(f"  - {p.id} ({p.model})")
            return 1
        packs = [pack]

    print("=== STORYTELLER AUDITION ===")
    print(f"scene: {scene_id} v{scene.version}")
    print(f"runs per pack: {runs_per}")
    print(f"packs: {len(packs)}")
    print()

    results = []
    for pack in packs:
        for n in range(1, runs_per + 1):
            label = pack.id
            print(f"--- {label} | run {n}/{runs_per} ---")
            result = audition_one(pack, scene, run_number=n, seed=seed)
            results.append(result)
            if result.status == "ok":
                preview = result.response.strip().splitlines()
                for line in preview[:6]:
                    print(f"  {line}")
                if len(preview) > 6:
                    print(f"  ... ({len(preview) - 6} more lines)")
                print(f"  [{result.latency_s:.2f}s]")
            elif result.status == "skipped":
                print(f"  SKIPPED - {result.skip_reason}")
            else:
                print(f"  ERROR - {result.error}")
            print()

    out_dir = write_artifacts(results)

    if blind:
        bmap = build_blind_map(results)
        (out_dir / "blind_map.txt").write_text(
            "\n".join(f"{v} -> {k}" for k, v in bmap.items()),
            encoding="utf-8",
        )

    print(f"saved: {out_dir}")
    failed = sum(1 for r in results if r.status == "error")
    skipped = sum(1 for r in results if r.status == "skipped")
    ok = sum(1 for r in results if r.status == "ok")
    print(f"summary: {ok} ok, {skipped} skipped, {failed} error")
    return 1 if failed else 0


def cmd_storyteller_benchmark(args) -> int:
    """norns storyteller-benchmark - blind A/B/C/D capability review.

    Three modes:
      run       - execute the full benchmark, write blind review files
      reveal    - print the identity mapping + tech context for an existing run
      review    - print the blank review worksheet for an existing run
    """
    from .storyteller import find_pack, list_packs
    from .storyteller_benchmark import (
        default_packs,
        list_default_fixtures,
        render_reveal,
        run_benchmark,
    )

    mode = getattr(args, "benchmark_cmd", "run")

    if mode == "reveal":
        out_dir = Path(getattr(args, "out_dir", ""))
        if not out_dir.is_dir():
            print(f"not a directory: {out_dir}")
            return 1
        # Build pack-context strings from the current pack list so the
        # reveal can show model + license + quant next to each label.
        extra: dict[str, str] = {}
        for pack in list_packs():
            lic = pack.license
            spdx = (lic.spdx if lic else "") or "?"
            comm = (lic.commercial_use if lic else "") or "?"
            quant = (pack.install.recommended_quant if pack.install else "") or "?"
            extra[pack.id] = (
                f"model={pack.model}  quant={quant}  "
                f"license={spdx}  commercial_use={comm}"
            )
        print(render_reveal(out_dir, extra_context=extra))
        return 0

    if mode == "review":
        out_dir = Path(getattr(args, "out_dir", ""))
        worksheet = out_dir / "review" / "WORKSHEET.txt"
        if not worksheet.is_file():
            print(f"no worksheet at {worksheet}")
            return 1
        print(worksheet.read_text(encoding="utf-8"))
        return 0

    # mode == "run"
    fixtures = list_default_fixtures()
    if not fixtures:
        print("no benchmark fixtures found under tests/fixtures/storyteller/")
        return 1

    if getattr(args, "pack", None):
        packs = []
        for name in args.pack:
            pack = find_pack(name)
            if pack is None:
                print(f"unknown storyteller pack {name!r}")
                return 1
            packs.append(pack)
    elif getattr(args, "model", None):
        pack = find_pack(getattr(args, "model"))
        if pack is None:
            print(f"unknown storyteller pack {getattr(args, 'model')!r}")
            return 1
        packs = [pack]
    else:
        packs = default_packs()
        if getattr(args, "exclude", None):
            packs = [p for p in packs if p.id not in set(args.exclude)]

    if not packs:
        print("no storyteller packs configured; install one under data/storytellers/")
        return 1

    runs_per = max(1, int(getattr(args, "runs", 3) or 3))
    seed = getattr(args, "seed", None)
    if seed is not None:
        seed = int(seed)

    print("=== STORYTELLER CAPABILITY BENCHMARK ===")
    print(f"fixtures: {len(fixtures)}")
    print(f"packs: {len(packs)}")
    print(f"runs per (fixture, pack): {runs_per}")
    print(f"blind mapping seed: {seed if seed is not None else 'system-random'}")
    print()

    def progress(fixture_id: str, pack_id: str, run_number: int, status: str) -> None:
        marker = {"ok": ".", "skipped": "S", "error": "E"}.get(status, "?")
        print(f"  {fixture_id:24s} {pack_id:24s} run {run_number}: {marker}")

    out_dir, mapping = run_benchmark(
        packs,
        fixtures,
        runs_per=runs_per,
        seed=seed,
        progress=progress,
    )

    review_dir = out_dir / "review"
    print()
    print(f"saved blind review: {review_dir}")
    print(f"identity mapping (PRIVATE): {out_dir / 'identity.json'}")
    print()
    print("review order:")
    for f in sorted(review_dir.glob("[0-9][0-9]-*.txt")):
        print(f"  {f.name}")
    print()
    print(
        "open the review files in order. read prose. write your rankings "
        "in review/WORKSHEET.txt. do not open identity.json until you "
        "are done."
    )
    return 0


def norns_main() -> int:
    ap = argparse.ArgumentParser(
        prog='norns', description=NORNS_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    craft = ap.add_subparsers(dest='craft_cmd', required=True)

    mc = craft.add_parser('chat', help='interview a new world into existence')
    mc.add_argument('--name', required=True, help='the new pack name (worlds/<name>)')
    mc.set_defaults(fn=cmd_chat)

    mm = craft.add_parser(
        'migrate', help='migrate a flat-shape pack to the acts tree'
    )
    mm.add_argument('--pack', required=True,
                    help='the world pack name (worlds/<pack>)')
    mm.add_argument('--act-id', default=None,
                    help='act id for the new tree (default: act-1)')
    mm.set_defaults(fn=cmd_migrate)

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

    md = craft.add_parser(
        'doctor',
        help='session-start health check: git, tests, pack, live stack',
    )
    md.add_argument('--pack', default=None)
    md.set_defaults(fn=cmd_doctor)

    mt = craft.add_parser(
        'storyteller-test',
        help='run a VEFR scene through one or all Storyteller Packs',
    )
    mt.add_argument('--model', default=None,
                    help='pack id or model name to run (mutually exclusive with --matrix)')
    mt.add_argument('--matrix', action='store_true',
                    help='run the scene through every installed pack')
    mt.add_argument('--scene', default=None,
                    help='scene fixture id (default: sample-scene)')
    mt.add_argument('--runs', type=int, default=1,
                    help='repetitions per pack (default: 1; 3 recommended for creative models)')
    mt.add_argument('--seed', type=int, default=None,
                    help='record a seed for reproducibility (informational; providers that support it will)')
    mt.add_argument('--blind', action='store_true',
                    help='label outputs Storyteller A/B/C and write a blind_map.txt for later reveal')
    mt.set_defaults(fn=cmd_storyteller_test)

    mb = craft.add_parser(
        'storyteller-benchmark',
        help='run the blind A/B/C/D story capability benchmark',
    )
    bench = mb.add_subparsers(dest='benchmark_cmd')
    bench.required = True

    mb_run = bench.add_parser('run', help='execute the full benchmark and write blind review files')
    mb_run.add_argument('--model', default=None,
                        help='benchmark only this pack (default: every installed pack)')
    mb_run.add_argument('--pack', action='append', default=None,
                        help='restrict to one or more pack ids; may be repeated. '
                             'Overrides --model if both are passed.')
    mb_run.add_argument('--exclude', action='append', default=None,
                        help='drop these pack ids from the default roster; may be repeated.')
    mb_run.add_argument('--runs', type=int, default=3,
                        help='repetitions per (fixture, pack) (default: 3)')
    mb_run.add_argument('--seed', type=int, default=None,
                        help='seed the blind label assignment so mapping is reproducible (default: system-random)')
    mb_run.set_defaults(fn=cmd_storyteller_benchmark)

    mb_reveal = bench.add_parser('reveal',
                                 help='print identity mapping + tech context for an existing run')
    mb_reveal.add_argument('--out-dir', required=True,
                           help='the artifact directory the benchmark run wrote to')
    mb_reveal.set_defaults(fn=cmd_storyteller_benchmark)

    mb_review = bench.add_parser('review',
                                 help='print the blank review worksheet for an existing run')
    mb_review.add_argument('--out-dir', required=True,
                           help='the artifact directory the benchmark run wrote to')
    mb_review.set_defaults(fn=cmd_storyteller_benchmark)

    args = ap.parse_args()
    # validate / build-map / verify / doctor default --pack to the
    # resolved world; chat doesn't take --pack and doesn't need the
    # lookup.
    if args.craft_cmd in ('validate', 'build-map', 'verify', 'doctor') \
            and getattr(args, 'pack', None) is None:
        args.pack = pack_root() / 'worlds' / world_name()
    return args.fn(args)


if __name__ == '__main__':
    sys.exit(ratatoskr_main())
