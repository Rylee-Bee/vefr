"""Storyteller Pack - the model-neutral AI provider boundary.

The engine owns truth (world, canon, NPCs, controls). The harness owns
context (what the model sees, how the prompt is shaped, what gets
validated back). The model owns imagination (prose, dialogue, surprise).

This module is the seam between the engine and whichever model the
player chose. The engine never imports a model name; it asks the
active storyteller for the model name, sampling, and capability tier,
then hands a context packet to the wire layer.

A Storyteller Pack is a directory containing a TOML manifest:

    data/storytellers/<name>/pack.toml

The manifest names the model, the endpoint, the capability tier, the
default sampling, and the licensing/source metadata. Weights do NOT
ship in the repo - the install step fetches them (or the user provides
their own).

Manifest shape (kept minimal, mirrors the spec's pack contents):

```toml
[storyteller]
id = "..."
name = "..."
version = "0.1.0"

[model]
provider = "openai-compatible"  # or "llama.cpp" / "ollama"
model = "..."
source = "huggingface"          # provenance hint
context_window = 0

[capabilities]
text = true
structured_output = false
tools = false
vision = false

[sampling]
temperature = 0.9
top_p = 0.95

[templates]                     # files relative to the pack dir; "" = inline empty
system = "system.md"            # optional; "" = use engine default
scene = "scene.md"              # optional; "" = use packet as-is
character = "character.md"      # reserved (Tier 2/3 future)
memory = "memory.md"            # reserved (Tier 2/3 future)

[license]
name = "..."
spdx = "Apache-2.0"
source_url = "..."
redistribution = "allowed"
commercial_use = "allowed"
attribution = "..."
notes = "..."

[notes]
"Human-readable summary of the pack."
```

Resolution order for the active storyteller:

    1. VEFR_STORYTELLER env var (BYOM pin by pack id or by inline name)
    2. The active marker at data/storytellers/active.toml
    3. The first installed pack under data/storytellers/
    4. The engine reference (gpt-oss-20b, what the engine used to
       hardcode - kept for back-compat so existing installs boot).

The bundled reference is the smart-control storyteller. It is NOT the
recommended creative storyteller; it is what the engine speaks when no
pack is installed. A fresh install should run `norns storyteller
install <pack-id>` to get a creative model.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any

from .paths import app_home

PACKS_DIRNAME = "storytellers"
ACTIVE_MARKER = "active.toml"
MANIFEST_FILENAME = "storyteller.toml"


class Provider(Enum):
    """The two wire protocols the engine actually speaks.

    OPENAI_COMPATIBLE: any runtime that exposes
    /v1/chat/completions (llama.cpp's server, LM Studio local server,
    vLLM, LocalAI, text-generation-inference, OpenRouter, etc.).
    One code path, many runtimes.

    OLLAMA: ollama's /api/generate endpoint. Kept as a separate path
    so ollama-specific fields (model keep_alive, native /api/generate
    response shape) don't leak into the universal adapter.

    A pack's [model].provider picks which path is used. Anything
    speaking the OpenAI-compatible chat-completions shape just works;
    we do not enumerate runtimes.
    """

    OPENAI_COMPATIBLE = "openai-compatible"
    OLLAMA = "ollama"


class Tier(IntEnum):
    """What we are allowed to ask the storyteller to do.

    Tier 1 - storyteller: text in, text out. This is enough for prose.
    Tier 2 - structured storyteller: also returns JSON proposals / metadata.
    Tier 3 - agentic helper: also calls tools or inspects state.

    A Tier 1 model is a perfectly valid VEFR storyteller. Tier 2/3 are
    useful upgrades, not requirements. Tier 1 callers must never ask
    the model for JSON or tools - that's how we keep a creative 12B in
    the box without coupling the engine to its agent features.
    """

    STORYTELLER = 1
    STRUCTURED = 2
    AGENTIC = 3


@dataclass(frozen=True)
class InstallMeta:
    """Optional install metadata for a Storyteller Pack.

    A pack author who ships zero model data omits this block entirely;
    the player uses whatever model they already have, named via the
    [model].model field. A pack author who recommends a specific
    download fills in `weights_source` and `recommended_quant` so a
    future install experience knows where to fetch from and how big
    the artifact is.

    All fields are optional; the dataclass exists so the schema is
    stable across packs that do and don't ship install metadata.
    """

    weights_source: str = ""  # "huggingface", "ollama", or a URL
    weights_repo: str = ""  # e.g. "google/gemma-4-E2B-it"
    weights_filename: str = ""  # e.g. "gemma-4-E2B-it-Q4_K_M.gguf"
    recommended_quant: str = ""  # e.g. "Q4_K_M", "Q5_K_M", "F16"
    approx_disk_mb: int = 0  # 0 = unknown
    fetch_command: str = ""  # human-readable command for the player
    attribution_url: str = ""
    notes: str = ""


@dataclass(frozen=True)
class LicenseMeta:
    """Source/redistribution metadata for the storyteller's weights.

    Recorded in the pack so we can prove provenance and warn if a user
    tries to redistribute a pack whose weights they don't have rights
    to ship. Empty strings are allowed (the field still exists) so the
    schema is uniform across packs.
    """

    name: str  # e.g. "Gemma", "gpt-oss", "Llama 3.1"
    spdx: str  # SPDX id where applicable, else "" (e.g. "Apache-2.0")
    source_url: str  # canonical upstream download URL
    redistribution: str  # "allowed", "derivatives-only", "no", "unknown"
    commercial_use: str  # "allowed", "restricted", "no", "unknown"
    attribution: str  # required attribution line, "" if none
    notes: str = ""  # human-readable summary of the license situation


@dataclass(frozen=True)
class ScenePacket:
    """A plain-text scene packet handed to a Tier 1 storyteller.

    The packet is the harness's whole job in one struct: it tells the
    model WHO it is, WHAT it knows, WHERE it is, WHAT JUST HAPPENED,
    and what to WRITE. No JSON. No tools. Just a prompt the model can
    answer with prose.

    Fields are deliberately stringy. The harness decides what each one
    contains based on the active speaker, location, and world state;
    the model never invents facts the packet doesn't give it.
    """

    speaker: str  # WHO YOU ARE
    speaker_knows: str  # WHAT YOU KNOW
    speaker_does_not_know: str  # WHAT YOU DO NOT KNOW
    scene: str  # CURRENT SCENE
    relationship: str = ""  # relationship to the player (may be "")
    recent_action: str = ""  # WHAT JUST HAPPENED (the player spoke/acted)
    open_threads: str = ""  # OPEN THREADS
    instruction: str = "Respond in voice. No exposition the speaker cannot know."

    def render(self) -> str:
        """Render the packet as a single plain-text prompt.

        One section per blank-line-separated block. The exact phrasing
        is part of the storyteller contract - changes here are visible
        to every Tier 1 model, so keep the sections stable.
        """
        sections = [
            f"WHO YOU ARE\n\n{self.speaker}",
            f"WHAT YOU KNOW\n\n{self.speaker_knows}",
        ]
        if self.speaker_does_not_know:
            sections.append(f"WHAT YOU DO NOT KNOW\n\n{self.speaker_does_not_know}")
        sections.append(f"CURRENT SCENE\n\n{self.scene}")
        if self.relationship:
            sections.append(f"RELATIONSHIP\n\n{self.relationship}")
        if self.recent_action:
            sections.append(f"WHAT JUST HAPPENED\n\n{self.recent_action}")
        if self.open_threads:
            sections.append(f"OPEN THREADS\n\n{self.open_threads}")
        sections.append(f"WRITE\n\n{self.instruction}")
        return "\n\n".join(sections)


@dataclass(frozen=True)
class Capabilities:
    """Granular feature flags derived from the pack's [capabilities] table.

    `tier` is derived from these (any one true beyond text bumps the
    tier). Storing the flags separately lets callers ask precise
    questions ("can this storyteller produce JSON?") without inferring
    from an integer.
    """

    text: bool = True
    structured_output: bool = False
    tools: bool = False
    vision: bool = False

    @property
    def tier(self) -> Tier:
        if self.tools:
            return Tier.AGENTIC
        if self.structured_output:
            return Tier.STRUCTURED
        return Tier.STORYTELLER


@dataclass(frozen=True)
class TemplatePaths:
    """Relative paths to optional template files inside the pack dir.

    `""` means "no template file" - the engine uses its own default for
    that slot. Templates are versioned alongside the manifest so a
    better Storyteller Pack can ship a better wrapper without touching
    engine code (the spec calls these out as game assets too).
    """

    system: str = ""
    scene: str = ""
    character: str = ""
    memory: str = ""


@dataclass(frozen=True)
class Storyteller:
    """One configurable storyteller.

    A Storyteller is *just config*. It does not hold weights, does not
    open sockets. The wire layer (`generator._completion`) reads these
    fields and adapts the request to the endpoint the pack names.

    Two storytellers with the same `model` but different `system_template`
    or `sampling` are still distinct storytellers - the template is
    part of the product experience, not just an attribute of the model.
    """

    id: str  # unique id, e.g. "gpt-oss-20b-reference", "gryphe-style-gemma-12b"
    name: str  # short display name
    version: str  # pack manifest version, "0.0.0" if absent
    model_provider: Provider
    model: str  # model name the backend expects
    capabilities: Capabilities
    sampling: dict[str, Any] = field(default_factory=lambda: {"temperature": 0.85})
    endpoint: str = ""  # "" = inherit from engine env (LLAMACPP_URL/OLLAMA_URL)
    chat_template_kwargs: dict[str, Any] = field(default_factory=dict)
    context_window: int = 0  # 0 = unknown / caller decides
    templates: TemplatePaths = field(default_factory=TemplatePaths)
    pack_dir: Path | None = None  # absolute path to the pack directory (for template loading)
    license: LicenseMeta | None = None
    install: InstallMeta | None = None
    notes: str = ""

    @property
    def tier(self) -> Tier:
        return self.capabilities.tier

    def is_text_only(self) -> bool:
        """True if this storyteller cannot be asked for JSON safely."""
        return self.tier == Tier.STORYTELLER

    def load_template(self, kind: str) -> str:
        """Load one named template from the pack dir, or "" if unset.

        kind in {"system", "scene", "character", "memory"}. Used by
        the harness when rendering prompts; the engine never assumes
        a pack has any of them.
        """
        if self.pack_dir is None:
            return ""
        rel = getattr(self.templates, kind, "")
        if not rel:
            return ""
        path = self.pack_dir / rel
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""


MANIFEST_FILENAME = "storyteller.toml"


@dataclass(frozen=True)
class _PackRecord:
    """A pack directory's on-disk layout as the engine sees it."""

    pack_id: str
    path: Path


def packs_root() -> Path:
    """Where installed Storyteller Packs live.

    Per-user, gitignored, follows the engine's `data/` convention
    (AGENTS.md: runtime state under data/, never hand-edited by the
    engine, never committed).
    """
    return app_home() / "data" / PACKS_DIRNAME


def _engine_packs_root() -> Path:
    """Engine-owned (tracked) Storyteller Packs shipped with the repo.

    These are the *recommendations*. They live next to the source so
    every checkout has the same defaults; user-installed overrides
    live under data/storytellers/ and win when both exist.
    """
    # __file__ is src/vefr/storyteller.py; parent.parent.parent = repo root.
    return Path(__file__).resolve().parents[2] / "storyteller_packs"


def _bundled_reference() -> Storyteller:
    """The engine reference storyteller.

    This is what the engine used to hardcode (gpt-oss-20b, Tier 3,
    temperature 0.95 for rumors, 0.85 for lines). Kept exactly so
    existing installs boot and the existing pytest contract holds.
    Picking a different default is a Storyteller Pack change, not an
    engine change.
    """
    return Storyteller(
        id="gpt-oss-20b-reference",
        name="gpt-oss 20b (engine reference)",
        version="0.0.0",
        model_provider=Provider.OPENAI_COMPATIBLE,
        model=os.environ.get("VEFR_MODEL", "gpt-oss-20b"),
        capabilities=Capabilities(text=True, structured_output=True, tools=True),
        sampling={"temperature": 0.85},
        chat_template_kwargs={"reasoning_effort": "low"},
        context_window=0,
        pack_dir=None,
        license=LicenseMeta(
            name="gpt-oss",
            spdx="Apache-2.0",
            source_url="https://huggingface.co/openai/gpt-oss-20b",
            redistribution="allowed",
            commercial_use="allowed",
            attribution="OpenAI gpt-oss 20b (Apache-2.0)",
            notes="Engine reference storyteller. Smart control, not the recommended creative default.",
        ),
        notes="Engine reference. Back-compat default for installs with no pack selected.",
    )


def _load_pack_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _manifest_to_storyteller(pack_id: str, manifest: dict[str, Any], pack_dir: Path | None = None) -> Storyteller:
    """Turn a parsed storyteller.toml into a Storyteller dataclass.

    Unknown fields are ignored (forward compatibility). Missing
    required fields raise with a useful message naming the pack.
    """
    st_block = manifest.get("storyteller") or {}
    model_block = manifest.get("model") or {}
    cap_block = manifest.get("capabilities") or {}
    tmpl_block = manifest.get("templates") or {}
    lic_block = manifest.get("license") or {}
    install_block = manifest.get("install") or {}

    capabilities = Capabilities(
        text=bool(cap_block.get("text", True)),
        structured_output=bool(cap_block.get("structured_output", False)),
        tools=bool(cap_block.get("tools", False)),
        vision=bool(cap_block.get("vision", False)),
    )

    try:
        model = str(model_block["model"])
    except KeyError as e:
        raise ValueError(f"storyteller pack {pack_id!r}: missing required field 'model.model'") from e

    try:
        provider = Provider(str(model_block.get("provider", "openai-compatible")))
    except ValueError as e:
        raise ValueError(
            f"storyteller pack {pack_id!r}: invalid model.provider "
            f"{model_block.get('provider')!r} (expected one of: "
            f"{', '.join(p.value for p in Provider)})"
        ) from e

    # Templates: explicit filenames from [templates], or fall back to
    # `system.md`/`scene.md`/`character.md`/`memory.md` at the pack
    # root. The harness convention is flat: one .toml + optional .md
    # siblings. `templates/` subdirs are not special-cased here; pack
    # authors who want them can name the files explicitly.
    templates = TemplatePaths(
        system=str(tmpl_block.get("system", "system.md")),
        scene=str(tmpl_block.get("scene", "scene.md")),
        character=str(tmpl_block.get("character", "character.md")),
        memory=str(tmpl_block.get("memory", "memory.md")),
    )

    license_meta = LicenseMeta(
        name=str(lic_block.get("name", "")),
        spdx=str(lic_block.get("spdx", "")),
        source_url=str(lic_block.get("source_url", "")),
        redistribution=str(lic_block.get("redistribution", "unknown")),
        commercial_use=str(lic_block.get("commercial_use", "unknown")),
        attribution=str(lic_block.get("attribution", "")),
        notes=str(lic_block.get("notes", "")),
    )

    install_meta = InstallMeta(
        weights_source=str(install_block.get("weights_source", "")),
        weights_repo=str(install_block.get("weights_repo", "")),
        weights_filename=str(install_block.get("weights_filename", "")),
        recommended_quant=str(install_block.get("recommended_quant", "")),
        approx_disk_mb=int(install_block.get("approx_disk_mb", 0) or 0),
        fetch_command=str(install_block.get("fetch_command", "")),
        attribution_url=str(install_block.get("attribution_url", "")),
        notes=str(install_block.get("notes", "")),
    )

    return Storyteller(
        id=str(st_block.get("id", pack_id)),
        name=str(st_block.get("name", pack_id)),
        version=str(st_block.get("version", "0.0.0")),
        model_provider=provider,
        model=model,
        capabilities=capabilities,
        sampling=dict(manifest.get("sampling") or {"temperature": 0.85}),
        endpoint=str(model_block.get("endpoint", manifest.get("endpoint", ""))),
        chat_template_kwargs=dict(manifest.get("chat_template_kwargs") or {}),
        context_window=int(model_block.get("context_window", manifest.get("context_window", 0) or 0)),
        templates=templates,
        pack_dir=pack_dir,
        license=license_meta,
        install=install_meta,
        notes=str(manifest.get("notes", "")),
    )


def list_installed_packs() -> list[_PackRecord]:
    """User-installed packs under data/storytellers/.

    Each subdirectory with a storyteller.toml is a pack. The directory
    name is the pack id. This is the install-side view; pack records
    are cheap to enumerate because the engine rarely needs to.
    """
    root = packs_root()
    if not root.is_dir():
        return []
    found: list[_PackRecord] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        manifest = child / MANIFEST_FILENAME
        if manifest.is_file():
            found.append(_PackRecord(pack_id=child.name, path=child))
    return found


def list_bundled_packs() -> list[_PackRecord]:
    """Engine-recommended packs shipped under storyteller_packs/."""
    root = _engine_packs_root()
    if not root.is_dir():
        return []
    found: list[_PackRecord] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        manifest = child / MANIFEST_FILENAME
        if manifest.is_file():
            found.append(_PackRecord(pack_id=child.name, path=child))
    return found


def _load_record(rec: _PackRecord) -> Storyteller:
    return _manifest_to_storyteller(rec.pack_id, _load_pack_toml(rec.path / MANIFEST_FILENAME), pack_dir=rec.path)


def list_packs() -> list[Storyteller]:
    """Every pack the engine can see (bundled + installed)."""
    out: list[Storyteller] = []
    seen: set[str] = set()
    for rec in list_bundled_packs():
        out.append(_load_record(rec))
        seen.add(rec.pack_id)
    for rec in list_installed_packs():
        if rec.pack_id in seen:
            # Installed overrides bundled: re-resolve on disk.
            # The resolution logic in resolve_active() picks the
            # installed version when both exist; here we just dedupe.
            continue
        out.append(_load_record(rec))
    return out


def find_pack(pack_id: str) -> Storyteller | None:
    """Look up one pack by id (or by model name), bundled or installed.

    Returns None if no pack matches - callers that need to distinguish
    "missing" from "error" should use this; the resolve_active() chain
    is for the engine's hot path and never returns None.
    """
    for st in list_packs():
        if st.id == pack_id or st.model == pack_id:
            return st
    return None


def resolve_active() -> Storyteller:
    """The storyteller every engine caller should use right now.

    Order:
      1. VEFR_STORYTELLER env var (BYOM pin)
      2. data/storytellers/active.toml pin
      3. First installed pack under data/storytellers/
      4. First bundled pack under storyteller_packs/
      5. Engine reference (gpt-oss-20b)
    """
    env_pin = os.environ.get("VEFR_STORYTELLER", "").strip()
    if env_pin:
        for st in list_packs():
            if st.id == env_pin or st.model == env_pin:
                return st
        # BYOM: env var names a model that has no installed pack.
        # Return a thin Tier-2 placeholder so the engine still works
        # without forcing the player to write a pack.toml first.
        return Storyteller(
            id=f"byom:{env_pin}",
            name=f"BYOM: {env_pin}",
            version="0.0.0",
            model_provider=Provider.OPENAI_COMPATIBLE,
            model=env_pin,
            capabilities=Capabilities(text=True, structured_output=True),
            chat_template_kwargs={"reasoning_effort": "low"},
            notes="Bring-your-own-model via VEFR_STORYTELLER; no installed pack.",
        )

    marker = packs_root() / ACTIVE_MARKER
    if marker.is_file():
        try:
            pin = _load_pack_toml(marker)
            pinned_id = str(pin.get("active", "")).strip()
            if pinned_id:
                for st in list_packs():
                    if st.id == pinned_id:
                        return st
        except (OSError, tomllib.TOMLDecodeError):
            pass

    installed = list_installed_packs()
    if installed:
        return _load_record(installed[0])

    bundled = list_bundled_packs()
    if bundled:
        return _load_record(bundled[0])

    return _bundled_reference()


def active_model_name() -> str:
    """Convenience: the model name the wire layer should send."""
    return resolve_active().model


def active_keep_alive() -> str:
    """The ollama keep_alive string, inherited from the engine env.

    Per-pack override is intentionally not exposed yet; one knob at a
    time until we have evidence a pack needs its own.
    """
    return os.environ.get("VEFR_KEEP_ALIVE", "1m")


def render_scene_packet(packet: ScenePacket) -> str:
    """Apply the active storyteller's scene template, if any.

    Priority:
      1. Templates loaded from the pack's [templates].scene file
      2. The literal `{packet}` substitution into the file's contents
      3. The packet rendered as-is (no template)
    """
    st = resolve_active()
    body = packet.render()
    template_text = st.load_template("scene")
    if not template_text:
        return body
    if "{packet}" in template_text:
        return template_text.replace("{packet}", body)
    # Template file exists but has no placeholder; the file IS the
    # wrapper, the packet goes after a blank line.
    return f"{template_text}\n\n{body}"


__all__ = [
    "Tier",
    "Capabilities",
    "TemplatePaths",
    "LicenseMeta",
    "ScenePacket",
    "Storyteller",
    "MANIFEST_FILENAME",
    "packs_root",
    "list_installed_packs",
    "list_bundled_packs",
    "list_packs",
    "find_pack",
    "resolve_active",
    "active_model_name",
    "active_keep_alive",
    "render_scene_packet",
]
