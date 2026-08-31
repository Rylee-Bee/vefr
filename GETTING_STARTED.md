# Getting started

This gets the engine running on your own computer and walks you
through building your own world. No story content is required to
try it - a demonstration world (Emberfield) ships with the engine.

## What you need

| Tool | Why | Check you have it |
|---|---|---|
| Python 3.11+ | The engine runs on it | `python3 --version` |
| [`uv`](https://docs.astral.sh/uv/) | Installs dependencies, runs the CLIs | `uv --version` |
| [Ollama](https://ollama.com) | Runs the local model that drafts prose | `ollama --version` |
| A pulled model | The thing Ollama runs | `ollama list` |

If you don't have a model yet: `ollama pull qwen3:8b` (or any model
you like - set `SMIDR_MODEL` to its name later).

Podman/Docker is optional. It's how you'd run this always-on on a
server; for trying it out, plain `uv run` is faster.

## 1. Get the code

```sh
git clone http://192.168.2.216:3000/rylee/old-name.git
cd old-name
uv sync --group test
```

## 2. Run it

```sh
OLLAMA_URL=http://127.0.0.1:11434 uv run uvicorn old-name.main:app --app-dir src --port 8820
```

Then, in a browser: `http://127.0.0.1:8820`

You should see a walkable town. `WASD`/arrows/pad to move, `E` or tap
to talk to whoever's near. Whichever world pack is present under
`worlds/` loads automatically - if you cloned the story separately
(see below), you'll see that; otherwise this is Emberfield, the
demonstration world.

> **Note (2026-08-31):** the author's own story and game, Old Name, lives
> in its own private repo (`the private story repo`) - it never ships
> inside a clone of this engine repo. This repo (now `rylee/old-name`)
> is the shareable tooling only; it doesn't know or need to know any
> specific game's name to run it.

## 3. Check the engine is sound

```sh
uv run raven test
```

That's the full pytest suite. It should pass with zero setup beyond
step 1 - the engine tests itself against the demonstration world.

## 4. Make your own world

Two ways in:

```sh
uv run old-name chat --name your-world
```

An interview, run against your own Ollama: it asks about your
story's canon, its color mood, its phases, its bonds, and one
speaker's voice - then drafts prose into `worlds/your-world/` and
checks it with `old-name validate` before it's done. You never have to
trust your own edits; the tool always checks.

Or by hand: copy `worlds/sample-world/` to `worlds/your-world/` and
edit `world.json`, `bible.md`, and the `voices/` files directly - see
the "Make your own world" section of `README.md` for the full
contract.

Either way, point the engine at it:

```sh
SMIDR_WORLD=your-world uv run uvicorn old-name.main:app --app-dir src --port 8820
```

## 5. The CLI reference

```sh
uv run raven --help    # memory: tidyup, deploy, backup, test
uv run old-name --help    # craft: chat, validate, build, verify
```

Both print a full command list with descriptions - that's the
canonical reference, always in sync with the code.

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
