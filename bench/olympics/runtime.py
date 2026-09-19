"""Runtime adapter: llama.cpp llama-server in podman (Vulkan on the 6900XT).

Every model is served with the same canonical flags:
  --jinja (chat template embedded in the GGUF wins)
  -ngl NGPU (GPU offload, 999 = all layers on Vulkan)
  -c SERVER_CTX, -t SERVER_THREADS
  --alias <participant key>

Wire protocol is OpenAI-compatible /v1/chat/completions. The rig is stdlib
only (urllib).
"""

import json
import subprocess
import time
import urllib.error
import urllib.request

from . import config


class ServerError(RuntimeError):
    pass


class ModelServer:
    def __init__(self, participant, port=None, ctx=None, ngl=None, extra_args=()):
        self.p = participant
        self.port = port or _free_port()
        self.ctx = ctx or config.SERVER_CTX
        self.ngl = ngl if ngl is not None else config.NGPU
        self.name = f"olympics-{participant.key}"
        self.url = f"http://127.0.0.1:{self.port}"
        self.extra_args = extra_args

    def start(self, wait=True, wait_timeout=120, warm=True):
        model = config.MODELS_DIR / self.p.file
        if not model.exists():
            raise ServerError(f"artifact missing: {model} (run bench download)")
        self._cleanup_leaked_container()
        cmd = [
            "podman",
            "run",
            "-d",
            "--rm",
            "--name",
            self.name,
            "-p",
            f"{self.port}:8080",
            "-v",
            f"{config.MODELS_DIR}:/models:Z",
            "--device",
            "/dev/dri:/dev/dri",
        ]
        cmd += [
            config.IMAGE,
            "--model",
            f"/models/{self.p.file}",
            "--alias",
            self.p.alias,
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
            "-c",
            str(self.ctx),
            "-t",
            str(config.SERVER_THREADS),
            "-ngl",
            str(self.ngl),
            "--jinja",
        ]
        cmd += list(self.extra_args)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise ServerError(f"podman run failed: {r.stderr}")
        self.cid = r.stdout.strip()
        if wait:
            self._wait_ready(wait_timeout)
        if warm:
            self.warmup()

    def _wait_ready(self, timeout):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                with urllib.request.urlopen(self.url + "/health", timeout=3) as resp:
                    if resp.status == 200:
                        time.sleep(1.5)  # allow slot initialization
                        return True
            except Exception:
                time.sleep(0.8)
        raise ServerError(f"server {self.name} not ready in {timeout}s")

    def warmup(self, timeout=180):
        """Force the gate warm: absorb lazy shader/pipeline compilation and
        first-slot init off the evaluated requests. Best-effort; a warmup
        failure does not fail the run (the next real request just pays it).
        """
        prompts = ["hi", "Say ok."]
        for prompt in prompts:
            t0 = time.time()
            try:
                msg = {"role": "user", "content": prompt}
                self.chat([msg], temperature=0.0, max_tokens=4)
            except Exception:
                continue
            self.warm_s = round(time.time() - t0, 3)
            return True
        self.warm_s = None
        return False

    def stop(self):
        subprocess.run(["podman", "rm", "-f", self.name], capture_output=True, text=True)

    def _cleanup_leaked_container(self):
        # a killed runner can leave the container behind; never reuse the name
        subprocess.run(["podman", "rm", "-f", self.name], capture_output=True, text=True)

    # ---- wire client ----
    def chat(self, messages, temperature=None, max_tokens=None, stop=None):
        gen = dict(config.GEN)
        if temperature is not None:
            gen["temperature"] = temperature
        if max_tokens is not None:
            gen["max_tokens"] = max_tokens
        body = {
            "model": self.p.alias,
            "messages": messages,
            "temperature": gen["temperature"],
            "max_tokens": gen["max_tokens"],
        }
        if stop:
            body["stop"] = stop
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            self.url + "/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                out = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:800]
            raise ServerError(f"wire 400/HTTP {e.code}: {body}")
        elapsed = time.time() - t0
        choice = out["choices"][0]
        msg = choice.get("message", {})
        content = msg.get("content", "") or ""
        reasoning = msg.get("reasoning_content", "") or ""
        finish_reason = choice.get("finish_reason", "") or ""
        truncated = finish_reason == "length"
        usage = out.get("usage", {})
        return {
            "content": content,
            "reasoning": reasoning,
            "finish_reason": finish_reason,
            "truncated": truncated,
            "latency_s": round(elapsed, 3),
            "tokens_in": usage.get("prompt_tokens"),
            "tokens_out": usage.get("completion_tokens"),
        }

    def finish_reason_probe(self, atomic=False):
        """Return current finish stats for latency/truncation evidence."""
        try:
            with urllib.request.urlopen(self.url + "/health", timeout=3) as _r:
                return {"healthy": True}
        except Exception as e:
            return {"healthy": False, "error": str(e)}


_AGE = 0


def _free_port():
    global _AGE
    _AGE += 1
    return config.SERVE_PORT_BASE + _AGE


def chat_on(
    participant_key,
    context_fn,
    tasks,
    temperature=None,
    max_tokens=None,
    stop=None,
    per_task_gen=None,
):
    """Run an ordered list of chat messages per task against one server.

    context_fn(task) -> list of msgs. Returns list of dict results aligned
    with tasks.
    """
    from .participants import PARTICIPANTS

    server = ModelServer(PARTICIPANTS[participant_key])
    server.start()
    try:
        results = []
        for task in tasks:
            msgs = context_fn(task)
            temp = per_task_gen(task, "temperature") if per_task_gen else temperature
            maxt = per_task_gen(task, "max_tokens") if per_task_gen else max_tokens
            results.append(server.chat(msgs, temperature=temp, max_tokens=maxt, stop=stop))
        return results
    finally:
        server.stop()
