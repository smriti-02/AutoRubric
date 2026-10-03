#!/usr/bin/env bash
set -euo pipefail

MODEL_DIR="${1:-models/roberta-large-autorubric}"
mkdir -p "$MODEL_DIR"

echo "=== Downloading AutoRubric Fine-Tuned Model Weights ==="
echo "Target directory: $MODEL_DIR"

if command -v huggingface-cli &> /dev/null; then
    echo "Downloading from Hugging Face Hub..."
    huggingface-cli download autorubric/roberta-large-entsbank --local-dir "$MODEL_DIR"
else
    echo "huggingface-cli not found. Please install huggingface_hub or copy checkpoint directly from Google Drive."
fi

echo "Model setup complete."
