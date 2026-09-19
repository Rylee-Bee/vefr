"""Evidence store. One JSONL line per trial; a run is a file.

Everything needed to answer "why did this model get this score?" is on the
line: participant artifact, runtime config, prompt(s), raw output, parse
artifacts, normalization flags, dimension scores, validator evidence, wire
stats, and the suite version.

Never delete or mutate prior run lines - a frozen suite's evidence is
append-only. New metadata produces a new run file, not edits.
"""

import json
import subprocess
import time
import uuid
from pathlib import Path

from .config import RUNDIR, SUITE_VERSION, MODELS_DIR, IMAGE, BOX, GEN


def probe_backend(cid):
    """OBSERVED backend evidence for a running server container.

    The claim 'vulkan' is only made when the drm render node is actually
    reachable inside the container (rootless podman shows an empty
    HostConfig.Devices despite --device working). Host amdgpu counters are
    sampled for contention context, never as a backend proof.
    """
    evidence = {"render_node": False}
    try:
        out = subprocess.run(
            ["podman", "exec", cid, "ls", "/dev/dri/"], capture_output=True, text=True, timeout=15
        )
        evidence["render_node"] = any(n.startswith("renderD") for n in out.stdout.split())
    except Exception:
        pass
    base = Path("/sys/class/drm/card1/device")
    for key, name in (
        ("vram_used_mib", "mem_info_vram_used"),
        ("vram_total_mib", "mem_info_vram_total"),
    ):
        try:
            evidence[key] = int(base.joinpath(name).read_text().strip()) // 1048576
        except Exception:
            pass
    try:
        evidence["gpu_busy_pct"] = int(base.joinpath("gpu_busy_percent").read_text().strip())
    except Exception:
        pass
    backend = "vulkan" if evidence["render_node"] else "cpu"
    return {"backend": backend, **evidence}


def new_run_id(participant_key, stage, version=SUITE_VERSION):
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return f"{ts}__{stage}__{participant_key}__{uuid.uuid4().hex[:6]}"


class TrialStore:
    def __init__(self, run_id, participant, stage, samples=None):
        self.run_id = run_id
        self.p = participant
        self.stage = stage
        self.path = RUNDIR / f"{run_id}.jsonl"
        self.header = {
            "run_id": run_id,
            "suite": "small-model-olympics",
            "suite_version": SUITE_VERSION,
            "stage": stage,
            "participant": participant.key,
            "family": participant.family,
            "params_b": participant.params_b,
            "quant": participant.quant,
            "artifact": participant.file,
            "artifact_path": str(MODELS_DIR / participant.file),
            "weight_class": participant.class_,
            "lineage": participant.lineage,
            "kind": participant.kind,
            "runtime": IMAGE,
            "engine": "llama.cpp llama-server (podman)",
            "box": BOX,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "samples": samples,
            "gen_defaults": {
                "temperature_default": GEN["temperature"],
                "max_tokens_default": GEN["max_tokens"],
            },
        }

    def write_header(self):
        with open(self.path, "w") as f:
            f.write(json.dumps({"kind": "run", "meta": self.header}) + "\n")

    def annotate(self, **kv):
        self.header.update(kv)

    def add_trial(self, trial):
        with open(self.path, "a") as f:
            f.write(json.dumps({"kind": "trial", "trial": trial}) + "\n")

    def add_abort(self, info):
        with open(self.path, "a") as f:
            f.write(json.dumps({"kind": "abort", "abort": info}) + "\n")

    def trial_count(self):
        try:
            return sum(1 for line in self.path.read_text().splitlines() if '"trial"' in line)
        except Exception:
            return 0


def summarize_run(run_id):
    """Return (participant, stage, trials) from a run file."""
    path = RUNDIR / f"{run_id}.jsonl"
    lines = path.read_text().splitlines()
    meta = next((json.loads(line)["meta"] for line in lines if '"run"' in line), {})
    trials = [json.loads(line)["trial"] for line in lines if '"trial"' in line]
    return meta, trials


def load_trials(run_id):
    return summarize_run(run_id)[1]
