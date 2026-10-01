"""The vefr front door: help, the verb set, alias wiring, exit codes.

The contract tests for `vefr` (`vefr_main` in src/vefr/cli.py):

* every door answers `--help` with exit 0 - the front door, the two
  old CLIs, and each verb;
* the SET of verbs in `vefr --help` is the contract (the prose is not);
* each verb dispatches to the SAME function object as its old
  spelling, asserted by running both parsers and comparing the
  resolved `fn` and flag defaults - not by grepping help text;
* no verb hides a reimplementation: every verb's `fn` is a module-level
  `cmd_*` of vefr.cli, and the vefr-only wrappers are proven thin;
* `vefr norns ARGS` / `vefr ratatoskr ARGS` reach the old CLIs' own
  behaviour verbatim;
* a usage error exits 2;
* `doctor --json` prints the six-key envelope - and `check --json` is
  a usage error (the NOTE on that test records the plan conflict).

Hermetic by construction: argv arrives through monkeypatched `sys.argv`,
every `cmd_*` is swapped for a recorder before a parser can dispatch
(no live model, no socket, no writes), and doctor's ambient rows are
pinned the way tests/test_doctor.py pins them.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import vefr.cli as cli
from vefr import find as find_mod

KEYS = {"ok", "status", "changed", "warnings", "actions", "data"}
ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PACK = ROOT / "worlds" / "sample-world"

NORNS = cli.norns_main
RATATOSKR = cli.ratatoskr_main

# The doors the front door names. `find` is a sibling task's verb,
# already present in the parser when this file was written, so it
# joins the expected set (a test that fails the moment a sibling
# lands is a bad test) - and its dispatch is covered below.
REQUIRED_VERBS = {
    "doctor", "check", "chat", "map", "delve", "weave", "spark",
    "test", "ferry", "handbok", "skipa", "norns", "ratatoskr",
}
VEFR_VERBS = REQUIRED_VERBS | {"find"}


# ------------------------------------------------------------- harness

def _recorded(monkeypatch):
    """Swap every `cmd_*` in vefr.cli for a dispatcher recorder.

    Each main() builds its parser at call time, so `set_defaults`
    picks the recorder up; the log keeps the ORIGINAL function object
    (captured before the swap) beside the namespace the verb dispatches
    with. Comparing those originals across two runs is the alias
    identity check - comparing the log entries alone would always
    match, which is exactly how such a test gets faked.
    """
    log = []
    for name, obj in sorted(vars(cli).items()):
        if name.startswith("cmd_") and callable(obj):
            def wrapper(args, _name=name, _fn=obj, _log=log):
                _log.append(SimpleNamespace(cmd=_name, fn=_fn, args=args))
                return 0
            monkeypatch.setattr(cli, name, wrapper)
    return log


def _dispatch(monkeypatch, log, main, argv):
    """Run one CLI front door over argv; return its single dispatch."""
    monkeypatch.setattr(sys, "argv", list(argv))
    rc = main()
    assert rc == cli.EXIT_OK
    assert len(log) == 1, f"{argv} produced {len(log)} dispatches, expected 1"
    return log.pop()


@pytest.fixture
def pinned_world(monkeypatch, tmp_path):
    """A resolved world that reads neither VEFR_WORLD nor the checkout:
    both mains' `--pack` defaulting runs through pack_root()/world_name()."""
    monkeypatch.setattr(cli, "pack_root", lambda: tmp_path)
    monkeypatch.setattr(cli, "world_name", lambda: "sample-world")
    return tmp_path / "worlds" / "sample-world"


def _main_for(argv):
    return {"vefr": cli.vefr_main, "norns": cli.norns_main,
            "ratatoskr": cli.ratatoskr_main}[argv[0]]


# ------------------------------------------------------------ 1. --help

HELP_ARGV = (
    [["vefr", "--help"]]
    + [["vefr", verb, "--help"] for verb in sorted(VEFR_VERBS)]
    + [["norns", "--help"], ["ratatoskr", "--help"]]
)


@pytest.mark.parametrize("argv", HELP_ARGV, ids=lambda a: " ".join(a))
def test_help_exits_zero(monkeypatch, capsys, argv):
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        _main_for(argv)()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("usage:"), argv


# ----------------------------------------------------------- 2. verbs

class _RecordingParser(argparse.ArgumentParser):
    """Every ArgumentParser vefr_main builds, remembered in order."""

    built: list = []

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        type(self).built.append(self)


class _ArgparseShim:
    """cli.argparse with only ArgumentParser swapped, so the verb-set
    test can read the parser object itself (the subparser choices)
    instead of re-parsing formatted help prose."""

    ArgumentParser = _RecordingParser

    def __getattr__(self, name):
        return getattr(argparse, name)


def test_vefr_help_names_every_verb(monkeypatch, capsys):
    _RecordingParser.built = []
    monkeypatch.setattr(cli, "argparse", _ArgparseShim())
    monkeypatch.setattr(sys, "argv", ["vefr", "--help"])
    with pytest.raises(SystemExit) as exc:
        cli.vefr_main()
    assert exc.value.code == 0

    top = next(p for p in _RecordingParser.built if p.prog == "vefr")
    sub = next(a for a in top._actions
               if isinstance(a, argparse._SubParsersAction))
    # the set of doors is the contract, asserted on the parser itself
    assert set(sub.choices) == VEFR_VERBS

    # and `vefr --help` NAMES every one of them, each on its own
    # command line (argparse's verb column sits at 2-8 spaces;
    # wrapped continuation lines are indented far deeper).
    out = capsys.readouterr().out
    for verb in sorted(VEFR_VERBS):
        assert re.search(rf"^ {{2,8}}{re.escape(verb)}\s", out, re.M), verb


# ------------------------------------------------- 3. alias dispatch

ALIAS_CASES = [
    # (vefr argv, old argv, old main, flags both must resolve to the
    #  same values, same_fn: identical resolved fn is the alias contract)
    (["check"], ["norns", "validate"], NORNS,
     {"map_cmd", "segments", "force", "pack"}, True),
    (["check", "--live", "http://live:8820"],
     ["norns", "verify", "--url", "http://live:8820"], NORNS,
     {"map_cmd", "url", "segments", "force", "pack"}, True),
    (["map", "--segments", "X"],
     ["norns", "build-map", "--segments", "X"], NORNS,
     {"map_cmd", "segments", "force", "pack"}, True),
    (["delve", "--pack", "p", "--seed", "s", "--from-region", "r",
      "--from-at", "1,2"],
     ["norns", "delve", "--pack", "p", "--seed", "s", "--from-region", "r",
      "--from-at", "1,2"], NORNS,
     {"pack", "seed", "floors", "from_region", "from_at", "width", "height",
      "rooms", "first_name", "force"}, True),
    (["weave"], ["ratatoskr", "weave"], RATATOSKR,
     {"pack", "out", "with_bundle", "vault", "journal", "pool",
      "from_live"}, True),
    (["handbok"], ["norns", "handbok"], NORNS, {"pack", "session"}, True),
    (["chat", "--name", "x"], ["norns", "chat", "--name", "x"], NORNS,
     {"name"}, True),
    (["test"], ["ratatoskr", "test"], RATATOSKR, {"test_args"}, True),
    (["spark", "status"], ["ratatoskr", "spark", "status"], RATATOSKR,
     {"profile", "host", "spark_url", "json"}, True),
    (["spark", "task", "npc", "hello"],
     ["ratatoskr", "spark", "task", "npc", "hello"], RATATOSKR,
     {"task", "prompt", "file", "speaker", "state", "no_world",
      "spark_url", "inspect", "json"}, True),
    (["ferry", "deploy"], ["ratatoskr", "ferry", "deploy"], RATATOSKR,
     {"url", "deploy_host", "deploy_vol", "nas_host", "ferry_verb",
      "init", "skip_tests", "rebuild", "no_health"}, True),
    # The two vefr-only wrappers: same resolved flags, and their fn is
    # deliberately its own function - the thinness proofs are
    # test_vefr_skipa_thins_cmd_skipa / test_vefr_doctor_reuses_machinery.
    (["doctor"], ["norns", "doctor"], NORNS, {"pack", "json"}, False),
    (["skipa"], ["ratatoskr", "skipa"], RATATOSKR,
     {"url", "deploy_host", "nas_host", "json"}, False),
]


@pytest.mark.parametrize(
    "vefr_argv,old_argv,old_main,shared,same_fn",
    ALIAS_CASES,
    ids=[c[0][0] if len(c[0]) == 1 else " ".join(c[0][:2])
         for c in ALIAS_CASES],
)
def test_alias_dispatch(monkeypatch, pinned_world, vefr_argv, old_argv,
                        old_main, shared, same_fn):
    """Both spellings dispatch through the same function object and
    resolve the same flag defaults (the namespace each fn receives)."""
    log = _recorded(monkeypatch)
    new = _dispatch(monkeypatch, log, cli.vefr_main, ["vefr"] + vefr_argv)
    old = _dispatch(monkeypatch, log, old_main, old_argv)

    if same_fn:
        assert new.fn is old.fn, (new.cmd, old.cmd)

    # every flag BOTH parsers declare must resolve to the same value...
    common = (set(vars(new.args)) & set(vars(old.args))) - {
        "fn", "cmd", "craft_cmd"}
    assert shared <= common, sorted(shared - common)
    diffs = {k: (vars(new.args)[k], vars(old.args)[k])
             for k in sorted(common)
             if vars(new.args)[k] != vars(old.args)[k]}
    assert diffs == {}, diffs


# --------------------------------------------------- 4. no reimplementation

# argv that reaches each verb's dispatch. The escape hatches are not
# dispatches: they hand argv to norns_main/ratatoskr_main verbatim.
DISPATCH_ARGV = {
    "find": ["find", "stone"],
    "doctor": ["doctor"],
    "check": ["check"],
    "chat": ["chat", "--name", "x"],
    "map": ["map", "--segments", "X"],
    "delve": ["delve", "--pack", "p", "--seed", "s", "--from-region", "r",
              "--from-at", "1,2"],
    "weave": ["weave"],
    "spark": ["spark", "status"],
    "test": ["test"],
    "ferry": ["ferry", "deploy"],
    "handbok": ["handbok"],
    "skipa": ["skipa"],
}


@pytest.mark.parametrize("verb", sorted(VEFR_VERBS - {"norns", "ratatoskr"}))
def test_no_verb_reimplements_a_command(monkeypatch, pinned_world, verb):
    """Every verb dispatches to a pre-existing module-level `cmd_*` of
    vefr.cli - not to logic written inside vefr_main's wiring. The
    identity-with-the-old-spelling half lives in test_alias_dispatch;
    the vefr-only wrappers are proven thin in their own tests below."""
    assert verb in DISPATCH_ARGV, f"add argv for the new {verb} verb"
    log = _recorded(monkeypatch)
    entry = _dispatch(monkeypatch, log, cli.vefr_main,
                      ["vefr"] + DISPATCH_ARGV[verb])
    assert entry.fn.__module__ == "vefr.cli"
    assert entry.fn.__name__.startswith("cmd_")
    # a nested def (a closure inside vefr_main) would carry a qualname
    # like `vefr_main.<locals>.<lambda>` - wiring-local reimplementation
    assert entry.fn.__qualname__ == entry.fn.__name__


def test_vefr_skipa_thins_cmd_skipa(monkeypatch, capsys):
    """`vefr skipa` is a one-line note over ratatoskr's own cmd_skipa:
    the old function runs, unchanged, with the same namespace."""
    seen = []
    monkeypatch.setattr(cli, "cmd_skipa", lambda args: seen.append(args) or 0)
    ns = SimpleNamespace(url=cli.DEFAULT_URL, deploy_host="",
                         nas_host="", json=False)
    assert cli.cmd_vefr_skipa(ns) == 0
    out = capsys.readouterr()
    assert seen and seen[0] is ns      # the old function got the args
    assert out.out == ""               # stdout keeps the old bytes
    assert "vefr doctor" in out.err    # the note rides on stderr only


def test_vefr_doctor_reuses_norns_doctor_machinery(monkeypatch, tmp_path):
    """cmd_vefr_doctor cannot literally call cmd_doctor (it appends
    skipa's three answers to doctor's rows), so the no-reimplementation
    proof is that BOTH route through the same row builders and the same
    reporter: doctor's logic exists once, and vefr doctor only adds rows."""
    calls = []
    monkeypatch.setattr(
        cli, "_doctor_local_rows",
        lambda pack: calls.append(("local", pack)) or [("git", "ok", "x")])
    monkeypatch.setattr(
        cli, "_doctor_live_row",
        lambda: calls.append(("live",)) or ("live", "skip", "x"))
    monkeypatch.setattr(
        cli, "q3_deployment",
        lambda url, host: calls.append(("q3",)) or ("down", "x"))
    monkeypatch.setattr(
        cli, "q5_backups",
        lambda host: calls.append(("q5",)) or ("fresh", "x"))
    monkeypatch.setattr(
        cli, "q6_vault",
        lambda host: calls.append(("q6",)) or ("persisted", "x"))
    # no deploy.toml under here, so --url stays the default
    monkeypatch.setattr(cli, "repo_root", lambda: tmp_path)

    def report(args, rows, header):
        calls.append(("report", header, tuple(r[0] for r in rows)))
        return cli.EXIT_OK

    monkeypatch.setattr(cli, "_doctor_report", report)

    ns = SimpleNamespace(pack=str(tmp_path / "w"), json=True,
                         url=cli.DEFAULT_URL, deploy_host="", nas_host="")
    assert cli.cmd_vefr_doctor(ns) == 0
    vefr_shape = list(calls)
    calls.clear()
    assert cli.cmd_doctor(ns) == 0
    norns_shape = list(calls)

    # both doctors build rows with the SAME helpers...
    assert {c[0] for c in vefr_shape} == {"local", "live", "q3", "q5", "q6",
                                          "report"}
    assert {c[0] for c in norns_shape} == {"local", "live", "report"}
    assert [c for c in vefr_shape if c[0] == "local"] == \
        [c for c in norns_shape if c[0] == "local"]
    # ...and report through the same reporter: vefr doctor is norns
    # doctor's rows plus skipa's three answers, nothing rewritten
    assert next(c for c in vefr_shape if c[0] == "report") == (
        "report", "vefr doctor",
        ("git", "live", "deploy", "backup", "vault"))
    assert next(c for c in norns_shape if c[0] == "report") == (
        "report", "norns doctor", ("git", "live"))


def test_vefr_find_delegates_to_the_find_module(monkeypatch, tmp_path,
                                                capsys):
    """`find` is a new door with no old spelling, so thinness is the
    delegation: cmd_find resolves the pack and hands the query to
    vefr.find - no search logic of its own."""
    seen = []
    monkeypatch.setattr(find_mod, "search",
                        lambda q, pack: seen.append((q, pack)) or [])
    (tmp_path / "world.json").write_text("{}", encoding="utf-8")
    rc = cli.cmd_find(SimpleNamespace(query="stone", pack=str(tmp_path)))
    out = capsys.readouterr().out
    assert rc == cli.EXIT_OK
    assert seen and seen[0][0] == "stone" and seen[0][1] == tmp_path
    assert "UNKNOWN" in out    # a search that found nothing still exits 0


# ------------------------------------------------- 5. escape hatches

def test_escape_hatch_norns_validate_help(monkeypatch, capsys):
    """`vefr norns validate --help` IS `norns validate --help`."""
    monkeypatch.setattr(sys, "argv", ["vefr", "norns", "validate", "--help"])
    with pytest.raises(SystemExit) as exc:
        cli.vefr_main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("usage: norns validate")


def test_escape_hatch_ratatoskr_weave_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv",
                        ["vefr", "ratatoskr", "weave", "--help"])
    with pytest.raises(SystemExit) as exc:
        cli.vefr_main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("usage: ratatoskr weave")


def test_escape_hatch_reaches_the_old_cli_error(monkeypatch, capsys):
    """A bad verb through the hatch gets the OLD parser's own error -
    the old prog's voice, not vefr's - and the old exit code."""
    monkeypatch.setattr(sys, "argv", ["vefr", "norns", "not-a-verb"])
    with pytest.raises(SystemExit) as exc:
        cli.vefr_main()
    assert exc.value.code == cli.EXIT_USAGE == 2
    # the OLD parser's own voice, after its usage block
    last = capsys.readouterr().err.splitlines()[-1]
    assert last.startswith("norns: error:")


# ------------------------------------------------------- 6. usage exit 2

USAGE_ERROR_ARGV = [
    ["vefr", "not-a-verb"],    # no such door
    ["vefr", "chat"],          # --name is required
    ["vefr", "map"],           # --segments is required
    ["vefr", "find"],          # the query positional is required
]


@pytest.mark.parametrize("argv", USAGE_ERROR_ARGV, ids=lambda a: " ".join(a))
def test_usage_errors_exit_two(monkeypatch, capsys, argv):
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        cli.vefr_main()
    assert exc.value.code == cli.EXIT_USAGE == 2
    # argparse prints the usage block first; the error line names the
    # parser that refused (`vefr: ...`, `vefr chat: ...`, `vefr find: ...`)
    last = capsys.readouterr().err.splitlines()[-1]
    assert last.startswith("vefr") and ": error:" in last


# ------------------------------------------------- 7. doctor --json

def test_doctor_json_envelope_on_the_sample_world(monkeypatch, capsys,
                                                  tmp_path):
    """`vefr doctor --json` against the shipped pack: valid JSON in the
    six-key envelope, with the right types - and hermetic: no ambient
    env, no socket, no writes (row drivers pinned the way
    tests/test_doctor.py pins them; the pack row runs for real)."""
    monkeypatch.setattr(
        cli, "q1_sync", lambda: ("in-sync", "local == remote @ abc1234"))
    monkeypatch.setattr(cli, "q2_dirty", lambda: ("clean", "0 changes"))
    monkeypatch.setattr(cli, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        cli, "_pytest_summary", lambda repo: ("ok", "passed tests in 0.5s"))

    def _offline(url, timeout=5):
        raise OSError("offline")

    # the health probe's one socket path, driven offline
    monkeypatch.setattr(cli, "fetch", _offline)
    # q5/q6 ssh unconditionally - pinned, never a connection
    monkeypatch.setattr(cli, "q5_backups",
                        lambda host: ("fresh", "bundle on nas"))
    monkeypatch.setattr(cli, "q6_vault",
                        lambda host: ("persisted", "~/vefr-data present"))
    monkeypatch.delenv("VEFR_LIVE_URL", raising=False)

    monkeypatch.setattr(
        sys, "argv",
        ["vefr", "doctor", "--json", "--pack", str(SAMPLE_PACK)])
    rc = cli.vefr_main()
    env = json.loads(capsys.readouterr().out)    # valid JSON, stdout only

    assert rc == cli.EXIT_OK
    assert set(env) == KEYS
    assert isinstance(env["ok"], bool)
    assert isinstance(env["status"], str)
    assert isinstance(env["changed"], bool)
    assert isinstance(env["warnings"], list)
    assert isinstance(env["actions"], list)
    assert isinstance(env["data"], dict)

    checks = env["data"]["checks"]
    assert checks and all(
        isinstance(c, dict)
        and all(isinstance(c[k], str) for k in ("name", "status", "detail"))
        for c in checks)
    counts = env["data"]["counts"]
    assert set(counts) == {"ok", "failed", "skipped"}
    assert all(isinstance(v, int) for v in counts.values())
    assert counts["failed"] == 0
    assert env["ok"] is True

    # the pack row is the REAL sample-world validation, by name
    pack_row = next(c for c in checks if c["name"] == "pack")
    assert pack_row["status"] == "ok" and "sample-world" in pack_row["detail"]
    # hermetic: no ambient VEFR_LIVE_URL and no deploy.toml under the
    # pinned repo root, so the live row skipped instead of probing
    live_row = next(c for c in checks if c["name"] == "live")
    assert live_row["status"] == "skip"
    # the deploy probe was answered by the offline stub, not a socket
    deploy_row = next(c for c in checks if c["name"] == "deploy")
    assert deploy_row["status"] == "down"


def test_check_rejects_json_flag(monkeypatch, capsys):
    # NOTE: plan conflict, resolved WITHOUT touching production code.
    # The plan's Task 3 asked to test `--json` on `check` too, but
    # Task 1 scopes `--json` to flags that "already exist" - and
    # `vefr check` is `norns validate`, which has no `--json` flag.
    # Adding one would be a NEW flag (the less restrictive option).
    # Reading taken: `check` legitimately has NO `--json` today, so
    # `vefr check --json` is a usage error (exit 2). Asserted as the
    # contract it is - not skipped, not "fixed" in the code under test.
    monkeypatch.setattr(sys, "argv", ["vefr", "check", "--json"])
    with pytest.raises(SystemExit) as exc:
        cli.vefr_main()
    assert exc.value.code == cli.EXIT_USAGE == 2
    assert "--json" in capsys.readouterr().err
