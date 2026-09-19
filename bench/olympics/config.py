"""Olympics suite configuration - paths and defaults.

The rig is deliberately stdlib-only (urllib, json, argparse) so it can be
versioned and run anywhere without dependency drift. All GPU/CPU work happens
in a llama.cpp llama-server podman container; this rig only points at it.
"""

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BENCH = REPO / "bench"

RUNDIR = BENCH / "runs"
REPORTDIR = BENCH / "reports"

MODELS_DIR = Path(
    os.environ.get("OLY_MODELS_DIR", Path.home() / "llama-server" / "models" / "bench")
)

# server lifecycle
IMAGE = os.environ.get("OLY_IMAGE", "ghcr.io/ggml-org/llama.cpp:server-vulkan")
SERVER_CTX = int(os.environ.get("OLY_CTX", "8192"))
SERVER_THREADS = int(os.environ.get("OLY_THREADS", "8"))
SERVE_PORT_BASE = int(os.environ.get("OLY_SERVE_PORT_BASE", "9000"))
NGPU = int(os.environ.get("OLY_NGPU", "999"))
BOX = "bazzite"  # host we run on; recorded for provenance

# generation defaults (canonical bounded-work config; per-task may override)
GEN = {"temperature": 0.3, "max_tokens": 768}
GEN_TOOL = {"temperature": 0.3, "max_tokens": 512}
GEN_STORY = {"temperature": 0.85, "max_tokens": 1024}

# suite versioning
SUITE_NAME = "Small Model Olympics"
SUITE_VERSION = "0.4.1"
SUITE_STATUS = "research/dev (not yet frozen)"


def ensure_dirs():
    for d in (RUNDIR, REPORTDIR):
        d.mkdir(parents=True, exist_ok=True)


# weight classes by params (billions), for reporting
def weight_class(params_b: float) -> str:
    if params_b < 0.5:
        return "FEATHERWEIGHT"
    if params_b < 1.0:
        return "BANTAMWEIGHT"
    if params_b < 1.5:
        return "LIGHTWEIGHT"
    if params_b < 2.5:
        return "WELTERWEIGHT"
    return "MIDDLEWEIGHT"