# Old Name

*old-name* - Old Norse: memory, and longing. The root of Muninn, the raven
that flies out every day and comes home.

A rumor engine for a personal RPG: a local LLM turns a phase and a
theme into a whispered tavern rumor, as structured JSON, on your own
GPU. The perception engine for an original Norse-flavored story.

Private until it isn't.

## Run (dev)

```bash
uv sync
OLLAMA_URL=http://192.168.2.76:11434 uv run --group test uvicorn old-name.main:app --port 8820
```

Open http://127.0.0.1:8820 - pick a phase, press Whisper.

The model (default `qwen3.8-27b:ctx32k`) is swappable via
`MUNR_MODEL`; `MUNR_KEEP_ALIVE` (default 1m) keeps VRAM free for
whatever else needs the card.

## Deploy (bazzite)

`deploy/old-name.container` is a quadlet for rootless podman; build the
image from `Containerfile` first:

```bash
podman build -t localhost/old-name .
cp deploy/old-name.container ~/.config/containers/systemd/
systemctl --user daemon-reload && systemctl --user start old-name.service
```

## Live

Deployed on bazzite at **http://192.168.2.76:8820** - quadlet,
rootless podman, host networking, linger on. The engine, the forge,
and the bell are reachable from any device on the LAN.

## The shape of it

- `WORLD_BIBLE.md` - the style guide every whisper reads. Rylee's file.
- `MAP.md` - Private Canon: the town's geometry, sightlines, the tower's
  blind spots.
- `STYLE.md` - Bog & Bell: palette, 32x32 tiles, the Gold Rule.
- `WHISPERS.md` - the ledger: collected whispers that teach the
  engine's voice.
- `ROADMAP.md` - the ladder from tool to playable story.
- Three views: **Rumors** (the perception engine), **Vault** (items
  with three bonds - assigned, attuned, cold), **Bell** (one ring
  per visit).
- Rumors come in phases - the world's tone toward the heroine shifts
  as the story progresses, and the engine speaks in that tone.
