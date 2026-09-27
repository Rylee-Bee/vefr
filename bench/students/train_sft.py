"""Train a small student on teacher examples (LoRA, loss on the answer only), then grade it
on the held-out EA cup requests with the same prompt and checks the cup uses.

    python -m bench.students.train_sft --base Qwen/Qwen3-0.6B --name qwen3-0.6b [--epochs 2]
    python -m bench.students.train_sft --base Qwen/Qwen3-0.6B --name qwen3-0.6b-base --eval-only

Examples: ~/apps/students/ratatoskr/examples.jsonl. Output: ~/apps/students/ratatoskr/runs/<name>/
(adapter, merged model, eval.json). The EA cup's 30 requests are never trained on.
"""
import argparse, json, math, random, sys, time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bench.story import ea

ROOT = Path.home() / "apps/students/ratatoskr"


def chat_ids(tok, messages, add_gen):
    kw = {"enable_thinking": False} if "qwen" in tok.name_or_path.lower() else {}
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=add_gen, **kw)
    return tok(text, add_special_tokens=False)["input_ids"]


def build(tok, ex, max_len=768):
    msgs = ea.prompts("voice", ex["request"])
    prompt = chat_ids(tok, msgs, True)
    full = chat_ids(tok, msgs + [{"role": "assistant", "content": ex["target"]}], False)
    if isinstance(prompt, dict): prompt, full = prompt["input_ids"], full["input_ids"]
    full = full[:max_len]
    labels = [-100] * min(len(prompt), len(full)) + full[len(prompt):]
    return torch.tensor(full), torch.tensor(labels[:len(full)])


@torch.no_grad()
def grade(model, tok, dev):
    model.eval(); rows = []
    for i, case in enumerate(ea.REQUESTS):
        ids = chat_ids(tok, ea.prompts("voice", case[0]), True)
        if isinstance(ids, dict): ids = ids["input_ids"]
        x = torch.tensor([ids], device=dev)
        t0 = time.time()
        y = model.generate(x, max_new_tokens=160, do_sample=False, pad_token_id=tok.eos_token_id)
        text = tok.decode(y[0][x.shape[1]:], skip_special_tokens=True)
        out = ea.parse(text); c = ea.check(out, case)
        rows.append({"case": i, "request": case[0], "output": out, "raw": text[:300], "checks": c,
                     "score": sum(c.values()), "of": 5, "seconds": round(time.time() - t0, 2)})
    right = sum(bool(r["checks"].get("right_room")) for r in rows)
    allc = sum(r["score"] == r["of"] for r in rows)
    return {"right_room": right, "all_checks": allc, "n": len(rows), "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--name", required=True)
    ap.add_argument("--epochs", type=float, default=2); ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16); ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--eval-only", action="store_true")
    ap.add_argument("--precision", choices=["fp32", "bf16", "fp16"], default="fp32",
                    help="fp16 autocast without a grad scaler went to nan on granite-350m (2026-09-26)")
    ap.add_argument("--max-steps", type=int, default=0, help="stop early (smoke tests)")
    ap.add_argument("--no-grade", action="store_true", help="skip the held-out grade (smoke tests)")
    ap.add_argument("--checkpointing", action="store_true", help="recompute activations (3-4B on 16 GB)")
    a = ap.parse_args()
    dev = "cuda"
    out = ROOT / "runs" / a.name; out.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(a.base)
    # bf16 keeps fp32's range (no overflow, unlike fp16) at half the memory: base weights
    # in bf16, the LoRA weights in fp32. fp32 everywhere for the smallest students.
    wdtype = torch.bfloat16 if a.precision == "bf16" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(a.base, dtype=wdtype).to(dev)
    if not a.eval_only:
        from peft import LoraConfig, get_peft_model
        model = get_peft_model(model, LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05,
                                                 target_modules="all-linear", task_type="CAUSAL_LM"))
        for p in model.parameters():
            if p.requires_grad:
                p.data = p.data.float()
        if a.checkpointing:
            model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
            model.enable_input_require_grads()
        exs = [json.loads(l) for l in open(ROOT / "examples.jsonl")]
        random.Random(7).shuffle(exs)
        data = [build(tok, e) for e in exs]
        opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=0.0)
        total = math.ceil(len(data) * a.epochs / a.accum)
        if a.max_steps: total = min(total, a.max_steps)
        amp = {"fp32": None, "bf16": torch.bfloat16, "fp16": torch.float16}[a.precision]
        sched = lambda s: a.lr * min(1, s / 20) * 0.5 * (1 + math.cos(math.pi * min(1, s / total)))
        model.train(); step = 0; t0 = time.time(); i = 0
        print(f"{len(data)} examples, {total} optimizer steps, trainable "
              f"{sum(p.numel() for p in model.parameters() if p.requires_grad)/1e6:.1f}M", flush=True)
        while step < total:
            loss_acc = 0.0
            for _ in range(a.accum):
                ids, labels = data[i % len(data)]; i += 1
                with torch.autocast("cuda", dtype=amp or torch.float32, enabled=amp is not None):
                    loss = model(input_ids=ids[None].to(dev), labels=labels[None].to(dev)).loss / a.accum
                if not torch.isfinite(loss):
                    raise SystemExit(f"loss is {loss.item()} at step {step} ({a.precision}); stopping instead of training on nan")
                loss.backward(); loss_acc += loss.item()
            for g in opt.param_groups: g["lr"] = sched(step)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); opt.zero_grad(set_to_none=True); step += 1
            if step % 20 == 0 or step <= 3:
                print(f"step {step}/{total} loss {loss_acc:.4f} {(time.time()-t0)/step:.2f}s/step", flush=True)
        model.save_pretrained(out / "adapter")
        if wdtype != torch.float32:
            model = model.to(wdtype)   # LoRA back to the base's dtype before merging
        model = model.merge_and_unload()
        model.save_pretrained(out / "merged"); tok.save_pretrained(out / "merged")
    if a.no_grade:
        return
    g = grade(model, tok, dev)
    g.update(base=a.base, name=a.name, trained=not a.eval_only)
    (out / "eval.json").write_text(json.dumps(g, indent=1))
    print(f"{a.name}: right room {g['right_room']}/{g['n']}, all checks {g['all_checks']}/{g['n']}", flush=True)


if __name__ == "__main__":
    main()
