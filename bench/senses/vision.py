"""Vision suite: can a small vision model say what's in the studio's own art?

Task 1: each model names the 27 sticker icons (web/art/icons/ui). An answer passes if
it names what is drawn (any listed word), so "lamp" counts for the lantern.
Gold is what the picture shows, not the button's job: the help icon is a
lantern. Task 2: read the main button's label off 12 rendered Workbench screens
(exact text). Served by llama.cpp with the model's mmproj, on CPU.

    python3 -m bench.senses.vision [<key> ...]
"""
import base64
import io
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from bench.olympics import config as OC
from bench.olympics.participants import Participant
from bench.olympics.runtime import ModelServer

ROOT = Path(__file__).resolve().parents[2]
ICONS = ROOT / "web" / "art" / "icons" / "ui"
ASK = "What object is shown in this picture? Answer with one or two words."

GOLD = {
    "bell": ["bell"], "book": ["book"], "chat": ["speech", "bubble", "chat", "dialog", "message", "balloon"],
    "check": ["check", "checkmark", "tick"], "chronicle": ["book", "quill", "feather", "journal", "diary", "notebook"],
    "export": ["boat", "ship", "wave"], "floor": ["tree", "trunk", "stump", "log"],
    "heart": ["heart"], "help": ["lantern", "lamp"], "home": ["door", "house", "home", "tree", "hut"],
    "info": ["stone", "pebble", "orb", "ball", "sphere", "gem", "egg", "marble", "pearl"], "library": ["book"],
    "lock": ["lock", "padlock"], "map-pin": ["acorn", "nut"], "new": ["sprout", "seedling", "plant", "seed", "acorn"],
    "open": ["chest", "treasure", "trunk"], "play": ["play", "button", "arrow"], "quill": ["quill", "feather", "ink", "pen"],
    "save": ["acorn", "box", "crate", "nut"], "search": ["magnif*", "lens", "glass"],
    "settings": ["gear", "cog", "sun"], "share": ["envelope", "letter", "mail"], "sparkle": ["star", "sparkle"],
    "star": ["star"], "trash": ["basket", "paper", "bin", "trash"], "undo": ["arrow", "vine", "leaf", "leaves"],
    "warning": ["mushroom", "toadstool"],
}

# (key, params_b incl. vision, model file, mmproj file, licence)
VISION = [
    ("smolvlm2-256m", 0.26, "SmolVLM2-256M-Video-Instruct-Q8_0.gguf", "mmproj-SmolVLM2-256M-Video-Instruct-Q8_0.gguf", "Apache-2.0"),
    ("lfm2.5-vl-450m", 0.45, "LFM2.5-VL-450M-Q8_0.gguf", "mmproj-LFM2.5-VL-450m-Q8_0.gguf", "LFM Open"),
    ("smolvlm2-500m", 0.5, "SmolVLM2-500M-Video-Instruct-Q8_0.gguf", "mmproj-SmolVLM2-500M-Video-Instruct-Q8_0.gguf", "Apache-2.0"),
    ("qwen3.5-0.8b-q8", 0.8, "Qwen3.5-0.8B-Q8_0.gguf", "mmproj-Qwen3.5-0.8B-F16.gguf", "Apache-2.0"),
    ("minicpm-v-4.6", 1.3, "MiniCPM-V-4.6-Q4_K_M.gguf", "mmproj-MiniCPM-V-4.6-Q8_0.gguf", "Apache-2.0"),
    ("lfm2.5-vl-1.6b", 1.6, "LFM2.5-VL-1.6B-Q4_K_M.gguf", "mmproj-LFM2.5-VL-1.6b-Q8_0.gguf", "LFM Open"),
    ("gemma4-e2b", 5.1, "gemma-4-E2B_q4_0-it.gguf", "gemma-4-E2B-it-mmproj.gguf", "Apache-2.0"),
]


def png_uri(path, size=384):
    """webp with alpha -> PNG on white (llama.cpp's decoder has no webp)."""
    png = subprocess.run(["magick", str(path), "-background", "white", "-alpha", "remove", "-resize",
                          f"{size}x{size}", "png:-"], capture_output=True, check=True).stdout
    return "data:image/png;base64," + base64.b64encode(png).decode()


def ask(url, alias, uri, question=ASK):
    body = json.dumps({"model": alias, "temperature": 0, "max_tokens": 48,
                       "chat_template_kwargs": {"enable_thinking": False},
                       "messages": [{"role": "user", "content": [
                           {"type": "image_url", "image_url": {"url": uri}}, {"type": "text", "text": question}]}]}).encode()
    t0 = time.time()
    req = urllib.request.Request(url + "/v1/chat/completions", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        msg = json.loads(r.read())["choices"][0]["message"]
    return (msg.get("content") or "").strip(), round(time.time() - t0, 2)


def passes(answer, words):
    """Whole words (plurals allowed); a trailing * marks a prefix."""
    a = re.sub(r"<think>.*?</think>", "", answer, flags=re.S).lower()
    return any(re.search(r"\b" + re.escape(w[:-1]) if w.endswith("*") else r"\b" + re.escape(w) + r"(s|es)?\b", a)
               for w in words)


# Task 2: read a label off a rendered studio screen (checking screenshots).
LABELS = ["Play newest build", "Clear cache", "Open the vault", "Rename world", "Export chronicle",
          "Undo last move", "Share with a friend", "Start the delve", "Save this floor", "Pack the satchel",
          "Ring the bell", "Carve a rune"]
DECOYS = ["Settings", "Help", "Cancel", "Back"]


def label_uris():
    """Small Workbench-style screens, each with one primary button among decoys."""
    from playwright.sync_api import sync_playwright
    css = (ROOT / "bench" / "design" / "workbench.css").read_text()
    uris = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 640, "height": 360})
        for i, lab in enumerate(LABELS):
            d = DECOYS[i % 4], DECOYS[(i + 1) % 4]
            pg.set_content(f"<style>{css}</style><body class='wb-page' style='padding:24px'><h1 class='wb-h1'>Project {i + 1}</h1>"
                           f"<p class='wb-lede'>{12 + i} images · 26 Sep</p><div class='wb-actions'><button class='wb-btn'>{d[0]}</button>"
                           f"<button class='wb-btn wb-btn--primary'>{lab}</button><button class='wb-btn wb-btn--quiet'>{d[1]}</button></div></body>")
            uris[lab] = "data:image/png;base64," + base64.b64encode(pg.screenshot()).decode()
        b.close()
    return uris


READ = "What does the highlighted main button say? Reply with its exact text only."


def run(keys):
    rid = time.strftime("%Y%m%dT%H%M%S")
    out = ROOT / "bench" / "runs" / "senses" / "vision" / rid
    out.mkdir(parents=True, exist_ok=True)
    images = {n: png_uri(ICONS / f"{n}.webp") for n in GOLD}
    labels = label_uris()
    results = []
    for key, pb, f, mm, lic in VISION:
        if keys and key not in keys:
            continue
        size = sum((OC.MODELS_DIR / x).stat().st_size for x in (f, mm) if (OC.MODELS_DIR / x).exists())
        rec = {"model": key, "params_b": pb, "licence": lic, "size_mb": round(size / 1e6), "answers": {}}
        srv = ModelServer(Participant(key, "vision", pb, "", f), ctx=4096, extra_args=["--mmproj", f"/models/{mm}"])
        try:
            srv.start(wait_timeout=300)
            secs = []
            for name, uri in images.items():
                a, s = ask(srv.url, key, uri)
                secs.append(s)
                rec["answers"][name] = {"answer": a, "pass": passes(a, GOLD[name]), "seconds": s}
            rec["named"] = sum(v["pass"] for v in rec["answers"].values())
            rec["reads"] = {}
            for lab, uri in labels.items():
                a, s = ask(srv.url, key, uri, READ)
                secs.append(s)
                rec["reads"][lab] = {"answer": a, "pass": lab.lower() in a.lower().strip(" .\"'"), "seconds": s}
            rec["read"] = sum(v["pass"] for v in rec["reads"].values())
            rec["of"] = len(images)
            rec["median_s"] = sorted(secs)[len(secs) // 2]
        except Exception as e:
            rec["error"] = str(e)[:300]
        finally:
            srv.stop()
        results.append(rec)
        print(f"{key:<18} {rec['size_mb']}MB named {rec.get('named')}/{rec.get('of')} read {rec.get('read')}/{len(LABELS)} {rec.get('median_s')}s {rec.get('error', '')}", flush=True)
    (out / "results.json").write_text(json.dumps({"threads": OC.SERVER_THREADS, "question": ASK, "read_question": READ, "results": results}, indent=1))
    return out


if __name__ == "__main__":
    print("evidence:", run(sys.argv[1:]))
