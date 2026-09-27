"""Embeddings suite: which small embedder finds the right passage?

Serves each GGUF with llama.cpp (--embedding, CPU) through the olympics
runtime, embeds the corpus and the paraphrased questions, and scores
recall@1, recall@3 and MRR, plus speed. Evidence: bench/runs/senses/embed/<rid>/.

    python3 -m bench.senses.embed [<key> ...]
"""
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

from bench.olympics import config as OC
from bench.olympics.participants import Participant
from bench.olympics.runtime import ModelServer
from .corpus import chunks
from .embed_queries import QUERIES

ROOT = Path(__file__).resolve().parents[2]

# (key, params_b, file, query_prefix, doc_prefix). Prefixes only where the
# model card documents one; everything else runs plain.
QWEN_Q = "Instruct: Given a question, retrieve the passage that answers it\nQuery: "
EMBEDDERS = [
    ("bekko-a25m", 0.123, "bekko-embedding-v1-a25m-Q8_0.gguf", "", ""),
    ("granite-embed-97m", 0.097, "granite-embedding-97M-multilingual-r2-Q8_0.gguf", "", ""),
    ("denseon-150m", 0.15, "DenseOn.Q8_0.gguf", "", ""),
    ("harrier-270m", 0.27, "harrier-oss-v1-270M-Q8_0.gguf", "", ""),
    ("embeddinggemma-300m", 0.3, "embeddinggemma-300m-qat-Q8_0.gguf", "task: search result | query: ", "title: none | text: "),
    ("granite-embed-311m", 0.311, "granite-embedding-311M-multilingual-r2-Q8_0.gguf", "", ""),
    ("qwen3-embed-0.6b", 0.6, "Qwen3-Embedding-0.6B-Q8_0.gguf", QWEN_Q, ""),
    ("pplx-embed-0.6b", 0.6, "pplx-embed-v1-0.6B-Q8_0.gguf", "", ""),
]


def _embed(url, texts, batch=16):
    out = []
    for i in range(0, len(texts), batch):
        body = json.dumps({"input": texts[i:i + batch], "model": "e"}).encode()
        req = urllib.request.Request(url + "/v1/embeddings", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read())["data"]
        out += [d["embedding"] for d in sorted(data, key=lambda d: d["index"])]
    return [_norm(v) for v in out]


def _norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def score(qv, dv, ids):
    r1 = r3 = mrr = 0.0
    misses = []
    for (q, gold), v in zip(QUERIES, qv):
        ranked = sorted(range(len(dv)), key=lambda j: -sum(a * b for a, b in zip(v, dv[j])))
        rank = next(i for i, j in enumerate(ranked, 1) if ids[j] in gold)
        r1 += rank == 1
        r3 += rank <= 3
        mrr += 1 / rank
        if rank > 3:
            misses.append({"q": q, "rank": rank, "top": ids[ranked[0]]})
    n = len(QUERIES)
    return {"recall@1": round(r1 / n, 3), "recall@3": round(r3 / n, 3), "mrr": round(mrr / n, 3), "misses": misses}


def bm25_baseline(docs, k1=1.5, b=0.75):
    """No model at all: classic keyword search, the bar every embedder must clear."""
    import re
    tok = lambda t: re.findall(r"[a-z0-9]+", t.lower())
    dt = [tok(c["text"]) for c in docs]
    avg = sum(map(len, dt)) / len(dt)
    df = {}
    for d in dt:
        for w in set(d):
            df[w] = df.get(w, 0) + 1
    N = len(dt)
    def s(q, d):
        return sum(math.log(1 + (N - df[w] + .5) / (df[w] + .5)) * d.count(w) * (k1 + 1)
                   / (d.count(w) + k1 * (1 - b + b * len(d) / avg)) for w in tok(q) if w in df)
    ids = [c["id"] for c in docs]
    r1 = r3 = mrr = 0.0
    for q, gold in QUERIES:
        ranked = sorted(range(N), key=lambda j: -s(q, dt[j]))
        rank = next(i for i, j in enumerate(ranked, 1) if ids[j] in gold)
        r1 += rank == 1; r3 += rank <= 3; mrr += 1 / rank
    n = len(QUERIES)
    return {"model": "bm25 (no model)", "size_mb": 0, "recall@1": round(r1 / n, 3), "recall@3": round(r3 / n, 3), "mrr": round(mrr / n, 3)}


def run(keys):
    rid = time.strftime("%Y%m%dT%H%M%S")
    out = ROOT / "bench" / "runs" / "senses" / "embed" / rid
    out.mkdir(parents=True, exist_ok=True)
    docs = chunks()
    ids = [c["id"] for c in docs]
    results = [bm25_baseline(docs)]
    print(results[0], flush=True)
    for key, pb, f, qp, dp in EMBEDDERS:
        if keys and key not in keys:
            continue
        rec = {"model": key, "params_b": pb, "file": f, "query_prefix": bool(qp),
               "size_mb": round((OC.MODELS_DIR / f).stat().st_size / 1e6) if (OC.MODELS_DIR / f).exists() else None}
        srv = ModelServer(Participant(key, "embed", pb, "Q8_0", f), ctx=2048, extra_args=["--embedding", "-ub", "2048", "-b", "2048"])
        try:
            srv.start(warm=False)
            t0 = time.time()
            dv = _embed(srv.url, [dp + c["text"] for c in docs])
            rec["docs_per_s"] = round(len(docs) / (time.time() - t0), 1)
            t0 = time.time()
            qv = _embed(srv.url, [qp + q for q, _ in QUERIES], batch=1)
            rec["query_ms"] = round((time.time() - t0) / len(QUERIES) * 1000)
            rec.update(score(qv, dv, ids))
        except Exception as e:
            rec["error"] = str(e)[:300]
        finally:
            srv.stop()
        results.append(rec)
        print(f"{key:<22} {rec.get('size_mb')}MB r@1 {rec.get('recall@1')} r@3 {rec.get('recall@3')} "
              f"mrr {rec.get('mrr')} {rec.get('docs_per_s')} doc/s {rec.get('query_ms')} ms/q {rec.get('error', '')}", flush=True)
    (out / "results.json").write_text(json.dumps({"corpus": len(docs), "queries": len(QUERIES),
                                                  "threads": OC.SERVER_THREADS, "results": results}, indent=1))
    return out


if __name__ == "__main__":
    print("evidence:", run(sys.argv[1:]))
