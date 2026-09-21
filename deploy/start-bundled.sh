#!/bin/bash
# ── vefr bundled brain entrypoint ─────────────────────────────
# Starts 3 llama.cpp servers (spark, storyteller, embeddings)
# then the vefr engine. All inside one container.
#
# To use an external brain instead:
#   VEFR_LLAMACPP_URL=http://host.lan:8084 VEFR_MODEL=qwen3-1.7b \
#   VEFR_BUNDLED_BRAIN=0 /app/start-bundled.sh
# ──────────────────────────────────────────────────────────────
set -e

MODELS_DIR="/app/models"
LOG_PREFIX="[bundled-brain]"

# If bundled brain is disabled, just run the engine directly
if [ "${VEFR_BUNDLED_BRAIN:-1}" = "0" ]; then
    echo "$LOG_PREFIX Bundled brain disabled — using external endpoint: ${VEFR_LLAMACPP_URL:-not set}"
    exec uvicorn vefr.main:app --host 0.0.0.0 --port 8820 --app-dir /app/src
fi

echo "$LOG_PREFIX Starting bundled brain..."

# Start spark (Qwen3-0.6B) — interface translator
echo "$LOG_PREFIX  Spark (Qwen3-0.6B) → :8083"
llama-server \
    --model "$MODELS_DIR/spark.gguf" \
    --port 8083 --host 0.0.0.0 \
    --ctx-size 2048 --threads $(nproc) --parallel 1 \
    --log-disable 2>/dev/null &

# Start storyteller (Qwen3-1.7B) — narration
echo "$LOG_PREFIX  Storyteller (Qwen3-1.7B) → :8084"
llama-server \
    --model "$MODELS_DIR/storyteller.gguf" \
    --port 8084 --host 0.0.0.0 \
    --ctx-size 4096 --threads $(nproc) --parallel 1 \
    --log-disable 2>/dev/null &

# Start embeddings (bge-m3) — lore retrieval
echo "$LOG_PREFIX  Embeddings (bge-m3) → :8086"
llama-server \
    --model "$MODELS_DIR/embeddings.gguf" \
    --port 8086 --host 0.0.0.0 \
    --ctx-size 512 --threads $(nproc) --parallel 1 \
    --embedding --log-disable 2>/dev/null &

# Wait for models to load (check /health on each port)
echo "$LOG_PREFIX Waiting for models to load..."
for port in 8083 8084 8086; do
    for i in $(seq 1 60); do
        if curl -sf "http://127.0.0.1:$port/health" > /dev/null 2>&1; then
            echo "$LOG_PREFIX  :$port ready"
            break
        fi
        if [ $i -eq 60 ]; then
            echo "$LOG_PREFIX  :$port failed to start (continuing without it)"
        fi
        sleep 1
    done
done

echo "$LOG_PREFIX All models loaded. Starting vefr engine..."

# Start the engine in foreground
exec uvicorn vefr.main:app --host 0.0.0.0 --port 8820 --app-dir /app/src
