# ── vefr: a rumor engine for playable worlds ──────────────────
# Bundled brain edition — ships with llama.cpp + 3 small models.
# `podman run vefr` = fully playable game, no external LLM setup.
#
# Override to external brain:
#   VEFR_LLAMACPP_URL=http://host.lan:8084 VEFR_MODEL=qwen3-1.7b podman run ...
# ──────────────────────────────────────────────────────────────

FROM python:3.12-slim AS engine
WORKDIR /app
ENV VEFR_HOME=/app \
    VEFR_VAULT=/app/data/vault.json \
    VEFR_JOURNAL=/app/data/journal.json

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY web ./web
COPY worlds ./worlds-template

RUN mkdir -p /app/worlds /app/data
VOLUME ["/app/worlds-template", "/app/worlds", "/app/data"]

# ── Bundled brain: llama.cpp + model fleet ────────────────────
FROM engine AS brain

# Install llama.cpp pre-built binary (CPU, AVX2)
RUN arch=$(uname -m) && \
    if [ "$arch" = "x86_64" ]; then arch="x86_64"; elif [ "$arch" = "aarch64" ]; then arch="arm64"; fi && \
    curl -sSL "https://github.com/ggml-org/llama.cpp/releases/download/b5530/llama.cpp-b5530-linux-${arch}-avx2.tar.gz" \
    | tar xz -C /usr/local --strip-components=1 bin/llama-server && \
    llama-server --version || echo "llama-server installed"

# Download the model fleet (~2.2GB total)
RUN mkdir -p /app/models && \
    curl -sSL "https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/main/qwen3-0.6b-q4_k_m.gguf" \
      -o /app/models/spark.gguf && \
    curl -sSL "https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/main/qwen3-1.7b-q4_k_m.gguf" \
      -o /app/models/storyteller.gguf && \
    curl -sSL "https://huggingface.co/nicepkg/bge-m3-gguf/resolve/main/bge-m3-Q8_0.gguf" \
      -o /app/models/embeddings.gguf && \
    ls -lh /app/models/

# Entrypoint: start bundled brain + engine
COPY deploy/start-bundled.sh /app/start-bundled.sh
RUN chmod +x /app/start-bundled.sh

# Non-root user
RUN useradd --system --no-create-home --shell /usr/sbin/nologin vefr \
    && chown -R vefr:vefr /app/data /app/worlds /app/models
USER vefr

# Bundled brain defaults (override with env vars for external brain)
ENV VEFR_LLAMACPP_URL=http://127.0.0.1:8084 \
    VEFR_MODEL=qwen3-1.7b \
    VEFR_SPARK_URL=http://127.0.0.1:8083 \
    VEFR_EMBED_URL=http://127.0.0.1:8086 \
    VEFR_BUNDLED_BRAIN=1

ARG ENGINE_SHA=unknown
LABEL vefr.engine_sha=${ENGINE_SHA} \
      vefr.bundled_brain=1 \
      vefr.models="qwen3-0.6b,qwen3-1.7b,bge-m3"

CMD ["/app/start-bundled.sh"]
