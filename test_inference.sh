#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHECKPOINT="${CHECKPOINT_PATH:-/mnt/d/sc/transcriptformer/checkpoints/tf_metazoa}"
DATA_FILE="${DATA_FILE:-$ROOT/test/data/chicken_val.h5ad}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/inference_results}"
OUTPUT_FILENAME="${OUTPUT_FILENAME:-embeddings.h5ad}"
BATCH_SIZE="${BATCH_SIZE:-1}"
PRECISION="${PRECISION:-16-mixed}"
DEVICE="${DEVICE:-auto}"
NUM_GPUS="${NUM_GPUS:-1}"
DISABLE_COMPILE="${DISABLE_COMPILE:-1}"

COMPILE_FLAGS=()
if [[ "$DISABLE_COMPILE" == "1" ]]; then
    COMPILE_FLAGS+=(--disable-compile-block-mask)
fi

if [[ ! -d "$CHECKPOINT" && "$CHECKPOINT" != /* ]]; then
    for candidate in "$PWD/$CHECKPOINT" "$ROOT/$CHECKPOINT"; do
        if [[ -d "$candidate" ]]; then
            CHECKPOINT="$candidate"
            break
        fi
    done
fi

if [[ ! -d "$CHECKPOINT" ]]; then
    echo "ERROR: checkpoint directory not found: $CHECKPOINT" >&2
    echo "Searched as given and under: $PWD, $ROOT" >&2
    echo "If you are testing the fine-tuned model, run 'bash test_finetune.sh' first." >&2
    echo "Otherwise set CHECKPOINT_PATH=/mnt/d/sc/transcriptformer/checkpoints/tf_metazoa" >&2
    exit 1
fi

if [[ ! -f "$DATA_FILE" ]]; then
    echo "ERROR: input H5AD file not found: $DATA_FILE" >&2
    exit 1
fi

echo "TranscriptFormer inference"
echo "  checkpoint : $CHECKPOINT"
echo "  data       : $DATA_FILE"
echo "  output     : $OUTPUT_DIR/$OUTPUT_FILENAME"
echo "  batch-size : $BATCH_SIZE"
echo "  precision  : $PRECISION"
echo "  device     : $DEVICE"
echo "  compile    : $([ "$DISABLE_COMPILE" == "1" ] && echo disabled || echo enabled)"
echo

"$ROOT/.venv/bin/transcriptformer" inference \
    --checkpoint-path "$CHECKPOINT" \
    --data-file "$DATA_FILE" \
    --output-path "$OUTPUT_DIR" \
    --output-filename "$OUTPUT_FILENAME" \
    --batch-size "$BATCH_SIZE" \
    --precision "$PRECISION" \
    --device "$DEVICE" \
    --num-gpus "$NUM_GPUS" \
    "${COMPILE_FLAGS[@]}"

echo
echo "Inference complete -> $OUTPUT_DIR/$OUTPUT_FILENAME"
