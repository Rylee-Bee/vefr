"""Teach cup: does the local model name the right idea (and stay quiet when it should)?

    VEFR_LLAMACPP_URL=... python -m bench.teach.cup
    VEFR_LLAMACPP_URL=... python -m bench.teach.cup --cases private.json [out.json]
Positives: every teachable idea's own example. Negatives: ordinary requests that
wake a cue but use no idea. Prints right / wrong / quiet, and the misses.
"""
import json
import sys
import time

from vefr import teach
from vefr.room import load_glossary

NEGATIVES = [
    "Can you fix the typo in the keeper's name until I get back?",
    "Make the font bigger please.",
    "What colour should the random rug be?",
    "I'll come back to this later.",
    "The keeper wants a better name, can you suggest one?",
    "How much gold does the player start with?",
    "Put the chair on top of the list.",
    "The map is hard to read for me right now, can you describe it?",
    "Remember that I prefer short answers.",
    "Is it safe to delete the old draft?",
]


def real_cases(path):
    """Outside cases: {"cases": [{"text", "want": [ideas or "none"]}]}. Kept outside the
    public repo when they're someone's own words (e.g. the owner's Cottage messages)."""
    g = load_glossary()
    rows = []
    for c in json.load(open(path))["cases"]:
        cands = teach.candidates(c["text"], g)
        got = teach.ask_model(c["text"], cands, g) if cands else ("none", "")
        term = got[0] if got else None
        rows.append({"text": c["text"], "want": c["want"], "got": term, "cands": cands,
                     "context": got[1] if got else "", "ok": term in c["want"]})
    right = sum(r["ok"] for r in rows)
    wrong_note = sum(r["got"] not in (None, "none") and not r["ok"] for r in rows)
    missed = sum(r["got"] in (None, "none") and "none" not in r["want"] for r in rows)
    print(f"real cases: fair {right}/{len(rows)}; a wrong idea named {wrong_note}; stayed quiet on a real one {missed}")
    for r in rows:
        if not r["ok"]:
            print(f"  got {r['got']!r} want {r['want']} from {r['cands']} :: {r['text'][:70]}")
    return rows


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--cases":
        rows = real_cases(sys.argv[2])
        if len(sys.argv) > 3:
            json.dump(rows, open(sys.argv[3], "w"), indent=1)
        return
    g = load_glossary()
    rows, t0 = [], time.time()
    for key, e in teach.teachable(g).items():
        c = teach.candidates(e["example"], g)
        got = teach.ask_model(e["example"], c, g) if c else ("none", "")
        rows.append({"want": key, "got": got[0] if got else None, "context": got[1] if got else "", "cands": c, "text": e["example"]})
    for text in NEGATIVES:
        c = teach.candidates(text, g)
        got = teach.ask_model(text, c, g) if c else ("none", "")
        rows.append({"want": "none", "got": got[0] if got else None, "context": "", "cands": c, "text": text})
    pos = [r for r in rows if r["want"] != "none"]
    neg = [r for r in rows if r["want"] == "none"]
    right = sum(r["got"] == r["want"] for r in pos)
    quiet = sum(r["got"] == "none" for r in pos)
    false = sum(r["got"] not in ("none", None) for r in neg)
    down = sum(r["got"] is None for r in rows)
    print(f"ideas named right {right}/{len(pos)} (quiet {quiet}); false notes {false}/{len(neg)}; no answer {down}; {time.time()-t0:.0f}s")
    for r in rows:
        if r["got"] != r["want"]:
            print(f"  want {r['want']!r} got {r['got']!r} from {r['cands']} :: {r['text'][:70]}")
    if len(sys.argv) > 1:
        json.dump(rows, open(sys.argv[1], "w"), indent=1)


if __name__ == "__main__":
    main()
