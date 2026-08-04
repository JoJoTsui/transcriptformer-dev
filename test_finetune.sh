#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHECKPOINT="${CHECKPOINT_PATH:-/mnt/d/sc/transcriptformer/checkpoints/tf_metazoa}"
DATA_FILE="${DATA_FILE:-$ROOT/test/data/chicken_val.h5ad}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/checkpoints/tf_metazoa_finetuned}"
BATCH_SIZE="${BATCH_SIZE:-1}"
LR="${LR:-1e-5}"
EPOCHS="${EPOCHS:-1}"
MAX_STEPS="${MAX_STEPS:-2}"
DEVICE="${DEVICE:-auto}"
PRECISION="${PRECISION:-16-mixed}"

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
    exit 1
fi

if [[ ! -f "$DATA_FILE" ]]; then
    echo "ERROR: input H5AD file not found: $DATA_FILE" >&2
    exit 1
fi

echo "TranscriptFormer finetune smoke test"
echo "  checkpoint : $CHECKPOINT"
echo "  data       : $DATA_FILE"
echo "  output     : $OUTPUT_DIR"
echo "  batch-size : $BATCH_SIZE"
echo "  lr         : $LR"
echo "  epochs     : $EPOCHS"
echo "  max-steps  : $MAX_STEPS"
echo "  device     : $DEVICE"
echo "  precision  : $PRECISION"
echo

"$ROOT/.venv/bin/python" "$ROOT/scripts/finetune.py" \
    --checkpoint-path "$CHECKPOINT" \
    --data-file "$DATA_FILE" \
    --output-path "$OUTPUT_DIR" \
    --batch-size "$BATCH_SIZE" \
    --lr "$LR" \
    --epochs "$EPOCHS" \
    --max-steps "$MAX_STEPS" \
    --device "$DEVICE" \
    --precision "$PRECISION"

echo
echo "Finetune smoke test complete -> $OUTPUT_DIR"
