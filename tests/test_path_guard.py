"""The join guard: resolve_under(), and the routes it stands behind.

safe_pack_name() and sessions.clean() say a *name* must be a bare
segment; resolve_under() refuses the *join* that turns a name into a
path. This is the second layer the CodeQL path-injection alerts need
(a regex is not a barrier to that query; a normpath + startswith test
whose failing branch raises is), so these pins hold the function's own
behaviour as well as the routes that now route through it.

The guard is lexical, not physical: normpath, not realpath. A symlink
that already lives inside the base and points out of it still
resolves - that is the operator's own tree, not a request value - and
`test_a_symlink_is_not_resolved_away` says so out loud.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vefr import journal, saga
from vefr.main import app
from vefr.paths import pack_dir, pack_file, resolve_under, worlds_dir
from vefr.sessions import derive

BASE = Path("/srv/vefr/worlds")
ROOT = Path(__file__).resolve().parents[1]


# ---- resolve_under itself ----


def test_accepts_a_plain_segment():
    assert resolve_under(BASE, "sample-world") == BASE / "sample-world"


def test_accepts_nested_segments():
    assert resolve_under(BASE, "pack", "acts", "act-1") == BASE / "pack" / "acts" / "act-1"


def test_accepts_a_str_base_and_several_parts():
    assert resolve_under(os.fspath(BASE), "a", "b.md") == BASE / "a" / "b.md"


def test_an_empty_part_joins_back_to_the_base():
    """`os.path.join(base, "")` is base + sep; normpath puts it home."""
    assert resolve_under(BASE, "") == BASE


def test_no_parts_is_the_base():
    assert resolve_under(BASE) == BASE


def test_a_dot_inside_the_base_is_normalised_not_refused():
    assert resolve_under(BASE / "." / "sub" / "..", "pack") == BASE / "pack"


@pytest.mark.parametrize(
    "parts",
    [
        ("..",),                       # the base's own parent
        ("../x",),                     # straight out
        ("a", "..", "..", "..", "x"),  # up through the segments we just joined
        ("/etc",),                     # absolute, single part
        ("pack", "/etc/passwd"),       # absolute second part
        ("..%s..%ssecret" % (os.sep, os.sep),),  # a separator that climbs out
        ("pack/../../elsewhere",),     # a separator mid-part that climbs out
        ("", ".."),                    # an empty part does not buy a level back
    ],
)
def test_refuses_to_leave_the_base(parts):
    with pytest.raises(ValueError, match="escapes its base"):
        resolve_under(BASE, *parts)


def test_a_sibling_with_a_shared_prefix_is_refused():
    """/srv/vefr/worlds-evil is not under /srv/vefr/worlds."""
    with pytest.raises(ValueError, match="escapes its base"):
        resolve_under(BASE, "../worlds-evil")


def test_a_symlink_is_not_resolved_away(tmp_path):
    """normpath, not realpath: the guard is lexical on purpose.

    A symlink the operator put inside the base keeps working; what it
    points at is their tree, and following it would also break every
    mount that is a symlink (the container's /app/worlds is one).
    """
    real = tmp_path / "elsewhere"
    real.mkdir()
    base = tmp_path / "worlds"
    base.mkdir()
    (base / "linked").symlink_to(real)

    got = resolve_under(base, "linked", "pack.json")

    assert got == base / "linked" / "pack.json"


# ---- the central builders that now go through it ----


def test_pack_dir_refuses_a_name_that_walks_out(fixture_vefr_home):
    for bad in ("../evil", "../../evil", "..", "a/../../evil"):
        with pytest.raises(ValueError, match="escapes its base"):
            pack_dir(bad)
    assert resolve_under(worlds_dir(), "four-phase-pack").is_dir()
    # a name that only goes *down* is still joined, as it always was
    assert pack_dir("a/b") == worlds_dir() / "a" / "b"


def test_pack_dir_still_takes_a_bare_name_and_an_absolute_path(fixture_vefr_home, tmp_path):
    """The guard must not cost the CLI its `--pack /srv/packs/mine`
    (it resolves to an absolute path) or a test its `load_world(str(pack))`."""
    assert pack_dir("four-phase-pack") == worlds_dir() / "four-phase-pack"

    elsewhere = tmp_path / "elsewhere-pack"
    shutil.copytree(fixture_vefr_home / "worlds" / "four-phase-pack", elsewhere)
    assert pack_dir(str(elsewhere)) == elsewhere


@pytest.mark.parametrize(
    "rel",
    [
        "../evil.md",                 # out of the pack, one level
        "../../evil.md",              # out of the pack, two levels
        "..",                         # the pack's own parent
        "voices/../../evil.md",       # up through a segment we just joined
        "/etc/passwd",                # absolute, ignoring the pack entirely
        "voices/../../../../evil.md", # far enough up to leave the tree
    ],
)
def test_pack_file_refuses_a_rel_that_walks_out_of_the_pack(fixture_vefr_home, rel):
    """The pack *name* is guarded by _pack_path(); `rel` is the second
    join of the same shape and gets the same guard."""
    with pytest.raises(ValueError, match="escapes its base"):
        pack_file(rel, "four-phase-pack")

    assert sorted(p.name for p in fixture_vefr_home.iterdir()) == ["worlds"]
    assert sorted(p.name for p in worlds_dir().iterdir()) == ["four-phase-pack"]


def test_pack_file_still_joins_a_plain_or_nested_rel(fixture_vefr_home, monkeypatch):
    """The guard is a second layer over the join, not a new rule: the
    downward joins callers make today still resolve to the same path."""
    pack = worlds_dir() / "four-phase-pack"

    assert pack_file("world.json", "four-phase-pack") == pack / "world.json"
    assert pack_file("voices", "four-phase-pack") == pack / "voices"
    assert pack_file("voices/npc.md", "four-phase-pack") == pack / "voices" / "npc.md"

    monkeypatch.setenv("VEFR_WORLD", "four-phase-pack")  # the no-name default
    assert pack_file("world.json") == pack / "world.json"


def test_pack_file_still_follows_an_absolute_pack(fixture_vefr_home, tmp_path):
    """The CLI resolves `--pack /srv/packs/mine` to an absolute path, so
    `rel` is guarded against *that* directory, not against worlds/."""
    elsewhere = tmp_path / "elsewhere-pack"
    shutil.copytree(fixture_vefr_home / "worlds" / "four-phase-pack", elsewhere)

    assert pack_file("world.json", str(elsewhere)) == elsewhere / "world.json"
    with pytest.raises(ValueError, match="escapes its base"):
        pack_file("../evil.md", str(elsewhere))


def test_logbok_still_reads_through_the_guarded_pack_file(fixture_vefr_home):
    """The one real caller, end to end: saga.logbok() must not have
    lost the pack it reads."""
    (worlds_dir() / "four-phase-pack" / "logbok.md").write_text(
        "the canon line", encoding="utf-8"
    )

    assert saga.logbok("four-phase-pack") == "the canon line"


def test_derive_keeps_every_id_that_works_today(tmp_path):
    base = tmp_path / "journal.json"
    assert derive(base, "a1b2c3d4") == tmp_path / "journal-a1b2c3d4.json"
    assert derive(base, "Good-Id_1") == tmp_path / "journal-Good-Id_1.json"
    assert derive(base, None) == base
    assert derive(base, "default") == base


@pytest.mark.parametrize("sid", ["../evil", "../../evil", "a/b", "..", "x/../y"])
def test_a_session_id_with_a_separator_cannot_escape_the_data_dir(
    tmp_path, monkeypatch, sid
):
    """clean() is the rule; the join it feeds is guarded underneath it."""
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal.json")

    path = journal.journal_path(sid)
    journal.log("rumor", sid=sid, whisper="one")

    assert tmp_path in path.parents
    assert list(tmp_path.parent.glob("*evil*")) == []
    assert [e["whisper"] for e in journal.list_entries(sid=sid)] == ["one"]


def test_a_session_id_cannot_write_outside_a_relative_base(tmp_path, monkeypatch):
    """A bare relative base keeps its old answer - clean() already
    leaves no separator in the name for the join to climb out with."""
    monkeypatch.chdir(tmp_path)
    assert derive(Path("journal.json"), "s1") == Path("journal-s1.json")


# ---- the request-facing routes ----


def test_the_builder_refuses_a_traversal_world_name(fixture_vefr_home):
    home = Path(os.environ["VEFR_HOME"])
    r = TestClient(app).post("/api/builder/worlds", json={"name": "../../evil"})

    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "world must be a bare pack name"
    assert not (home.parent / "evil").exists()
    assert sorted(p.name for p in worlds_dir().iterdir()) == ["four-phase-pack"]


def test_the_builder_still_creates_a_bare_name(fixture_vefr_home):
    """The guard is a second layer, not a new rule: a bare name still
    lands under worlds/ (the full create flow lives in test_world_create).
    """
    home = Path(os.environ["VEFR_HOME"])
    (home / "worlds" / "sample-world").mkdir(parents=True)
    shutil.copytree(ROOT / "worlds" / "sample-world", home / "worlds" / "sample-world",
                    dirs_exist_ok=True)

    r = TestClient(app).post("/api/builder/worlds", json={"name": "new-world"})

    assert r.status_code == 200, r.text
    assert (worlds_dir() / "new-world" / "world.json").is_file()


def test_the_features_route_refuses_a_traversal_pack(fixture_vefr_home):
    r = TestClient(app).get("/api/features", params={"pack": "../../etc"})

    assert r.status_code == 400, r.text


def test_the_features_route_still_reads_a_bare_pack(fixture_vefr_home):
    r = TestClient(app).get("/api/features", params={"pack": "four-phase-pack"})

    assert r.status_code == 200, r.text


def test_room_art_sticker_traversal_is_a_404_not_a_file(monkeypatch, tmp_path):
    """The sticker's id is pasted into a filename; the allow-list and
    the join both refuse a "../" in it."""
    monkeypatch.setenv("VEFR_ROOM_TOKEN", "test-token")
    monkeypatch.setenv("VEFR_HOME", str(tmp_path))
    secret = tmp_path / "secret.webp"
    secret.write_bytes(b"not art")

    r = TestClient(app).get(
        "/room/art/stickers-..%2F..%2Fsecret.webp",
        headers={"Authorization": "Bearer test-token"},
    )

    assert r.status_code == 404, r.status_code
