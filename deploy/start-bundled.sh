#!/usr/bin/env bash
# start-bundled.sh — launch the full vefr bundled-brain stack
#
# Starts all 4 llama.cpp model servers + the vefr engine.
# Designed for the bundled deployment where everything runs on one host.
#
# Usage:
#   ./deploy/start-bundled.sh [--data-dir PATH]
#
# Env overrides (all optional):
#   MODELS_DIR     - directory containing .gguf model files
#                    (default: ./models)
#   ENGINE_DIR     - path to the vefr checkout
#                    (default: auto-detect from script location)
#   VEFR_PORT      - engine listen port
#                    (default: 8820)
#   PARALLEL       - max parallel model loads (default: 2)

set -euo pipefail

# --- resolve paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_DIR="${ENGINE_DIR:-$(dirname "$SCRIPT_DIR")}"
MODELS_DIR="${MODELS_DIR:-$ENGINE_DIR/models}"
VEFR_PORT="${VEFR_PORT:-8820}"
PARALLEL="${PARALLEL:-2}"
LOG_DIR="${LOG_DIR:-/tmp/vefr}"

mkdir -p "$LOG_DIR"

# --- model fleet (port → role → model file) ---
declare -A MODEL_ROLES=(
    [8083]="spark:Qwen3-0.6B-Instruct"
    [8084]="storyteller:Qwen3-1.7B"
    [8085]="vision:SmolVLM2-500M-Instruct"
    [8086]="embeddings:bge-m3"
)

PORTS=(8083 8084 8085 8086)
PIDS=()

# --- cleanup on exit ---
cleanup() {
    echo ""
    echo "⏹  Shutting down model servers..."
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    wait 2>/dev/null || true
    echo "✓  All servers stopped."
}
trap cleanup EXIT INT TERM

# --- find model files ---
find_model() {
    local model_pattern="$1"
    # Try exact name first, then glob for GGUF
    local found
    found=$(find "$MODELS_DIR" -maxdepth 2 -name "*.gguf" 2>/dev/null | grep -i "$model_pattern" | head -1)
    if [[ -n "$found" ]]; then
        echo "$found"
        return 0
    fi
    echo ""
    return 1
}

# --- health check ---
wait_healthy() {
    local port="$1"
    local role="$2"
    local max_wait=120
    local elapsed=0

    echo -n "  ⏳ $role (:$port) loading..."
    while (( elapsed < max_wait )); do
        if curl -sf "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
            echo " ✓ healthy (${elapsed}s)"
            return 0
        fi
        # Also try the completions endpoint (some llama.cpp builds)
        if curl -sf "http://127.0.0.1:$port/v1/models" >/dev/null 2>&1; then
            echo " ✓ responding (${elapsed}s)"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    echo " ✗ TIMEOUT after ${max_wait}s"
    return 1
}

# --- banner ---
echo "╔══════════════════════════════════════════════╗"
echo "║  vefr bundled brain — model fleet launcher   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Models dir:  $MODELS_DIR"
echo "Engine dir:  $ENGINE_DIR"
echo "Log dir:     $LOG_DIR"
echo ""

# --- verify models exist ---
echo "🔍 Checking model files..."
MISSING=0
for port in "${PORTS[@]}"; do
    IFS=':' read -r role model_pattern <<< "${MODEL_ROLES[$port]}"
    model_file=$(find_model "$model_pattern")
    if [[ -z "$model_file" ]]; then
        echo "  ❌ $role ($model_pattern) — not found in $MODELS_DIR"
        MISSING=1
    else
        echo "  ✅ $role → $(basename "$model_file")"
    fi
done

if (( MISSING )); then
    echo ""
    echo "⚠️  Some models missing. Server will start but those roles won't be available."
    echo "   Place .gguf files in: $MODELS_DIR"
    echo ""
fi

# --- start llama.cpp servers ---
echo ""
echo "🚀 Starting model servers (max $PARALLEL concurrent)..."

running=0
for port in "${PORTS[@]}"; do
    IFS=':' read -r role model_pattern <<< "${MODEL_ROLES[$port]}"
    model_file=$(find_model "$model_pattern")

    if [[ -z "$model_file" ]]; then
        echo "  ⏭  $role — skipped (model not found)"
        continue
    fi

    log_file="$LOG_DIR/llama-${role}.log"

    echo "  🔧 $role → :$port ($(basename "$model_file"))"
    llama-server \
        --model "$model_file" \
        --port "$port" \
        --host 127.0.0.1 \
        --ctx-size 4096 \
        --n-predict -1 \
        --log-disable \
        > "$log_file" 2>&1 &

    PIDS+=($!)
    running=$((running + 1))

    # Simple parallel throttle
    if (( running >= PARALLEL )); then
        wait "${PIDS[0]}" 2>/dev/null || true
        PIDS=("${PIDS[@]:1}")
        running=$((running - 1))
    fi
done

echo ""
echo "🏥 Waiting for health checks..."
HEALTHY=0
UNHEALTHY=0
for port in "${PORTS[@]}"; do
    IFS=':' read -r role model_pattern <<< "${MODEL_ROLES[$port]}"
    if wait_healthy "$port" "$role"; then
        HEALTHY=$((HEALTHY + 1))
    else
        UNHEALTHY=$((UNHEALTHY + 1))
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Model fleet: $HEALTHY healthy, $UNHEALTHY failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# --- start the engine ---
echo ""
echo "⚔️  Starting vefr engine on :$VEFR_PORT ..."

export VEFR_HOME="${VEFR_HOME:-$ENGINE_DIR}"
export VEFR_WORLD="${VEFR_WORLD:-sample-world}"
export VEFR_LLAMACPP_URL="http://127.0.0.1:8084"
export VEFR_MODEL="qwen3-1.7b"
export VEFR_KEEP_ALIVE="1m"
export VEFR_SPARK_URL="http://127.0.0.1:8083"
export VEFR_VISION_URL="http://127.0.0.1:8085"
export VEFR_EMBED_URL="http://127.0.0.1:8086"

exec uv run uvicorn vefr.main:app \
    --app-dir "$ENGINE_DIR/src" \
    --host 127.0.0.1 \
    --port "$VEFR_PORT"
