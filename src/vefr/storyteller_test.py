"""Storyteller Audition Harness.

A tiny, repeatable way to run the same VEFR scene through several
local models and compare whether the resulting characters feel alive.

This is NOT a benchmark suite. No automated scoring. No leaderboard.
The output is human-readable prose, side by side, so a reader can
compare characters and decide which pack brings them alive.

Architecture:
    VEFR scene state
        ↓
    context / story packet builder (this module)
        ↓
    Storyteller Pack (data/storytellers/... or storyteller_packs/...)
        ↓
    provider adapter (generator._completion)
        ↓
    model
        ↓
    narrative response

That is the same route the eventual game uses. We are testing the
architecture as much as the models.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

from .storyteller import (
    ScenePacket,
    Storyteller,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "storyteller"
ARTIFACTS_ROOT = Path(__file__).resolve().parent.parent.parent / "artifacts" / "storyteller-tests"


@dataclass(frozen=True)
class SceneFixture:
    """One canonical VEFR scene for the audition.

    A fixture is data, not code. It carries everything the packet
    builder needs to construct a ScenePacket without leaking
    character-specific assumptions into the engine (the spec's
    "no game-specific characters in engine code" rule).
    """

    id: str
    speaker: str
    speaker_knows: str
    speaker_does_not_know: str
    scene: str
    relationship: str
    recent_action: str
    open_threads: str
    instruction: str = "Respond naturally. Do not reveal facts the speaker cannot know. Do not resolve every mystery. Leave room for the player to continue."
    version: str = "0.1.0"

    def to_packet(self) -> ScenePacket:
        """Build the ScenePacket this fixture describes.

        The packet builder is the boundary the engine owns: every
        model in the audition gets the same packet, so comparison
        is meaningful. The fixture supplies the semantics; the
        packet supplies the shape.
        """
        return ScenePacket(
            speaker=self.speaker,
            speaker_knows=self.speaker_knows,
            speaker_does_not_know=self.speaker_does_not_know,
            scene=self.scene,
            relationship=self.relationship,
            recent_action=self.recent_action,
            open_threads=self.open_threads,
            instruction=self.instruction,
        )


@dataclass(frozen=True)
class RunResult:
    """One audition run against one pack, one scene.

    Output fields are intentionally simple - the harness is for
    humans reading prose, not for a metrics dashboard. Latency is
    always present; token counts only when the backend reports them.
    """

    pack_id: str
    model: str
    provider: str
    scene_id: str
    scene_version: str
    run_number: int  # 1-indexed
    seed: int | None
    status: str  # "ok" | "skipped" | "error"
    skip_reason: str = ""
    error: str = ""
    response: str = ""
    latency_s: float = 0.0
    output_tokens: int | None = None
    sampling: dict = field(default_factory=dict)
    pack_license: dict = field(default_factory=dict)


# Fixtures are JSON files. The engine bundles one neutral sample under
# tests/fixtures/storyteller/; a pack supplies its own scenes from its
# own repo by pointing VEFR_STORYTELLER_FIXTURES at extra directories
# (PATH-style). Fixture content follows ownership: story data lives
# with whoever owns the story (D6).
def fixture_dirs() -> list[Path]:
    """Every directory the fixture search covers, in priority order.

    Explicit configuration wins over the bundled default: env-supplied
    dirs come first, the engine's own dir is the fallback.
    """
    dirs: list[Path] = []
    for part in os.environ.get("VEFR_STORYTELLER_FIXTURES", "").split(os.pathsep):
        if part.strip():
            dirs.append(Path(part.strip()))
    dirs.append(FIXTURES_DIR)
    return dirs


def load_fixture(scene_id: str) -> SceneFixture:
    """Load a named scene fixture from the first dir that carries it.

    Raises FileNotFoundError if the fixture id is unknown - the
    caller (CLI) catches that and prints the available list.
    """
    for dir_ in fixture_dirs():
        path = dir_ / f"{scene_id}.json"
        if path.is_file():
            return SceneFixture(**json.loads(path.read_text(encoding="utf-8")))
    raise FileNotFoundError(
        f"fixture {scene_id!r} not found in: "
        + ", ".join(str(d) for d in fixture_dirs())
    )


def list_fixtures() -> list[str]:
    """All fixture ids the harness knows about, across every search dir."""
    ids: set[str] = set()
    for dir_ in fixture_dirs():
        if dir_.is_dir():
            ids.update(p.stem for p in dir_.glob("*.json"))
    return sorted(ids)


def audition_one(
    pack: Storyteller,
    scene: SceneFixture,
    *,
    run_number: int = 1,
    seed: int | None = None,
    max_tokens: int = 180,
) -> RunResult:
    """Run the scene through one pack, one time.

    Returns a RunResult with status="skipped" if the pack's model
    is not actually loaded on the backend (HTTP 404 from ollama,
    "model not found" from llama.cpp, etc.) so a matrix run can
    continue past a missing candidate rather than crashing.

    The HTTP probe happens lazily inside the call; we use a tiny
    request and translate the failure mode uniformly.
    """
    from .generator import storytell

    started = time.monotonic()
    try:
        response = storytell(scene.to_packet(), temperature=None)
    except Exception as e:  # noqa: BLE001 - audit mode: never crash a matrix run
        return RunResult(
            pack_id=pack.id,
            model=pack.model,
            provider=pack.model_provider.value,
            scene_id=scene.id,
            scene_version=scene.version,
            run_number=run_number,
            seed=seed,
            status="skipped" if _looks_like_missing_model(e) else "error",
            skip_reason=str(e) if _looks_like_missing_model(e) else "",
            error="" if _looks_like_missing_model(e) else str(e),
            latency_s=time.monotonic() - started,
            sampling=dict(pack.sampling),
            pack_license=asdict(pack.license) if pack.license else {},
        )
    elapsed = time.monotonic() - started
    return RunResult(
        pack_id=pack.id,
        model=pack.model,
        provider=pack.model_provider.value,
        scene_id=scene.id,
        scene_version=scene.version,
        run_number=run_number,
        seed=seed,
        status="ok",
        response=response,
        latency_s=elapsed,
        sampling=dict(pack.sampling),
        pack_license=asdict(pack.license) if pack.license else {},
    )


def _looks_like_missing_model(exc: Exception) -> bool:
    """Heuristic: is this exception a "model not loaded" failure?

    Keeps the matrix run moving past a not-yet-downloaded model
    without pretending a hard error is a skip.
    """
    msg = str(exc).lower()
    needles = (
        "model not found",
        "model '",
        "no such model",
        "404",
        "not installed",
        "unknown model",
    )
    return any(n in msg for n in needles)


def write_artifacts(results: list[RunResult], *, out_dir: Path | None = None) -> Path:
    """Save a matrix run's results to a timestamped directory.

    Layout per spec:
        artifacts/storyteller-tests/<timestamp>/
            manifest.json   # every result, structured
            <pack_id>.txt    # one file per pack, prose only, repeated runs concatenated
            blind_map.txt    # only when --blind was used
    """
    out_dir = out_dir or (ARTIFACTS_ROOT / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps([asdict(r) for r in results], indent=2, default=str),
        encoding="utf-8",
    )

    # Group prose by pack; one file per pack keeps the artifacts easy
    # to skim with `less` or paste into a doc.
    by_pack: dict[str, list[RunResult]] = {}
    for r in results:
        by_pack.setdefault(r.pack_id, []).append(r)

    for pack_id, runs in by_pack.items():
        lines = []
        for r in sorted(runs, key=lambda x: x.run_number):
            lines.append(f"--- run {r.run_number} | status={r.status} | {r.latency_s:.2f}s ---")
            if r.status == "ok":
                lines.append(r.response)
            elif r.status == "skipped":
                lines.append(f"SKIPPED - {r.skip_reason}")
            else:
                lines.append(f"ERROR - {r.error}")
            lines.append("")
        (out_dir / f"{pack_id}.txt").write_text("\n".join(lines), encoding="utf-8")

    return out_dir


def build_blind_map(results: list[RunResult]) -> dict[str, str]:
    """Map pack_id -> anonymous label for blind evaluation.

    Returned in the order results first appear so a side-by-side
    read can be reconstructed even if the manifest is shuffled.
    """
    label_pool = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    mapping: dict[str, str] = {}
    idx = 0
    for r in results:
        if r.pack_id not in mapping:
            mapping[r.pack_id] = f"Storyteller {label_pool[idx]}"
            idx += 1
    return mapping


__all__ = [
    "SceneFixture",
    "RunResult",
    "audition_one",
    "build_blind_map",
    "fixture_dirs",
    "list_fixtures",
    "load_fixture",
    "write_artifacts",
    "FIXTURES_DIR",
    "ARTIFACTS_ROOT",
]
