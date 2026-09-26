"""The CLI's machine face: --json envelopes and exit codes (the Worlds contract)."""

import argparse
import json

import pytest

from vefr import spark as spark_mod
from vefr.cli import (EXIT_ERROR, EXIT_OK, EXIT_UNAVAILABLE, EXIT_USAGE,
                      cmd_spark_task, envelope)

KEYS = {"ok", "status", "changed", "warnings", "actions", "data"}


def _args(**kw):
    base = dict(task="dialogue", prompt="Two lines at dusk.", file=None, speaker=None,
                state=None, no_world=True, spark_url=None, inspect=False, json=True)
    base.update(kw)
    return argparse.Namespace(**base)


def _env(capsys):
    return json.loads(capsys.readouterr().out)


def test_envelope_has_the_stable_keys():
    assert set(envelope(True, "healthy", {"x": 1})) == KEYS


def test_unknown_task_is_a_usage_error(capsys):
    assert cmd_spark_task(_args(task="nonsense")) == EXIT_USAGE
    assert "unknown task" in capsys.readouterr().err


def test_inspect_makes_no_model_call(capsys, monkeypatch):
    monkeypatch.setattr(spark_mod, "_spark_completion",
                        lambda *a, **k: pytest.fail("inspect must not call the model"))
    assert cmd_spark_task(_args(inspect=True)) == EXIT_OK
    env = _env(capsys)
    assert set(env) == KEYS and env["status"] == "inspected"
    assert env["data"]["messages"][-1]["content"] == "Two lines at dusk."


def test_validated_result_goes_in_data(capsys, monkeypatch):
    monkeypatch.setattr(spark_mod, "_spark_completion",
                        lambda *a, **k: json.dumps({"text": "The stone holds the heat."}))
    assert cmd_spark_task(_args()) == EXIT_OK
    env = _env(capsys)
    assert env["ok"] and env["status"] == "validated"
    assert env["data"]["result"] == {"text": "The stone holds the heat."}


def test_malformed_output_fails_closed(capsys, monkeypatch):
    monkeypatch.setattr(spark_mod, "_spark_completion", lambda *a, **k: "not json at all")
    assert cmd_spark_task(_args()) == EXIT_ERROR
    env = _env(capsys)
    assert not env["ok"] and env["status"] == "malformed" and "result" not in env["data"]


def test_unreachable_spark_is_exit_3(capsys, monkeypatch):
    def down(*a, **k):
        raise spark_mod.SparkUnavailable("spark unreachable at http://127.0.0.1:1")
    monkeypatch.setattr(spark_mod, "_spark_completion", down)
    assert cmd_spark_task(_args()) == EXIT_UNAVAILABLE
    env = _env(capsys)
    assert env["status"] == "unavailable" and env["actions"] == ["ratatoskr spark status"]


def test_plain_mode_prints_result_and_meta_line(capsys, monkeypatch):
    monkeypatch.setattr(spark_mod, "_spark_completion",
                        lambda *a, **k: json.dumps({"text": "Sit."}))
    assert cmd_spark_task(_args(json=False)) == EXIT_OK
    out = capsys.readouterr()
    assert json.loads(out.out) == {"text": "Sit."}
    assert out.err.startswith("[dialogue · profile ")
