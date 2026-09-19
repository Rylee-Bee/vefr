"""Participant registry.

A participant is the complete operational unit: model artifact + quant +
canonical runtime/template configuration. A derived model (fine-tune) is a
distinct participant and carries its lineage. Do not transfer a derivative's
capability back to its base model.

`gguf_file` must exist in OLY_MODELS_DIR. `alias` is the -alias given to the
llama-server so the wire model name stays stable.
"""

from .config import weight_class


class Participant:
    def __init__(self, key, family, params_b, quant, file, alias=None,
                 template="jinja", class_=None, lineage=None, kind="base",
                 tags=()):
        self.key = key
        self.family = family
        self.params_b = params_b
        self.quant = quant
        self.file = file
        self.alias = alias or key
        self.template = template
        self.class_ = class_ or weight_class(params_b)
        self.lineage = lineage  # for derivatives: (base_model, note)
        self.kind = kind  # base | derivative
        self.tags = tuple(tags)

    def describe(self):
        d = f"{self.family} {self.params_b}B {self.quant}"
        if self.kind == "derivative":
            d += f" (derivative of {self.lineage[0]})"
        return d


P = [
    # ---- FEATHERWEIGHT / BANTAM (<1B) ----
    Participant("qwen2.5-0.5b", "Qwen2.5", 0.49, "Q4_K_M",
                "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf", class_="BANTAMWEIGHT"),
    Participant("qwen3-0.6b", "Qwen3", 0.6, "Q4_K_M",
                "Qwen3-0.6B-Q4_K_M.gguf", class_="BANTAMWEIGHT"),
    Participant("qwen3.5-0.8b", "Qwen3.5", 0.8, "Q4_K_M",
                "Qwen3.5-0.8B-Q4_K_M.gguf", class_="BANTAMWEIGHT"),
    Participant("smollm2-360m", "SmolLM2", 0.36, "Q8_0",
                "SmolLM2-360M-Q8_0.gguf", class_="FEATHERWEIGHT"),

    # ---- LIGHTWEIGHT (1-1.49B) ----
    Participant("gemma3-1b", "Gemma3", 1.0, "Q4_K_M",
                "Gemma-3-1B-Q4_K_M.gguf", class_="LIGHTWEIGHT"),
    Participant("llama3.2-1b", "Llama3.2", 1.0, "Q4_K_M",
                "Llama-3.2-1B-Q4_K_M.gguf", class_="LIGHTWEIGHT"),
    Participant("lfm2.5-1.2b", "LFM2.5", 1.2, "Q4_K_M",
                "LFM2.5-1.2B-Q4_K_M.gguf", class_="LIGHTWEIGHT"),
    Participant("xlam-2-1b-fc-r", "xLAM2", 1.5, "Q4_K_M",
                "xLAM-2-1b-fc-r-Q4_K_M.gguf", class_="LIGHTWEIGHT",
                kind="derivative", lineage=("Qwen2.5-base", "function-calling SFT (APIGen-MT, BFCL, tau-bench)")),

    # ---- WELTER (1.5-2.49B) ----
    Participant("qwen2.5-1.5b", "Qwen2.5", 1.5, "Q4_K_M",
                "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf", class_="WELTERWEIGHT",
                tags=("current-default",)),
    Participant("qwen3-1.7b", "Qwen3", 1.7, "Q4_K_M",
                "Qwen3-1.7B-Q4_K_M.gguf", class_="WELTERWEIGHT"),
    Participant("qwen3.5-2b", "Qwen3.5", 2.0, "Q4_K_M",
                "Qwen3.5-2B-Q4_K_M.gguf", class_="WELTERWEIGHT"),
    Participant("smollm2-1.7b", "SmolLM2", 1.7, "Q4_K_M",
                "SmolLM2-1.7B-Q4_K_M.gguf", class_="WELTERWEIGHT"),
    Participant("qwen2.5-hermes-1.5b", "Qwen2.5-Hermes", 1.5, "Q4_K_M",
                "Qwen2.5-Hermes-Instruct-1.5B-Q4_K_M.gguf", class_="WELTERWEIGHT",
                kind="derivative", lineage=("Qwen2.5-1.5B", "Hermes-style instruct fine-tune (koshuro)")),
    Participant("qwen2.5-1.5b-tools", "Qwen2.5-tools", 1.5, "Q4_K_M",
                "qwen2.5-1.5b-tool-use-reasoning.Q4_K_M.gguf", class_="WELTERWEIGHT",
                kind="derivative", lineage=("Qwen2.5-1.5B", "community tool-use/reasoning fine-tune (lineage unverified)")),

    # ---- MIDDLE (2.5-4B) ----
    Participant("qwen2.5-3b", "Qwen2.5", 3.0, "Q4_K_M",
                "Qwen2.5-3B-Instruct-Q4_K_M.gguf"),
    Participant("qwen3.5-4b", "Qwen3.5", 4.2, "Q4_K_M",
                "Qwen3.5-4B-Q4_K_M.gguf"),
    Participant("granite-4.1-3b", "Granite4.1", 3.0, "Q4_K_M",
                "Granite-4.1-3B-Q4_K_M.gguf", tags=("fallback",)),
    Participant("granite-4.2-3b", "Granite4.2", 3.0, "Q4_K_M",
                "granite-4.2-3b-Q4_K_M.gguf"),
    Participant("gemma3-4b", "Gemma3", 4.0, "Q4_K_M",
                "Gemma-3-4B-Q4_K_M.gguf"),
    Participant("lfm2.5-2.6b", "LFM2.5", 2.6, "Q4_K_M",
                "LFM2.5-2.6B-Q4_K_M.gguf"),
    Participant("llama3.2-3b", "Llama3.2", 3.0, "Q4_K_M",
                "Llama-3.2-3B-Q4_K_M.gguf"),
    Participant("ministral-3-3b", "Ministral3", 3.0, "Q4_K_M",
                "Ministral-3-3B-Q4_K_M.gguf"),
    Participant("phi-4-mini", "Phi4-mini", 3.8, "Q4_K_M",
                "Phi-4-mini-Q4_K_M.gguf"),
    Participant("phi-3.5-mini", "Phi3.5-mini", 3.8, "Q4_K_M",
                "Phi-3.5-mini-3.8B-Q4_K_M.gguf"),
    Participant("smollm3-3b", "SmolLM3", 3.0, "Q4_K_M",
                "SmolLM3-3B-Q4_K_M.gguf"),
    Participant("falcon3-3b", "Falcon3", 3.0, "Q4_K_M",
                "Falcon3-3B-Instruct-Q4_K_M.gguf"),
    Participant("stablelm-zephyr-3b", "StableLM", 3.0, "Q4_K_M",
                "StableLM-Zephyr-3B-Q4_K_M.gguf"),
]

PARTICIPANTS = {p.key: p for p in P}


def missing_files():
    from .config import MODELS_DIR
    return [(k, p.file) for k, p in PARTICIPANTS.items()
            if not (MODELS_DIR / p.file).exists()]


def list_participants():
    return P