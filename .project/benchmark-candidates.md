# VEFR Small-Model Benchmark — Candidate Research

**Date**: 2026-09-12
**Current large reference**: Qwen3.8-27B IQ4_XS (already installed)
**Historical data**: Spark benchmark 2026-09-06 (Phi-4-mini 100/100, Qwen3.5-0.8B 80.3/100)

## Current Local Models

| Model | Params | Quant | Size | Status |
|-------|--------|-------|------|--------|
| Qwen3.8-27B | 27.3B | IQ4_XS | 15.6 GB | INSTALLED (port 8081) |
| K2-Horizon-MoVA-36B-A4B | 36B (4B active) | Q6_K | 30.8 GB | INSTALLED (not running) |
| bge-m3 | 567M | Q8_0 | 635 MB | INSTALLED (embedding, not generative) |

## Candidate Table

| Model | Params | Arch | Context | License | GGUF Available | llama.cpp Compat | Quant Size (est) | Reason to Test |
|-------|--------|------|---------|---------|----------------|------------------|------------------|----------------|
| Qwen3.5-0.8B | 0.8B | Qwen | 128K | Apache 2.0 | Yes (unsloth) | Yes | ~1 GB | Smallest serious candidate; historical 80.3/100 |
| Qwen3.5-2B | 2B | Qwen | 128K | Apache 2.0 | Yes (unsloth) | Yes | ~2 GB | Intermediate size, same family as 0.8B |
| Gemma 3 1B | 1B | Gemma | 32K | Gemma ToS | Yes (unsloth) | Yes | ~0.7 GB | Smallest viable; different architecture |
| Llama 3.2 1B | 1B | Llama | 128K | Llama 3.2 | Yes (unsloth) | Yes | ~0.7 GB | Meta's smallest; different training |
| Llama 3.2 3B | 3B | Llama | 128K | Llama 3.2 | Yes (unsloth) | Yes | ~2 GB | Strong 3B workhorse; tool calling |
| Ministral-3-3B | 3.4B | Mistral | 256K | Apache 2.0 | Yes | Yes | ~2 GB | Clean Apache; European languages |
| Phi-4-mini-instruct | 3.8B | Phi | 16K | MIT | Yes (unsloth) | Yes | ~2.2 GB | Historical 100/100; reasoning |
| Gemma 3 4B | 4B | Gemma | 128K | Gemma ToS | Yes (unsloth) | Yes | ~2.5 GB | Upper-small baseline; multimodal |
| SmolLM2 1.7B | 1.7B | - | 8K | Apache 2.0 | Yes (unsloth) | Yes | ~1.1 GB | Fast; different training data |
| Qwen3.5-4B | 4B | Qwen | 256K | Apache 2.0 | Yes (unsloth) | Yes | ~2.5 GB | Multimodal; newer than 3.5-0.8B |

## Rejected Candidates

| Model | Reason |
|-------|--------|
| Gemma 4 E2B/E4B | Superseded by Gemma 3 for our use; Gemma 4 is newer but we want proven |
| Qwen 3 1.7B/Qwen 3 0.6B | Superseded by Qwen 3.5 line |
| Qwen 3 4B | Superseded by Qwen 3.5 4B |
| Phi-4 (14B) | Too large for small-model contest; Phi-4-mini covers the architecture |
| DeepSeek-R1 Distill | License unclear for VEFR's use case |
| Falcon 3 | Less community support; harder to run reproducibly |

## Selected Candidates (6 models)

```text
~0.8B   → Qwen3.5-0.8B       (Apache 2.0, same family as our 27B reference)
~1B     → Gemma 3 1B          (different architecture, smallest viable)
~2B     → Qwen3.5-2B          (intermediate, same family as 0.8B)
~3B     → Llama 3.2 3B        (different architecture, strong 3B workhorse)
~3B     → Ministral-3-3B      (Apache 2.0, alternate architecture)
~4B     → Phi-4-mini-instruct (historical 100/100, reasoning)
```

**Total download size**: ~8-10 GB (manageable)
**Architecture diversity**: Qwen (2), Gemma (1), Llama (1), Mistral (1), Phi (1)
**License coverage**: Apache 2.0 (3), MIT (1), Gemma ToS (1), Llama 3.2 (1)

## Next Steps

1. Download selected GGUFs
2. Verify llama.cpp load
3. Run qualification battery
4. Run full VEFR benchmark
5. Profile each model
6. Build routing ladder