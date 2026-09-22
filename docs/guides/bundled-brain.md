# Bundled Brain — vefr ships with its own intelligence

The bundled brain is vefr's zero-setup deployment: `podman run vefr`
gives you a fully playable game with no external LLM configuration.
CPU-only, no GPU required.

## Model fleet (locked 2026-09-21)

| Port | Role | Model | Size | Purpose |
|---|---|---|---|---|
| :8083 | Spark | Qwen3-0.6B-Instruct | ~460 MB | Interface translator — structured state edits, bounded NPC logic, continuity |
| :8084 | Storyteller | Qwen3-1.7B | ~1.1 GB | Primary narration, dialogue, scene description |
| :8085 | Vision | SmolVLM2-500M-Video-Instruct (Q8_0 + mmproj) | 546 MB | Image understanding for visual scenes |
| :8086 | Embeddings | bge-m3 | ~600 MB | Vector embeddings for lore retrieval (optional) |

**Total resident memory: ~2.8 GB**

All models run on CPU via llama.cpp. Each model gets its own
llama-server process on its designated port.

### Why these models

- **Qwen3-0.6B (Spark):** Fastest sub-1B with reliable structured output. Q4 quantization is forbidden for sub-1B models — state edits corrupt. Runs at ~58 tok/s on CPU.
- **Qwen3-1.7B (Storyteller):** Best quality-to-size ratio for narration within the bundled budget. ~21 tok/s on CPU — fast enough for conversational flow.
- **SmolVLM2-500M (Vision):** `SmolVLM2-500M-Video-Instruct` at Q8_0 plus its mmproj projector (546 MB total) — SmolVLM2's only official 500M checkpoint, and the smallest model that handles scene descriptions. Keeps the vision role available without blowing the memory budget.
- **bge-m3 (Embeddings):** Runs the lore retrieval pipeline. Marked optional — the game works without it, just loses semantic lore search.

## Port topology

```
┌─────────────────────────────────────────────┐
│              vefr engine (:8820)             │
│         FastAPI + world + validation         │
├──────────┬──────────┬──────────┬─────────────┤
│  :8083   │  :8084   │  :8085   │   :8086     │
│  Spark   │ Story-   │ Vision   │  Embeddings │
│ Qwen3    │ teller   │ SmolVLM2 │   bge-m3    │
│  0.6B    │ Qwen3    │  500M    │             │
│          │  1.7B    │          │             │
└──────────┴──────────┴──────────┴─────────────┘
```

Engine env vars map these ports:

| Env var | Default (no bundle) | Bundled value |
|---|---|---|
| `VEFR_LLAMACPP_URL` | `http://127.0.0.1:8081` | `http://127.0.0.1:8084` |
| `VEFR_MODEL` | `gpt-oss-20b` | `qwen3-1.7b` |
| `VEFR_SPARK_URL` | `http://127.0.0.1:8082` | `http://127.0.0.1:8083` |
| `VEFR_VISION_URL` | _(not yet read by the engine)_ | `http://127.0.0.1:8085` |
| `VEFR_EMBED_URL` | `http://127.0.0.1:8082` | `http://127.0.0.1:8086` |

## Hardware requirements

- **Minimum:** 4 GB RAM, any modern CPU (x86_64 or aarch64)
- **Recommended:** 8 GB RAM, 4+ cores
- **Storage:** ~3.6 GB for model files + engine + world data
- **GPU:** Not required. All models run on CPU via llama.cpp.

## How to swap models

1. Replace the `.gguf` file in your models directory
2. Update the port-to-model mapping in `deploy/start-bundled.sh`
   (or `deploy/llama-vefr.container` for quadlet deployments)
3. Restart: `systemctl --user restart llama-vefr vefr`

The engine env vars (`VEFR_MODEL`, `VEFR_SPARK_URL`, etc.) are
process-global — a restart picks them up cleanly.

## Degradation behavior

The bundled brain is designed to degrade gracefully:

- **All models down:** The engine still serves the world. Players
  can walk around, examine locations, and interact with the world
  geometry. No narration, no dialogue, no NPC interaction.
- **Storyteller down only:** Spark can still handle interface tasks.
  Lore retrieval still works if embeddings are up.
- **Engine down, models up:** The llama.cpp servers sit idle.
  Restart the engine container — no model reload needed.
- **Partial recovery:** If a model server crashes mid-session, the
  engine raises `SparkUnavailable` or similar. Callers degrade
  gracefully. The model server restarts via its systemd unit, and
  the engine reconnects on the next request.

This is the "town is walkable" guarantee: the world is always
available even when the brain isn't.

## Deployment topology

### Bundled (single host, quadlet)

Two systemd units, both enabled:

```ini
# ~/.config/containers/systemd/llama-vefr.container
# (see deploy/llama-vefr.container — ships with the repo)
```

```ini
# ~/.config/containers/systemd/vefr.container
# (see deploy/vefr.container — ships with the repo)
```

```sh
systemctl --user daemon-reload
systemctl --user enable --now llama-vefr vefr
```

### Development (local, one command)

```sh
./deploy/start-bundled.sh
```

Starts all model servers + the engine in one process group.
Ctrl-C stops everything cleanly.

## Relationship to brain-socket.md

The bundled brain is one configuration through the brain socket
described in [brain-socket.md](brain-socket.md). The architecture
promise — "bring your own brain; VEFR provides the world" — still
holds. The bundled brain is the **default** brain, not the only one.

Operators can:
- Replace bundled models with larger ones (edit the pack + restart)
- Point at a remote GPU server (set `VEFR_LLAMACPP_URL` to the remote host)
- Use Ollama instead (set `OLLAMA_URL`, clear `VEFR_LLAMACPP_URL`)
- Mix local + remote (Spark locally, storyteller remotely, etc.)

The quadlet templates in `deploy/` are starting points, not mandates.
