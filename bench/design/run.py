"""Design cup: can a model build a correct Workbench screen?

Each participant gets the Workbench guide and one brief per task and must
return a single HTML file. Checks are automatic (Playwright + axe):
renders, workbench-only styling, accessibility, phone fit, 44px targets,
required parts. Evidence (HTML, screenshots, scores) lands in
bench/runs/design/<run-id>/.

    python3 -m bench.design.run <participant> [<participant> ...]

Participants: an olympics key (served on CPU by bench.olympics.runtime), or
`endpoint:<name>` defined in ENDPOINTS below.
"""
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from bench.olympics import config as OC
from bench.olympics.participants import PARTICIPANTS
from bench.olympics.runtime import ModelServer
from .briefs import BRIEFS, HARD_BRIEFS

# DESIGN_SET: base | hard | all.  DESIGN_REPEATS: runs per brief (ties need >1).
SET = os.environ.get("DESIGN_SET", "base")
REPEATS = int(os.environ.get("DESIGN_REPEATS", "1"))
# DESIGN_REPAIR: extra tries after the checks say what failed (0 = one shot).
REPAIR = int(os.environ.get("DESIGN_REPAIR", "0"))
KEYS = ["renders", "workbench_only", "accessible", "phone_fit", "targets_44", "required_parts"]

AXE_HINTS = {
    "color-contrast": "some text has too little contrast: only put wb-text or wb-text-dim on wb-bg, wb-surface or wb-raise, and never set colours yourself",
    "image-alt": "every <img> needs an alt attribute (alt=\"\" if it is decorative)",
    "button-name": "every button needs visible text",
    "link-name": "every link needs visible text",
    "label": "every input needs a <label>",
    "list": "a <ul> or <ol> may only contain <li> children",
    "listitem": "every <li> must sit inside a <ul> or <ol>",
    "aria-allowed-attr": "remove ARIA attributes the element does not allow",
    "nested-interactive": "do not put a link or button inside another link or button",
    "td-headers-attr": "use <th scope=\"col\"> for column headers",
}


def _briefs():
    return {"base": BRIEFS, "hard": HARD_BRIEFS, "all": BRIEFS + HARD_BRIEFS}[SET]

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AXE = ROOT / "scripts" / "vendor" / "axe.min.js"
GUIDE = (HERE / "guide.md").read_text()
CSS = HERE / "workbench.css"
SYSTEM = ("You build internal tool screens with the Workbench design system. "
          "Reply with ONE complete HTML document only (start with <!doctype html>), "
          "no explanation. Link the stylesheet as <link rel=\"stylesheet\" href=\"/workbench.css\">. "
          "Use only wb- classes and the markup shown below; never write colours yourself.\n\n" + GUIDE)


def _opencode_key(provider):
    cfg = json.loads(re.sub(r"^\s*//.*$", "", (Path.home() / ".config/opencode/opencode.json").read_text(), flags=re.M))
    return cfg["provider"][provider]["options"]


ENDPOINTS = {
    # the workstation's resident 35B (llama-subagent)
    "local-35b": lambda: ("http://127.0.0.1:11500/v1", "qwen35-35b-iq3xxs", None),
    # cloud reference on the owner's plan (key read at run time, never stored)
    "qwen3.8-flash-cloud": lambda: (_opencode_key("bailian-cli")["baseURL"], "qwen3.8-flash", _opencode_key("bailian-cli")["apiKey"]),
}


def _chat(url, model, key, messages, max_tokens=3500):
    body = json.dumps({"model": model, "messages": messages, "temperature": 0.2, "max_tokens": max_tokens}).encode()
    h = {"Content-Type": "application/json"}
    if key:
        h["Authorization"] = "Bearer " + key
    t0 = time.time()
    with urllib.request.urlopen(urllib.request.Request(url.rstrip("/") + "/chat/completions", data=body, headers=h), timeout=900) as r:
        out = json.loads(r.read())
    msg = out["choices"][0]["message"]
    return (msg.get("content") or ""), round(time.time() - t0, 1), (out.get("usage") or {}).get("completion_tokens")


def extract_html(text):
    m = re.search(r"```(?:html)?\s*(<!doctype.*?)```", text, re.S | re.I)
    if m:
        return m.group(1)
    i = text.lower().find("<!doctype")
    return text[i:] if i >= 0 else text


def check(html_path, shot_path):
    """Return {check: bool} for one design."""
    from playwright.sync_api import sync_playwright
    src = html_path.read_text(errors="replace")
    res = {}
    raw = re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)", re.sub(r"<link[^>]*>", "", src))
    res["workbench_only"] = bool(re.search(r'class="[^"]*\bwb-', src)) and not raw
    res["_raw_colours"] = sorted(set(raw))[:6]
    with sync_playwright() as p:
        b = p.chromium.launch()
        errs = []
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.route("**/workbench.css", lambda r: r.fulfill(path=str(CSS), content_type="text/css"))
        pg.route(re.compile(r".*\.(webp|png|jpg)$"), lambda r: r.fulfill(status=200, content_type="image/svg+xml",
                 body="<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 4 4'><rect width='4' height='4' fill='gray'/></svg>"))
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "favicon" not in m.text else None)
        try:
            pg.route("http://design.test/index.html", lambda r: r.fulfill(body=src, content_type="text/html"))
            pg.goto("http://design.test/index.html", wait_until="load")
            pg.wait_for_timeout(300)
            res["renders"] = not errs and pg.evaluate("document.body.innerText.trim().length > 40")
            res["_errors"] = errs[:3]
            pg.screenshot(path=str(shot_path))
            pg.add_script_tag(path=str(AXE))
            v = pg.evaluate("() => axe.run(document, {resultTypes:['violations']}).then(r => r.violations.filter(v => ['serious','critical'].includes(v.impact)).map(v => v.id))")
            res["accessible"] = len(v) == 0
            res["_axe"] = v
            small = pg.evaluate("""() => [...document.querySelectorAll('button, [role=button], .wb-btn, input, select')]
                .filter(e => e.offsetParent !== null).filter(e => e.getBoundingClientRect().height < 43.5)
                .map(e => e.outerHTML.slice(0, 80))""")
            res["targets_44"] = not small
            res["_small"] = small[:4]
            pg.set_viewport_size({"width": 390, "height": 844})
            pg.wait_for_timeout(200)
            res["_phone_w"] = pg.evaluate("document.documentElement.scrollWidth")
            res["phone_fit"] = res["_phone_w"] <= 392
        except Exception as e:
            res["renders"] = False
            res["_error"] = str(e)[:200]
        b.close()
    return res


def run(participants):
    rid = time.strftime("%Y%m%dT%H%M%S")
    out_root = ROOT / "bench" / "runs" / "design" / rid
    summary = []
    for key in participants:
        server = None
        if key.startswith("endpoint:"):
            url, model, api_key = ENDPOINTS[key.split(":", 1)[1]]()
        else:
            server = ModelServer(PARTICIPANTS[key], ctx=16384 if REPAIR else None)
            server.start()
            url, model, api_key = server.url + "/v1", PARTICIPANTS[key].alias, None
        d = out_root / key.replace(":", "_")
        d.mkdir(parents=True, exist_ok=True)
        try:
            for b, rep in [(b, r) for b in _briefs() for r in range(1, REPEATS + 1)]:
                tag = b["id"] if REPEATS == 1 else f"{b['id']}.r{rep}"
                rec = {"participant": key, "brief": b["id"], "repeat": rep, "repair_max": REPAIR,
                       "backend": "cpu" if server and OC.NGPU == 0 else ("endpoint" if not server else "gpu")}
                msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": b["brief"]}]
                rounds, total_s = [], 0.0
                for attempt in range(REPAIR + 1):
                    try:
                        text, secs, toks = _chat(url, model, api_key, msgs)
                    except Exception as e:
                        rounds.append({"chat_error": str(e)[:200], "score": 0})
                        break
                    total_s += secs
                    html = extract_html(text)
                    suffix = "" if attempt == 0 else f".fix{attempt}"
                    hp = d / f"{tag}{suffix}.html"
                    hp.write_text(html)
                    res = check(hp, d / f"{tag}{suffix}.png")
                    missing = _required(html, b["require"], b.get("forbid_many"))
                    res["required_parts"] = not missing
                    res["_missing"] = missing
                    r = {k: bool(res.get(k)) for k in KEYS}
                    r.update(score=sum(r.values()), seconds=secs, tokens_out=toks, axe=res.get("_axe"), error=res.get("_error"))
                    rounds.append(r)
                    if r["score"] == len(KEYS) or attempt == REPAIR:
                        break
                    # the fix-it loop: keep only the latest attempt, say exactly what failed
                    msgs = msgs[:2] + [{"role": "assistant", "content": html}, {"role": "user", "content": feedback(res)}]
                last = rounds[-1]
                if "chat_error" in last and len(rounds) == 1:
                    rec.update(error=last["chat_error"], score=0)
                    summary.append(rec)
                    (d / f"{tag}.json").write_text(json.dumps(rec, indent=1))
                    continue
                best = max((x for x in rounds if "chat_error" not in x), key=lambda x: x["score"])
                rec.update({k: best[k] for k in KEYS}, seconds=round(total_s, 1), tokens_out=best["tokens_out"],
                           axe=best["axe"], error=best["error"], first_score=rounds[0].get("score", 0),
                           fixes_used=len(rounds) - 1, rounds=rounds)
                rec["score"] = best["score"]
                rec["pass"] = rec["renders"] and rec["required_parts"] and rec["score"] >= 5
                summary.append(rec)
                (d / f"{tag}.json").write_text(json.dumps(rec, indent=1))
                print(f"{key:<28} {tag:<22} {rec['first_score']}->{rec['score']}/6 {'PASS' if rec['pass'] else 'fail'} "
                      f"fixes {rec['fixes_used']} {rec['seconds']}s", flush=True)
        finally:
            if server:
                server.stop()
    (out_root / "summary.json").write_text(json.dumps(summary, indent=1))
    return out_root, summary


def feedback(res):
    """Plain, specific fix list from the checks (the wrapper a studio would give a small model)."""
    out = []
    if not res.get("renders"):
        out.append("The page failed to render or showed almost no text" + (f": {'; '.join(res.get('_errors') or [])}" if res.get("_errors") else "") + ".")
    if not res.get("workbench_only"):
        out.append(f"Remove every hand-written colour ({', '.join(res.get('_raw_colours') or [])}) and style only with wb- classes from the guide."
                   if res.get("_raw_colours") else "Use the wb- classes from the guide; the page has none.")
    for v in res.get("_axe") or []:
        out.append("Accessibility: " + AXE_HINTS.get(v, f"fix the '{v}' problem") + ".")
    if not res.get("targets_44"):
        out.append("These controls are shorter than 44px: " + " | ".join(res.get("_small") or []) +
                   ". Give every button and button-like link the wb-btn class and no custom sizes.")
    if not res.get("phone_fit"):
        out.append(f"On a 390px-wide phone the page is {res.get('_phone_w')}px wide. Let rows wrap, and put every table inside <div class=\"wb-table-wrap\">.")
    if res.get("_missing"):
        out.append("Missing or wrong parts: " + "; ".join(res["_missing"]) + ". Use the exact markup from the guide.")
    return ("Your page failed these checks:\n- " + "\n- ".join(out) +
            "\n\nReply with the complete corrected HTML document only (start with <!doctype html>). Keep everything that already worked.")


def _required(html, selectors, forbid_many=None):
    """Every selector present (a (selector, n) pair needs at least n);
    forbid_many: a selector allowed at most once (e.g. one primary action)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content(html)
        missing = []
        for s in selectors:
            sel, n = (s, 1) if isinstance(s, str) else s
            have = len(pg.query_selector_all(sel))
            if have < n:
                missing.append(f"{sel} (need {n}, found {have})" if n > 1 else f"{sel} (missing)")
        if forbid_many and len(pg.query_selector_all(forbid_many)) > 1:
            missing.append(f"only one {forbid_many} allowed, found {len(pg.query_selector_all(forbid_many))}")
        b.close()
    return missing


def table(summary):
    """Per participant: pass rate, mean score, median seconds."""
    rows = {}
    for r in summary:
        rows.setdefault(r["participant"], []).append(r)
    lines = [f"{'participant':<28} {'pass':>7} {'score':>6} {'med s':>6}"]
    for k, rs in rows.items():
        secs = sorted(r.get("seconds") or 0 for r in rs)
        lines.append(f"{k:<28} {sum(bool(r.get('pass')) for r in rs):>3}/{len(rs):<3} "
                     f"{sum(r['score'] for r in rs) / len(rs):>6.2f} {secs[len(secs) // 2]:>6}")
    return "\n".join(lines)


if __name__ == "__main__":
    root, summary = run(sys.argv[1:])
    print(table(summary))
    print("evidence:", root)
