"""Search corpus for the embeddings suite: the sample world, the lore packs
and the studio handbook, split into paragraph chunks with stable ids."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ["worlds/sample-world", "worlds/lore", "web/library"]


def chunks(min_words=25, max_words=180):
    out = []
    for src in SOURCES:
        for f in sorted((ROOT / src).rglob("*.md")):
            if f.name.upper().startswith("LICENSE"):
                continue
            rel = f.relative_to(ROOT).as_posix()
            buf, n = [], 0
            for para in re.split(r"\n\s*\n", f.read_text(errors="replace")):
                para = para.strip()
                if not para:
                    continue
                buf.append(para)
                n += len(para.split())
                if n >= min_words:
                    out.append({"id": f"{rel}#{len([c for c in out if c['file'] == rel])}", "file": rel,
                                "text": " ".join(" ".join(buf).split()[:max_words])})
                    buf, n = [], 0
            if buf:
                out.append({"id": f"{rel}#{len([c for c in out if c['file'] == rel])}", "file": rel,
                            "text": " ".join(" ".join(buf).split()[:max_words])})
    return out
