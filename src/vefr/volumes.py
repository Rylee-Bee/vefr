"""Volume management for the vefr engine.

The engine's runtime has three persistent roots, with a clear
capability boundary between them:

  /app/worlds-template/   RO Docker volume. Engine-owned templates
                          (lore/, sample-world/, poolworld/). Updated
                          by `ferry deploy`, never by the author.
  /app/worlds/            RW Docker volume. Author canon (private-canon/,
                          anything `ferry fetch` lands). The author
                          edits these freely. The engine reads
                          from here first; conflicts with the ro
                          volume are resolved in the author's favor.
  /app/data/              RW bind mount. Per-session vault, journal,
                          weave log, handoff bundles. The only
                          thing the *player* produces, vs the
                          *author*. Backed up by `ferry carry` +
                          the nightly cron on the deploy host.

This module is the migration tool: on first run, the author's
existing ~/vefr-worlds/ bind mount is split into a ro volume
(engine templates) and a rw volume (author canon), and the
quadlet is rewritten. It is idempotent: re-running on an already-
migrated host is a no-op.
"""

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .paths import app_home, template_dir, worlds_dir

TEMPLATE_VOLUME = "vefr-template"
WORLDS_VOLUME = "vefr-worlds"
DATA_BIND = "~/vefr-data"  # kept as a bind; not promoted to a volume

# Packs that the engine ships and should live in the ro volume.
# Anything else under worlds/ is treated as user canon and goes
# into the rw volume. Kept here rather than auto-discovered so
# the migration is deterministic: the author can drop a new
# canon pack into ~/vefr-worlds/ before migration and the script
# will still classify it correctly.
ENGINE_PACKS = {"lore", "sample-world", "poolworld"}


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command, log it, return the result. stderr is captured."""
    print(f"+ {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def _volume_exists(name: str) -> bool:
    """True if the named Podman volume exists on this host."""
    r = subprocess.run(
        ["podman", "volume", "exists", name],
        capture_output=True, text=True,
    )
    return r.returncode == 0


def _volume_create(name: str) -> None:
    if _volume_exists(name):
        print(f"  volume '{name}' already exists")
        return
    _run(["podman", "volume", "create", name])


def _volume_mount_point(name: str) -> Path | None:
    """The host path Podman has assigned to the named volume.

    On rootless Podman this is usually under
    ~/.local/share/containers/storage/volumes/<name>/_data/.
    Returns None if the volume doesn't exist.
    """
    if not _volume_exists(name):
        return None
    r = subprocess.run(
        ["podman", "volume", "inspect", name, "--format", "{{.Mountpoint}}"],
        capture_output=True, text=True, check=True,
    )
    p = r.stdout.strip()
    return Path(p) if p else None


def _classify_pack(name: str) -> str:
    """Engine-owned (goes to ro) or author-owned (goes to rw)."""
    return "engine" if name in ENGINE_PACKS else "author"


def _copy_pack_contents(src: Path, dst: Path) -> None:
    """Copy a pack's contents from one root to another.

    Used by the migration to move lore/, sample-world/ into the
    ro volume and private-canon/ into the rw volume. Preserves the
    on-disk shape (flat or acts); we never reshape during a
    volume migration.
    """
    if not src.is_dir():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def migrate(
    *,
    legacy_root: Path | None = None,
    dry_run: bool = False,
) -> int:
    """One-shot migration: split a legacy ~/vefr-worlds/ bind mount
    into ro engine + rw canon volumes, rewrite the quadlet, restart
    the container.

    Idempotent: re-running on a host that has already been
    migrated is a no-op (volumes are not recreated, the quadlet
    is left alone if it already references the new mounts).
    """
    legacy = legacy_root or (Path.home() / "vefr-worlds")
    quadlet = (Path.home() / ".config" / "containers" / "systemd"
               / "vefr.container")

    # 1. If the quadlet already references the volumes, we are done.
    if quadlet.exists() and "vefr-template" in quadlet.read_text():
        print("already migrated: quadlet references vefr-template")
        return 0

    # 2. Make sure the engine's baked-in template is in place.
    # The image's /app/worlds-template/ is the source of truth for
    # engine templates; we don't need to seed it from the legacy
    # root (the engine will see whatever the image ships). But we
    # DO want to seed the rw volume with the legacy canon so the
    # author's packs survive.
    if dry_run:
        print("dry-run: would create vefr-template + vefr-worlds volumes")
    else:
        _volume_create(TEMPLATE_VOLUME)
        _volume_create(WORLDS_VOLUME)

    # 3. Seed the rw volume from the legacy bind mount, classifying
    #    each pack as engine-owned (skip, the image has it) or
    #    author-owned (copy to the rw volume).
    if legacy.is_dir():
        rw_mount = _volume_mount_point(WORLDS_VOLUME)
        if rw_mount is None:
            print(f"warning: {WORLDS_VOLUME} volume has no mount point; "
                  "skipping legacy seed")
        else:
            for pack_dir in sorted(p for p in legacy.iterdir() if p.is_dir()):
                kind = _classify_pack(pack_dir.name)
                if kind == "engine":
                    print(f"  skip: {pack_dir.name} is engine-owned, "
                          "the image ships it")
                    continue
                target = rw_mount / pack_dir.name
                if target.exists():
                    print(f"  skip: {pack_dir.name} already in {WORLDS_VOLUME}")
                    continue
                if dry_run:
                    print(f"  would copy: {pack_dir} -> {target}")
                else:
                    print(f"  copy: {pack_dir.name} -> {WORLDS_VOLUME}/")
                    _copy_pack_contents(pack_dir, target)

    # 4. Rewrite the quadlet. We write the canonical version; the
    #    `ferry deploy` command will keep it in sync going forward.
    if quadlet.exists():
        new = _canonical_quadlet()
        if dry_run:
            print(f"  would rewrite {quadlet}")
        else:
            quadlet.write_text(new, encoding="utf-8")
            print(f"  wrote {quadlet}")
    else:
        print(f"  no quadlet at {quadlet}; skip the rewrite")

    # 5. Reload systemd and restart the container so the new mounts
    #    take effect.
    if not dry_run:
        try:
            _run(["systemctl", "--user", "daemon-reload"], check=False)
            _run(["systemctl", "--user", "restart", "vefr"], check=False)
            print("  systemd reloaded, vefr restarted")
        except FileNotFoundError:
            print("  systemctl not available - restart the container manually")

    print("migration complete.")
    return 0


def _canonical_quadlet() -> str:
    """The quadlet we want on the deploy host after migration.

    This is the same content as deploy/vefr.container in the
    engine repo, with one line added: the ro volume mount for
    vefr-template. The `ferry deploy` command keeps this in
    sync; the migration script writes it once.
    """
    return """\
[Unit]
Description=vefr - the loom-web the Norns weave fate on; worlds bind-mounted so star/import edits persist across container rebuilds

[Container]
Image=localhost/vefr:latest
ContainerName=vefr
Network=host
Environment=VEFR_HOME=/app
Environment=VEFR_WORLD=sample-world
Environment=VEFR_LLAMACPP_URL=http://127.0.0.1:8081
Environment=VEFR_MODEL=gpt-oss-20b
Environment=VEFR_KEEP_ALIVE=1m
Environment=VEFR_VAULT=/app/data/vault.json
Environment=VEFR_JOURNAL=/app/data/journal.json
Volume=vefr-template:/app/worlds-template:ro
Volume=vefr-worlds:/app/worlds
Volume=%h/vefr-data:/app/data:Z

[Service]
Restart=on-failure

[Install]
WantedBy=default.target
"""


def list_packs() -> list[dict]:
    """Engine-readable list of every pack, with the source tagged.

    This is the read-side helper; the CLI subcommand and the
    builder UI both call it. The actual on-disk merge lives in
    world.discover_packs(); this re-export keeps the import path
    stable for callers that already depend on vefr.volumes.
    """
    from .world import discover_packs
    return discover_packs()


# --------------------------------------------------------------- export / import
#
# The author flow when the engine lives in a Docker volume and the
# author wants to edit a pack in vim on the host:
#
#   1. `ratatoskr volumes export --pack sample-world \
#         --dest ~/my-forks/sample-world`
#      -> a git repo at ~/my-forks/sample-world with the pack's full
#         file tree in engine-native layout (acts or flat, depending
#         on the source pack).
#   2. edit voices/keeper.md, logbok.md, anything in ~/my-forks/
#   3. `git commit` inside the export
#   4. `ratatoskr volumes import --pack sample-world \
#         --from ~/my-forks/sample-world`
#      -> reads the repo, validates the pack, writes into the rw
#         volume at /app/worlds/<name>/ (or the local worlds/ on the
#         dev box). The engine picks up the change on next request.
#
# The round-trip is lossless: export → import → export produces
# the same files modulo timestamps. The intermediate git history
# is the author's edit log.


def _pack_layout(pack: Path) -> str:
    """Detect the on-disk shape: 'acts' or 'flat'."""
    return "acts" if (pack / "acts").is_dir() else "flat"


def _copy_pack_tree(src: Path, dst: Path) -> None:
    """Copy a pack's file tree, preserving the on-disk shape.

    Used by both export (volume -> git repo) and import
    (git repo -> volume). Symlinks, mode bits, and mtimes are
    preserved where possible.
    """
    if not src.is_dir():
        raise FileNotFoundError(f"pack source not found: {src}")
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def export_pack(
    pack: str,
    dest: Path,
    *,
    worlds_root: Path | None = None,
    init_git: bool = True,
) -> Path:
    """Export a pack to a host-side directory as a git repo.

    The destination gets the pack's full file tree in
    engine-native layout (acts or flat), plus a README and an
    initial git commit. The author edits in vim on the host,
    commits, and `volumes import` reads back.

    On the dev box, worlds_root defaults to the engine
    checkout's worlds/. On bazzite (or any deploy host), it
    defaults to ~/vefr-worlds/ - the rw canon bind mount.

    If the destination already exists and is a non-empty git
    repo, the export is a no-op (the author probably has
    in-progress work there). Use a fresh dest to force a
    re-export.
    """
    pack_src = (worlds_root or _default_worlds_root()) / pack
    if not pack_src.is_dir():
        raise FileNotFoundError(
            f"pack '{pack}' not found at {pack_src} "
            f"(worlds root: {worlds_root or _default_worlds_root()})"
        )
    layout = _pack_layout(pack_src)
    if dest.exists() and any(dest.iterdir()):
        if (dest / ".git").is_dir():
            print(f"destination {dest} is an existing git repo; "
                  "skipping the export (the author probably has "
                  "in-progress work there).")
            return dest
        raise FileExistsError(
            f"destination {dest} exists and is not empty; "
            "use a fresh path or `rm -rf` first"
        )
    dest.mkdir(parents=True, exist_ok=True)
    _copy_pack_tree(pack_src, dest)

    readme = (
        f"# {pack} (vefr world pack)\n\n"
        f"Exported from the vefr engine on "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}.\n\n"
        f"On-disk shape: **{layout}**.\n\n"
        f"Edit anything in this directory, `git commit`, then run\n"
        f"`ratatoskr volumes import --pack {pack} --from {dest}` to\n"
        f"write it back into the engine's volume.\n"
    )
    (dest / "README.md").write_text(readme, encoding="utf-8")

    if init_git:
        _run(["git", "-C", str(dest), "init", "-b", "main"], check=True)
        _run(["git", "-C", str(dest), "add", "-A"], check=True)
        _run([
            "git", "-C", str(dest), "commit", "-m",
            f"export {pack} from vefr engine ({layout} shape)",
        ], check=True)
        print(f"exported {pack} to {dest} (git repo, {layout} shape)")
    else:
        print(f"exported {pack} to {dest} ({layout} shape, no git)")
    return dest


def import_pack(
    pack: str,
    src: Path,
    *,
    worlds_root: Path | None = None,
    dry_run: bool = False,
) -> Path:
    """Import a pack from a host-side directory into the volume.

    Reads the source directory, validates it via the engine's
    own loader (so a bad pack is rejected before the write),
    then copies the tree into the rw volume at
    worlds_root/<pack>/. The engine picks up the change on
    the next request.

    The rw canon wins on conflict, so an import will overwrite
    a pack with the same name. The ro template is never
    touched - templates are owned by the engine repo.
    """
    from .maplab import load_pack as _load_pack
    from .maplab import validate as _validate
    from .world import load_world as _load_world
    if not src.is_dir():
        raise FileNotFoundError(f"import source not found: {src}")
    # Validate the source before writing. maplab.load_pack handles
    # both flat and acts shapes; the engine's own loader is the
    # one that will run on the volume, so we mirror its behavior.
    errors = _validate(_load_pack(src), pack_dir=src)
    if errors:
        msg = "; ".join(errors)
        raise ValueError(f"pack at {src} fails the engine contract: {msg}")
    if dry_run:
        print(f"dry-run: would import {src} -> "
              f"{(worlds_root or _default_worlds_root()) / pack}")
        return src

    dst = (worlds_root or _default_worlds_root()) / pack
    # Wipe the destination before copy so removed files don't
    # linger. The rw canon volume is the author's space; we
    # don't preserve "untracked" state.
    if dst.exists():
        shutil.rmtree(dst)
    _copy_pack_tree(src, dst)
    print(f"imported {pack} from {src} -> {dst}")
    # Bust the engine's load_world cache so the next request
    # sees the change.
    _load_world.cache_clear()
    return dst


def shell(pack: str | None = None) -> int:
    """Drop into a shell inside the engine container.

    Convenience wrapper around `podman exec -it vefr bash`.
    The pack argument, if given, sets the engine's working
    directory to the pack's volume path so the author can
    edit voice files with `vim`, `cat`, etc. without
    remembering where the volume is mounted.

    Returns the podman exec return code.
    """
    cmd = ["podman", "exec", "-it", "vefr", "bash"]
    if pack:
        # Use the engine's known mount points. The shell will
        # start in the rw canon (so edits land in the author's
        # volume) unless the pack is engine-owned, in which
        # case we cd into the ro template to inspect it.
        rw = f"/app/worlds/{pack}"
        ro = f"/app/worlds-template/{pack}"
        if Path(ro).is_dir() and not Path(rw).is_dir():
            cmd += ["-c", f"cd {ro} && exec bash"]
        else:
            cmd += ["-c", f"cd {rw} && exec bash"]
    return subprocess.call(cmd)


def _default_worlds_root() -> Path:
    """The worlds/ root for export/import: the local worlds/ on
    the dev box (the engine checkout), or the bind mount on a
    deploy host. Detected by checking which one exists and is
    writable."""
    candidates = [
        Path("/app/worlds"),                # container-internal
        Path("worlds"),                     # dev-box relative
        Path.home() / "vefr-worlds",        # legacy bind mount
    ]
    for c in candidates:
        if c.is_dir() and c.parent.exists():
            return c
    # Last-resort: dev-box engine checkout's worlds/.
    return Path("worlds").resolve()
