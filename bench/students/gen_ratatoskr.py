"""Training data for Ratatoskr (the studio's EA): teachers write, rules filter.

Teachers (terms checked 2026-09-26, all allow training on their output):
  deepseek   - DeepSeek official API, deepseek-flash (ToS 4.2(3) allows distillation);
               key read from ~/.config/deepseek/key at run time, never printed.
  qwen-plan  - Qwen 3.8 flash on the owner's paid Alibaba token plan.
Never Claude or Codex output.

Step 1: each teacher writes varied requests for one room (the room is the label).
Step 2: each teacher answers a request as Ratatoskr, using the EA cup's 'voice' prompt.
Keep only when: the teacher's room == the label, the note keeps the request's content
words, no invented names, and the request is not near any held-out EA cup request.

Spend guard: DeepSeek tokens are priced at PEAK rates and calls stop at SPEND_CAP_USD.
Writes ~/apps/students/ratatoskr/{requests,examples}.jsonl and spend.json.
"""
import json
import os
import random
import re
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bench.story import ea  # the cup: rooms, voice prompt, checks, held-out requests

OUT = Path.home() / "apps/students/ratatoskr"; OUT.mkdir(parents=True, exist_ok=True)
SPEND_CAP_USD = float(os.environ.get("SPEND_CAP_USD", "8"))
PRICE = {"in": 0.30 / 1e6, "out": 1.20 / 1e6}          # deepseek-flash, peak
spend = {"deepseek_usd": 0.0, "deepseek_in": 0, "deepseek_out": 0, "calls": {}}
lock = threading.Lock()


def _opencode(provider):
    cfg = json.loads(re.sub(r"^\s*//.*$", "", (Path.home() / ".config/opencode/opencode.json").read_text(), flags=re.M))
    return cfg["provider"][provider]["options"]


TEACHERS = {
    "deepseek": lambda: ("https://api.deepseek.com/v1", "deepseek-flash", (Path.home() / ".config/deepseek/key").read_text().strip()),
    "qwen-plan": lambda: (_opencode("bailian-cli")["baseURL"], "qwen3.8-flash", _opencode("bailian-cli")["apiKey"]),
}


def chat(teacher, messages, max_tokens=900, temperature=0.9):
    if teacher == "deepseek" and spend["deepseek_usd"] >= SPEND_CAP_USD:
        raise RuntimeError("spend cap reached")
    url, model, key = TEACHERS[teacher]()
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if teacher == "qwen-plan":
        body["enable_thinking"] = False
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                out = json.loads(r.read())
            break
        except Exception:
            if attempt == 2: raise
            time.sleep(3 * (attempt + 1))
    u = out.get("usage") or {}
    with lock:
        spend["calls"][teacher] = spend["calls"].get(teacher, 0) + 1
        if teacher == "deepseek":
            spend["deepseek_in"] += u.get("prompt_tokens", 0); spend["deepseek_out"] += u.get("completion_tokens", 0)
            spend["deepseek_usd"] = spend["deepseek_in"] * PRICE["in"] + spend["deepseek_out"] * PRICE["out"]
        (OUT / "spend.json").write_text(json.dumps(spend, indent=1))
    return out["choices"][0]["message"].get("content") or ""


def words(s):
    return {w for w in re.findall(r"[a-z]+", s.lower()) if len(w) > 3}


HELD = [set(re.findall(r"[a-z]+", r[0].lower())) for r in ea.REQUESTS]


def near_held_out(req):
    w = set(re.findall(r"[a-z]+", req.lower()))
    return any(len(w & h) / max(1, len(w | h)) > 0.5 for h in HELD)


STYLES = ["short and casual", "polite and detailed", "tired, one line, lowercase", "excited", "a bit vague",
          "with a small typo", "as a question", "as an instruction"]


def gen_requests(teacher, room, n=12):
    if room == "none":
        brief = ("things an author might say to a game-studio assistant that are NOT the studio's job or are too unclear to route: "
                 "everyday errands, real-world tasks, maths homework, weather, shopping, one-word mumbles, greetings")
    else:
        name, job = ea.ROOMS[room]
        brief = f"requests that belong to {name} in a cozy game-making studio: {job}"
    style = ", ".join(random.sample(STYLES, 3))
    text = chat(teacher, [{"role": "user", "content":
        f"Write {n} different short requests an author might type to a game-making studio's assistant. They must all be {brief} "
        f"Mix these styles: {style}. Invent your own specifics (places, things, characters). Never name the room. "
        "Reply with only a JSON list of strings."}], max_tokens=1200)
    m = re.search(r"\[.*\]", text, re.S)
    try:
        items = [s.strip() for s in json.loads(m.group(0)) if isinstance(s, str) and 3 <= len(s) <= 220] if m else []
    except json.JSONDecodeError:
        items = []
    return [{"request": s, "label": room, "teacher": teacher} for s in items if not near_held_out(s)]


def answer(teacher, r):
    text = chat(teacher, ea.prompts("voice", r["request"]), max_tokens=400, temperature=0.7)
    out = ea.parse(text)
    if not isinstance(out, dict):
        return None
    room = str(out.get("room", "")).strip().lower()
    note = str(out.get("note", "")).strip()
    ok_room = room == r["label"]
    content = words(r["request"]) - {"please", "could", "would", "want", "need", "make", "like"}
    keeps = r["label"] == "none" or not content or len(content & words(note)) / len(content) >= 0.6
    names_ok = not ea._invented_names(note + " " + str(out.get("say", "")), ea.ALLOWED | ea.STUDIO_NAMES | set(re.findall(r"[A-Z][a-z]+", r["request"])))
    short = len(note.split()) <= 40 and len(str(out.get("say", "")).split()) <= 40
    if ok_room and keeps and names_ok and short:
        return {"request": r["request"], "label": r["label"], "teacher": teacher,
                "target": json.dumps({"room": room, "note": note, "say": str(out.get("say", "")).strip()}, ensure_ascii=False)}
    return None


def main(rounds=int(os.environ.get("ROUNDS", "6"))):
    rooms = list(ea.ROOMS) + ["none"]
    jobs = [(t, room) for _ in range(rounds) for room in rooms for t in TEACHERS]
    reqs = []
    with ThreadPoolExecutor(6) as ex:
        for batch in ex.map(lambda j: _safe(gen_requests, *j), jobs):
            reqs += batch or []
    seen, uniq = set(), []
    for r in reqs:
        k = re.sub(r"\W", "", r["request"].lower())
        if k not in seen: seen.add(k); uniq.append(r)
    with open(OUT / "requests.jsonl", "w") as f:
        for r in uniq: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(uniq), "requests;", {room: sum(r["label"] == room for r in uniq) for room in rooms}, flush=True)
    kept = []
    with ThreadPoolExecutor(8) as ex:   # each request answered by the OTHER teacher too, for variety
        pairs = [(t, r) for r in uniq for t in TEACHERS]
        for ex_ in ex.map(lambda p: _safe(answer, *p), pairs):
            if ex_: kept.append(ex_)
    with open(OUT / "examples.jsonl", "w") as f:
        for e in kept: f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(len(kept), "kept of", len(pairs), "answers; spend", json.dumps(spend), flush=True)


def _safe(fn, *a):
    try: return fn(*a)
    except Exception as e:
        print("skip:", str(e)[:100], flush=True); return None


if __name__ == "__main__":
    main()
