"""Voice suite: listening (speech to text) and speaking (text to speech).

Listening: 30 LibriSpeech clean clips (CC BY 4.0), word error rate (WER)
and real-time factor (RTF: seconds of compute per second of audio; below 1
is faster than real time). Speaking: 10 plain studio sentences per voice,
RTF, and intelligibility = WER when a fixed judge (Whisper small.en) listens.
Naturalness is not measured here; listen to the saved WAVs.

Runs in its own venv (onnxruntime, kokoro-onnx, kittentts, piper-tts,
useful-moonshine-onnx, faster-whisper, soundfile, jiwer, pyarrow); model
files live in VOICE_DATA (default ~/.cache/vefr-senses/data).

    VOICE_DATA=... <venv>/bin/python -m bench.senses.voice [<key> ...]

Kitten needs the official wheel (github.com/KittenML/KittenTTS releases,
0.8.1); PyPI's `kittentts` is an old 0.1 build that can't load 0.8 models.
"""
import io
import json
import os
import re
import time
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("VOICE_DATA", Path.home() / ".cache" / "vefr-senses" / "data"))
THREADS = int(os.environ.get("OLY_THREADS", "4"))
N_CLIPS = 30

SENTENCES = [
    "Your game is saved. You can close the studio now.",
    "Three new pictures are ready in the gallery.",
    "Press play to try the newest build.",
    "The map needs one more room before it can be shared.",
    "Open the chest to see what you found.",
    "This book was added to your library on Saturday.",
    "The delve has twelve floors, and each one is remembered.",
    "Pack the lantern, the rope and two apples into the satchel.",
    "Would you like to rename this world?",
    "Nothing is waiting for review. Take a break!",
]


def norm(t):
    t = t.lower().replace("mister", "mr")
    return " ".join(re.sub(r"[^a-z0-9' ]", " ", t).split())


def wer(refs, hyps):
    import jiwer
    return round(jiwer.wer([norm(r) for r in refs], [norm(h) or "∅" for h in hyps]), 3)


# ---- listening ----------------------------------------------------------
def clips(tmp):
    import pyarrow.parquet as pq
    rows = pq.read_table(DATA / "libri-dummy.parquet").slice(0, N_CLIPS).to_pylist()
    out = []
    for r in rows:
        a, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32")
        p = tmp / f"{r['id']}.wav"
        sf.write(p, a, sr)
        out.append((p, r["text"], len(a) / sr))
    return out


def whisper(size):
    from faster_whisper import WhisperModel
    m = WhisperModel(size, device="cpu", compute_type="int8", cpu_threads=THREADS)
    return lambda p: "".join(s.text for s in m.transcribe(str(p), beam_size=1, language="en")[0])


def moonshine(name):
    import moonshine_onnx
    moonshine_onnx.transcribe(str(next(iter((DATA / "_tmp").glob("*.wav")))), name)  # load once
    return lambda p: " ".join(moonshine_onnx.transcribe(str(p), name))


LISTENERS = [
    ("moonshine-tiny", 27, lambda: moonshine("moonshine/tiny"), "MIT"),
    ("whisper-tiny.en", 39, lambda: whisper("tiny.en"), "MIT"),
    ("moonshine-base", 61, lambda: moonshine("moonshine/base"), "MIT"),
    ("whisper-base.en", 74, lambda: whisper("base.en"), "MIT"),
    ("whisper-small.en", 244, lambda: whisper("small.en"), "MIT"),
]


# ---- speaking -----------------------------------------------------------
def kitten(repo):
    from kittentts import KittenTTS
    m = KittenTTS(repo)
    voice = (getattr(m, "available_voices", None) or [None])[0]
    return lambda t: (np.asarray(m.generate(t, voice=voice) if voice else m.generate(t), dtype="float32"), 24000)


def kokoro():
    from kokoro_onnx import Kokoro
    k = Kokoro(str(DATA / "kokoro-v1.0.int8.onnx"), str(DATA / "voices-v1.0.bin"))
    return lambda t: k.create(t, voice="af_heart", speed=1.0, lang="en-us")


def piper(name):
    from piper import PiperVoice
    v = PiperVoice.load(str(DATA / f"{name}.onnx"))
    def say(t):
        chunks = list(v.synthesize(t))
        return np.concatenate([c.audio_float_array for c in chunks]).astype("float32"), chunks[0].sample_rate
    return say


SPEAKERS = [
    ("kitten-nano-0.8-int8", 15, lambda: kitten("KittenML/kitten-tts-nano-0.8-int8"), "Apache-2.0"),
    ("kitten-micro-0.8", 40, lambda: kitten("KittenML/kitten-tts-micro-0.8"), "Apache-2.0"),
    ("piper-lessac-low", 63, lambda: piper("en_US-lessac-low"), "MIT (voice: see card)"),
    ("piper-lessac-medium", 63, lambda: piper("en_US-lessac-medium"), "MIT (voice: see card)"),
    ("kitten-mini-0.8", 80, lambda: kitten("KittenML/kitten-tts-mini-0.8"), "Apache-2.0"),
    ("kokoro-82m-int8", 82, kokoro, "Apache-2.0"),
]


def run(only=None):
    rid = time.strftime("%Y%m%dT%H%M%S")
    out = ROOT / "bench" / "runs" / "senses" / "voice" / rid
    out.mkdir(parents=True, exist_ok=True)
    tmp = DATA / "_tmp"
    tmp.mkdir(exist_ok=True)
    cl = clips(tmp)
    audio_s = sum(c[2] for c in cl)
    listen = []
    for key, mb, make, lic in LISTENERS:
        if only and key not in only:
            continue
        rec = {"model": key, "size_mb": mb, "licence": lic}
        try:
            f = make()
            t0 = time.time()
            hyps = [f(p) for p, _, _ in cl]
            rec.update(wer=wer([c[1] for c in cl], hyps), rtf=round((time.time() - t0) / audio_s, 3),
                       samples=[{"ref": c[1], "hyp": h} for c, h in list(zip(cl, hyps))[:5]])
        except Exception as e:
            rec["error"] = repr(e)[:300]
        listen.append(rec)
        print(f"listen {key:<22} WER {rec.get('wer')} RTF {rec.get('rtf')} {rec.get('error', '')}", flush=True)
    judge = whisper("small.en")
    speak = []
    for key, mb, make, lic in SPEAKERS:
        if only and key not in only:
            continue
        rec = {"model": key, "size_mb": mb, "licence": lic}
        try:
            f = make()
            gen = spoken = 0.0
            hyps = []
            for i, s in enumerate(SENTENCES):
                t0 = time.time()
                a, sr = f(s)
                gen += time.time() - t0
                spoken += len(a) / sr
                p = out / f"{key}-{i:02d}.wav"
                sf.write(p, a, sr)
                hyps.append(judge(p))
            rec.update(wer=wer(SENTENCES, hyps), rtf=round(gen / spoken, 3),
                       heard=[{"said": s, "heard": h} for s, h in zip(SENTENCES, hyps)])
        except Exception as e:
            rec["error"] = repr(e)[:300]
        speak.append(rec)
        print(f"speak  {key:<22} WER {rec.get('wer')} RTF {rec.get('rtf')} {rec.get('error', '')}", flush=True)
    (out / "results.json").write_text(json.dumps({"threads": THREADS, "clips": N_CLIPS, "audio_s": round(audio_s, 1),
                                                  "judge": "whisper-small.en", "listen": listen, "speak": speak}, indent=1))
    return out


if __name__ == "__main__":
    import sys
    print("evidence:", run(sys.argv[1:]))
