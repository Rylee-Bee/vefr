import os
from pathlib import Path


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
        if (cand / "worlds-template").is_dir() or (cand / "worlds").is_dir():
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


def world_name() -> str:
    """Which world pack is loaded.

    VEFR_WORLD wins. Otherwise the first pack alphabetically across
    BOTH the rw canon mount and the ro template mount - the bones
    boot with any flesh, or none at all beyond the sample that
    ships with the engine. No pack name is ever special-cased here;
    the engine doesn't know or care whose story it's running.
    """
    env = os.environ.get('VEFR_WORLD')
    if env:
        return env
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


def pack_dir(name: str | None = None) -> Path:
    """The world pack directory: logbok, ledger, map, voices, config.

    The author canon wins: pack_dir() resolves to the rw mount if
    the pack is there, falling back to the ro template if not. This
    is the *write* path - the loader's *read* path walks both.
    """
    name = name or world_name()
    rw = worlds_dir() / name
    if rw.is_dir():
        return rw
    ro = template_dir() / name
    if ro.is_dir():
        return ro
    # Fall back to the rw path even if it doesn't exist; callers
    # that try to write to it will get a clear OSError, and the
    # `norns validate` / `migrate` flows can detect the missing
    # pack and tell the user.
    return rw


def pack_file(rel: str, name: str | None = None) -> Path:
    return pack_dir(name) / rel
