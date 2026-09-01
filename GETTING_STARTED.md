# Getting started

This gets the engine running on your own computer and walks you
through building your own world. No story content is required to
try it - a demonstration world (Emberfield) ships with the engine.

## What you need

| Tool | Why | Check you have it |
|---|---|---|
| Python 3.11+ | The engine runs on it | `python3 --version` |
| [`uv`](https://docs.astral.sh/uv/) | Installs dependencies, runs the CLIs | `uv --version` |
| A local model server | Runs the model that drafts prose | see below |
| A pulled model | The thing the server runs | see below |

The engine talks to any OpenAI-compatible `/v1/chat/completions`
server. Two options:

- **[llama.cpp](https://github.com/ggerganov/llama.cpp) (preferred)** —
  faster, and what the engine is tuned for. Point it at
  `VEFR_LLAMACPP_URL` (default `http://127.0.0.1:8081`).
- **[Ollama](https://ollama.com) (fallback)** — simpler to install.
  Set `OLLAMA_URL=http://127.0.0.1:11434` and pull a model first:
  `ollama pull qwen3:8b` (or any model you like - set `VEFR_MODEL` to
  its name later).

If both are set, `VEFR_LLAMACPP_URL` wins.

Tip: keep your endpoint config in one place. Copy `example.env`
to `.env` (gitignored), fill in your host, and source it before
any entry point - the engine reads plain process env vars:

```sh
cp example.env .env
# edit .env - point VEFR_LLAMACPP_URL at your llama.cpp host
set -a; source .env; set +a
```

Podman/Docker is optional. It's how you'd run this always-on on a
server; for trying it out, plain `uv run` is faster.

## 1. Get the code

```sh
git clone ${VEFR_GITEA_URL:-https://your-git-host/user/vefr.git}
cd vefr
uv sync --group test
```

## 2. Run it

```sh
OLLAMA_URL=http://127.0.0.1:11434 uv run uvicorn vefr.main:app --app-dir src --port 8820
```

Then, in a browser: `http://127.0.0.1:8820`

You should see a walkable town. `WASD`/arrows/pad to move, `E` or tap
to talk to whoever's near. Whichever world pack is present under
`worlds/` loads automatically - if you cloned the story separately
(see below), you'll see that; otherwise this is Emberfield, the
demonstration world.

> **Note (2026-08-31):** the author's own story and game live in
> their own private repo - they never ship inside a clone of this
> engine repo. This repo (`rylee/vefr`) is the shareable tooling
> only; it doesn't know or need to know any specific game's name
> to run it.

## 3. Check the engine is sound

```sh
uv run ratatoskr test
```

That's the full pytest suite. It should pass with zero setup beyond
step 1 - the engine tests itself against the demonstration world.

## 4. Make your own world

Two ways in:

```sh
uv run norns chat --name your-world
```

An interview, run against your own Ollama: it asks about your
story's canon, its color mood, its phases, its bonds, and one
speaker's voice - then drafts prose into `worlds/your-world/` and
checks it with `norns validate` before it's done. You never have to
trust your own edits; the tool always checks.

Or by hand: copy `worlds/sample-world/` to `worlds/your-world/` and
edit `world.json`, `logbok.md`, and the `voices/` files directly - see
the "Make your own world" section of `README.md` for the full
contract.

Either way, point the engine at it:

```sh
VEFR_WORLD=your-world uv run uvicorn vefr.main:app --app-dir src --port 8820
```

## 5. The CLI reference

```sh
uv run ratatoskr --help    # memory: skipa, test, weave, ferry (deploy, carry, fetch)
uv run norns --help    # craft: chat, validate, build-map, verify
```

Both print a full command list with descriptions - that's the
canonical reference, always in sync with the code.

## 5b. Shipping to a deploy host

The deploy wrapper hides rsync + podman build + quadlet restart +
health check behind one command. First-time setup:

```sh
uv run ratatoskr ferry deploy --init          # writes deploy.toml.example
cp deploy.toml.example deploy.toml            # then edit to match your host
export VEFR_DEPLOY_HOST=$(grep ^host deploy.toml | cut -d'"' -f2)
uv run ratatoskr ferry deploy                 # pre-flight + build + restart + verify
```

Full guide: `docs/guides/deploy.md`.

## 6. The API reference

The FastAPI app serves interactive docs for free, no separate file
to keep in sync:

```
http://127.0.0.1:8820/docs
```

Every route, every request/response shape, try-it-out included.

## Where to go next

| Question | Read |
|---|---|
| How does the bones/flesh split work? | `README.md` |
| What's landed, what's next? | `ROADMAP.md` |
| Who can use what, under what license? | `LICENSE` (engine) and `worlds/<name>/LICENSE` (a specific world, if it has one) |
| How do I run this always-on? | `README.md` Quickstart (container) section |
