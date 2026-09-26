"""Re-check a design run's saved pages with the current checks and stylesheet.

The model outputs don't change; only the scoring does. Writes rescore.json
next to summary.json (the original scores stay untouched) and prints the
per-participant table. Used after the 26 Sep Workbench fix (.wb-table td a
shrank wb-btn links in tables to 36px).

    python3 -m bench.design.rescore bench/runs/design/<rid> [...]
"""
import json
import sys
from pathlib import Path

from .briefs import BRIEFS, HARD_BRIEFS
from .run import KEYS, _required, check, table

BY_ID = {b["id"]: b for b in BRIEFS + HARD_BRIEFS}


def rescore(run_dir):
    run_dir = Path(run_dir)
    out = []
    for rec_path in sorted(run_dir.glob("*/*.json")):
        rec = json.loads(rec_path.read_text())
        if "brief" not in rec:
            continue
        b = BY_ID[rec["brief"]]
        base = rec_path.with_suffix("")
        pages = [base.with_suffix(".html")] + sorted(base.parent.glob(base.name + ".fix*.html"))
        best = None
        for hp in [p for p in pages if p.exists()]:
            res = check(hp, hp.with_suffix(".rescore.png"))
            hp.with_suffix(".rescore.png").unlink(missing_ok=True)
            res["required_parts"] = not _required(hp.read_text(errors="replace"), b["require"], b.get("forbid_many"))
            score = sum(bool(res.get(k)) for k in KEYS)
            if best is None or score > best[0]:
                best = (score, {k: bool(res.get(k)) for k in KEYS})
        new = dict(rec, was_score=rec.get("score"))
        if best:
            new.update(best[1], score=best[0])
            new["pass"] = new["renders"] and new["score"] >= 5
        out.append(new)
    (run_dir / "rescore.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    for d in sys.argv[1:]:
        rows = rescore(d)
        changed = [(r["participant"], r["brief"], r["was_score"], r["score"]) for r in rows if r.get("was_score") != r["score"]]
        print(d, "\n" + table(rows), "\nchanged:", changed)
