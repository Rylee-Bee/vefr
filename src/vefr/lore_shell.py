"""vefr-lore - the Lorekeeper slice of the small-models fleet.

A boring, portable, local lore store for VEFR worlds.

    vefr-lore add "The western gate was destroyed."
    vefr-lore ask "What happened to the western gate?"

Two durable objects:

  facts.jsonl   authoritative structured lore records (id, text,
                created_at, source, metadata, tags). Humans can
                read and edit it; the engine never fabricates it.
  index/        DERIVED data - one JSONL vector per fact id plus a
                small meta.json (model, dimensions). Deleting or
                rebuilding the index must never lose a fact.

The embedding model contributes representation only. There is NO
generative model call anywhere in this module: `add` reads the
embed endpoint and stores a vector; `ask` embeds the query, does a
brute-force cosine search over the local index, and returns the
matched *stored records* - evidence, not synthesized prose.

Config (plain process env, repo convention):

  VEFR_EMBED_URL    embed endpoint   (default http://127.0.0.1:8082)
  VEFR_EMBED_MODEL  model name sent  (default bge-m3)
  VEFR_LORE_DIR     lore root        (default $VEFR_HOME/data/lore)

Only 127.0.0.1 - this host's pasta IPv6 loopback is broken, never
resolve localhost to ::1.
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from .paths import data_dir


class EmbedUnavailable(RuntimeError):
    """The embed service is down, unreachable, or too slow. Callers
    surface an explicit 'unavailable' state; they never pretend."""


class EmbedMalformed(RuntimeError):
    """The embed endpoint answered, but the payload did not match
    the /v1/embeddings contract we asked for. Fail honestly."""


class LoreFact(BaseModel):
    id: str
    text: str
    created_at: str
    source: str = "owner"
    metadata: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class LoreIndexEntry(BaseModel):
    id: str
    embedding: list[float]


# --- configuration ------------------------------------------------------

def embed_url() -> str:
    return os.environ.get("VEFR_EMBED_URL", "http://127.0.0.1:8082").rstrip("/")


def embed_model() -> str:
    return os.environ.get("VEFR_EMBED_MODEL", "bge-m3")


def embed_timeout() -> float:
    return float(os.environ.get("VEFR_EMBED_TIMEOUT", "120"))


def lore_dir() -> Path:
    """The lore root. Defaults under VEFR_HOME/data so the repo's
    existing runtime-state rule covers it (gitignored, session data
    not engine code)."""
    env = os.environ.get("VEFR_LORE_DIR")
    if env:
        return Path(env)
    return data_dir() / "lore"


def facts_path() -> Path:
    return lore_dir() / "facts.jsonl"


def index_dir() -> Path:
    return lore_dir() / "index"


def vectors_path() -> Path:
    return index_dir() / "vectors.jsonl"


def meta_path() -> Path:
    return index_dir() / "meta.json"


# --- embedding client -----------------------------------------------

def _embed_http(url: str, model: str, texts: list[str], timeout: float) -> list[list[float]]:
    """POST /v1/embeddings; raise EmbedUnavailable/EmbedMalformed."""
    try:
        r = httpx.post(
            f"{url}/v1/embeddings",
            json={"model": model, "input": texts},
            timeout=timeout,
        )
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        raise EmbedUnavailable(f"embed endpoint {url} unreachable: {e}") from e
    if r.status_code != 200:
        raise EmbedUnavailable(f"embed endpoint {url} returned HTTP {r.status_code}")
    try:
        data = r.json()["data"]
        vectors = [item["embedding"] for item in data]
    except (KeyError, TypeError, ValueError) as e:
        raise EmbedMalformed(f"embed endpoint {url} returned malformed payload: {e}") from e
    if len(vectors) != len(texts):
        raise EmbedMalformed(
            f"embed endpoint answered {len(vectors)} vectors for {len(texts)} inputs"
        )
    return vectors


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts via the configured endpoint."""
    return _embed_http(embed_url(), embed_model(), texts, embed_timeout())


# --- storage --------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_facts() -> dict[str, LoreFact]:
    """All facts keyed by id, in file order."""
    out: dict[str, LoreFact] = {}
    path = facts_path()
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fact = LoreFact(**json.loads(line))
        out[fact.id] = fact
    return out


def _facts_by_text() -> dict[str, LoreFact]:
    return {f.text: f for f in _load_facts().values()}


def _append_fact(fact: LoreFact) -> None:
    path = facts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(fact.model_dump(), ensure_ascii=False) + "\n")


def _load_index() -> dict[str, list[float]]:
    path = vectors_path()
    if not path.exists():
        return {}
    out: dict[str, list[float]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ent = LoreIndexEntry(**json.loads(line))
        out[ent.id] = ent.embedding
    return out


def _atomic_write_vectors(entries: list[LoreIndexEntry], dims: int) -> None:
    index_dir().mkdir(parents=True, exist_ok=True)
    tmp = vectors_path().with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for ent in entries:
            fh.write(json.dumps(ent.model_dump(), ensure_ascii=False) + "\n")
    tmp.replace(vectors_path())
    meta_path().write_text(
        json.dumps({"model": embed_model(), "dimensions": dims}, ensure_ascii=False),
        encoding="utf-8",
    )
    # The accelerator is best-effort: a failure here must never lose the
    # portable index or the facts.
    try:
        _vec_write(entries, dims)
    except Exception as e:
        print(f"[vefr-lore] warning: vector accelerator not written: {e}",
              file=sys.stderr)


def _cos(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a))
    nb = sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# --- vector search --------------------------------------------------
#
# `vectors.jsonl` stays the derived, portable index (facts.jsonl is
# authoritative above it). We also write `index/lore.db`, a vec0 table,
# and `ask` uses it for a KNN search instead of scanning every vector in
# Python. sqlite-vec is a bundled dependency, but if it fails to import or
# load we fall back to the brute-force cosine over the JSONL index - the
# answer is the same, only slower, so a fact is never lost to it. The
# accelerator is derived state: deleting it loses nothing, and `rebuild`
# recreates it from the facts.

VEC_DB_NAME = "lore.db"

_VEC = None  # cached sqlite_vec module, or False once found missing


def _vec_module():
    """The sqlite_vec module when importable, else None. Cached so the
    dependency is probed once per process."""
    global _VEC
    if _VEC is None:
        try:
            import sqlite_vec

            _VEC = sqlite_vec
        except ImportError:
            _VEC = False
    return _VEC or None


def vec_db_path() -> Path:
    """The derived search accelerator. Rebuildable from facts; never
    authoritative."""
    return index_dir() / VEC_DB_NAME


def _vec_write(entries: list[LoreIndexEntry], dims: int) -> None:
    """Write the vec0 accelerator beside the JSONL index. No-op when
    sqlite-vec is unavailable or there is nothing to index."""
    vec = _vec_module()
    if vec is None or dims <= 0:
        return
    import sqlite3

    path = vec_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".db.tmp")
    if tmp.exists():
        tmp.unlink()
    conn = sqlite3.connect(str(tmp))
    try:
        conn.enable_load_extension(True)
        vec.load(conn)
        conn.enable_load_extension(False)
        conn.execute(
            "CREATE VIRTUAL TABLE lore_vec USING vec0("
            f"id TEXT PRIMARY KEY, embedding FLOAT[{dims}] "
            "distance_metric=cosine)"
        )
        conn.executemany(
            "INSERT INTO lore_vec(id, embedding) VALUES (?, ?)",
            [(e.id, vec.serialize_float32(e.embedding)) for e in entries],
        )
        conn.commit()
    finally:
        conn.close()
    tmp.replace(path)


def _vec_rank(qvec: list[float], k: int) -> list[tuple[str, float]] | None:
    """Nearest ids via the vec0 accelerator, or None when it cannot be
    used (missing extension, missing/odd table). Never raises."""
    vec = _vec_module()
    path = vec_db_path()
    if vec is None or not path.exists():
        return None
    import sqlite3

    conn = None
    try:
        conn = sqlite3.connect(str(path))
        conn.enable_load_extension(True)
        vec.load(conn)
        conn.enable_load_extension(False)
        rows = conn.execute(
            "SELECT id, distance FROM lore_vec "
            "WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (vec.serialize_float32(qvec), k),
        ).fetchall()
    except Exception:
        return None
    finally:
        if conn is not None:
            conn.close()
    # vec0 cosine distance is 1 - cosine similarity; report the same
    # similarity the brute-force path reports.
    return [(str(r[0]), round(1.0 - float(r[1]), 4)) for r in rows]


def _rank(
    qvec: list[float], facts: list[LoreFact], k: int
) -> list[tuple[LoreFact, float]]:
    """Rank facts by similarity, fast path first."""
    fast = _vec_rank(qvec, k)
    if fast is not None:
        by_id = {f.id: f for f in facts}
        ranked = [(by_id[fid], score) for fid, score in fast if fid in by_id]
        if ranked:
            return ranked
    index = _load_index()
    scored = [(f, _cos(qvec, index[f.id])) for f in facts if f.id in index]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:k]


def _index_exists() -> bool:
    return vectors_path().exists() or vec_db_path().exists()


# --- operations -----------------------------------------------------

def add_fact(text: str, *, source: str = "owner", tags: list[str] | None = None) -> LoreFact:
    """Store a structured fact and its derived vector. Duplicate texts
    are deliberate: an identical existing fact is returned unchanged
    (no re-embed, no duplicate row)."""
    existing = _facts_by_text()
    if text in existing:
        return existing[text]
    fact = LoreFact(
        id=uuid.uuid4().hex[:12],
        text=text,
        created_at=_now(),
        source=source,
        tags=list(tags or []),
    )
    _append_fact(fact)
    try:
        vectors = embed_texts([text])
        existing = _load_index()
        entries = [
            LoreIndexEntry(id=fid, embedding=vec)
            for fid, vec in existing.items()
        ]
        entries.append(LoreIndexEntry(id=fact.id, embedding=vectors[0]))
        _atomic_write_vectors(entries, len(vectors[0]))
    except (EmbedUnavailable, EmbedMalformed) as e:
        # Facts are authoritative; a missing vector is a derived-data
        # gap, not a lost fact. Surface explicitly and keep going so
        # `ask` can rebuild the index later.
        print(f"[vefr-lore] warning: embed unavailable, fact stored without vector: {e}",
              file=sys.stderr)
    return fact


def rebuild() -> None:
    """Re-derive the entire index from the authoritative facts. Facts
    are never touched; only index/ is rewritten."""
    facts = list(_load_facts().values())
    if not facts:
        return
    texts = [f.text for f in facts]
    vectors = embed_texts(texts)
    entries = [LoreIndexEntry(id=f.id, embedding=v) for f, v in zip(facts, vectors)]
    dims = len(vectors[0]) if vectors else 0
    _atomic_write_vectors(entries, dims)


def list_facts() -> list[LoreFact]:
    return list(_load_facts().values())


def ask(query: str, *, k: int = 3) -> dict:
    """Return nearest stored facts for a query - evidence, not prose."""
    facts = list(_load_facts().values())
    if not facts:
        return {"query": query, "matches": []}
    if not _index_exists():
        rebuild()
    qvec = embed_texts([query])[0]
    scored = _rank(qvec, facts, k)
    return {
        "query": query,
        "matches": [
            {
                "id": f.id,
                "text": f.text,
                "score": round(s, 4),
                "source": f.source,
            }
            for f, s in scored
        ],
    }


def status() -> dict:
    idx = _load_index()
    meta = {}
    if meta_path().exists():
        try:
            meta = json.loads(meta_path().read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            meta = {}
    result = {
        "embed_url": embed_url(),
        "embed_model": embed_model(),
        "fact_count": len(_load_facts()),
        "indexed_count": len(idx),
        "dimensions": meta.get("dimensions"),
        "lore_dir": str(lore_dir()),
    }
    try:
        t0 = time.monotonic()
        dims = len(embed_texts(["ping"])[0])
        result["embed_ok"] = True
        result["embed_latency_ms"] = round((time.monotonic() - t0) * 1000, 1)
        if result["dimensions"] is None:
            result["dimensions"] = dims
    except (EmbedUnavailable, EmbedMalformed) as e:
        result["embed_ok"] = False
        result["embed_error"] = str(e)
    return result


# --- CLI -----------------------------------------------------------

def _cmd_add(args: argparse.Namespace) -> int:
    fact = add_fact(args.text, source=args.source, tags=args.tags)
    print(f"Added lore fact {fact.id}")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    try:
        result = ask(args.query, k=args.k)
    except EmbedUnavailable as e:
        print(f"[vefr-lore] embed service unavailable: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not result["matches"]:
        print("[vefr-lore] no lore yet - nothing stored to answer with.")
        return 0
    for m in result["matches"]:
        print(m["text"])
        print(f"score: {m['score']}")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    facts = list_facts()
    if args.json:
        print(json.dumps([f.model_dump() for f in facts], ensure_ascii=False, indent=2))
        return 0
    if not facts:
        print("[vefr-lore] empty - no lore facts stored.")
        return 0
    for f in facts:
        extra = f"  tags={','.join(f.tags)}" if f.tags else ""
        print(f"{f.id}  {f.source}  {f.created_at}  {f.text}{extra}")
    return 0


def _cmd_rebuild(args: argparse.Namespace) -> int:
    try:
        rebuild()
    except EmbedUnavailable as e:
        print(f"[vefr-lore] embed service unavailable: {e}", file=sys.stderr)
        return 2
    print("[vefr-lore] index rebuilt from lore facts")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    s = status()
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0
    for key in ("embed_url", "embed_model", "fact_count", "indexed_count",
                "dimensions", "lore_dir"):
        print(f"{key}: {s.get(key)}")
    if s.get("embed_ok"):
        print(f"embed_ok: true ({s.get('embed_latency_ms')} ms)")
    else:
        print(f"embed_ok: false ({s.get('embed_error')})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vefr-lore",
        description="Lorekeeper: store and retrieve lore facts (no generative model).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="store a structured lore fact")
    p_add.add_argument("text")
    p_add.add_argument("--source", default="owner")
    p_add.add_argument("--tag", action="append", dest="tags", default=[])
    p_add.set_defaults(func=_cmd_add)

    p_ask = sub.add_parser("ask", help="retrieve nearest stored lore facts")
    p_ask.add_argument("query")
    p_ask.add_argument("-k", type=int, default=3)
    p_ask.add_argument("--json", action="store_true")
    p_ask.set_defaults(func=_cmd_ask)

    p_list = sub.add_parser("list", help="list stored lore facts")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cmd_list)

    p_rebuild = sub.add_parser("rebuild", help="re-derive the vector index")
    p_rebuild.set_defaults(func=_cmd_rebuild)

    p_status = sub.add_parser("status", help="service + store state")
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=_cmd_status)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())