import os
import re
from pathlib import Path

# A name that can be joined onto a pack root without escaping it: one
# bare path segment, no separators, no leading dot. The request-facing
# routes validate through safe_pack_name() so "../elsewhere" can never
# reach pack_dir().
_PACK_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def safe_pack_name(name: str | None) -> str | None:
    """Validate a pack/world name that arrived from an untrusted caller.

    None and "" mean "the current pack" and pass through unchanged.
    Anything else must be a bare pack name, so it stays under worlds/
    or templates/ when pack_dir() joins it. Raises ValueError for
    anything else; the HTTP layer turns that into a 400. This is the
    single source of the pack-name rule - main.py's routes no longer
    carry their own regex.
    """
    if not name:
        return None
    if not isinstance(name, str) or not _PACK_NAME_RE.match(name):
        raise ValueError("world must be a bare pack name")
    return name


def resolve_under(base, *parts) -> Path:
    """Join `parts` onto `base` and refuse anything that leaves it.

    The second layer, under safe_pack_name()/sessions.clean(): those
    say a *name* must be a bare segment, this one refuses the *join*
    itself. A name can be valid by the first rule and still walk out
    (or a caller can skip the first rule entirely), so every place a
    caller-supplied value becomes a path segment goes through here.

    Written in the shape CodeQL's py/path-injection recognises as a
    sanitiser - os.path.normpath of the joined path, then a direct
    startswith(base + os.sep) whose failing branch raises - because a
    regex guard is not a barrier to that query and a normpath+prefix
    test is. normpath, not realpath: this refuses "..", not an
    operator's own symlinks, and stays inside the tree it was handed.
    """
    base_s = os.path.normpath(os.fspath(base))
    p = os.path.normpath(os.path.join(base_s, *map(str, parts)))
    if not (p == base_s or p.startswith(base_s + os.sep)):
        raise ValueError("path escapes its base")
    return Path(p)


def app_home() -> Path:
    """Where web/ and worlds/ live.

    Container installs put the package in site-packages, so the dev-box
    parent trick points at the wrong tree. VEFR_HOME (set in the
    Containerfile) wins; otherwise fall back to /app, then the repo
    checkout (dev runs).
    """
    env = os.environ.get("VEFR_HOME")
    if env:
        return Path(env)
    dev = Path(__file__).resolve().parents[2]
    for cand in (Path("/app"), dev):
        # The container ships /app/worlds-template/ (engine-owned
        # lore + sample-world). The dev box has worlds/ at the top
        # of the checkout. Either one counts as "this is the engine
        # home."
        if (cand / "worlds-template").is_dir() or (cand / "worlds").is_dir() or (cand / "web").is_dir():
            return cand
    return dev


def template_dir() -> Path:
    """The read-only engine-template mount.

    Holds lore/ and sample-world/ (and any future engine-owned packs).
    Updated by `ferry deploy`, not by the author. If the path doesn't
    exist (legacy installs, dev box without the new layout), the
    loader falls back to scanning the rw worlds/ for everything.
    """
    return app_home() / "worlds-template"


def worlds_dir() -> Path:
    """The read-write canon mount. Holds user-owned packs and any
    edits the author makes via the builder / `volumes import` /
    manual `podman exec`. The container's bind point is
    /app/worlds; the dev box's is the engine checkout's worlds/.
    """
    return app_home() / "worlds"


def data_dir() -> Path:
    """Runtime state that isn't a world pack - sessions, journals,
    the active-world choice. Lives under the app home, next to the
    tracked data/ tree, and is never committed. VEFR_DATA_DIR points it
    elsewhere (a test copy of the studio must never write the real one).
    """
    env = os.environ.get("VEFR_DATA_DIR")
    return Path(env).expanduser() if env else app_home() / "data"


def active_world_file() -> Path:
    """The tiny file the active-world choice persists to."""
    return data_dir() / "active-world"


# The in-memory half of the override: a request that just switched
# worlds takes effect immediately, before the file is ever re-read.
_ACTIVE_WORLD: str | None = None


def active_world() -> str | None:
    """The server-side world override, if one was chosen at runtime.

    In-memory first (someone just picked a world in the web UI),
    then the persisted file under data/. None when neither names
    one, so world_name() falls through to its normal resolution.
    """
    global _ACTIVE_WORLD
    name = _ACTIVE_WORLD
    if not name:
        try:
            name = active_world_file().read_text(encoding="utf-8").strip()
        except OSError:
            name = ""
    # The file is server-written, but it is still read back from disk:
    # hold it to the same bare-name rule as a request.
    try:
        return safe_pack_name(name)
    except ValueError:
        return None


def set_active_world(name: str) -> None:
    """Remember + persist the active-world override.

    The caller has already validated `name` as a bare pack name that
    resolves to a real pack. The module global makes the switch take
    effect without a restart; the file makes it survive one.
    """
    global _ACTIVE_WORLD
    _ACTIVE_WORLD = name
    f = active_world_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f"{name}\n", encoding="utf-8")


def _pack_exists(name: str) -> bool:
    return (
        _pack_path(worlds_dir(), name).joinpath("world.json").is_file()
        or _pack_path(template_dir(), name).joinpath("world.json").is_file()
    )


def world_name() -> str:
    """Which world pack is loaded.

    VEFR_WORLD wins - the operator's env always has the last word.
    Then the runtime active-world override (what the web UI picked,
    in-memory or on disk), so the served page can switch worlds
    without a restart. Otherwise the first pack alphabetically
    across BOTH the rw canon mount and the ro template mount - the
    bones boot with any flesh, or none at all beyond the sample that
    ships with the engine. No pack name is ever special-cased here;
    the engine doesn't know or care whose story it's running.
    """
    env = os.environ.get('VEFR_WORLD')
    if env:
        return env
    active = active_world()
    # A persisted choice can outlive the pack it named; ignore a
    # stale one rather than loading a directory that isn't there.
    if active and _pack_exists(active):
        return active
    # Union of (rw canon) + (ro template), author canon wins on
    # conflict. The loader does the same merge; here we just need
    # *a* default if no env is set.
    seen: set[str] = set()
    candidates: list[Path] = []
    for base in (worlds_dir(), template_dir()):
        if not base.is_dir():
            continue
        for p in sorted(base.glob('*/world.json')):
            pack = p.parent.name
            if pack in seen:
                continue
            seen.add(pack)
            candidates.append(p.parent)
    if candidates:
        return candidates[0].name
    return 'sample-world'


def _pack_path(root: Path, name) -> Path:
    """A pack `name` under one of the two pack roots.

    Everything a request can carry, and every bare pack name, goes
    through resolve_under(): the guard that refuses a name which walks
    out of the root, whatever the caller's own validator said. An
    already-absolute path keeps the plain join it has always had - the
    CLI resolves its `--pack` argument to one (`vefr validate
    /srv/packs/mine`) and `load_world(str(pack))` passes one, both at
    the operator's own terminal.
    """
    s = os.fspath(name)
    if os.path.isabs(s):
        return root / s
    return resolve_under(root, s)


def pack_dir(name: str | None = None) -> Path:
    """The world pack directory: logbok, ledger, map, voices, config.

    The author canon wins: pack_dir() resolves to the rw mount if
    the pack is there, falling back to the ro template if not. This
    is the *write* path - the loader's *read* path walks both.

    A pack *name* is joined through _pack_path(), so a caller that
    skipped safe_pack_name() still cannot walk out of either root.
    """
    name = name or world_name()
    rw = _pack_path(worlds_dir(), name)
    if rw.is_dir():
        return rw
    ro = _pack_path(template_dir(), name)
    if ro.is_dir():
        return ro
    # Fall back to the rw path even if it doesn't exist; callers
    # that try to write to it will get a clear OSError, and the
    # `norns validate` / `migrate` flows can detect the missing
    # pack and tell the user.
    return rw


def pack_file(rel: str, name: str | None = None) -> Path:
    """A file inside a pack: pack_dir(), then `rel` under it.

    The pack *name* is guarded by _pack_path(); `rel` is the second
    join of the same shape, so it gets the same guard. It is a
    caller-supplied value too, and a pack-root join is exactly the
    place a "../" must not walk out of - the callers today pass
    literals ("logbok.md"), but the builder this function is has to
    hold whatever the next one passes.

    Downward segments still join as they always have
    ("voices/npc.md"); an absolute `rel`, or one that climbs out of
    the pack, raises instead of resolving.
    """
    return resolve_under(pack_dir(name), rel)


# The world whose play history lives in the unscoped files (journal.json,
# vault.json). History predates per-world files and was recorded almost
# entirely in the sample world, so it stays that world's.
LEGACY_HISTORY_WORLD = 'sample-world'


def world_scoped(base: Path, world: str | None = None) -> Path:
    """The per-world file for a history base path (journal, vault).

    journal.json -> journal.<world>.json beside it, so kept items and
    whispers never bleed between worlds. The legacy world keeps the
    base file itself. `world` defaults to the world being served.
    """
    w = world if world is not None else world_name()
    if not w or w == LEGACY_HISTORY_WORLD:
        return base
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', w)
    return base.with_name(f"{base.stem}.{safe}{base.suffix}")
