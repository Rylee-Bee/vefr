# The Lorekeeper (`vefr-lore`)

A small, local, offline store of the **facts** a world knows, with a derived
vector index so `ask` can find the nearest ones. No generative model is
involved anywhere in this module - only an embedding endpoint.

## Two durable objects

- `data/lore/facts.jsonl` - the authoritative records (`id`, `text`,
  `created_at`, `source`, `metadata`, `tags`). Human-readable and
  hand-editable. The engine never fabricates a fact.
- `data/lore/index/` - **derived**, rebuildable from the facts:
  - `vectors.jsonl` + `meta.json` - the portable index;
  - `lore.db` - a `sqlite-vec` KNN accelerator (cosine) written beside it.

Deleting `index/` loses nothing; `vefr-lore rebuild` recreates it from the
facts. If the `sqlite-vec` extension cannot load, `ask` falls back to a
brute-force cosine over `vectors.jsonl` - the same answer, only slower - so a
fact is never lost to a missing extension.

## Commands

```sh
vefr-lore add "The western gate was destroyed."
vefr-lore ask "What happened to the western gate?"
vefr-lore list
vefr-lore rebuild
vefr-lore status
```

## Configuration (plain process env)

- `VEFR_EMBED_URL` - the `/v1/embeddings` endpoint (default `http://127.0.0.1:8082`).
- `VEFR_EMBED_MODEL` - the model name sent (default `bge-m3`).
- `VEFR_LORE_DIR` - the lore root (default `$VEFR_HOME/data/lore`).

Loopback only; never resolve `localhost` to `::1` on this host.

## What it is not

No chat payload, no generation, no network beyond the embed endpoint. A fact
is evidence; `ask` returns the stored records, never synthesised prose. A
structural test pins this (`tests/test_lore_shell.py`), so the boundary cannot
quietly erode.
